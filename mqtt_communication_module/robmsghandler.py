import json
import socket
from mqtt_communication_module.mqtt_msghandler import MessageHandler
from mqtt_communication_module.data_model import RecvCommandData, RobotData
from utils.storyboard import LogConfig, RobotConfig, CmdConfig, ELVConfig, MqttConfig
from utils.msglog import rob_communication_log, msg_log, log_id, action_log
from formal_verification.FV import maude_class_monitor, maude_fnuc_monitor

# @maude_class_monitor(PID='ROB', ocom_statuses=['recv_cmd'])
class RobMessageHandler(MessageHandler):
    def __init__(self, send_topic, recv_topic, broker, port, robs, time):
        self.port = port
        self.broker = broker
        self.time = time
        self.Robs = robs
        self.client_ip_list = MqttConfig.client_ip
        self.client_ip = None
        self.rob_id = "ROB"

        self.send_R2B = send_topic[0]  # R2B res
        self.send_ROB_DT = send_topic[1]  # Dt data
        self.recv_B2R = recv_topic[0]  # B2R cmd data
        self.recv_elv_dt = recv_topic[1]  # elv,dt data

        # init log file
        self.rob_jp_file = LogConfig.FILE_ROB_JP_LOG
        self.rob_com_file = LogConfig.FILE_ROB_LOG
        self.rob_position_file = LogConfig.FILE_ROB_POSITION_LOG
        self.runtime_file = LogConfig.RUNTIME_REPORT
        # init data instance and topic
        self.send_robdata_instance = RobotData(self.time)
        enable_allowlist = False

        use_mqtts = (port == 8883)
        cert_path = key_path = ca_path = None

        if use_mqtts:
            cert_path = MqttConfig.CRT
            key_path = MqttConfig.KEY
            ca_path = MqttConfig.CA

        self.client_ip = None
        super().__init__(send_topic, recv_topic, broker, port, use_mqtts, enable_allowlist, cert_path, key_path, ca_path, self.client_ip)


        self.task_lists = {}
        self.rob_dt_data = {}
        self.elv_dt_count = {}
        for rob in self.Robs:
            self.task_lists[rob.name] = []
            self.rob_dt_data[rob.name] = None
            self.elv_dt_count[rob.name] = 0

    def init(self):
        for rob in self.Robs:
            self.task_lists[rob.name] = []
            self.rob_dt_data[rob.name] = None
            self.elv_dt_count[rob.name] = 0

    def bind_client_to_port(self):
        """Bind the client to a static IP"""
        try:
            local_ip = self.client_ip_list.get(self.rob_id, "192.168.0.102")  # Default IP

            # Bind to this IP (using dynamic port)
            local_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            local_socket.bind((local_ip, 0))  # Bind IP and automatically assign available ports

            # Bind the MQTT client
            self.client_ip, self.client_port = local_socket.getsockname()
            client_info = f"{self.rob_id} bound to {self.client_ip}:{self.client_port} ++++++++++++++++"
            print(client_info)
            log_id(self.runtime_file, client_info)
            return self.client_ip

        except Exception as e:
            print(f"Error binding client {self.rob_id}: {e}")
            return None

    def find_rob(self, rob_name):
        for rob in self.Robs:
            if rob_name == rob.name:
                return rob

    def on_connect(self, client, userdata, flags, rc):
        super().on_connect(client, userdata, flags, rc)
        recv_topics = [(self.recv_B2R, 1), (self.recv_elv_dt, 1)]
        for topic, qos in recv_topics:
            self.client.subscribe(topic=topic, qos=1)

    def send_rob_dt(self, rob):
        rob_status = rob.get_rob_status()
        dt = self.send_robdata_instance.dt_robot(rob_status)
        # dt.update(data)
        self.rob_com_send(dt, self.send_ROB_DT, time_sim=self.time, file_path=self.rob_com_file % rob.name)


    # @maude_fnuc_monitor
    def recv_command(self, command, result, rob, reason):
        data = self.send_robdata_instance.robot_recv_command(command, result, reason, name=rob.name)
        self.send(data, self.send_R2B, time_sim=self.time, file_path=self.rob_com_file % rob.name)

    def check_command(self, command):
        success_attr = f"{command}_success"
        # Set the attribute based on the result
        setattr(self, success_attr, True)

        if command == CmdConfig.GETTING_ON:
            self.GettingOff_success = False
        elif command == CmdConfig.GETTING_OFF:
            self.GettingOn_success = False

    def add_task(self, rob_name, task):
        if rob_name not in self.task_lists:
            self.task_lists[rob_name] = []
        self.task_lists[rob_name].append(task)

    def get_tasks(self, rob_name):
        return self.task_lists.get(rob_name)

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload)
            status = payload.get(CmdConfig.STATUS)
            target_floor = int(payload.get(ELVConfig.TARGET_FLOOR)) if payload.get(ELVConfig.TARGET_FLOOR) else None

            if msg.topic == self.recv_elv_dt:
                for rob in self.Robs:
                    msg_log(msg.topic, payload, self.time, rob.com_file_name)
                    cmd = None
                    target_floor = None
                    rob_communication_log(cmd, target_floor, payload, self.time, rob.communication_file_name,
                                          message_type='elv')
                    self.elv_dt_count[rob.name] += 1
                    if self.elv_dt_count[rob.name] == 9:
                        self.rob_dt_data[rob.name] = rob.get_rob_status()
                        rob_communication_log(cmd, target_floor, self.rob_dt_data[rob.name], self.time,
                                              rob.communication_file_name, message_type='rob')
                        self.elv_dt_count[rob.name] = 0

            elif msg.topic == self.recv_B2R:
                rob_name = payload.get(RobotConfig.NAME)
                rob = self.find_rob(rob_name)
                msg_log(msg.topic, payload, self.time, rob.com_file_name)
                command = payload.get(CmdConfig.COMMAND)
                self.check_command(command)
                if command in self.task_lists[rob_name]:
                    return
                self.recv_cmd = command

                if command == RobotConfig.GO_TO_ELV:
                    if rob.set_go_to_elv_status():
                        self.rob.set_go_to_elv_status()
                        self.task_list.insert(-1, RobotConfig.GO_TO_ELV)

                elif command == RobotConfig.CALLING:
                    self.rob.next_floor = payload[ELVConfig.TARGET_FLOOR]
                    self.rob.bot_dt_send_time = 10
                    self.rob.bot_pos_log_time = 5
                    self.rob.set_elv_call_status(target_floor)
                    rob_communication_log(command, self.rob.next_floor, self.rob_dt_data, self.time, self.rob_jp_file, message_type='rob')

                elif command == RobotConfig.GET_ON:
                    self.rob.bot_dt_send_time = 10
                    self.rob.bot_pos_log_time = 5
                    self.rob.set_elv_getting_on()
                    self.task_list.insert(-1, RobotConfig.GET_ON)
                    rob_communication_log(command, None, self.rob_dt_data, self.time, self.rob_jp_file, message_type='rob')

                elif command == RobotConfig.GET_OFF:
                    self.rob.floor = self.rob.elv_floor_status
                    self.rob.bot_dt_send_time = 10
                    self.rob.bot_pos_log_time = 5
                    self.rob.set_elv_getting_off_status()
                    self.task_list.insert(-1, RobotConfig.GET_OFF)
                    rob_communication_log(command, self.rob.floor, self.rob_dt_data, self.time, self.rob_jp_file, message_type='rob')

                elif command == RobotConfig.ELVStay:
                    self.rob.set_elv_stay_status()
                    self.send_rob_dt()
                    self.task_list.insert(-1, RobotConfig.ELVStay)

                elif command == RobotConfig.CHARGE:
                    self.rob.set_go_to_charge_status()
                    self.task_list.insert(-1, RobotConfig.CHARGE)

                elif command == RobotConfig.Schedule_Work:
                    self.rob.set_schedule_work_status()
                    self.task_list.insert(-1, RobotConfig.Schedule_Work)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")


    def fm_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload)
            status = payload.get(CmdConfig.STATUS)
            target_floor = int(payload.get(ELVConfig.TARGET_FLOOR)) if payload.get(ELVConfig.TARGET_FLOOR) else None
            
            if msg.topic == self.recv_elv_dt:
                for rob in self.Robs:
                    msg_log(msg.topic, payload, self.time, rob.com_file_name)
                    cmd = None
                    target_floor = None
                    rob_communication_log(cmd, target_floor, payload, self.time, rob.communication_file_name,
                                          message_type='elv')
                    self.elv_dt_count[rob.name] += 1
                    if self.elv_dt_count[rob.name] == 9:
                        self.rob_dt_data[rob.name] = rob.get_rob_status()
                        rob_communication_log(cmd, target_floor, self.rob_dt_data[rob.name], self.time,
                                              rob.communication_file_name, message_type='rob')
                        self.elv_dt_count[rob.name] = 0
            elif msg.topic == self.recv_B2R:
                rob_name = payload.get(RobotConfig.NAME)
                rob = self.find_rob(rob_name)
                msg_log(msg.topic, payload, self.time, rob.com_file_name)
                command = payload.get(CmdConfig.COMMAND)
                self.check_command(command)

                if command in self.task_lists[rob_name]:
                    return
                self.recv_cmd = command

                if command == RobotConfig.GO_TO_ELV:
                    if rob.set_go_to_elv_status():
                        self.recv_command(command, 'success', rob, reason=None)
                        self.task_lists[rob_name].insert(-1, RobotConfig.GO_TO_ELV)
                        action_log(command + "_start", rob.map_no, self.time, rob.act_file_name)
                    elif rob.state == RobotConfig.robq1:
                        self.recv_command(command, 'success', rob, reason=None)
                        action_log(command + "_start", rob.map_no, self.time, rob.act_file_name)
                        self.recv_command(command, 'completed', rob, reason=None)
                        action_log(command + "_completed", rob.map_no, self.time, rob.act_file_name)
                elif command == RobotConfig.CALLING:
                    if rob.set_elv_call_status(target_floor):
                        self.recv_command(command, 'success', rob, reason=None)
                        rob.next_floor = payload[ELVConfig.TARGET_FLOOR]
                        rob.bot_dt_send_time = 10
                        rob.bot_pos_log_time = 5
                        action_log(command, rob.map_no, self.time, rob.act_file_name)
                        self.rob_dt_data[rob_name] = rob.get_rob_status()
                        rob_communication_log(command, rob.next_floor, self.rob_dt_data[rob_name], self.time,
                                              rob.communication_file_name, message_type='rob')
                elif command == RobotConfig.GET_ON:
                    if rob.set_elv_getting_on():
                        self.recv_command(command, 'success', rob, reason=None)
                        rob.bot_dt_send_time = 10
                        rob.bot_pos_log_time = 5
                        self.task_lists[rob_name].insert(-1, RobotConfig.GET_ON)
                        action_log(command + "_start", rob.map_no, self.time, rob.act_file_name)
                        self.rob_dt_data[rob_name] = rob.get_rob_status()
                        rob_communication_log(command, None, self.rob_dt_data[rob_name], self.time,
                                              rob.communication_file_name, message_type='rob')
                    elif rob.state == RobotConfig.robq2:
                        self.recv_command(command, 'success', rob, reason=None)
                        action_log(command + "_start", rob.map_no, self.time, rob.act_file_name)
                        self.recv_command(command, 'completed', rob, reason=None)
                        action_log(command + "_completed", rob.map_no, self.time, rob.act_file_name)
                elif command == RobotConfig.GET_OFF:
                    if rob.set_elv_getting_off_status():
                        self.recv_command(command, 'success', rob, reason=None)
                        rob.bot_dt_send_time = 10
                        rob.bot_pos_log_time = 5
                        self.task_lists[rob_name].insert(-1, RobotConfig.GET_OFF)
                        action_log(command + "_start", rob.map_no, self.time, rob.act_file_name)
                        self.rob_dt_data[rob_name] = rob.get_rob_status()
                        rob_communication_log(command, rob.floor, self.rob_dt_data[rob_name], self.time,
                                              rob.communication_file_name, message_type='rob')
                    elif rob.state == RobotConfig.robq0:
                        self.recv_command(command, 'success', rob, reason=None)
                        action_log(command + "_start", rob.map_no, self.time, rob.act_file_name)
                        self.recv_command(command, 'completed', rob, reason=None)
                        action_log(command + "_completed", rob.map_no, self.time, rob.act_file_name)
                elif command == RobotConfig.ELVStay:
                    if rob.set_elv_stay_status():
                        self.recv_command(command, 'success', rob, reason=None)
                        self.send_rob_dt(rob_name)
                        self.task_lists[rob_name].insert(-1, RobotConfig.ELVStay)
                        action_log(command + "_start", rob.map_no, self.time, rob.act_file_name)
                elif command == RobotConfig.CHARGE:
                    if rob.set_go_to_charge_status():
                        self.recv_command(command, 'success', rob, reason=None)
                        self.task_lists[rob_name].insert(-1, RobotConfig.CHARGE)
                        action_log(command + "_start", rob.map_no, self.time, rob.act_file_name)
                elif command == RobotConfig.Schedule_Work:
                    if rob.set_schedule_work_status():
                        self.recv_command(command, 'success', rob, reason=None)
                        self.task_lists[rob_name].insert(-1, RobotConfig.Schedule_Work)
                        action_log(command + "_start", rob.map_no, self.time, rob.act_file_name)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")




