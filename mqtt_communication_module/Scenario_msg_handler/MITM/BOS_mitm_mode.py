import json
from mqtt_communication_module.Scenario_msg_handler.base_handler.BOS_base_handler import BOS_ModeHandler
from utils.msglog import msg_log
from utils.storyboard import CmdConfig


class BOSMitmMode(BOS_ModeHandler):
    def handle_msg(self, client, userdata, msg):
        self.bos_handler.fake_open_response_sent = False
        payload = json.loads(msg.payload)
        msg_log(msg.topic, payload, self.bos_handler.time, self.bos_handler.file_path)
        command = payload.get("command")

        if msg.topic == self.bos_handler.recv_ELV_DT:
            if command == "open" and not self.bos_handler.close_success:
                payload["door_status"] = "open"
            self.bos_handler.dt_received = True
            self.bos_handler.forward_message(msg.topic, payload)

        elif msg.topic == self.bos_handler.recv_B2D:
            if command == "open":
                # Send fake open success response
                msg = "Send fake open success response-----"
                fake_response = {
                    "command": "open",
                    "result": "success"
                }
                self.bos_handler.forward_message(self.bos_handler.recv_E2D, fake_response)
                self.bos_handler.fake_open_response_sent = True
                self.bos_handler.open_success = True
                return
            elif command == "close":
                self.close_success = True
                self.fake_open_response_sent = False  # Reset for next open command
                self.bos_handler.forward_message(msg.topic, payload)
            else:
                self.bos_handler.forward_message(msg.topic, payload)

        elif msg.topic == self.bos_handler.recv_E2D:  # E2D
            if payload.get(CmdConfig.RESULT) in [CmdConfig.SUCCESS, CmdConfig.ACCEPT, CmdConfig.ARRIVE]:
                # self.observe_dt_status(self.time)
                command = payload.get(CmdConfig.COMMAND)
                # self.recv_command_response(command)

                if command == CmdConfig.INTERLOCK:
                    self.interlock_success = True
                elif command == CmdConfig.CALL:
                    self.call_accept = True
                elif command == CmdConfig.OPEN:
                    self.open_success = True
                elif command == CmdConfig.CLOSE:
                    self.close_success = True
                elif command == CmdConfig.GO:
                    self.go_accept = True
                self.bos_handler.forward_message(msg.topic, payload)