import json
from mqtt_communication_module.Scenario_msg_handler.base_handler.BOS_base_handler import BOS_ModeHandler
from utils.msglog import msg_log
from utils.storyboard import CmdConfig


class BosNormalMode(BOS_ModeHandler):

    def handle_msg(self, client, userdata, msg):
        payload = json.loads(msg.payload)
        msg_log(msg.topic, payload, self.bos_handler.time, self.bos_handler.file_path)

        if msg.topic == self.bos_handler.recv_ELV_DT:
            self.bos_handler.dt_received = True

        elif msg.topic == self.bos_handler.recv_E2D:
            if payload.get(CmdConfig.RESULT) in [CmdConfig.SUCCESS, CmdConfig.ACCEPT, CmdConfig.ARRIVE]:
                command = payload.get(CmdConfig.COMMAND)
                if command == CmdConfig.INTERLOCK:
                    self.bos_handler.interlock_success = True
                elif command == CmdConfig.CALL:
                    self.bos_handler.call_accept = True
                elif command == CmdConfig.OPEN:
                    self.bos_handler.open_success = True
                elif command == CmdConfig.CLOSE:
                    self.bos_handler.close_success = True
                elif command == CmdConfig.GO:
                    self.bos_handler.go_accept = True

        self.bos_handler.forward_message(msg.topic, payload)
