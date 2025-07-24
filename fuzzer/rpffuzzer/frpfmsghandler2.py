"""
The basic function is consistent with mqtt_communication_module/frpmsghandler.py.
"""
from utils.storyboard import Mode
from mqtt_communication_module.rpfmsghandler import RpfMessageHandler
from fuzzer.rpffuzzer.frpfnormalmode2 import FRpfNormalMode2

class FRPFMsgHandler(RpfMessageHandler):
    def __init__(self, send_topic, recv_topic, broker, port, time):
        super().__init__(send_topic, recv_topic, broker, port, time)
        self.mode_handlers = {
            Mode.FUZZING2: FRpfNormalMode2(self),
        }