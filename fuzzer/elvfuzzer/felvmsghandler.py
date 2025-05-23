"""
The basic function is consistent with mqtt_communication_module/elvmsghandler.py.
"""
import json
import sys
from mqtt_communication_module.elvmsghandler import ElvMessageHandler
from mqtt_communication_module.data_model import RecvCommandData
from utils.storyboard import CmdConfig, ELVConfig
from utils.msglog import msg_log, action_log

class FElvMessageHandler(ElvMessageHandler):
    def __init__(self, send_topic, recv_topic, broker, port, elevator, time):
        super().__init__(send_topic, recv_topic, broker, port, elevator, time)
        self.fdp1 = None
        self.fdp2 = None
        self.stop_event = None
        self.msg_count = 0
    
    def is_fdp(self):
        if not self.fdp1 or not self.fdp2:
            return True
        else:
            return False

    def set_fdp(self, fdp):
        if self.fdp1 == None:    
            self.fdp1 = fdp
        else:
            self.fdp2 = fdp

    def send_dt_elv(self):
        while not self.stop_event:
            pass
        while not self.fdp1 and not self.stop_event.is_set():
            pass
        dt = {
            "floor": self.fdp1.ConsumeIntInRange(2, 11),
            "door": self.fdp1.PickValueInList(['open', 'close']),
            "movingStatus": self.fdp1.PickValueInList(['stay','up', 'down']),
            "inService": True,
            "inDrivingPermission": self.fdp1.PickValueInList([True, False]),
            "answerBack": False,
            "trouble": False,
            "time": int(self.time.current_timestamp())
            }
        self.send(dt, self.send_dt_topic, self.time, file_path=self.file_path)
        print(dt, file=sys.stderr)
        self.fdp1 = None

    def recv_command_response(self, command, result):
        msg = self.fdp2.PickValueInList([RecvCommandData('fuzz').interlock_true_command_success(), 
                                        RecvCommandData('fuzz').interlock_false_command_success(), 
                                        RecvCommandData('fuzz').call_command_accept(), 
                                        RecvCommandData('fuzz').call_command_arrive(), 
                                        RecvCommandData('fuzz').open_command_success(), 
                                        RecvCommandData('fuzz').close_command_success(), 
                                        RecvCommandData('fuzz').go_command_arrive(),
                                        RecvCommandData('fuzz').go_command_accept()
                                        ])
        self.send(msg, self.send_cmd_arrive_topic, self.time, file_path=self.file_path)
        print(msg, file=sys.stderr)

    def on_message(self, client, userdata, msg):
        while not self.stop_event:
            pass
        while not self.fdp2 and not self.stop_event.is_set():
            pass
        if self.fdp2.ConsumeBool():
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
        
        else:
            payload = json.loads(msg.payload)
            msg_log(msg.topic, payload, self.time, self.file_path)
            self.recv_command_response(None, None)
        self.fdp2 = None