import sys
import signal
import atheris
from threading import Thread, Event
from mqtt_communication_module.data_model import set_run_parameters
from utils.msglog import generate_runtime_report
from utils.storyboard import MqttConfig, LogConfig, Mode, ScenarioConfig, CER, FuzzingConfig
from utils.utils import load_scenario
from utils.timesim import TimeSim
from simulator import bossim
from fuzzer.rpffuzzer import frpfsim, frpfsim2
from fuzzer.bosfuzzer.fbossim import FBosSimulator
from fuzzer.robfuzzer import frobsim, frobsim2
from fuzzer.elvfuzzer import felvsim, felvsim2
from fuzzer.fuzzing_utils import get_seed, generate_scenario

felv = None
fbos = None
frpf = None
frob = None

class SBCSE():
    def __init__(self):
        self.sim_speed = 1
        self.time = TimeSim(self.sim_speed)
        self.task = []
        self.broker = MqttConfig.MQTT_BROKER
        self.port = MqttConfig.MQTT
        self.mqtts_listen = MqttConfig.MQTTS
        self.runtime_log_file = LogConfig.RUNTIME_REPORT
        self.mqtt_client = None
        self.message_handler = None
        self.running = False
        self.stop_event = Event()

        # self.traffic_monitor = PortTrafficMonitor()
        # self.monitor_thread = None

        self.Rob = None
        self.Tasks = None
        self.ELV = None
        self.ATT_scenario = None
        self.target = None
        self.selected_protocol = None
        self.DosAtt = None

        self.fuzzer = None

        self.server_thread = None
        self.running = False
        self.log_callback = None

        self.current_mode = Mode.DEFAULT
        self.bos_mode = Mode.FUZZING
        self.rpf_mode = Mode.FUZZING

        # BAC
        # self.rpf_username = CER.U_RPF
        # self.rpf_pw = CER.PW_RPF
        # self.bos_username = CER.U_BOS
        # self.bos_pw = CER.PW_BOS
        # self.use_encryption = False  # True/False
        # self.use_allowlist = False  # True/False

        # self.init_database()

    def setup_simulators(self):
        if self.Rob is None and self.Tasks is None and self.ELV is None and self.ATT_scenario is None and self.target is None and self.selected_protocol is None and self.fuzzer is None:
            Sim_Speed, PROTOCOL, Rob, TASKS, ELV, SCENARIO_NAME, TARGET, self.fuzzer = load_scenario(
                'fuzzer/fuzzing_scenario.yaml',
            ScenarioConfig.Sim_Speed,
            ScenarioConfig.PROTOCOL,
            ScenarioConfig.Service_Robots,
            ScenarioConfig.Tasks,
            ScenarioConfig.Elevators,
            ScenarioConfig.ATT_SCENARIO,
            ScenarioConfig.Service_Robot_Name,
            ScenarioConfig.Service_Robot_PRIORITY,
            self.time,
            ScenarioConfig.FUZZER
        )

            self.sim_speed = Sim_Speed
            self.Rob = Rob  # instance_list
            self.Tasks = TASKS
            self.ELV = ELV
            self.ATT_scenario = SCENARIO_NAME
            self.target = TARGET
            self.selected_protocol = PROTOCOL
            # self.use_encryption = encryption
            self.time = TimeSim(self.sim_speed)

        if self.selected_protocol == MqttConfig.MQTT:
            self.port = MqttConfig.MQTT_PORT
        elif self.selected_protocol == MqttConfig.MQTTS:
            self.port = MqttConfig.MQTTS_PORT

        run_parameters = set_run_parameters(self.sim_speed, self.selected_protocol, self.Rob, self.ELV, self.Tasks,
                                            self.ATT_scenario, self.target)
        generate_runtime_report(self.runtime_log_file, run_parameters, False, False)

        self.bos_mode, self.rpf_mode = Mode.mapping.get((self.ATT_scenario, self.target), (Mode.Normal, Mode.Normal))
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
        if self.fuzzer[0][FuzzingConfig.ELVSIM]:
            self.elv_sim = felvsim.FElevatorSimulator(elv_send_topic, elv_recv_topic, self.broker, self.port, self.ELV, self.time, None)
        else:
            self.elv_sim = felvsim2.FElevatorSimulator(elv_send_topic, elv_recv_topic, self.broker, self.port, self.ELV, self.time, None)

        if self.fuzzer[0][FuzzingConfig.BOSSIM]:
            self.bos_sim = FBosSimulator(bos_send_topic, bos_recv_topic, self.broker, self.port, self.time, CER.U_BOS, CER.PW_BOS, False, False)
        else:
            self.bos_sim = bossim.BosSimulator(bos_send_topic, bos_recv_topic, self.broker, self.port, self.time, CER.U_BOS, CER.PW_BOS, False, False)

        if self.fuzzer[0][FuzzingConfig.ROBSIM]:    
            self.rob_sim = frobsim.FRobotSimulator(rob_send_topic, rob_recv_topic, self.broker, self.port, self.Rob, self.ELV, self.time, None)
        else:
            self.rob_sim = frobsim2.FRobotSimulator(rob_send_topic, rob_recv_topic, self.broker, self.port, self.Rob, self.ELV, self.time, None)

        if self.fuzzer[0][FuzzingConfig.RPFSIM]:
            self.rpf_sim = frpfsim.FRPFSimulator(rpf_send_topic, rpf_recv_topic, self.broker, self.port, self.Tasks, self.time, CER.U_RPF, CER.PW_RPF, False, False)
        else:
            self.rpf_sim = frpfsim2.FRPFSimulator(rpf_send_topic, rpf_recv_topic, self.broker, self.port, self.Tasks, self.time, CER.U_RPF, CER.PW_RPF, False, False)
        
        # # change scenario
        # if self.ATT_scenario:
        #     self.bos_mode, self.rpf_mode = switch_mode(self.ATT_scenario, self.target, self.selected_protocol, self.use_encryption)
        #     # print(f"---BOS:{self.bos_mode}, RPF:{self.rpf_mode}")
        #     self.bos_mode = self.bos_mode if self.bos_mode else Mode.Normal
        #     self.rpf_mode = self.rpf_mode if self.rpf_mode else Mode.Normal

        #     self.bos_sim.handler.set_mode(self.bos_mode)
        #     self.rpf_sim.handler.set_mode(self.rpf_mode)

        # if self.ATT_scenario == 'DDOS':
        #     self.DosAtt = True

        self.stop_event = Event()

    def start_server(self):
        elv_thread = Thread(target=self.elv_sim.start_simulation, args=(self.stop_event,), daemon=True)
        bos_thread = Thread(target=self.bos_sim.start_simulation, args=(self.stop_event,), daemon=True)
        rob_thread = Thread(target=self.rob_sim.start_simulation, args=(self.stop_event,), daemon=True)
        rpf_thread = Thread(target=self.rpf_sim.start_simulation, args=(self.stop_event,), daemon=True)

        elv_thread.start()
        bos_thread.start()
        rob_thread.start()
        rpf_thread.start()

        self.running = True

        elv_thread.join()
        bos_thread.join()
        rob_thread.join()
        rpf_thread.join()
        sys.exit(0)


    def stop_server(self):
        self.stop_event.set()
        self.elv_sim.stop_simulation()
        self.rob_sim.stop_simulation()
        self.rpf_sim.stop_simulation()
        self.bos_sim.stop_simulation()
        self.running = False
        print("Server stopped")

