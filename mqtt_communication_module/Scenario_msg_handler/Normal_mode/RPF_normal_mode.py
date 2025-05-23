import threading
from mqtt_communication_module.Scenario_msg_handler.base_handler.RPF_base_handler import RPF_ModeHandler
from control_protocol.rcp import RCPMachine
from device_motion_module.elevator import ElvHandler
from device_motion_module.servicerobot import RobotHandler
from utils.storyboard import RobotConfig, ScenarioConfig, CmdConfig
from formal_verification.FV import Maude_Generator


class RpfNormalMode(RPF_ModeHandler):
    def start_BCPMachine(self, rob_name):
        if self.rpf_handler.rob_dt_data_dict[rob_name][RobotConfig.FLOOR] != self.robothandler.rob_dict[rob_name][RobotConfig.TASK][0][RobotConfig.TASK_FLOOR]:
            self.robothandler.rob_dict[rob_name]['rcp_state_machine'].target_floor = self.robothandler.rob_dict[rob_name][RobotConfig.TASK][0][RobotConfig.TASK_FLOOR]
            while not self.robothandler.rob_dict[rob_name]['rcp_state_machine'].isCompleted():
                self.robothandler.rob_dict[rob_name]['rcp_state_machine'].rcp_states_handler()     
        self.robothandler.rob_dict[rob_name]['rcp_state_machine'].init_rcp_status()
        self.rpf_handler.init_rob_status(rob_name)
        self.rpf_handler.init_elv_status()
        # Maude_Generator().generator_maude_code()

    def handle_task(self):
        # rcp msg control machine
        self.elvhandler = ElvHandler()
        self.robothandler = RobotHandler()
        threads = []
        for rob_name, rob_attributes in self.robothandler.rob_dict.items():
            rob_attributes['rcp_state_machine'] = RCPMachine(self.rpf_handler, rob_name)
            thread = threading.Thread(target=self.process_robot_task, args=(rob_name,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

    def process_robot_task(self, rob_name):
        try:
            task = self.robothandler.rob_dict[rob_name][RobotConfig.TASK][0]['task_name']
        except:
            return

        # Execute tasks based on the task name
        if task == ScenarioConfig.Task_Schedule_Work:
            self.start_BCPMachine(rob_name)
            print(f"Executing schedule_work task for {rob_name}")

            self.rpf_handler.send_B2R_command(command=RobotConfig.Schedule_Work, status=RobotConfig.WAIT, rob_name=rob_name)

            while not self.rpf_handler.rob_status_dict[rob_name][CmdConfig.SCHEDULE_WORK_COMPLETED] and not self.rpf_handler.rob_status_dict[rob_name][RobotConfig.ERROR]:
                pass

        elif task == ScenarioConfig.Task_Charge:
            self.start_BCPMachine(rob_name)
            print(f"Executing charge task for {rob_name}")

            self.rpf_handler.send_B2R_command(command=RobotConfig.CHARGE, status=RobotConfig.WAIT, rob_name=rob_name)

            while not self.rpf_handler.rob_status_dict[rob_name][CmdConfig.CHARGE_COMPLETED] and not self.rpf_handler.rob_status_dict[rob_name][RobotConfig.ERROR]:
                pass
        if not self.rpf_handler.rob_status_dict[rob_name][RobotConfig.ERROR]:
            for task in self.rpf_handler.tasks:
                if task == self.robothandler.rob_dict[rob_name][RobotConfig.TASK][0]:
                    self.rpf_handler.tasks.remove(task)
                    break
            self.robothandler.rob_dict[rob_name][RobotConfig.TASK].pop(0)
            self.rpf_handler.init_rob_status(rob_name)
        else:
            if self.rpf_handler.rob_dt_data_dict[rob_name][RobotConfig.MOVING_STATUS] == RobotConfig.E002:
                self.rpf_handler.init_rob_status(rob_name)