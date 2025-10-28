import threading
from mqtt_communication_module.Scenario_msg_handler.base_handler.RPF_base_handler import RPF_ModeHandler
from utils.storyboard import RobotConfig, ScenarioConfig, CmdConfig
from device_motion_module.elevator import ElvHandler
from utils.storyboard import StateMachineConfig as S
from utils.storyboard import RobotConfig as R
from utils.storyboard import ELVConfig as ELV
from device_motion_module.servicerobot import RobotHandler


class RpfMitmMode(RPF_ModeHandler):
    def start_FakeMachine(self, rob_name):
        try:
            target_floor = self.robothandler.rob_dict[rob_name][RobotConfig.TASK][0][RobotConfig.TASK_FLOOR]
        except Exception:
            return

        sm = self.robothandler.rob_dict[rob_name].get('rcp_state_machine')
        if sm is None:
            sm = FakeMachine(self.rpf_handler, rob_name)
            self.robothandler.rob_dict[rob_name]['rcp_state_machine'] = sm

        sm.target_floor = target_floor

        while not sm.isCompleted():
            sm.rcp_states_handler()

        sm.init_status()
        self.rpf_handler.init_rob_status(rob_name)
        self.rpf_handler.init_elv_status()

    def handle_task(self):
        self.elvhandler = ElvHandler()
        self.robothandler = RobotHandler()
        threads = []

        for rob_name, rob_attr in self.robothandler.rob_dict.items():
            if 'rcp_state_machine' not in rob_attr or rob_attr['rcp_state_machine'] is None:
                rob_attr['rcp_state_machine'] = FakeMachine(self.rpf_handler, rob_name)

            thread = threading.Thread(target=self.process_robot_task, args=(rob_name,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

    def process_robot_task(self, rob_name):
        try:
            task = self.robothandler.rob_dict[rob_name][RobotConfig.TASK][0]['task_name']
        except Exception:
            return

        # Execute tasks based on the task name
        if task == ScenarioConfig.Task_Schedule_Work:
            self.start_FakeMachine(rob_name)
            print(f"Executing schedule_work task for {rob_name}")

        elif task == ScenarioConfig.Task_Charge:
            self.start_FakeMachine(rob_name)

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


class FakeMachine:
    def __init__(self, handler, rob_name, retry_interval=1, max_retries=6):
        self.handler = handler
        self.rob_name = rob_name
        self.retry_interval = retry_interval
        self.max_retries = max_retries
        self.recall_retries = 0
        self.rego_retries = 0
        self.reopen_retries = 0
        self.stop = False
        self.fk_rcp_status = S.r0e0

        self.states = {
            S.r0e0: self.move_to_elevator,
            S.r1e0: self.interlock1,
            S.calling: self.calling,
            S.r1e1: self.call_elv,
            S.r1e2: self.call_arrive,
            S.r1e4: self.enter_elevator_crash,
            S.COMPLETED: self.completed
        }

    def rcp_states_handler(self):
        while not self.stop:
            func = self.states.get(self.fk_rcp_status)
            if func:
                func()
            else:
                print(f"[FakeMachine] {self.rob_name}: unknown state {self.fk_rcp_status}")
                self.stop = True

    def check_success(self, attr):
        for _ in range(self.max_retries):
            if self.handler.rob_status_dict[self.rob_name][attr] == True:
                return True
            self.handler.time.sleep(self.retry_interval)
        return False

    def move_to_elevator(self):
        if self.check_success(R.GO_TO_ELV_SUCCESS):
            if self.check_success(R.GO_TO_ELV_COMPLETED):
                self.fk_rcp_status = S.r1e0
                try:
                    self.handler.robothandler.enqueue(self.rob_name)
                except Exception:
                    pass
        else:
            self.handler.send_B2R_command(command=R.GO_TO_ELV, status=R.WAIT, rob_name=self.rob_name)
            self.handler.time.sleep(self.retry_interval)

    def calling(self):
        if self.check_success(R.CALL_SUCCESS):
            self.fk_rcp_status = S.r1e1
            return
        else:
            self.handler.send_B2R_command(target_floor=self.target_floor, command=R.CALLING, status=R.CALLING, rob_name=self.rob_name)

    def interlock1(self):
        if self.handler.robothandler.istop(self.rob_name) and self.check_success(ELV.INTERLOCK_TRUE_SUCCESS):
            self.fk_rcp_status = S.calling
        else:
            self.handler.send_interlock_command(True)
            self.handler.time.sleep(self.retry_interval)

    def call_elv(self):
        if self.check_success(ELV.CALL_ACCEPT):
            self.fk_rcp_status = S.r1e2
        else:
            direction = self.compute_direction(
                current_floor=self.handler.elv_current_floor,
                target_floor=self.handler.rob_dt_data_dict[self.rob_name][R.FLOOR]
            )
            self.handler.send_call_command(self.handler.rob_dt_data_dict[self.rob_name][R.FLOOR], direction)
            self.handler.time.sleep(self.retry_interval)

    def call_arrive(self):
        if self.check_success(ELV.CALL_ARRIVE):
            if self.handler.elv_current_floor == self.handler.rob_dt_data_dict[self.rob_name][R.FLOOR]:
                self.fk_rcp_status = S.r1e4
        else:
            self.handler.time.sleep(self.retry_interval)

    def enter_elevator_crash(self):
        print(f"[FakeMachine] {self.rob_name} entering elevator (door closed!) 🚪💥")
        try:
            self.handler.send_B2R_command(command=R.GET_ON, status="crash_door", rob_name=self.rob_name)
        except Exception:
            pass
        self.fk_rcp_status = S.COMPLETED
        self.stop = True

    def completed(self):
        print(f"[FakeMachine] {self.rob_name} task completed ✅")
        self.fk_rcp_status = S.COMPLETED
        self.stop = True

    def init_status(self):
        self.stop = False
        self.fk_rcp_status = S.r0e0
        self.recall_retries = 0
        self.rego_retries = 0
        self.reopen_retries = 0

    def isCompleted(self):
        return self.fk_rcp_status == S.COMPLETED

    def compute_direction(self, current_floor, target_floor):
        if current_floor < target_floor:
            return 'up'
        elif current_floor > target_floor:
            return 'down'
        return 'stay'
