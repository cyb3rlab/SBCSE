import json
import socket
import paho.mqtt.client as mqtt
from device_motion_module.elevator import Elevator
from mqtt_communication_module.mqtt_msghandler import MessageHandler
from mqtt_communication_module.data_model import RecvCommandData, ElvDtData, SendCommandData
from utils.storyboard import LogConfig, MqttConfig, CmdConfig, ELVConfig, StateMachineConfig
from utils.msglog import msg_log, log_id, action_log
from utils.utils import load_ip_config
from formal_verification.FV import maude_class_monitor, maude_fnuc_monitor

# Define the ELV class for ELV component communication
# @maude_class_monitor(PID='ELV', ocom_statuses=['recv_cmd'])
class ElvMessageHandler(MessageHandler):
    def __init__(self, send_topic, recv_topic, broker, port, elevator, time):
        self.port = port
        self.broker = broker
        self.client_ip_list = MqttConfig.client_ip
        self.client_ip = None
        self.client_port = None
        self.time = time
        self.file_path = LogConfig.FILE_ELV_LOG  # File path for ELV logging
        self.runtime_file = LogConfig.RUNTIME_REPORT
        self.send_dtdata_instance = ElvDtData(time.time())  # instance for sending dt_data
        self.send_data_instance = RecvCommandData()  # Instance for sending （E2D success） command data
        self.recv_data_instance = SendCommandData()  # Instance for receiving （D2E recv data）
        self.send_dt_topic = send_topic[0]  # Topic for E2D dt data
        self.send_cmd_arrive_topic = send_topic[1]  # Topic for E2D recv cmd success
        self.recv_topic = recv_topic[0]  # Topic for D2E cmd
        self.elevator = elevator  # Elevator instance
        self.port = port
        self.session_id = "elv001"  # Session ID
        self.cmd_list = []
        enable_allowlist = False
        self.elv_id = "ELV"

        use_mqtts = (port == 8883)
        cert_path = key_path = ca_path = None

        if use_mqtts:
            cert_path = MqttConfig.CRT
            key_path = MqttConfig.KEY
            ca_path = MqttConfig.CA

        self.client_ip_port = None
        super().__init__(send_topic, recv_topic, broker, port, use_mqtts, enable_allowlist, cert_path, key_path, ca_path,  self.client_ip)



    def bind_client_to_port(self):
        """Bind the client to a static IP"""
        try:
            local_ip = self.client_ip_list.get(self.elv_id, "192.168.0.102")  # Use default IP if not found

            # Bind to this IP (using dynamic ports)
            local_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            local_socket.bind((local_ip, 0))  # IP binding, automatic allocation of available ports

            # Binding MQTT Clients
            self.client_ip, self.client_port = local_socket.getsockname()
            client_info = f"{self.elv_id} bound to {self.client_ip}:{self.client_port} ++++++++++++++++"
            print(client_info)
            log_id(self.runtime_file,client_info)

            return self.client_ip
        except Exception as e:
            print(f"Error binding client {self.elv_id}: {e}")
            return None


    def on_connect(self, client, userdata, flags, rc):
        # Called when the client connects to the broker
        super().on_connect(client, userdata, flags, rc)
        recv_topics = [(self.recv_topic, 1)]
        for topic, qos in recv_topics:
            self.client.subscribe(topic=topic, qos=1)

    def send_dt_elv(self):
        # Sends elevator status data
        elv_status = self.elevator.get_elv_status()
        dt = self.send_dtdata_instance.dt_elevator(elv_status)
        self.send(dt, self.send_dt_topic, self.time, file_path=self.file_path)

    # @maude_fnuc_monitor
    def recv_command_response(self, command, result):
        # General function to receive command response arrive/success/accept
        method_map = CmdConfig.METHOD_MAP
        if command in method_map:
            methods = method_map[command]
            if isinstance(methods, tuple):
                for method_name in methods:
                    if method_name.endswith(result):
                        method = getattr(self.send_data_instance, method_name, None)
                        if method:
                            data = method()
                            self.send(data, topic=self.send_cmd_arrive_topic, time_sim=self.time, file_path=self.file_path)
                            break
            else:
                method_name = f"{command}_command_{result}"
                method = getattr(self.send_data_instance, method_name, None)
                if method:
                    data = method()
                    self.send(data, topic=self.send_cmd_arrive_topic, time_sim=self.time, file_path=self.file_path)

    def check_current_floor(self, max_retries=5, retry_interval=2):
        # Check the current floor status with retries
        retries = 0
        while retries < max_retries:
            if self.elevator.get_elv_status()[ELVConfig.FLOOR]:
                return True
            retries += 1
            self.time.sleep(retry_interval)
        return False

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload)
            command = payload.get(CmdConfig.COMMAND)
            target_floor = int(payload.get(ELVConfig.FLOOR)) if payload.get(ELVConfig.FLOOR) else None
            moving_status = payload.get(ELVConfig.DIRECTION)

            # Update elevator status in log
            msg_log(msg.topic, payload, self.time, self.file_path)

            if command == CmdConfig.INTERLOCK:
                interlock_value = payload.get(CmdConfig.INTERLOCK)
                current_permission = self.elevator.get_elv_status()[ELVConfig.INDRIVING_PERMISSION]
                if current_permission != interlock_value:
                    self.elevator.set_interlock(interlock_value)
                    if interlock_value:
                        self.recv_command_response(CmdConfig.INTERLOCK_TRUE, CmdConfig.SUCCESS)
                    else:
                        self.recv_command_response(CmdConfig.INTERLOCK_FALSE, CmdConfig.SUCCESS)
                    

            elif command == CmdConfig.CALL:
                self.recv_command_response(CmdConfig.CALL, CmdConfig.ACCEPT)
                current_floor = self.elevator.get_elv_status()[ELVConfig.FLOOR]
                if current_floor != target_floor:
                    if not self.cmd_list or self.cmd_list[-1][0] != CmdConfig.CALL:
                        self.elevator.call_elv(target_floor, moving_status)
                        self.cmd_list.append([command, target_floor])
                else:
                    self.recv_command_response(CmdConfig.CALL, CmdConfig.ARRIVE)


            elif command == CmdConfig.OPEN:
                self.elevator.open_door()
                self.recv_command_response(CmdConfig.OPEN, CmdConfig.SUCCESS)

            elif command == CmdConfig.CLOSE:
                self.elevator.close_door()
                self.recv_command_response(CmdConfig.CLOSE, CmdConfig.SUCCESS)

            elif command == CmdConfig.GO:
                self.recv_command_response(CmdConfig.GO, CmdConfig.ACCEPT)
                current_floor = self.elevator.get_elv_status()[ELVConfig.FLOOR]
                if not self.cmd_list or self.cmd_list[-1][0] != CmdConfig.GO:
                    self.elevator.elv_go(target_floor)
                    self.cmd_list.append([command, target_floor])

        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")

    def fm_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload)
            # print(f"Received message: {payload}")
            command = payload.get(CmdConfig.COMMAND)
            target_floor = int(payload.get(ELVConfig.FLOOR)) if payload.get(ELVConfig.FLOOR) else None
            moving_status = payload.get(ELVConfig.DIRECTION)

            # Update elevator status in log
            msg_log(msg.topic, payload, self.time, self.file_path)
            if command in self.cmd_list:
                return
            if command == CmdConfig.INTERLOCK:
                interlock_value = payload.get(CmdConfig.INTERLOCK)
                self.recv_cmd = command + str(interlock_value)
                current_permission = self.elevator.get_elv_status()[ELVConfig.INDRIVING_PERMISSION]
                if self.elevator.get_elv_status()[
                    ELVConfig.STATE] == ELVConfig.elvq0 and not current_permission and interlock_value:
                    if self.elevator.set_interlock(interlock_value):
                        self.recv_command_response(CmdConfig.INTERLOCK_TRUE, CmdConfig.SUCCESS)
                        action_log(command + "_" + str(interlock_value), self.elevator.current_floor, self.time,
                                   self.elevator.act_log)
                elif self.elevator.get_elv_status()[
                    ELVConfig.STATE] == ELVConfig.elvq7 and current_permission and not interlock_value:
                    if self.elevator.set_interlock(interlock_value):
                        self.recv_command_response(CmdConfig.INTERLOCK_FALSE, CmdConfig.SUCCESS)
                        action_log(command + "_" + str(interlock_value), self.elevator.current_floor, self.time,
                                   self.elevator.act_log)
                elif self.elevator.get_elv_status()[
                    ELVConfig.STATE] == ELVConfig.elvq1 and current_permission and interlock_value:
                    if self.elevator.set_interlock(interlock_value):
                        self.recv_command_response(CmdConfig.INTERLOCK_TRUE, CmdConfig.SUCCESS)
                        action_log(command + "_" + str(interlock_value), self.elevator.current_floor, self.time,
                                   self.elevator.act_log)
                elif self.elevator.get_elv_status()[
                    ELVConfig.STATE] == ELVConfig.elvq0 and not current_permission and not interlock_value:
                    if self.elevator.set_interlock(interlock_value):
                        self.recv_command_response(CmdConfig.INTERLOCK_FALSE, CmdConfig.SUCCESS)
                        action_log(command + "_" + str(interlock_value), self.elevator.current_floor, self.time,
                                   self.elevator.act_log)

            elif command == CmdConfig.CALL:
                if not self.cmd_list or self.cmd_list[-1][0] != CmdConfig.CALL:
                    self.recv_cmd = command
                    current_floor = self.elevator.get_elv_status()[ELVConfig.FLOOR]
                    if current_floor != target_floor:
                        if self.elevator.call_elv(target_floor, moving_status):
                            self.recv_command_response(CmdConfig.CALL, CmdConfig.ACCEPT)
                            self.cmd_list.append([command, target_floor])
                            action_log(command + " target: " + str(target_floor) + " floor",
                                       self.elevator.current_floor, self.time, self.elevator.act_log)
                        elif self.elevator.state == ELVConfig.elvq2:
                            self.elevator.state = ELVConfig.elvq1
                            if self.elevator.call_elv(target_floor, moving_status):
                                self.recv_command_response(CmdConfig.CALL, CmdConfig.ACCEPT)
                                self.cmd_list.append([command, target_floor])
                                action_log(command + " target: " + str(target_floor) + " floor",
                                           self.elevator.current_floor, self.time, self.elevator.act_log)
                    elif self.elevator.state == ELVConfig.elvq1 or self.elevator.state == ELVConfig.elvq2:
                        self.recv_command_response(CmdConfig.CALL, CmdConfig.ACCEPT)
                        action_log(command + " target: " + str(target_floor) + " floor", self.elevator.current_floor,
                                   self.time, self.elevator.act_log)
                        self.elevator.state = ELVConfig.elvq2
                        self.time.sleep(0.1)
                        self.recv_command_response(CmdConfig.CALL, CmdConfig.ARRIVE)
                        action_log(command + " arrive: " + str(target_floor) + " floor", self.elevator.current_floor,
                                   self.time, self.elevator.act_log)

            elif command == CmdConfig.OPEN:
                if not self.cmd_list:
                    self.recv_cmd = command
                    if self.elevator.open_door():
                        self.recv_command_response(CmdConfig.OPEN, CmdConfig.SUCCESS)
                        action_log(command, self.elevator.current_floor, self.time, self.elevator.act_log)

            elif command == CmdConfig.CLOSE:
                if not self.cmd_list:
                    self.recv_cmd = command
                    if self.elevator.close_door():
                        self.recv_command_response(CmdConfig.CLOSE, CmdConfig.SUCCESS)
                        action_log(command, self.elevator.current_floor, self.time, self.elevator.act_log)

            elif command == CmdConfig.GO:
                if not self.cmd_list or self.cmd_list[-1][0] != CmdConfig.GO:
                    self.recv_cmd = command
                    current_floor = self.elevator.get_elv_status()[ELVConfig.FLOOR]
                    if self.elevator.elv_go(target_floor):
                        self.recv_command_response(CmdConfig.GO, CmdConfig.ACCEPT)
                        self.cmd_list.append([command, target_floor])
                        action_log(command + ' target:' + str(target_floor) + " floor", self.elevator.current_floor,
                                   self.time, self.elevator.act_log)
                    elif self.elevator.state == ELVConfig.elvq5:
                        self.elevator.state = ELVConfig.elvq4
                        if self.elevator.elv_go(target_floor):
                            self.recv_command_response(CmdConfig.GO, CmdConfig.ACCEPT)
                            self.cmd_list.append([command, target_floor])
                            action_log(command + ' target:' + str(target_floor) + " floor", self.elevator.current_floor,
                                       self.time, self.elevator.act_log)

        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")

