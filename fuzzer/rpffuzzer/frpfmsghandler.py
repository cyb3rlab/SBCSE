"""
The basic function is consistent with mqtt_communication_module/frpmsghandler.py.
"""
import sys
from utils.storyboard import Mode
from mqtt_communication_module.rpfmsghandler import RpfMessageHandler
from fuzzer.rpffuzzer.frpfnormalmode import FRpfNormalMode
from utils.storyboard import RobotConfig, ELVConfig

class FRPFMsgHandler(RpfMessageHandler):
    def __init__(self, send_topic, recv_topic, broker, port, time):
        super().__init__(send_topic, recv_topic, broker, port, time)
        self.mode_handlers = {
            Mode.FUZZING: FRpfNormalMode(self),
        }
        self.fdp = None
        
    def send_ELV_command_data(self):
        value = self.fdp.ConsumeBool()
        target_floor = self.fdp.ConsumeIntInRange(2, 11)
        direction = self.fdp.PickValueInList([ELVConfig.UP, ELVConfig.DOWN, ELVConfig.STAY])
        data = self.fdp.PickValueInList([self.send_data_instance.interlock_command(value), 
                                         self.send_data_instance.call_command(target_floor, direction), 
                                         self.send_data_instance.open_command(), self.send_data_instance.close_command(), 
                                         self.send_data_instance.go_command(target_floor)])
        return data

    def send_interlock_command(self, value):
        data = self.send_ELV_command_data()
        self.send(data, topic=self.send_B2D, time_sim=self.time, file_path=self.rpf_log_file)
        print(data, file=sys.stderr)


    def send_call_command(self, target_floor, direction):
        data = self.send_ELV_command_data()
        self.send(data, topic=self.send_B2D, time_sim=self.time, file_path=self.rpf_log_file)
        print(data, file=sys.stderr)

    def send_open_command(self):
        data = self.send_ELV_command_data()
        self.send(data, topic=self.send_B2D, time_sim=self.time, file_path=self.rpf_log_file)
        print(data, file=sys.stderr)


    def send_close_command(self):
        data = self.send_ELV_command_data()
        self.send(data, topic=self.send_B2D, time_sim=self.time, file_path=self.rpf_log_file)
        print(data, file=sys.stderr)


    def send_go_command(self, floor):
        data = self.send_ELV_command_data()
        self.send(data, topic=self.send_B2D, time_sim=self.time, file_path=self.rpf_log_file)
        print(data, file=sys.stderr)

    def send_B2R_command(self, target_floor=None, command=None, status=None, rob_name=None):
        if self.fdp == None:
            return
        fdptarget_floor=target_floor if target_floor is not None else self.fdp.ConsumeIntInRange(2, 11)
        fdpcommand=command if command is not None else self.fdp.PickValueInList([RobotConfig.CALLING, RobotConfig.GET_ON, RobotConfig.GET_OFF, RobotConfig.GO_TO_ELV, RobotConfig.Schedule_Work, RobotConfig.CHARGE])
        fdpstatus=status if status is not None else self.fdp.PickValueInList([RobotConfig.CALLING, RobotConfig.WAIT, RobotConfig.GET_ON, RobotConfig.GET_OFF])

        data = self.b2r_data_instance.B2R_command(fdptarget_floor, fdpcommand, fdpstatus, rob_name)
        self.send(data, topic=self.send_B2R, time_sim=self.time, file_path=self.robothandler.get_rpf_rob_comfile(rob_name))
        print(data, file=sys.stderr)