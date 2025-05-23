"""
The basic function is consistent with mqtt_communication_module/frpmsghandler.py.
"""
import json
from mqtt_communication_module.robmsghandler import RobMessageHandler
from utils.storyboard import RobotConfig, CmdConfig, ELVConfig
from utils.msglog import rob_communication_log, msg_log, action_log
from device_motion_module.servicerobot import RobotHandler

class FRobMessageHandler(RobMessageHandler):
    def __init__(self, send_topic, recv_topic, broker, port, robs, time):
        super().__init__(send_topic, recv_topic, broker, port, robs, time)
        self.Robs = RobotHandler()

    def init(self):
        for rob in self.Robs.find_bots():
            self.task_lists[rob.name] = []
            self.rob_dt_data[rob.name] = None
            self.elv_dt_count[rob.name] = 0

    def find_rob(self, rob_name):
        return self.Robs.find_bot(rob_name)

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload)
            status = payload.get(CmdConfig.STATUS)
            target_floor = int(payload.get(ELVConfig.TARGET_FLOOR)) if payload.get(ELVConfig.TARGET_FLOOR) else None
            
            if msg.topic == self.recv_elv_dt:
                for rob in self.Robs.find_bots():
                    msg_log(msg.topic, payload, self.time, rob.com_file_name)
                    cmd = None
                    target_floor = None
                    rob_communication_log(cmd, target_floor, payload, self.time, rob.communication_file_name, message_type='elv')
                    self.elv_dt_count[rob.name] += 1
                    if self.elv_dt_count[rob.name] == 9:
                        self.rob_dt_data[rob.name] = rob.get_rob_status()
                        rob_communication_log(cmd, target_floor, self.rob_dt_data[rob.name], self.time, rob.communication_file_name, message_type='rob')
                        self.elv_dt_count[rob.name] = 0

            elif msg.topic == self.recv_B2R:
                rob_name = payload.get(RobotConfig.NAME)
                rob = self.find_rob(rob_name)
                msg_log(msg.topic, payload, self.time, rob.com_file_name)
                command = payload.get(CmdConfig.COMMAND)
                self.check_command(command)

                if command in self.task_lists[rob_name]:
                    return

                if command == RobotConfig.GO_TO_ELV:
                    if rob.set_go_to_elv_status():
                        self.recv_command(command, 'success', rob, reason=None)
                        self.task_lists[rob_name].insert(-1, RobotConfig.GO_TO_ELV)
                        action_log(command+"_start", rob.realfloor, self.time, rob.act_file_name)
                    elif rob.state == RobotConfig.robq1:
                        self.recv_command(command, 'success', rob, reason=None)
                        action_log(command+"_start", rob.realfloor, self.time, rob.act_file_name)
                        self.recv_command(command, 'completed', rob, reason=None)
                        action_log(command+"_completed", rob.realfloor, self.time, rob.act_file_name)

                elif command == RobotConfig.CALLING:
                    if rob.set_elv_call_status(target_floor):
                        self.recv_command(command, 'success', rob, reason=None)
                        rob.next_floor = payload[ELVConfig.TARGET_FLOOR]
                        rob.bot_dt_send_time = 10
                        rob.bot_pos_log_time = 5
                        action_log(command, rob.realfloor, self.time, rob.act_file_name)
                        self.rob_dt_data[rob_name] = rob.get_rob_status()
                        rob_communication_log(command, rob.next_floor, self.rob_dt_data[rob_name], self.time, rob.communication_file_name, message_type='rob')

                elif command == RobotConfig.GET_ON:
                    if rob.set_elv_getting_on():
                        self.recv_command(command, 'success', rob, reason=None)
                        rob.bot_dt_send_time = 10
                        rob.bot_pos_log_time = 5
                        self.task_lists[rob_name].insert(-1, RobotConfig.GET_ON)
                        action_log(command+"_start", rob.realfloor, self.time, rob.act_file_name)
                        self.rob_dt_data[rob_name] = rob.get_rob_status()
                        rob_communication_log(command, None, self.rob_dt_data[rob_name], self.time, rob.communication_file_name, message_type='rob')
                    elif rob.state == RobotConfig.robq2:
                        self.recv_command(command, 'success', rob, reason=None)
                        action_log(command+"_start", rob.realfloor, self.time, rob.act_file_name)
                        self.recv_command(command, 'completed', rob, reason=None)
                        action_log(command+"_completed", rob.realfloor, self.time, rob.act_file_name)

                elif command == RobotConfig.GET_OFF:
                    if rob.set_elv_getting_off_status():
                        self.recv_command(command, 'success', rob, reason=None)
                        rob.bot_dt_send_time = 10
                        rob.bot_pos_log_time = 5
                        self.task_lists[rob_name].insert(-1, RobotConfig.GET_OFF)
                        action_log(command+"_start", rob.realfloor, self.time, rob.act_file_name)
                        self.rob_dt_data[rob_name] = rob.get_rob_status()
                        rob_communication_log(command, rob.floor, self.rob_dt_data[rob_name], self.time, rob.communication_file_name, message_type='rob')
                    elif rob.state == RobotConfig.robq0:
                        self.recv_command(command, 'success', rob, reason=None)
                        action_log(command+"_start", rob.realfloor, self.time, rob.act_file_name)
                        self.recv_command(command, 'completed', rob, reason=None)
                        action_log(command+"_completed", rob.realfloor, self.time, rob.act_file_name)

                elif command == RobotConfig.ELVStay:
                    if rob.set_elv_stay_status():
                        self.recv_command(command, 'success', rob, reason=None)
                        self.send_rob_dt(rob_name)
                        self.task_lists[rob_name].insert(-1, RobotConfig.ELVStay)
                        action_log(command+"_start", rob.realfloor, self.time, rob.act_file_name)


                elif command == RobotConfig.CHARGE:
                    if rob.set_go_to_charge_status():
                        self.recv_command(command, 'success', rob, reason=None)
                        self.task_lists[rob_name].insert(-1, RobotConfig.CHARGE)
                        action_log(command+"_start", rob.realfloor, self.time, rob.act_file_name)


                elif command == RobotConfig.Schedule_Work:
                    if rob.set_schedule_work_status():
                        self.recv_command(command, 'success', rob, reason=None)
                        self.task_lists[rob_name].insert(-1, RobotConfig.Schedule_Work)
                        action_log(command+"_start", rob.realfloor, self.time, rob.act_file_name)

        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
