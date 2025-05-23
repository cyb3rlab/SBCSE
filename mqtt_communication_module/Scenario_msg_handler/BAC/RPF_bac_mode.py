from mqtt_communication_module.Scenario_msg_handler.base_handler.RPF_base_handler import RPF_ModeHandler
from utils.storyboard import RobotConfig, ScenarioConfig
from utils.storyboard import StateMachineConfig as S
from utils.storyboard import RobotConfig as R
from utils.storyboard import ELVConfig as ELV

class RpfBacMode(RPF_ModeHandler):
    def start_FakeMachine(self):
        if self.rpf_handler.rob_dt_data_dict[next(iter(self.rpf_handler.rob_dt_data_dict))][
            R.FLOOR] != self.rpf_handler.task_floor:
            self.fake_machine.move_to_elevator()
            while not self.rpf_handler.rob_dt_data_dict[next(iter(self.rpf_handler.rob_dt_data_dict))][
                          R.ELV_PREPARATION] == RobotConfig.ELV_PREPARATION_Completed:
                pass
            self.fake_machine.target_floor = self.rpf_handler.task_floor

            while not self.fake_machine.isCompleted():
                self.fake_machine.states_handler()
            self.fake_machine.init_status()  # Initialize the state machine

    def handle_task(self):
        self.fake_machine = FakeMachine(self.rpf_handler)

        self.rpf_handler.process_task()

        # Execute tasks
        if self.rpf_handler.task_name == ScenarioConfig.Task_Schedule_Work:
            self.start_FakeMachine()
            print("Executing schedule_work task")

            self.rpf_handler.send_B2R_command(command=RobotConfig.Schedule_Work, status=RobotConfig.WAIT)

            while not self.rpf_handler.Schedule_Work_completed:
                pass

        elif self.rpf_handler.task_name == ScenarioConfig.Task_Charge:
            self.start_FakeMachine()
            print("Executing charge task")

            self.rpf_handler.send_B2R_command(command=RobotConfig.CHARGE, status=RobotConfig.WAIT)

            while not self.rpf_handler.bot_dt_charge_completed:
                pass
        self.rpf_handler.init_rob_status()
        self.rpf_handler.init_elv_status()


class FakeMachine:
    def __init__(self, handler, retry_interval=4, max_retries=6):
        self.handler = handler
        self.retry_interval = retry_interval
        self.max_retries = max_retries  # Maximum number of resends
        self.fake_status = S.E0
        # State Transition Table
        self.state_transitions = S.STATE_MAP
        self.target_floor = None  # init target_floor

        self.states = {
            # S.R0: self.move_to_elevator,
            S.E0: self.interlock,
            S.E1: self.call_elv,
            S.E2: self.call_arrive,
            S.E3: self.open_elv_door,
            S.R1: self.enter_elevator,
            S.E4: self.close_elv_door,
            S.R2: self.exit_elevator,
            S.COMPLETED: self.completed
        }

    def init_status(self):
        self.fake_status = S.E0

    def states_handler(self):
        while self.fake_status != S.COMPLETED:
            state_func = self.states.get(self.fake_status)
            if state_func:
                # Execute function
                state_func()
            else:
                raise ValueError(f"Invalid state: {self.fake_status}")

    def check_success(self, attr):
        retries = 0
        self.handler.time.sleep(self.retry_interval)
        while retries < self.max_retries:
            if self.handler.rob_status_dict[next(iter(self.handler.rob_dt_data_dict))][attr] == True:
                return True
            retries += 1
            # self.handler.time.sleep(self.retry_interval)
        return False

    """
    Send interlock cmd to Elv
    """
    def interlock(self):
        if self.fake_status == S.E0:
            self.handler.send_interlock_command(True)
            if self.check_success(ELV.INTERLOCK_TRUE_SUCCESS):
                self.fake_status = S.E1  # Move to the next state
                # send cmd to rob movingStatus or next task
                self.handler.send_B2R_command(target_floor=self.target_floor, command=R.CALLING, status=R.CALLING,
                                              rob_name=next(iter(self.handler.rob_status_dict)))

    """
    Send call cmd to Elv
    """
    def call_elv(self):
        if self.fake_status == S.E1:
            if self.target_floor != self.handler.rob_dt_data_dict[next(iter(self.handler.rob_dt_data_dict))][R.FLOOR] and not self.check_success(ELV.CALL_ACCEPT):
                direction = self.compute_direction(current_floor=self.handler.elv_current_floor,
                                                   target_floor=self.target_floor)
                self.handler.send_call_command(self.handler.rob_dt_data_dict[next(iter(self.handler.rob_dt_data_dict))][R.FLOOR], direction)
            elif self.check_success(ELV.CALL_ACCEPT):
                self.fake_status = S.E2
            elif self.target_floor == self.handler.rob_dt_data_dict[next(iter(self.handler.rob_dt_data_dict))][R.FLOOR]:
                self.fake_status = S.COMPLETED

    """
    Check call arrival Elv
    """
    def call_arrive(self):
        if self.fake_status == S.E2:
            if self.check_success(ELV.CALL_ARRIVE):
                self.fake_status = S.E3

    def open_elv_door(self):
        self.handler.send_open_command()
        if self.check_success(ELV.OPEN_SUCCESS):
            if self.fake_status == S.E3:
                self.fake_status = S.R1
            elif self.fake_status == S.E7:
                self.fake_status = S.R2

    def close_elv_door(self):
        self.handler.send_close_command()
        if self.check_success(ELV.CLOSE_SUCCESS):
            if self.fake_status == S.E4:
                self.fake_status = S.R2

    def enter_elevator(self):
        retries = 0
        max_retries = 3
        while retries < max_retries:
            if self.check_success(R.GETTING_ON_SUCCESS):
                # self.handler.time.sleep(30)
                if self.check_success(R.GETTING_ON_COMPLETED):
                    self.fake_status = S.E4  # Rob leaves the elevator and turns to close the elevator
                    return
                else:
                    retries += 1
            else:
                self.handler.send_B2R_command(command=R.GET_ON, status=R.GET_ON, rob_name=next(iter(self.handler.rob_dt_data_dict)))
                retries += 1

    '''
    Rob exit Elv
    '''
    def exit_elevator(self):
        retries = 0
        max_retries = 2
        while retries < max_retries:
            if self.check_success(R.GETTING_OFF_SUCCESS):
                if self.check_success(R.GETTING_OFF_COMPLETED):
                    self.fake_status = S.E8
                    return
                else:
                    retries += 1
            else:
                self.handler.send_B2R_command(command=R.GET_OFF, status=R.GET_OFF, rob_name=next(iter(self.handler.rob_dt_data_dict)))
                retries += 1

    def completed(self):
        # if self.rcp_status == S.COMPLETED:
        #     return True
        print("Task completed")

    def isCompleted(self):
        if self.fake_status == S.COMPLETED:
            return True
        self.init_status()

    '''
    Move Rob to Elv
    '''
    def move_to_elevator(self):
        if self.check_success(R.GO_TO_ELV_SUCCESS):
            # next status
            self.fake_status = S.E0
        else:
            self.handler.send_B2R_command(command=R.GO_TO_ELV, status=R.WAIT, rob_name=next(iter(self.handler.rob_dt_data_dict)))

    def compute_direction(self, current_floor, target_floor):
        if current_floor < target_floor:
            return 'up'
        elif current_floor > target_floor:
            return 'down'
        else:
            return 'stay'
