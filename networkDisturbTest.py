import sys
import signal
import argparse
from threading import Thread, Event
from utils.utils import load_scenario
from utils.storyboard import MqttConfig, ClientConfig, ScenarioConfig, Mode, LogConfig, CER
from utils.timesim import TimeSim
from simulator import elvsim, bossim, rpfsim, robsim
from mqtt_communication_module.data_model import set_run_parameters
from utils.msglog import generate_runtime_report
from security_attack_module.scene_switcher import switch_mode
from database.user_management import db
from security_attack_module.DDoS import DDOSAttackScenario
from mqtt_communication_module.com_traffic import ConnectionMonitor, MQTTBrokerMonitor
from mqtt_communication_module.cpu_monitor import MonitorCPU
from mqtt_communication_module.network_disturb import enable_network_disturbance, log_network_disturb_status



class Manager:
    def __init__(self):
        # create TimeSim instance
        self.sim_speed = 10  # default
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

    def init_database(self):
        db.init_db(self.use_encryption)
        db.print_users()

    def setup_simulators(self, external_timesim=None):
        if self.Rob is None and self.Tasks is None and self.ELV is None and self.ATT_scenario is None and self.target is None and self.selected_protocol is None:
            Sim_Speed, PROTOCOL, Rob, TASKS, ELV, SCENARIO_NAME, TARGET, _ = load_scenario(
                ClientConfig.SCENARIO_FILE,
                ScenarioConfig.Sim_Speed,
                ScenarioConfig.PROTOCOL,
                ScenarioConfig.Service_Robots,
                ScenarioConfig.Tasks,
                ScenarioConfig.Elevators,
                ScenarioConfig.ATT_SCENARIO,
                ScenarioConfig.Service_Robot_Name,
                ScenarioConfig.Service_Robot_PRIORITY,
                time=external_timesim if external_timesim else self.time,

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
            # self.time = external_timesim if external_timesim else TimeSim(self.sim_speed)

        # set port
        if self.selected_protocol == MqttConfig.MQTT:
            self.port = MqttConfig.MQTT_PORT
        elif self.selected_protocol == MqttConfig.MQTTS:
            self.port = MqttConfig.MQTTS_PORT

        run_parameters = set_run_parameters(self.sim_speed, self.selected_protocol, self.Rob, self.ELV, self.Tasks,
                                            self.ATT_scenario, self.target)
        generate_runtime_report(self.runtime_log_file, run_parameters, self.use_encryption, self.use_allowlist)

        # topic
        elv_send_topic = [MqttConfig.TOPIC_ELV_DT, MqttConfig.TOPIC_E2D]  # Elv_dt/E2D
        elv_recv_topic = [MqttConfig.TOPIC_D2E]  # D2E
        bos_send_topic = [MqttConfig.TOPIC_D2E, MqttConfig.TOPIC_D2B, MqttConfig.TOPIC_D2B_FORWARD_ELV]  # D2E/D2B/DF_elv_dt
        bos_recv_topic = [MqttConfig.TOPIC_ELV_DT, MqttConfig.TOPIC_E2D, MqttConfig.TOPIC_B2D]  # elv_dt/E2D/B2D
        rpf_send_topic = [MqttConfig.TOPIC_B2D, MqttConfig.TOPIC_B2R, MqttConfig.TOPIC_B2R_FORWARD_ELV]  # B2D/B2R/RPF_F_elv_dt
        rpf_recv_topic = [MqttConfig.TOPIC_D2B, MqttConfig.TOPIC_R2B, MqttConfig.TOPIC_ROB_DT, MqttConfig.TOPIC_D2B_FORWARD_ELV]  # D2B/R2B/rob_dt/Bos_F_elv_dtx
        rob_send_topic = [MqttConfig.TOPIC_R2B, MqttConfig.TOPIC_ROB_DT]  # R2B/rob_dt
        rob_recv_topic = [MqttConfig.TOPIC_B2R, MqttConfig.TOPIC_B2R_FORWARD_ELV]  # B2R/RPF_F_elv_dt


        # instance
        self.elv_sim = elvsim.ElevatorSimulator(elv_send_topic, elv_recv_topic, self.broker, self.port, self.ELV, self.time, self.use_allowlist)
        self.bos_sim = bossim.BosSimulator(bos_send_topic, bos_recv_topic, self.broker, self.port, self.time, self.bos_username, self.bos_pw, self.use_encryption, self.use_allowlist)
        self.rpf_sim = rpfsim.RpfSimulator(rpf_send_topic, rpf_recv_topic, self.broker, self.port, self.Tasks, self.time, self.rpf_username, self.rpf_pw, self.use_encryption, self.use_allowlist)
        self.rob_sim = robsim.RobotSimulator(rob_send_topic, rob_recv_topic, self.broker, self.port, self.Rob, self.ELV, self.time, self.use_allowlist)


        # change scenario
        if self.ATT_scenario:
            self.bos_mode, self.rpf_mode = switch_mode(self.ATT_scenario, self.target, self.selected_protocol, self.use_encryption)
            # print(f"---BOS:{self.bos_mode}, RPF:{self.rpf_mode}")
            self.bos_mode = self.bos_mode if self.bos_mode else Mode.Normal
            self.rpf_mode = self.rpf_mode if self.rpf_mode else Mode.Normal

            self.bos_sim.handler.set_mode(self.bos_mode)
            self.rpf_sim.handler.set_mode(self.rpf_mode)

        if self.ATT_scenario == 'DDOS':
            self.DosAtt = True

        self.stop_event = Event()

    def start_server(self, block=True):
        self.running = True
        # only set signal handler when blocking (i.e., interactive run)
        if block:
            signal.signal(signal.SIGINT, self.signal_handler)

        # connection_monitor
        connection_monitor = ConnectionMonitor(
            broker=MqttConfig.MQTT_BROKER,
            port=MqttConfig.MQTT_PORT,
            monitor_interval=1,
            log_file=LogConfig.CONNECTIONS_LOG,
            time_sim=self.time
        )
        connection_monitor_thread = Thread(target=connection_monitor.start_monitoring, daemon=True)
        connection_monitor_thread.start()

        CPU = MonitorCPU(file_path=LogConfig.CPU_LOG, target_process_name="mosquitto", interval=1, time_sim=self.time)
        cpu_thread = Thread(target=CPU.start_monitoring, daemon=True)
        cpu_thread.start()

        # simulator threads (daemon so tests can exit cleanly)
        elv_thread = Thread(target=self.elv_sim.start_simulation, args=(self.stop_event,), daemon=True)
        bos_thread = Thread(target=self.bos_sim.start_simulation, args=(self.stop_event,), daemon=True)
        rpf_thread = Thread(target=self.rpf_sim.start_simulation, args=(self.stop_event,), daemon=True)
        rob_thread = Thread(target=self.rob_sim.start_simulation, args=(self.stop_event,), daemon=True)

        elv_thread.start()
        bos_thread.start()
        rpf_thread.start()
        rob_thread.start()

        mqtt_monitor = MQTTBrokerMonitor(broker_address="localhost")
        mqtt_thread = Thread(target=mqtt_monitor.start_monitoring, daemon=True)
        mqtt_thread.start()

        print("Server successfully started and listening...")

        if self.DosAtt:
            ddos_scenario = DDOSAttackScenario(target=self.target, protocol="MQTT", enable_allowlist=self.use_allowlist, time=self.time)
            # start DDOS attack in daemon thread for non-blocking mode
            attack_thread = Thread(target=ddos_scenario.start_attack, daemon=not block)
            attack_thread.start()
            if block:
                attack_thread.join()
                print("Attack simulation finished or failed.")
            else:
                print("Attack simulation started (non-blocking).")

        # only block the thread/process when requested
        if block:
            signal.pause()
        else:
            # return to caller immediately (non-blocking)
            return

    def stop_server(self):
        self.stop_event.set()

        if self.rpf_sim.task_complete:
            self.elv_sim.stop_simulation()
            self.bos_sim.stop_simulation()
            self.rpf_sim.stop_simulation()
            self.rob_sim.stop_simulation()

            self.running = False
            print("Server stopped")
            # sys.exit(0)

    def signal_handler(self, signal, frame):
        print("Signal received, stopping server...")
        self.stop_server()



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet_loss", type=float, default=0.001)
    parser.add_argument("--delay_min", type=float, default=0.1)
    parser.add_argument("--delay_max", type=float, default=1.6)
    parser.add_argument("--delay_chance", type=float, default=0.95)
    args = parser.parse_args()

    Sim_Speed, _, _, _, _, _, _, _ = load_scenario(
        ClientConfig.SCENARIO_FILE,
        ScenarioConfig.Sim_Speed,
        ScenarioConfig.PROTOCOL,
        ScenarioConfig.Service_Robots,
        ScenarioConfig.Tasks,
        ScenarioConfig.Elevators,
        ScenarioConfig.ATT_SCENARIO,
        ScenarioConfig.Service_Robot_Name,
        ScenarioConfig.Service_Robot_PRIORITY,
        time=None
    )
    timesim = TimeSim(time_scale=Sim_Speed)

    enable_network_disturbance(
        packet_loss=args.packet_loss,
        delay_range=(args.delay_min, args.delay_max),
        delay_chance=args.delay_chance,
        use_timesim=timesim,
        log_file=LogConfig.FILE_NETWORK_RUNTIME_REPORT
    )
    log_network_disturb_status(LogConfig.FILE_NETWORK_DISTURBANCE)
    main = Manager()
    main.sim_speed = Sim_Speed
    main.time = timesim
    main.setup_simulators(external_timesim=timesim)
    main.start_server()