"""
The basic function is consistent with mqtt_communication_module/Scenario_msg_handler/Normal_mode/RPF_normal_mode.py.
"""
import sys
from mqtt_communication_module.Scenario_msg_handler.base_handler.RPF_base_handler import RPF_ModeHandler
from fuzzer.rpffuzzer.frcp import RCPMachine
from device_motion_module.elevator import ElvHandler
from device_motion_module.servicerobot import RobotHandler
from utils.storyboard import RobotConfig, ScenarioConfig, CmdConfig
from formal_verification.FV import Maude_Generator


class FRpfNormalMode(RPF_ModeHandler):
    def __init__(self, rpf_handler):
        self.elvhandler = ElvHandler()
        self.robothandler = RobotHandler()
        super().__init__(rpf_handler)

    def start_RCPMachine(self, rob_name, stop_event):
        if not self.rpf_handler.tasks:
            stop_event.set()
            return
        if not self.robothandler.rob_dict[rob_name][RobotConfig.TASK]:
            return
        self.robothandler.paste_bot(rob_name)
        self.elvhandler.paste_elv()
        while not self.rpf_handler.rob_dt_data_dict[rob_name] or not self.robothandler.rob_dict[rob_name][RobotConfig.TASK] or self.robothandler.rob_dict[rob_name]['rcp_state_machine'] is None:
            pass
        if self.rpf_handler.rob_dt_data_dict[rob_name][RobotConfig.FLOOR] != self.robothandler.rob_dict[rob_name][RobotConfig.TASK][0][RobotConfig.TASK_FLOOR] or not self.robothandler.rob_dict[rob_name]['rcp_state_machine'].isCompleted():
            self.robothandler.rob_dict[rob_name]['rcp_state_machine'].target_floor = self.robothandler.rob_dict[rob_name][RobotConfig.TASK][0][RobotConfig.TASK_FLOOR]
            while not self.robothandler.rob_dict[rob_name]['rcp_state_machine'].isStoped():
                try:
                    self.robothandler.rob_dict[rob_name]['rcp_state_machine'].rcp_states_handler()
                except Exception as e:
                    print(e, file=sys.stderr)
                    stop_event.set()
        self.robothandler.rob_dict[rob_name]['rcp_state_machine'].stop = False
        if self.robothandler.rob_dict[rob_name]['rcp_state_machine'].isCompleted():
            self.robothandler.rob_dict[rob_name]['rcp_state_machine'].init_rcp_status()
            self.rpf_handler.init_elv_status()
            self.rpf_handler.init_rob_status(rob_name)
            self.rpf_handler.tasks.remove(self.robothandler.rob_dict[rob_name][RobotConfig.TASK][0])
            self.robothandler.del_paste(rob_name)
            self.robothandler.rob_dict[rob_name][RobotConfig.TASK].pop(0)
            if not self.rpf_handler.tasks:
                stop_event.set()
            
            
    def handle_task(self):
        threads = []
        for rob_name, rob_attributes in self.robothandler.rob_dict.items():
            if not rob_attributes['rcp_state_machine']:
                rob_attributes['rcp_state_machine'] = RCPMachine(self.rpf_handler, rob_name)
            # thread = threading.Thread(target=self.start_RCPMachine, args=(rob_name,))
            # threads.append(thread)
            # thread.start()

        # for thread in threads:
        #     thread.join()