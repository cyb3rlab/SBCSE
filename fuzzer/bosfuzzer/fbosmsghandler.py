"""
The basic function is consistent with mqtt_communication_module/bosmsghandler.py.
"""
import sys
from mqtt_communication_module.data_model import SendCommandData, RecvCommandData, ElvDtData
from mqtt_communication_module.mqtt_msghandler import MessageHandler
from utils.storyboard import LogConfig, CmdConfig, ELVConfig, Mode, MqttConfig
from utils.msglog import msg_log
import json
from fuzzer.bosfuzzer.fbosnormalmode import FBosNormalMode
import atheris

class FBosMessageHandler(MessageHandler):
    def __init__(self, send_topic, recv_topic, broker, port, time):
        self.file_path = LogConfig.FILE_BOS_LOG
        self.runtime_file = LogConfig.RUNTIME_REPORT
        self.time = time
        self.port = port
        self.broker = broker
        self.client_ip_list = MqttConfig.client_ip
        self.client_ip = None
        self.bos_id = "BOS"

        self.recv_data_instance = RecvCommandData()
        self.send_data_instance = SendCommandData()
        self.dt_data_instance = ElvDtData(self.time)
        self.send_D2E = send_topic[0]
        self.send_D2B = send_topic[1]
        self.send_T3 = send_topic[2]
        self.recv_ELV_DT = recv_topic[0]
        self.recv_E2D = recv_topic[1]
        self.recv_B2D = recv_topic[2]

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

        self.mode = Mode.FUZZING

        self.mode_handlers = {
            Mode.FUZZING: FBosNormalMode(self),
        }

        self.fdp = None
        self.stop_event = None
        self.forward_message_list = []
        
        use_mqtts = (port == 8883)
        cert_path = key_path = ca_path = None

        if use_mqtts:
            cert_path = MqttConfig.CRT
            key_path = MqttConfig.KEY
            ca_path = MqttConfig.CA

        self.client_ip_port = None
        super().__init__(send_topic, recv_topic, broker, port, use_mqtts, cert_path, key_path, ca_path)

    def on_connect(self, client, userdata, flags, rc):
        super().on_connect(client, userdata, flags, rc)
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
        return
    
    def forward_message(self, topic, msg, fdp):
        while not self.forward_message_list and not self.stop_event.is_set():
            pass
        if self.stop_event.is_set():
            return
        topic = self.forward_message_list[0][0]
        msg = self.forward_message_list[0][1]
        self.forward_message_list.pop(0)
        
        if topic == self.recv_B2D:
            new_topic = self.send_D2E
            value = fdp.ConsumeBool()
            target_floor = fdp.ConsumeIntInRange(2, 11)
            direction = fdp.PickValueInList([ELVConfig.UP, ELVConfig.DOWN, ELVConfig.STAY])
            msg = fdp.PickValueInList([SendCommandData('fuzz').interlock_command(value), 
                                             SendCommandData('fuzz').call_command(target_floor, direction), 
                                             SendCommandData('fuzz').open_command(), 
                                             SendCommandData('fuzz').close_command(), 
                                             SendCommandData('fuzz').go_command(target_floor)])
            self.send(msg, new_topic, self.time, file_path=self.file_path)
        elif topic == self.recv_E2D:
            new_topic = self.send_D2B
            value = fdp.ConsumeBool()
            target_floor = fdp.ConsumeIntInRange(2, 11)
            direction = fdp.PickValueInList([ELVConfig.UP, ELVConfig.DOWN, ELVConfig.STAY])
            msg = fdp.PickValueInList([RecvCommandData('fuzz').interlock_true_command_success(), 
                                            RecvCommandData('fuzz').interlock_false_command_success(), 
                                            RecvCommandData('fuzz').call_command_accept(), 
                                            RecvCommandData('fuzz').call_command_arrive(), 
                                            RecvCommandData('fuzz').open_command_success(), 
                                            RecvCommandData('fuzz').close_command_success(), 
                                            RecvCommandData('fuzz').go_command_arrive(),
                                            RecvCommandData('fuzz').go_command_accept()
                                            ])
            self.send(msg, new_topic, self.time, file_path=self.file_path)
        elif topic == self.recv_ELV_DT:
            new_topic = self.send_T3
            msg = {
            "floor": fdp.ConsumeIntInRange(2, 11),
            "door": fdp.PickValueInList(['open', 'close']),
            "movingStatus": fdp.PickValueInList(['stay','up', 'down']),
            "inService": True,
            "inDrivingPermission": fdp.PickValueInList([True, False]),
            "answerBack": False,
            "trouble": False,
            "time": int(self.time.current_timestamp())
            }
            self.send(msg, new_topic, self.time, file_path=self.file_path)
        print(msg, file=sys.stderr)

    def on_message(self, client, userdata, msg):
        if self.mode in self.mode_handlers:
            self.mode_handlers[self.mode].handle_msg(client, userdata, msg)
        else:
            print(f"Unsupported mode: {self.mode}")