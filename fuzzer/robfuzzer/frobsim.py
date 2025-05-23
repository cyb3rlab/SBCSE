"""
The basic function is consistent with simulator/robsim.py.
"""
import threading
import sys
from device_motion_module.servicerobot import RobotHandler
from device_motion_module.elevator import ElvHandler
from mqtt_communication_module.data_model import RobotData
from fuzzer.robfuzzer.frobmsghandler import FRobMessageHandler
from utils.storyboard import CmdConfig, ClientConfig, RobotConfig, ELVConfig
from utils.msglog import rob_position_log, action_log


class FRobotSimulator(object):
    def __init__(self, send_topic, recv_topic, broker, port, robs, elvs, time, enable_allowlist):
        self.time = time
        self.Robs = RobotHandler()
        self.port = port
        self.broker = broker
        self.running = True

        self.token = ClientConfig.TOKEN
        self.client_id = ClientConfig.CLIENT_ID
        self.session_id = ClientConfig.SESSION_ID
        self.send_robdata_instance = RobotData(self.time)

        self.handler = FRobMessageHandler(send_topic, recv_topic, broker, port, robs, self.time)
        # self.handler.client_ip_port = self.handler.bind_client_to_port()
        # self.handler.enable_allowlist = enable_allowlist
        self.client = self.handler.client
        self.client.on_connect = self.handler.on_connect
        self.client.on_message = self.handler.on_message

        # self.communication_file_name = LogConfig.FILE_ROB_JP_LOG  # rob log
        # self.position_file_name = LogConfig.FILE_ROB_POSITION_LOG

        self.ELV_floor = '-1'
        self.ELV_door = 'close'
        self.ELV_inDrivingPermission = True
        self.ELV_interlock = False

        self.session_id = ClientConfig.SESSION_ID
        
        for i in range(len(robs)):
            robs[i].elv = ElvHandler().find_elv()
        self.reason = None
        self.task_complete_event = threading.Event()
    
    def init(self):
        self.handler.init() 

    def find_bot(self, rob_name):
        self.Robs.find_bot(rob_name)

    def bot_cmd(self, rob):
        if self.handler.get_tasks(rob.name):
            rob.elv = ElvHandler().find_elv()
            rob.update_config_status()
            task = self.handler.get_tasks(rob.name)[0]
            if task == RobotConfig.GO_TO_ELV:
                if rob.cmd_interrupt:
                    action_log(self.handler.get_tasks(rob.name).pop(0) + '_completed', rob.map_no, self.time, rob.act_file_name)
                elif rob.go_to_elv():
                    self.reason = None
                    self.rob_dt_data = rob.get_rob_status()
                    self.handler.recv_command(CmdConfig.GO_TO_ELV, CmdConfig.COMPLETED, rob, self.reason)
                    action_log(self.handler.get_tasks(rob.name).pop(0) + '_completed', rob.map_no, self.time, rob.act_file_name)

            elif task == RobotConfig.GET_ON:
                if rob.cmd_interrupt:
                    action_log(self.handler.get_tasks(rob.name).pop(0) + '_completed', rob.map_no, self.time, rob.act_file_name)
                elif rob.elv_getting_on():
                    self.reason = None
                    self.rob_dt_data = rob.get_rob_status()
                    self.handler.recv_command(CmdConfig.GETTING_ON, CmdConfig.COMPLETED, rob, self.reason)
                    action_log(self.handler.get_tasks(rob.name).pop(0) + '_completed', rob.map_no, self.time, rob.act_file_name)
                else:
                    if rob.movingStatus == RobotConfig.E004:
                        self.reason = f"door:{rob.elv_door_status},Status = {rob.movingStatus}"
                        self.handler.recv_command(CmdConfig.GETTING_ON, CmdConfig.NOT_COMPLETED, rob, reason=self.reason)

            elif task == RobotConfig.GET_OFF:
                if rob.cmd_interrupt:
                    action_log(self.handler.get_tasks(rob.name).pop(0) + '_completed', rob.map_no, self.time, rob.act_file_name)
                elif rob.elv_getting_off():
                    self.reason = None
                    self.handler.recv_command(CmdConfig.GETTING_OFF, CmdConfig.COMPLETED, rob, self.reason)
                    action_log(self.handler.get_tasks(rob.name).pop(0) + '_completed', rob.map_no, self.time, rob.act_file_name)
                else:
                    if rob.movingStatus == RobotConfig.E004:
                        self.reason = f"door:{rob.elv_door_status},Status = {rob.movingStatus}"
                        self.handler.recv_command(CmdConfig.GETTING_OFF, CmdConfig.NOT_COMPLETED, rob, reason=self.reason)

            elif task == RobotConfig.Schedule_Work:
                if rob.cmd_interrupt:
                    action_log(self.handler.get_tasks(rob.name).pop(0) + '_completed', rob.map_no, self.time, rob.act_file_name)
                elif rob.schedule_work():
                    self.handler.recv_command(CmdConfig.SCHEDULE_WORK, CmdConfig.COMPLETED, rob, self.reason)
                    action_log(self.handler.get_tasks(rob.name).pop(0) + '_completed', rob.map_no, self.time, rob.act_file_name)
                else:
                    if rob.movingStatus == RobotConfig.E002:
                        self.reason = f"Status = {rob.movingStatus}"
                        self.handler.recv_command(CmdConfig.SCHEDULE_WORK, CmdConfig.NOT_COMPLETED, rob, reason=self.reason)


            elif task == RobotConfig.CHARGE:
                if rob.cmd_interrupt:
                    action_log(self.handler.get_tasks(rob.name).pop(0) + '_completed', rob.map_no, self.time, rob.act_file_name)
                if rob.go_to_charge():
                    self.handler.recv_command(CmdConfig.CHARGE, CmdConfig.COMPLETED, rob, self.reason)
                    action_log(self.handler.get_tasks(rob.name).pop(0) + '_completed', rob.map_no, self.time, rob.act_file_name)

    def check_elv_status_periodically(self, interval=2):
        while True:
            elv_status = self.elv.get_elv_status()
            if elv_status:
                self.Rob.elv_status = elv_status
                self.Rob.elv_door_status = elv_status.get(ELVConfig.DOOR)
                print(f"Current elevator status: {elv_status}")
            else:
                print("Failed to retrieve elevator status.")

                self.Rob.elv_status = None
                self.Rob.elv_door_status = None
            self.time.sleep(interval)

    def rob_dt_update(self, rob):
        current_time = self.time.current_timestamp()
        time = current_time - rob.last_dt_time
        if rob.bot_dt_send_time < 1:
            rob.bot_dt_send_time = 10
            self.handler.send_rob_dt(rob)
        else:
            rob.bot_dt_send_time -= time
        rob.last_dt_time = current_time

    def position_log_update(self, rob):
        current_time = self.time.current_timestamp()
        time = current_time - rob.last_log_time
        if rob.bot_pos_log_time < 1:
            rob.bot_pos_log_time = 5
            data = self.send_robdata_instance.robot_position(rob.get_rob_status())
            rob_position_log(data, self.time, rob.position_file_name)
        else:
            rob.bot_pos_log_time -= time
        rob.last_log_time = current_time

    def bot_camera(self, rob):
        current_time = self.time.current_timestamp()
        time = current_time - rob.last_cam_time
        if rob.bot_cam_time < 1:
            rob.bot_cam_time = 2
            rob.update_config_status()
        else:
            rob.bot_cam_time -= time
        rob.last_cam_time = current_time 


    def start_simulation(self, stop_event):
        self.handler.stop_event = stop_event
        try:
            while not stop_event.is_set() and not self.handler.client.is_connected():
                self.time.sleep(1)

            self.client.loop_start()
            while self.running and not stop_event.is_set():
                if not self.client.is_connected():
                    self.client.connect(self.broker, self.port)
                for rob in self.Robs.find_bots():
                    self.rob_dt_update(rob)
                    self.position_log_update(rob)
                    self.bot_cmd(rob)
                    self.bot_camera(rob)
                for _ in range(1):
                    if stop_event.is_set():
                        break
                    self.time.sleep(1)
        except Exception as e:
            print("FROB: "+e, sys.stderr)
        finally:
            self.stop_simulation()

    def stop_simulation(self):
        if self.running:
            self.running = False
            self.client.loop_stop()
            self.handler.fdp = None
            try:
                self.client.disconnect()
            except Exception as e:
                print(f"Error during disconnection: {e}")
            print("Robot stopped")