import json
from mqtt_communication_module.Scenario_msg_handler.base_handler.BOS_base_handler import BOS_ModeHandler
from utils.msglog import msg_log
from utils.storyboard import CmdConfig, ClientConfig


class BOSBacMode(BOS_ModeHandler):
    def handle_msg(self, client, userdata, msg):
        self.bos_handler.fake_close_cmd_sent = False
        payload = json.loads(msg.payload)
        msg_log(msg.topic, payload, self.bos_handler.time, self.bos_handler.file_path)
        command = payload.get("command")

        if msg.topic == self.bos_handler.recv_ELV_DT:
            if command == "open" and not self.bos_handler.close_success:
                payload["door_status"] = "open"
            self.bos_handler.dt_received = True
            self.bos_handler.forward_message(msg.topic, payload)

        elif msg.topic == self.bos_handler.recv_B2D:
            if self.bos_handler.go_accept and command == "open":
                # Send fake close response to elv
                fake_response = {
                    "sessionId": ClientConfig.SESSION_ID,
                    "clientId": ClientConfig.CLIENT_ID,
                    "token": ClientConfig.TOKEN,
                    "command": 'close',
                }
                self.bos_handler.forward_message(self.bos_handler.recv_B2D, fake_response)
                self.bos_handler.fake_close_cmd_sent = True
                return
            else:
                self.bos_handler.forward_message(msg.topic, payload)

        elif msg.topic == self.bos_handler.recv_E2D:  # E2D
            if payload.get(CmdConfig.RESULT) in [CmdConfig.SUCCESS, CmdConfig.ACCEPT, CmdConfig.ARRIVE]:
                # self.observe_dt_status(self.time)
                command = payload.get(CmdConfig.COMMAND)
                # self.recv_command_response(command)

                if command == CmdConfig.INTERLOCK_TRUE:
                    self.bos_handler.interlock_success = True
                    self.bos_handler.forward_message(msg.topic, payload)
                elif command == CmdConfig.CALL:
                    self.bos_handler.call_accept = True
                    self.bos_handler.forward_message(msg.topic, payload)
                elif command == CmdConfig.OPEN:
                    self.bos_handler.open_success = True
                    self.bos_handler.forward_message(msg.topic, payload)
                elif command == CmdConfig.CLOSE:
                    if self.bos_handler.go_accept:
                        fake_success_response = {
                            "command": "open",
                            "result": "success"
                        }
                        self.bos_handler.forward_message(self.bos_handler.recv_E2D, fake_success_response)
                        self.bos_handler.open_success = True
                    else:
                        self.bos_handler.close_success = True
                        self.bos_handler.forward_message(msg.topic, payload)

                elif command == CmdConfig.GO:
                    self.bos_handler.go_accept = True
                    self.bos_handler.forward_message(msg.topic, payload)

