"""
The basic function is consistent with mqtt_communication_module/elvmsghandler.py.
"""
import json
from device_motion_module.elevator import ElvHandler
from mqtt_communication_module.elvmsghandler import ElvMessageHandler
from utils.storyboard import CmdConfig, ELVConfig
from utils.msglog import msg_log, action_log


class FElvMessageHandler(ElvMessageHandler):
    def __init__(self, send_topic, recv_topic, broker, port, elevator, time):
        super().__init__(send_topic, recv_topic, broker, port, elevator, time)
        self.elevator = ElvHandler()

    def send_dt_elv(self):
        elv_status = self.elevator.find_elv().get_elv_status()
        dt = self.send_dtdata_instance.dt_elevator(elv_status)
        self.send(dt, self.send_dt_topic, self.time, file_path=self.file_path)

    def check_current_floor(self, max_retries=5, retry_interval=2):
        retries = 0
        while retries < max_retries:
            if self.elevator.find_elv().get_elv_status()[ELVConfig.FLOOR]:
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

            msg_log(msg.topic, payload, self.time, self.file_path)
            if command in self.cmd_list:
                    return
            if command == CmdConfig.INTERLOCK:
                interlock_value = payload.get(CmdConfig.INTERLOCK)
                current_permission = self.elevator.find_elv().get_elv_status()[ELVConfig.INDRIVING_PERMISSION]
                if self.elevator.find_elv().get_elv_status()[ELVConfig.STATE] == ELVConfig.elvq0 and not current_permission and interlock_value:
                    if self.elevator.find_elv().set_interlock(interlock_value):  
                        self.recv_command_response(CmdConfig.INTERLOCK_TRUE, CmdConfig.SUCCESS)
                        action_log(command +"_"+ str(interlock_value), self.elevator.find_elv().current_floor, self.time, self.elevator.find_elv().act_log)
                elif self.elevator.find_elv().get_elv_status()[ELVConfig.STATE] == ELVConfig.elvq7 and current_permission and not interlock_value:
                    if self.elevator.find_elv().set_interlock(interlock_value):
                        self.recv_command_response(CmdConfig.INTERLOCK_FALSE, CmdConfig.SUCCESS)
                        action_log(command +"_"+ str(interlock_value), self.elevator.find_elv().current_floor, self.time, self.elevator.find_elv().act_log)
                elif self.elevator.find_elv().get_elv_status()[ELVConfig.STATE] == ELVConfig.elvq1 and current_permission and interlock_value:
                    if self.elevator.find_elv().set_interlock(interlock_value):
                        self.recv_command_response(CmdConfig.INTERLOCK_TRUE, CmdConfig.SUCCESS)
                        action_log(command +"_"+ str(interlock_value), self.elevator.find_elv().current_floor, self.time, self.elevator.find_elv().act_log)
                elif self.elevator.find_elv().get_elv_status()[ELVConfig.STATE] == ELVConfig.elvq0 and not current_permission and not interlock_value:
                    if self.elevator.find_elv().set_interlock(interlock_value):
                        self.recv_command_response(CmdConfig.INTERLOCK_FALSE, CmdConfig.SUCCESS)
                        action_log(command +"_"+ str(interlock_value), self.elevator.find_elv().current_floor, self.time, self.elevator.find_elv().act_log)

            elif command == CmdConfig.CALL:
                current_floor = self.elevator.find_elv().get_elv_status()[ELVConfig.FLOOR]
                if not self.cmd_list or self.cmd_list[-1][0] != CmdConfig.CALL:
                    if current_floor != target_floor: 
                        if self.elevator.find_elv().call_elv(target_floor, moving_status):
                            self.recv_command_response(CmdConfig.CALL, CmdConfig.ACCEPT)
                            self.cmd_list.append([command, target_floor])
                            action_log(command + " target: " + str(target_floor) + " floor", self.elevator.find_elv().current_floor, self.time, self.elevator.find_elv().act_log)
                        elif self.elevator.find_elv().state == ELVConfig.elvq2:
                            self.elevator.find_elv().state = ELVConfig.elvq1
                            if self.elevator.find_elv().call_elv(target_floor, moving_status):
                                self.recv_command_response(CmdConfig.CALL, CmdConfig.ACCEPT)
                                self.cmd_list.append([command, target_floor])
                                action_log(command + " target: " + str(target_floor) + " floor", self.elevator.find_elv().current_floor, self.time, self.elevator.find_elv().act_log) 
                    elif self.elevator.find_elv().state == ELVConfig.elvq1 or self.elevator.find_elv().state == ELVConfig.elvq2:
                        self.recv_command_response(CmdConfig.CALL, CmdConfig.ACCEPT)
                        action_log(command + " target: " + str(target_floor) + " floor", self.elevator.find_elv().current_floor, self.time, self.elevator.find_elv().act_log)
                        self.elevator.find_elv().state = ELVConfig.elvq2
                        self.time.sleep(0.1)
                        self.recv_command_response(CmdConfig.CALL, CmdConfig.ARRIVE)
                        action_log(command + " arrive: " + str(target_floor) + " floor", self.elevator.find_elv().current_floor, self.time, self.elevator.find_elv().act_log)

            elif command == CmdConfig.OPEN:
                if not self.cmd_list:
                    if self.elevator.find_elv().open_door():
                        self.recv_command_response(CmdConfig.OPEN, CmdConfig.SUCCESS)
                        action_log(command, self.elevator.find_elv().current_floor, self.time, self.elevator.find_elv().act_log)
                    elif self.elevator.find_elv().state == ELVConfig.elvq3:
                        self.elevator.find_elv().state = ELVConfig.elvq2
                        if self.elevator.find_elv().open_door():
                            self.recv_command_response(CmdConfig.OPEN, CmdConfig.SUCCESS)
                            action_log(command, self.elevator.find_elv().current_floor, self.time, self.elevator.find_elv().act_log)
                    elif self.elevator.find_elv().state == ELVConfig.elvq6:
                        self.elevator.find_elv().state = ELVConfig.elvq5
                        if self.elevator.find_elv().open_door():
                            self.recv_command_response(CmdConfig.OPEN, CmdConfig.SUCCESS)
                            action_log(command, self.elevator.find_elv().current_floor, self.time, self.elevator.find_elv().act_log)


            elif command == CmdConfig.CLOSE:
                if not self.cmd_list:
                    if self.elevator.find_elv().close_door():
                        self.recv_command_response(CmdConfig.CLOSE, CmdConfig.SUCCESS)
                        action_log(command, self.elevator.find_elv().current_floor, self.time, self.elevator.find_elv().act_log)

            elif command == CmdConfig.GO:
                current_floor = self.elevator.find_elv().get_elv_status()[ELVConfig.FLOOR]
                if not self.cmd_list or self.cmd_list[-1][0] != CmdConfig.GO:
                    if self.elevator.find_elv().elv_go(target_floor):
                        self.recv_command_response(CmdConfig.GO, CmdConfig.ACCEPT)
                        self.cmd_list.append([command, target_floor])
                        action_log(command +' target:'+ str(target_floor) + " floor", self.elevator.find_elv().current_floor, self.time, self.elevator.find_elv().act_log)
                    elif self.elevator.find_elv().state == ELVConfig.elvq5:
                            self.elevator.find_elv().state = ELVConfig.elvq4
                            if self.elevator.find_elv().elv_go(target_floor):
                                self.recv_command_response(CmdConfig.GO, CmdConfig.ACCEPT)
                                self.cmd_list.append([command, target_floor])
                                action_log(command +' target:'+ str(target_floor) + " floor", self.elevator.find_elv().current_floor, self.time, self.elevator.find_elv().act_log)

        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
