import json
import socket
from mqtt_communication_module.mqtt_msghandler import MessageHandler
from mqtt_communication_module.data_model import SendCommandData, RecvCommandData, B2R_cmdData, RobotData
from utils.storyboard import LogConfig, RobotConfig, CmdConfig, ScenarioConfig, Mode, ELVConfig, MqttConfig, StateMachineConfig
from utils.msglog import msg_log, log_id
# from .control_protocol.rcp import RCPMachine
from mqtt_communication_module.Scenario_msg_handler.Normal_mode.RPF_normal_mode import RpfNormalMode
from mqtt_communication_module.Scenario_msg_handler.MITM.RPF_mitm_mode import RpfMitmMode
from mqtt_communication_module.Scenario_msg_handler.BAC.RPF_bac_mode import RpfBacMode
from device_motion_module.servicerobot import RobotHandler
from formal_verification.FV import maude_class_monitor, maude_fnuc_monitor


# @maude_class_monitor(PID='RCP', ocom_statuses=['recv_cmd'])
class RpfMessageHandler(MessageHandler):
    def __init__(self, send_topic, recv_topic, broker, port, time):
        self.port = port
        self.broker = broker
        self.time = time
        self.client_ip_list = MqttConfig.client_ip
        self.client_ip = None
        self.rpf_id = "RPF"

        self.rpf_log_file = LogConfig.FILE_RPF_BOS_LOG
        self.rpf_rob_comfile = LogConfig.FILE_RPF_ROB_LOG
        self.runtime_file = LogConfig.RUNTIME_REPORT
        # send command to bos->elv
        self.send_data_instance = SendCommandData()
        # recv from elv-> bos
        self.recv_data_instance = RecvCommandData()
        # send command to robot
        self.b2r_data_instance = B2R_cmdData()
        self.rob_data_instance = RobotData(self.time)
        self.b2r_data_instance = B2R_cmdData()
        self.rob_data_instance = RobotData(self.time)
        self.send_B2D = send_topic[0]  # B2D
        self.send_B2R = send_topic[1]  # B2R
        self.send_B2R_FORWARD_ELV = send_topic[2]
        self.recv_D2B = recv_topic[0]  # D2B
        self.recv_R2B = recv_topic[1]  # R2B
        self.recv_Rob_dt = recv_topic[2]  # rob dt data
        self.recv_Elv_dt = recv_topic[3]  # elv dt data
        self.robothandler = RobotHandler()
        self.elv_dt_data = False
        self.rob_dt_data = False
        self.init_elv_status()
        enable_allowlist = False

        self.rob_dt_data_dict = {}
        self.rob_status_dict = {}
        for rob_name in self.robothandler.rob_dict.keys():
            self.rob_dt_data_dict[rob_name] = None
            self.rob_status_dict[rob_name] = RobotConfig.rob_status0.copy()

        # Task
        self.tasks = []
        self.mode = Mode.Normal  # default setting

        self.mode_handlers = {
            Mode.Normal: RpfNormalMode(self),
            Mode.MITM: RpfMitmMode(self),
            Mode.BAC: RpfBacMode(self)
        }

        use_mqtts = (port == 8883)
        cert_path = key_path = ca_path = None

        if use_mqtts:
            cert_path = MqttConfig.CRT
            key_path = MqttConfig.KEY
            ca_path = MqttConfig.CA

        self.client_ip_port = None
        super().__init__(send_topic, recv_topic, broker, port, use_mqtts, enable_allowlist, cert_path, key_path, ca_path, self.client_ip)

    def bind_client_to_port(self):
        """Bind the client to a static IP"""
        try:
            local_ip = self.client_ip_list.get(self.rpf_id, "192.168.0.102")

            local_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            local_socket.bind((local_ip, 0))

            self.client_ip, self.client_port = local_socket.getsockname()
            client_info = f"{self.rpf_id} bound to {self.client_ip}:{self.client_port} ++++++++++++++++"
            print(client_info)
            log_id(self.runtime_file, client_info)
            return self.client_ip

        except Exception as e:
            print(f"Error binding client {self.rpf_id}: {e}")
            return None


    def set_mode(self, mode):
        # method to set current mode
        self.mode = mode

    def process_task(self):
        if self.tasks:
            self.task = self.tasks.pop(0)
            self.task_floor = self.task[RobotConfig.TASK_FLOOR]
            self.task_name = self.task[ScenarioConfig.Task_Name]
        else:
            self.tasks = []
            # self.check_and_stop_on_tasks_complete()
            print("No tasks available to process.")

    def init(self):
        self.init_elv_status()
        self.init_rob_status()


    def init_elv_status(self):
        # elv status
        self.elv_dt_data = False
        self.elv_current_floor = None
        self.interlock_success = False
        self.open_success = False
        self.close_success = True
        self.call_accept = False
        self.call_arrive = False
        self.go_accept = False
        self.go_arrive = False

    def init_rob_status(self, rob_name=None):
        # bot status
        if rob_name:
            if rob_name in self.rob_status_dict:
                self.rob_status_dict[rob_name] = RobotConfig.rob_status0.copy()
        else:
            for rob_name in self.rob_status_dict.keys():
                self.rob_status_dict[rob_name] = RobotConfig.rob_status0.copy()


    def on_connect(self, client, userdata, flags, rc):
        super().on_connect(client, userdata, flags, rc)
        recv_topics = [(self.recv_D2B, 1), (self.recv_R2B, 1), (self.recv_Rob_dt, 1), (self.recv_Elv_dt, 1)]
        for topic, qos in recv_topics:
            self.client.subscribe(topic=topic, qos=1)

    """
    send command to elv
    """
    # @maude_fnuc_monitor
    def send_interlock_command(self, value):
        data = self.send_data_instance.interlock_command(value)
        self.send(data, topic=self.send_B2D, time_sim=self.time, file_path=self.rpf_log_file)

    # @maude_fnuc_monitor
    def send_call_command(self, target_floor, direction):
        data = self.send_data_instance.call_command(target_floor, direction)
        self.send(data, topic=self.send_B2D, time_sim=self.time, file_path=self.rpf_log_file)

    # @maude_fnuc_monitor
    def send_open_command(self):
        data = self.send_data_instance.open_command()
        self.send(data, topic=self.send_B2D, time_sim=self.time, file_path=self.rpf_log_file)

    # @maude_fnuc_monitor
    def send_close_command(self):
        data = self.send_data_instance.close_command()
        self.send(data, topic=self.send_B2D, time_sim=self.time, file_path=self.rpf_log_file)

    # @maude_fnuc_monitor
    def send_go_command(self, floor):
        data = self.send_data_instance.go_command(floor)
        self.send(data, topic=self.send_B2D, time_sim=self.time, file_path=self.rpf_log_file)

    """
    send command to robot  
    """
    # @maude_fnuc_monitor
    def send_B2R_command(self, target_floor=None, command=None, status=None, rob_name=None):
        data = self.b2r_data_instance.B2R_command(target_floor=target_floor, command=command, status=status, rob_name=rob_name)
        self.send(data, topic=self.send_B2R, time_sim=self.time, file_path=self.robothandler.get_rpf_rob_comfile(rob_name))

    def check_command(self, command, result, rob_name=None):
        success_attr = f"{command}_{result}"
        if result in [CmdConfig.SUCCESS, CmdConfig.ACCEPT, CmdConfig.ARRIVE, CmdConfig.COMPLETED]:
            # Set the attribute based on the result
            self.rob_status_dict[next(iter(self.rob_dt_data_dict))][success_attr] = True

        if command == CmdConfig.OPEN and result == CmdConfig.SUCCESS:
            self.rob_status_dict[next(iter(self.rob_dt_data_dict))][ELVConfig.CLOSE_SUCCESS] = False
        elif command == CmdConfig.CLOSE and result == CmdConfig.SUCCESS:
            self.rob_status_dict[next(iter(self.rob_dt_data_dict))][ELVConfig.OPEN_SUCCESS] = False
        if command == CmdConfig.GETTING_ON and result == CmdConfig.SUCCESS:
            self.rob_status_dict[next(iter(self.rob_dt_data_dict))][CmdConfig.GETTING_OFF_SUCCESS] = False
            self.rob_status_dict[next(iter(self.rob_dt_data_dict))][CmdConfig.GETTING_OFF_COMPLETED] = False
        elif command == CmdConfig.GETTING_OFF and result == CmdConfig.SUCCESS:
            self.rob_status_dict[next(iter(self.rob_dt_data_dict))][CmdConfig.GETTING_ON_SUCCESS] = False
            self.rob_status_dict[next(iter(self.rob_dt_data_dict))][CmdConfig.GETTING_ON_COMPLETED] = False

        elif command == CmdConfig.GETTING_OFF:
            if result == CmdConfig.SUCCESS:
                self.rob_status_dict[next(iter(self.rob_dt_data_dict))][CmdConfig.GETTING_ON_SUCCESS] = False
            elif result == CmdConfig.COMPLETED:
                self.rob_status_dict[next(iter(self.rob_dt_data_dict))][CmdConfig.GETTING_ON_COMPLETED] = False
            elif result == CmdConfig.NOT_COMPLETED:
                self.rob_status_dict[next(iter(self.rob_dt_data_dict))][CmdConfig.GETTING_OFF_COMPLETED] = False

    def mf_check_command(self, command, result, rob_name=None):
        success_attr = f"{command}_{result}"
        if rob_name:
            if not command:
                return
            self.update_rob_state(rob_name, success_attr)
            current_state = self.robothandler.rob_dict[rob_name]['rcp_state_machine'].rcp_status
            if current_state == StateMachineConfig.r1e4 and command == CmdConfig.GETTING_ON and result == CmdConfig.SUCCESS:
                self.rob_status_dict[rob_name][CmdConfig.GETTING_OFF_SUCCESS] = False
                self.rob_status_dict[rob_name][CmdConfig.GETTING_OFF_COMPLETED] = False
            elif current_state == StateMachineConfig.r2e8 and command == CmdConfig.GETTING_OFF and result == CmdConfig.SUCCESS:
                self.rob_status_dict[rob_name][CmdConfig.GETTING_ON_SUCCESS] = False
                self.rob_status_dict[rob_name][CmdConfig.GETTING_ON_COMPLETED] = False
            elif command == CmdConfig.GETTING_OFF and result == CmdConfig.NOT_COMPLETED:
                self.rob_status_dict[rob_name][CmdConfig.GETTING_OFF_COMPLETED] = False
        else:
            if result in [CmdConfig.SUCCESS, CmdConfig.ACCEPT, CmdConfig.ARRIVE, CmdConfig.COMPLETED]:
                rob_name = self.robothandler.peek()
                if rob_name:
                    self.update_elv_state(rob_name, success_attr)

    def update_rob_state(self, rob_name, success_attr):
        current_state = self.robothandler.rob_dict[rob_name]['rcp_state_machine'].rcp_status
        self.rob_status_dict[rob_name][success_attr] = True

    def update_elv_state(self, rob_name, success_attr):
        current_state = self.robothandler.rob_dict[rob_name]['rcp_state_machine'].rcp_status
        if current_state in CmdConfig.STATE_ATTR_MAP and success_attr == CmdConfig.STATE_ATTR_MAP[current_state]:
            self.rob_status_dict[rob_name][success_attr] = True
            if success_attr == ELVConfig.OPEN_SUCCESS:
                self.rob_status_dict[rob_name][ELVConfig.CLOSE_SUCCESS] = False
            elif success_attr == ELVConfig.CLOSE_SUCCESS:
                self.rob_status_dict[rob_name][ELVConfig.OPEN_SUCCESS] = False
        elif current_state == StateMachineConfig.r1e1 and success_attr == ELVConfig.CALL_ARRIVE:
            self.rob_status_dict[rob_name][success_attr] = True
        elif current_state == StateMachineConfig.r2e5 and success_attr == ELVConfig.GO_ARRIVE:
            self.rob_status_dict[rob_name][success_attr] = True

    def forward_message(self, topic, msg):
        if topic == self.recv_Elv_dt:  # B2D
            new_topic = self.send_B2R_FORWARD_ELV  # D2E
            self.send(msg, new_topic, self.time, file_path=self.rpf_log_file)

    def rob_error_solver(self, rob_name, reason):
        if RobotConfig.E002 in reason:
            self.rob_status_dict[rob_name][RobotConfig.ERROR] = RobotConfig.E002
        elif RobotConfig.E004 in reason:
            self.rob_status_dict[rob_name][RobotConfig.ERROR] = RobotConfig.E004

    def stop_system(self):
        # stop and clean up message handling
        try:
            self.client.disconnect()
        except Exception as e:
            print(f"Error during disconnection: {e}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload)
            command = payload.get(CmdConfig.COMMAND)
            result = payload.get(CmdConfig.RESULT)
            reason = payload.get(CmdConfig.REASON)
            rob_name = payload.get(RobotConfig.NAME)

            if msg.topic == self.recv_D2B:          # D2B
                msg_log(msg.topic, payload, self.time, self.rpf_log_file)
                self.recv_cmd = command

            elif msg.topic == self.recv_Elv_dt:    # elv dt data
                self.elv_current_floor = payload[RobotConfig.FLOOR]
                self.elv_door_status = payload[ELVConfig.DOOR]
                self.elv_moving_status = payload[ELVConfig.MOVINGSTATUS]
                self.elv_dt_data = True
                msg_log(msg.topic, payload, self.time, self.rpf_log_file)

            elif msg.topic == self.recv_R2B:        # R2B
                msg_log(msg.topic, payload, self.time, self.robothandler.get_rpf_rob_comfile(rob_name))
                self.recv_cmd = command

            elif msg.topic == self.recv_Rob_dt:     # rob dt data
                self.rob_dt_data_dict.update({rob_name: {
                    RobotConfig.FLOOR: payload[RobotConfig.FLOOR],
                    RobotConfig.MOVING_STATUS: payload[CmdConfig.STATUS],
                    RobotConfig.ELV_PREPARATION: payload[RobotConfig.ELV_PREPARATION]
                }})
                msg_log(msg.topic, payload, self.time, self.robothandler.get_rpf_rob_comfile(rob_name))

            self.check_command(command, result, rob_name)
            self.forward_message(msg.topic, payload)
            if result == 'not_completed':
                self.rob_error_solver(rob_name, reason)

        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
