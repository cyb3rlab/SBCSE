"""
The basic function is consistent with control_protocol/rcp.py.
"""
import sys
from utils.storyboard import StateMachineConfig as S
from utils.storyboard import RobotConfig as R
from utils.storyboard import ELVConfig as ELV
from utils.error import RCPTimeOut, RCPError
from device_motion_module.servicerobot import RobotHandler
from device_motion_module.elevator import ElvHandler
import atheris

"""
Robot Control Protocol
"""
class RCPMachine:
    def __init__(self, handler, rob_name, retry_interval=4, max_retries=6):
        self.handler = handler
        self.retry_interval = retry_interval
        self.max_retries = max_retries
        self.recall_retries = 0
        self.rego_retries = 0
        self.reopen_retries = 0
        self.rcp_status = S.r0e0
        self.rob_name = rob_name
        self.state_transitions = S.STATE_MAP
        self.target_floor = None
        self.stop = False

        self.rob = RobotHandler()
        self.elv = ElvHandler()

        self.states = { 
            S.r0e0: self.move_to_elevator,
            S.r1e0: self.interlock1,
            S.r1e1: self.call_elv,
            S.r1e2: self.call_arrive,
            S.r1e3: self.open_elv_door1,
            S.r1e4: self.enter_elevator,
            S.r2e4: self.close_elv_door1,
            S.r2e5: self.elv_go,
            S.r2e6: self.elv_go_arrive,
            S.r2e7: self.open_elv_door2,
            S.r2e8: self.exit_elevator,
            S.r3e8: self.close_elv_door2,
            S.r3e9: self.interlock2,
            S.calling: self.calling,
            S.COMPLETED: self.completed,
        }

    def init_rcp_status(self):
        self.stop = False
        self.recall_retries = 0
        self.rego_retries = 0
        self.reopen_retries = 0
        self.rcp_status = S.r0e0

    def rcp_states_handler(self):
        while not self.stop:
            state_func = self.states.get(self.rcp_status)
            if state_func:
                print(self.rob_name + " " + self.rcp_status, file=sys.stderr)
                state_func()
            else:
                raise ValueError(f"Invalid state: {self.rcp_status}")
    
    def check_success(self, attr):
        retries = 0
        self.handler.time.sleep(self.retry_interval)
        while retries < self.max_retries:
            if self.handler.rob_status_dict[self.rob_name][attr] == True:
                return True
            retries += 1
        return False

    """
    Send interlock cmd to Elv
    """
    @atheris.instrument_func
    def interlock1(self):
        retries = 0
        max_retries = 6
        while retries < max_retries:
            if self.handler.robothandler.istop(self.rob_name):
                if self.check_success(ELV.INTERLOCK_TRUE_SUCCESS):
                    self.rcp_status = S.calling 
                    self.rob.copy_bot(self.rob_name)
                    self.elv.copy_elv()
                    return
                else:
                    self.handler.send_interlock_command(True)
                    retries += 1
            else:
                self.handler.time.sleep(10)
                retries += 10
        self.exit()
    
    @atheris.instrument_func
    def calling(self):
        self.retries = 0
        max_retries = 6
        while self.retries < max_retries and not self.stop:      
            if self.check_success(R.CALL_SUCCESS):
                self.rcp_status = S.r1e1 
                self.rob.copy_bot(self.rob_name)
                self.elv.copy_elv()
                return
            else:
                self.handler.send_B2R_command(target_floor=self.target_floor, command=R.CALLING, status=R.CALLING, rob_name=self.rob_name)
                self.retries += 1
        self.exit()

    @atheris.instrument_func
    def interlock2(self):
        retries = 0
        max_retries = 6
        while retries < max_retries:
            if self.check_success(ELV.INTERLOCK_FALSE_SUCCESS):
                self.handler.robothandler.pop()
                # self.stop = True
                self.rcp_status = S.COMPLETED
                self.rob.copy_bot(self.rob_name)
                self.elv.copy_elv()
                # self.init_rcp_status()
                return
            else:
                self.handler.send_interlock_command(False)
                retries += 1
        self.exit()

    """
    Send call cmd to Elv
    """
    @atheris.instrument_func
    def call_elv(self):
        retries = 0
        max_retries = 6
        while retries < max_retries:
            if self.check_success(ELV.CALL_ACCEPT):
                self.rcp_status = S.r1e2
                self.rob.copy_bot(self.rob_name)
                self.elv.copy_elv()
                return
            else:
                direction = self.compute_direction(current_floor=self.handler.elv_current_floor,
                                                target_floor=self.handler.rob_dt_data_dict[self.rob_name][R.FLOOR])
                self.handler.send_call_command(self.handler.rob_dt_data_dict[self.rob_name][R.FLOOR], direction)
                retries += 1
        self.exit()

    """
    Check call arrival Elv
    """
    @atheris.instrument_func
    def call_arrive(self):
        retries = 0
        max_retries = 6
        while retries < max_retries:
            if self.check_success(ELV.CALL_ARRIVE):
                if self.handler.elv_current_floor != self.handler.rob_dt_data_dict[self.rob_name][R.FLOOR]:
                    if self.recall_retries < self.max_retries:
                        self.handler.rob_status_dict[self.rob_name][ELV.CALL_ACCEPT] = False
                        self.handler.rob_status_dict[self.rob_name][ELV.CALL_ARRIVE] = False
                        direction = self.compute_direction(current_floor=self.handler.elv_current_floor,
                                                        target_floor=self.handler.rob_dt_data_dict[self.rob_name][R.FLOOR])
                        self.handler.send_call_command(self.handler.rob_dt_data_dict[self.rob_name][R.FLOOR], direction)
                        self.rcp_status = S.r1e1
                        self.recall_retries += 1
                        return
                    else:
                        self.exit()
                else:
                    self.rcp_status = S.r1e3
                    return
            else:
                retries += 1
        self.exit()

    """
    Send open cmd to Elv
    """
    @atheris.instrument_func
    def open_elv_door1(self):
        retries = 0
        max_retries = 6
        while retries < max_retries:
            if self.check_success(ELV.OPEN_SUCCESS):
                self.rcp_status = S.r1e4
                self.rob.copy_bot(self.rob_name)
                self.elv.copy_elv()
                return
            else:
                self.handler.send_open_command()
                retries += 1
        self.exit()

    @atheris.instrument_func
    def open_elv_door2(self):
        retries = 0
        max_retries = 6
        while retries < max_retries:
            if self.check_success(ELV.OPEN_SUCCESS):
                self.rcp_status = S.r2e8
                self.rob.copy_bot(self.rob_name)
                self.elv.copy_elv()
                return
            else:
                self.handler.send_open_command()
                retries += 1
        self.exit()
    """
    Send close cmd to Elv
    """
    @atheris.instrument_func
    def close_elv_door1(self):
        retries = 0
        max_retries = 6
        while retries < max_retries:
            self.handler.send_close_command()
            if self.check_success(ELV.CLOSE_SUCCESS):
                self.rcp_status = S.r2e5
                self.rob.copy_bot(self.rob_name)
                self.elv.copy_elv()
                return
            else:
                retries += 1
        self.exit()

    @atheris.instrument_func
    def close_elv_door2(self):
        retries = 0
        max_retries = 6
        while retries < max_retries:
            self.handler.send_close_command()
            if self.check_success(ELV.CLOSE_SUCCESS):
                self.rcp_status = S.r3e9
                self.rob.copy_bot(self.rob_name)
                self.elv.copy_elv()
                return
            else:
                retries += 1
        self.exit()

    """
    Send go cmd to Elv
    """
    @atheris.instrument_func
    def elv_go(self):
        retries = 0
        max_retries = 6
        while retries < max_retries:
            if self.check_success(ELV.GO_ACCEPT):
                self.rcp_status = S.r2e6
                self.rob.copy_bot(self.rob_name)
                self.elv.copy_elv()
                return
            else:
                self.handler.send_go_command(self.target_floor)
                retries += 1
        self.exit()

    @atheris.instrument_func
    def elv_go_arrive(self):
        retries = 0
        max_retries = 6
        while retries < max_retries:
            if self.check_success(ELV.GO_ARRIVE):
                if self.handler.elv_current_floor != self.target_floor:
                    if self.rego_retries < self.max_retries:
                        self.handler.rob_status_dict[self.rob_name][ELV.GO_ACCEPT] = False
                        self.handler.rob_status_dict[self.rob_name][ELV.GO_ARRIVE] = False
                        self.handler.send_go_command(self.target_floor)
                        self.rcp_status = S.r2e5
                        self.rego_retries += 1
                        return
                    else:
                        self.exit()
                else:
                    self.rcp_status = S.r2e7
                    return
            else:
                retries += 1
        self.exit()


    def compute_direction(self, current_floor, target_floor):
        if current_floor < target_floor:
            return 'up'
        elif current_floor > target_floor:
            return 'down'
        else:
            return 'stay'

    def completed(self):
        self.stop = True
        print("Task completed")

    def isCompleted(self):
        return self.rcp_status == S.COMPLETED
        
    def isStoped(self):
        return self.stop

    '''
    Move Rob to Elv
    '''
    @atheris.instrument_func
    def move_to_elevator(self):
        retries = 0
        max_retries = 6
        while retries < max_retries:
            if self.check_success(R.GO_TO_ELV_SUCCESS):
                self.rob.copy_bot(self.rob_name)
                self.elv.copy_elv()
                if self.check_success(R.GO_TO_ELV_COMPLETED):
                    self.rcp_status = S.r1e0
                    self.rob.copy_bot(self.rob_name)
                    self.elv.copy_elv()
                    self.handler.robothandler.enqueue(self.rob_name)
                    return
                else:
                    # self.print_reason_and_retry()
                    retries += 1
            else:
                self.handler.send_B2R_command(command=R.GO_TO_ELV, status=R.WAIT, rob_name=self.rob_name)
                retries += 1
        self.exit()
            
    '''
    Rob enter Elv
    '''
    @atheris.instrument_func
    def enter_elevator(self):
        retries = 0
        max_retries = 6
        while retries < max_retries:
            if self.check_success(R.GETTING_ON_SUCCESS):
                self.rob.copy_bot(self.rob_name)
                self.elv.copy_elv()
                if self.check_success(R.GETTING_ON_COMPLETED):
                    self.rcp_status = S.r2e4
                    self.reopen_retries = 0
                    self.rob.copy_bot(self.rob_name)
                    self.elv.copy_elv()
                    return
                else:
                    if self.handler.rob_status_dict[self.rob_name][R.ERROR] == R.E004:
                        if self.reopen_retries < self.max_retries:
                            self.handler.rob_status_dict[self.rob_name][R.GETTING_ON_SUCCESS] = False
                            self.handler.rob_status_dict[self.rob_name][R.ERROR] = False
                            self.handler.open_success = False
                            self.rcp_status = S.r1e3
                            self.reopen_retries += 1
                        else:
                            self.exit()
                retries += 1
            else:
                self.handler.send_B2R_command(command=R.GET_ON, status=R.GET_ON, rob_name=self.rob_name)
                retries += 1
        self.exit()

    '''
    Rob exit Elv
    '''
    @atheris.instrument_func
    def exit_elevator(self):
        retries = 0
        max_retries = 6
        while retries < max_retries:
            # self.handler.time.sleep(30)
            if self.check_success(R.GETTING_OFF_SUCCESS):
                self.rob.copy_bot(self.rob_name)
                self.elv.copy_elv()
                if self.check_success(R.GETTING_OFF_COMPLETED):
                    self.rcp_status = S.r3e8
                    self.rob.copy_bot(self.rob_name)
                    self.elv.copy_elv()
                    return
                else:
                    if self.handler.rob_status_dict[self.rob_name][R.ERROR] == R.E004:
                        if self.reopen_retries < self.max_retries:
                            self.handler.rob_status_dict[self.rob_name][R.GETTING_OFF_SUCCESS] = False
                            self.handler.rob_status_dict[self.rob_name][R.ERROR] = False
                            self.handler.open_success = False
                            self.rcp_status = S.r2e7
                        else:
                            self.exit()
                retries += 1
            else:
                self.handler.send_B2R_command(command=R.GET_OFF, status=R.GET_OFF, rob_name=self.rob_name)
                retries += 1
        self.exit()
        
    def exit(self):
        self.stop = True
        # self.rcp_status = S.COMPLETED
        if self.handler.rob_status_dict[self.rob_name][R.ERROR]:
            raise RCPError(self.handler.rob_status_dict[self.rob_name][R.ERROR])
        elif self.recall_retries == self.max_retries:
            raise RCPError('E001')
        elif self.rego_retries == self.max_retries:
            raise RCPError('E001')
        elif self.rcp_status != S.r0e0 and not self.handler.robothandler.istop(self.rob_name):
            return
        # else:
        #     raise RCPTimeOut()
        return 