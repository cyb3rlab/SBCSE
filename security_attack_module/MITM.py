from utils.storyboard import StateMachineConfig as S
from utils.storyboard import MqttConfig, ClientConfig, ScenarioConfig, Mode, LogConfig
from utils.msglog import log_att_process


# MITMAttackScenario
class MITMAttackScenario:
    def __init__(self, target, protocol, use_encryption=None):
        self.target_protocol = protocol # Attack target protocol
        self.target = target
        self.current_state = None
        self.success = False
        self.file_path = LogConfig.RUNTIME_REPORT

        self.states = {
            S.A0: self.scan,  # Step1.Information Gathering/Scanning------Assuming success
            S.A1: self.listen,  # Step2.Initial positioning and listening------Assuming success
            S.A2: self.intercept,  # Step3.intercept msg
            S.A3: self.manipulate  # Step4.Manipulation target system(PRF/BOS)
        }

    def start_attack(self):
        self.current_state = S.A0
        while self.current_state in self.states:
            self.states[self.current_state]()

    def scan(self):
        # Assuming success
        if self.current_state == S.A0:
            print("->Scanning target............")
            msg = f"->Scanning target:{self.target}"
            log_att_process(self.file_path, msg)

            self.current_state = S.A1

    def listen(self):
        print(f"->Listening on target:{self.target}")
        msg = f"->Listening on target:{self.target}............"
        log_att_process(self.file_path, msg)
        if self.target_protocol == MqttConfig.MQTTS:
            print("+++++++++++++++++++++++++++Listening failed(Secure connection)")
            msg = "+++++++++++++++++++++++++++Listening failed(Secure connection)"
            log_att_process(self.file_path, msg)
            self.success = False
            self.current_state = None
        else:
            print(f"->Listening success on {self.target}, continuing attack.......")
            msg = f"->Listening success on {self.target}, continuing attack......."
            log_att_process(self.file_path, msg)
            self.success = True
            self.current_state = S.A2

    def intercept(self):
        # intercept msg
        if self.current_state == S.A2:
            print(f"->Intercepting messages..........")
            msg = f"->Intercepting messages.........."
            log_att_process(self.file_path, msg)
            self.current_state = S.A3
        else:
            print(f"->Cannot intercept messages, attack failed.")
            msg = f"->Cannot intercept messages, attack failed."
            log_att_process(self.file_path, msg)
            self.current_state = None

    def manipulate(self):
        print(f"->Manipulating in {self.target}")
        msg = f"->Manipulating in {self.target}"
        log_att_process(self.file_path, msg)

        self.bos_mode, self.rpf_mode = Mode.mapping.get(("MITM", self.target), (Mode.Normal, Mode.Normal))
        self.success = True
        self.current_state = None
        return self.bos_mode, self.rpf_mode





