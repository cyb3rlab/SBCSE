import socket
from mqtt_communication_module.data_model import SendCommandData, RecvCommandData, ElvDtData
from mqtt_communication_module.mqtt_msghandler import MessageHandler
from utils.storyboard import LogConfig, CmdConfig, ELVConfig, Mode, MqttConfig
from utils.msglog import msg_log, log_id
from mqtt_communication_module.Scenario_msg_handler.Normal_mode.BOS_normal_mode import BosNormalMode
from mqtt_communication_module.Scenario_msg_handler.MITM.BOS_mitm_mode import BOSMitmMode
from mqtt_communication_module.Scenario_msg_handler.BAC.BOS_bac_mode import BOSBacMode
from formal_verification.FV import maude_class_monitor

# Define the BOS class for Building OS component communication
# @maude_class_monitor(PID='BOS', ocom_statuses=['recv_cmd'])
class BosMessageHandler(MessageHandler):
    def __init__(self, send_topic, recv_topic, broker, port, time):
        # super().__init__(send_topic, recv_topics, broker, port)
        self.file_path = LogConfig.FILE_BOS_LOG
        self.runtime_file = LogConfig.RUNTIME_REPORT
        self.time = time
        self.port = port
        self.broker = broker
        self.client_ip_list = MqttConfig.client_ip
        self.client_ip = None
        self.bos_id = "BOS"

        self.recv_data_instance = RecvCommandData()  # D2B  cmd_response
        self.send_data_instance = SendCommandData()  # B2D D2E cmd_data
        self.dt_data_instance = ElvDtData(self.time)
        self.send_D2E = send_topic[0]  # D2E
        self.send_D2B = send_topic[1]  # D2B
        self.send_T3 = send_topic[2]  # forward elv dt data to rpf
        self.recv_ELV_DT = recv_topic[0]  # dt data
        self.recv_E2D = recv_topic[1]  # E2D
        self.recv_B2D = recv_topic[2]  # B2D

        self.recv_topics = recv_topic
        self.response_sent = False
        self.dt_received = False
        self.interlock_success = False
        self.open_success = False
        self.close_success = False
        self.call_accept = False
        self.go_accept = False
        self.response_timer = None
        enable_allowlist = False

        # Add mode to control attack
        self.mode = Mode.Normal  # The default setting is normal

        self.mode_handlers = {
            Mode.Normal: BosNormalMode(self),
            Mode.MITM: BOSMitmMode(self),
            Mode.BAC: BOSBacMode(self)
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
        """Bind Client to Static IP"""
        try:
            local_ip = self.client_ip_list.get(self.bos_id, "192.168.0.102")  # Use default IP if not found
            # Bind to this IP (using dynamic ports)
            local_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            local_socket.bind((local_ip, 0))  # IP binding, automatic allocation of available ports
            # Bind the MQTT client
            self.client_ip, self.client_port = local_socket.getsockname()
            client_info = f"{self.bos_id} bound to {self.client_ip}:{self.client_port} ++++++++++++++++"
            print(client_info)
            log_id(self.runtime_file, client_info)

            return self.client_ip
        except Exception as e:
            print(f"Error binding client {self.bos_id}: {e}")
            return None

    def set_mode(self, mode):
        # method to set current mode
        self.mode = mode

    def on_connect(self, client, userdata, flags, rc):
        super().on_connect(client, userdata, flags, rc)
        # Subscribe to recv_topics/qos
        recv_topics = [(self.recv_ELV_DT, 1), (self.recv_E2D, 1), (self.recv_B2D, 1)]
        for topic, qos in recv_topics:
            self.client.subscribe(topic=topic, qos=1)

    def observe_dt_status(self, time_sim):
        while not self.dt_received:
            time_sim.sleep(1)
        self.dt_received = False

    def dt_received_from_elevator(self, latest_dt_data):
        if latest_dt_data:
            command = latest_dt_data.get(CmdConfig.COMMAND)
            if command == CmdConfig.INTERLOCK:
                if latest_dt_data.get(CmdConfig.INTERLOCK) == True:
                    return True
            elif command == CmdConfig.CALL:
                if latest_dt_data.get(ELVConfig.FLOOR) == latest_dt_data.get(ELVConfig.FLOOR):
                    return True
            elif command == CmdConfig.OPEN:
                if latest_dt_data.get(ELVConfig.DOOR) == CmdConfig.OPEN:
                    return True
            elif command == CmdConfig.CLOSE:
                if latest_dt_data.get(ELVConfig.DOOR) == CmdConfig.CLOSE:
                    return True
            elif command == CmdConfig.GO:
                if latest_dt_data.get(ELVConfig.FLOOR) == latest_dt_data.get(ELVConfig.FLOOR):
                    return True

        return False

    def recv_command_response(self, command, data_dict):
        method_name = f"recv_{command}_command"
        if hasattr(self.recv_data_instance, method_name):
            method = getattr(self.recv_data_instance, method_name)
            data = method(data_dict) if data_dict else method()
            msg_log(self.send_D2B, data, time_sim=self.time, file_path=self.file_path)

    def forward_message(self, topic, msg):
        if topic == self.recv_B2D:  # B2D
            new_topic = self.send_D2E  # D2E
            command = msg.get(CmdConfig.COMMAND)
            self.recv_cmd = command
            self.send(msg, new_topic, self.time, file_path=self.file_path)
        elif topic == self.recv_E2D:  # E2D
            new_topic = self.send_D2B  # D2B
            command = msg.get(CmdConfig.COMMAND)
            self.recv_cmd = command
            self.send(msg, new_topic, self.time, file_path=self.file_path)
        elif topic == self.recv_ELV_DT:  # dt
            new_topic = self.send_T3  # D2B
            self.send(msg, new_topic, self.time, file_path=self.file_path)

    def on_message(self, client, userdata, msg):
        if self.mode in self.mode_handlers:
            self.mode_handlers[self.mode].handle_msg(client, userdata, msg)
        else:
            print(f"Unsupported mode: {self.mode}")
