import sys
import signal
import argparse
import copy
from threading import Thread, Event
from utils.testyaml import generate_test_yaml
from utils.utils import load_scenario
from utils.storyboard import (
    MqttConfig, ClientConfig, ScenarioConfig,
    Mode, LogConfig, CER
)
from utils.timesim import TimeSim

from simulator import elvsim, bossim, rpfsim, robsim
# from simulator import robsim_fast as robsim
from mqtt_communication_module.data_model import set_run_parameters
from utils.msglog import generate_runtime_report
from database.user_management import db

from mqtt_communication_module.com_traffic import (
    ConnectionMonitor,
    MQTTBrokerMonitor
)
from mqtt_communication_module.cpu_monitor import MonitorCPU
from mqtt_communication_module.load_scalability import enable_load_scalability


class Manager:

    def __init__(self, duration=120, scenario_file=None):
        self.duration = duration
        self.scenario_file = scenario_file

        self.sim_speed = 1  # default
        self.time = TimeSim(self.sim_speed)
        self.task = []
        self.broker = MqttConfig.MQTT_BROKER
        self.port = MqttConfig.MQTT_PORT
        self.mqtts_listen = MqttConfig.MQTTS_PORT
        self.runtime_log_file = LogConfig.RUNTIME_REPORT
        self.mqtt_client = None
        self.message_handler = None
        self.running = False
        self.stop_event = Event()

        self.Rob = None
        self.Tasks = None
        self.ELV = None
        self.ATT_scenario = None
        self.target = None
        self.selected_protocol = None
        self.DosAtt = False

        self.server_thread = None
        self.running = False
        self.log_callback = None

        self.current_mode = Mode.DEFAULT
        self.bos_mode = Mode.Normal
        self.rpf_mode = Mode.Normal

        # BAC
        self.rpf_username = CER.U_RPF
        self.rpf_pw = CER.PW_RPF
        self.bos_username = CER.U_BOS
        self.bos_pw = CER.PW_BOS
        self.use_encryption = False  # True/False
        self.use_allowlist = False  # True/False

        self.init_database()

        # loaded later
        self.Rob = None
        self.Tasks = None
        self.ELV = None
        self.selected_protocol = None


    def init_database(self):
        db.init_db(self.use_encryption)
        db.print_users()

    # =====================================================
    # setup simulators
    # =====================================================

    def setup_simulators(self):
        if self.Rob is None and self.Tasks is None and self.ELV is None and self.ATT_scenario is None and self.target is None and self.selected_protocol is None:
            Sim_Speed, PROTOCOL, Rob, TASKS, ELV, SCENARIO_NAME, TARGET, _ = load_scenario(
                self.scenario_file or ClientConfig.SCENARIO_FILE,
                ScenarioConfig.Sim_Speed,
                ScenarioConfig.PROTOCOL,
                ScenarioConfig.Service_Robots,
                ScenarioConfig.Tasks,
                ScenarioConfig.Elevators,
                ScenarioConfig.ATT_SCENARIO,
                ScenarioConfig.Service_Robot_Name,
                ScenarioConfig.Service_Robot_PRIORITY,
                time=self.time,

            )

        self.sim_speed = Sim_Speed
        self.Rob = Rob  # instance_list
        self.Tasks = TASKS
        self.ELV = ELV
        self.ATT_scenario = SCENARIO_NAME
        self.target = TARGET
        self.selected_protocol = PROTOCOL
        # self.use_encryption = encryption
        # self.time = TimeSim(self.sim_speed)
        self.time.time_scale = self.sim_speed

        # set port
        if self.selected_protocol == MqttConfig.MQTT:
            self.port = MqttConfig.MQTT_PORT
        elif self.selected_protocol == MqttConfig.MQTTS:
            self.port = MqttConfig.MQTTS_PORT


        enable_load_scalability(
            duration=self.duration,
            time_sim=self.time,
            log_file=LogConfig.FILE_LOAD_RUNTIME_REPORT
        )

        run_parameters = set_run_parameters(
            self.sim_speed,
            self.selected_protocol,
            self.Rob,
            self.ELV,
            self.Tasks,
            None,
            None
        )

        generate_runtime_report(
            self.runtime_log_file,
            run_parameters,
            self.use_encryption,
            self.use_allowlist
        )

        # =================================================
        # simulators
        # =================================================
        # topic
        elv_send_topic = [MqttConfig.TOPIC_ELV_DT, MqttConfig.TOPIC_E2D]  # Elv_dt/E2D
        elv_recv_topic = [MqttConfig.TOPIC_D2E]  # D2E
        bos_send_topic = [MqttConfig.TOPIC_D2E, MqttConfig.TOPIC_D2B,
                          MqttConfig.TOPIC_D2B_FORWARD_ELV]  # D2E/D2B/DF_elv_dt
        bos_recv_topic = [MqttConfig.TOPIC_ELV_DT, MqttConfig.TOPIC_E2D, MqttConfig.TOPIC_B2D]  # elv_dt/E2D/B2D
        rpf_send_topic = [MqttConfig.TOPIC_B2D, MqttConfig.TOPIC_B2R,
                          MqttConfig.TOPIC_B2R_FORWARD_ELV]  # B2D/B2R/RPF_F_elv_dt
        rpf_recv_topic = [MqttConfig.TOPIC_D2B, MqttConfig.TOPIC_R2B, MqttConfig.TOPIC_ROB_DT,
                          MqttConfig.TOPIC_D2B_FORWARD_ELV]  # D2B/R2B/rob_dt/Bos_F_elv_dtx
        rob_send_topic = [MqttConfig.TOPIC_R2B, MqttConfig.TOPIC_ROB_DT]  # R2B/rob_dt
        rob_recv_topic = [MqttConfig.TOPIC_B2R, MqttConfig.TOPIC_B2R_FORWARD_ELV]  # B2R/RPF_F_elv_dt

        # instance
        self.elv_sim = elvsim.ElevatorSimulator(elv_send_topic, elv_recv_topic, self.broker, self.port, self.ELV,
                                                self.time, self.use_allowlist)
        self.bos_sim = bossim.BosSimulator(bos_send_topic, bos_recv_topic, self.broker, self.port, self.time,
                                           self.bos_username, self.bos_pw, self.use_encryption, self.use_allowlist)
        self.rpf_sim = rpfsim.RpfSimulator(rpf_send_topic, rpf_recv_topic, self.broker, self.port, self.Tasks,
                                           self.time, self.rpf_username, self.rpf_pw, self.use_encryption,
                                           self.use_allowlist)
        self.rob_sim = robsim.RobotSimulator(rob_send_topic, rob_recv_topic, self.broker, self.port, self.Rob, self.ELV,
                                             self.time, self.use_allowlist)

        if self.ATT_scenario:
                try:
                    self.bos_mode, self.rpf_mode = switch_mode(self.ATT_scenario, self.target, self.selected_protocol,
                                                               self.use_encryption)
                except Exception as e:
                    print(f"[Manager] switch_mode raised exception: {e}. Falling back to Normal mode.")
                    # fallback
                    self.bos_mode, self.rpf_mode = Mode.Normal, Mode.Normal

                # ensure defaults
                self.bos_mode = self.bos_mode if self.bos_mode else Mode.Normal
                self.rpf_mode = self.rpf_mode if self.rpf_mode else Mode.Normal

                # set handler modes safely (check attribute exists)
                try:
                    if hasattr(self.bos_sim, "handler") and hasattr(self.bos_sim.handler, "set_mode"):
                        self.bos_sim.handler.set_mode(self.bos_mode)
                except Exception as e:
                    print(f"[Manager] Failed to set BOS mode: {e}")

                try:
                    if hasattr(self.rpf_sim, "handler") and hasattr(self.rpf_sim.handler, "set_mode"):
                        self.rpf_sim.handler.set_mode(self.rpf_mode)
                except Exception as e:
                    print(f"[Manager] Failed to set RPF mode: {e}")

        if self.ATT_scenario == 'DDOS':
            self.DosAtt = True

        self.stop_event = Event()



    # =====================================================
    # start
    # =====================================================

    def start_server(self):

        self.setup_simulators()

        # CPU monitor
        cpu = MonitorCPU(
            file_path=LogConfig.CPU_LOG,
            target_process_name="mosquitto",
            interval=1,
            time_sim=self.time
        )
        Thread(target=cpu.start_monitoring, daemon=True).start()

        # simulators
        Thread(target=self.elv_sim.start_simulation, args=(self.stop_event,), daemon=True).start()
        Thread(target=self.bos_sim.start_simulation, args=(self.stop_event,), daemon=True).start()
        Thread(target=self.rpf_sim.start_simulation, args=(self.stop_event,), daemon=True).start()
        Thread(target=self.rob_sim.start_simulation, args=(self.stop_event,), daemon=True).start()

        mqtt_monitor = MQTTBrokerMonitor(broker_address="localhost")
        mqtt_thread = Thread(target=mqtt_monitor.start_monitoring, daemon=True)
        mqtt_thread.start()

        print(f"Server running for {self.duration}s ...")

        self.time.sleep(self.duration)

        self.stop_server()


    # =====================================================
    # stop
    # =====================================================

    def stop_server(self):

        self.stop_event.set()

        self.elv_sim.stop_simulation()
        self.bos_sim.stop_simulation()
        self.rpf_sim.stop_simulation()
        self.rob_sim.stop_simulation()

        print("Server stopped")

if __name__ == "__main__":
    DEVICES = 1
    DURATION = 200
    # =====================================
    scenario_path = generate_test_yaml(DEVICES)

    print("==============================")
    print(f"robots   = {DEVICES}")
    print(f"duration = {DURATION}s")
    print("==============================\n")

    manager = Manager(
        duration=DURATION,
        scenario_file=scenario_path
    )

    manager.start_server()