def signal_handler(signal, frame):
    exit()

@atheris.instrument_func
def Fuzzer(data:bytes):
    fdp = atheris.FuzzedDataProvider(data)
    if frpf:
        while not all(value is not None for value in frpf.handler.rob_dt_data_dict.values()):
            frpf.time.sleep(0.5)
        frpf.handler.fdp = fdp
        if not frpf.stop_event.is_set():
            for rob in frpf.robothandler.rob_dict.keys():
                frpf.fuzzing_msg(rob)
    if felv:
        if felv.handler.is_fdp():
            felv.handler.set_fdp(fdp)
        else:
            return
        while not felv.handler.stop_event:
            pass
        while not felv.handler.is_fdp() and not felv.handler.stop_event.is_set():
            pass
    if fbos:
        while not fbos.handler.stop_event:
            pass
        if not fbos.handler.stop_event.is_set():
            fbos.handler.forward_message(None,None, fdp)
    if frob:
        if frob.handler.is_fdp():
            frob.handler.set_fdp(fdp)
        else:
            return
        while not frob.handler.stop_event:
            pass
        while not frob.handler.is_fdp() and not frob.handler.stop_event.is_set():
            pass
    print(data, file=sys.stderr)


def Fuzzing(simulator, server_process):
    try:
        atheris.Setup(sys.argv, Fuzzer)
        atheris.Fuzz()
    except Exception as e:
        print('Exception:\n'+e, file=sys.stderr)
    finally:
        simulator.stop_server() 
        server_process.join()
        print('fuzzing stopped')


if __name__ == "__main__":
    seed = get_seed()
    generate_scenario(seed)
    signal.signal(signal.SIGINT, signal_handler)
    simulator = SBCSE()
    simulator.setup_simulators()
    server_process = Thread(target=simulator.start_server)
    server_process.start()

    if simulator.fuzzer[0][FuzzingConfig.ELVSIM]:
        felv = simulator.elv_sim
    if simulator.fuzzer[0][FuzzingConfig.BOSSIM]:
        fbos = simulator.bos_sim
    if simulator.fuzzer[0][FuzzingConfig.RPFSIM]:
        frpf = simulator.rpf_sim
        while not frpf.initialized:
            pass
    if simulator.fuzzer[0][FuzzingConfig.ROBSIM]:
        frob = simulator.rob_sim        
    while not simulator.running:
        pass
    Fuzzing(simulator, server_process)