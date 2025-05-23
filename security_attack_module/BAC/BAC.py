from utils.storyboard import StateMachineConfig as S
from utils.storyboard import MqttConfig, ClientConfig, ScenarioConfig, Mode, LogConfig, CER
from mqtt_communication_module.Authenticator.login_authen import Authenticator
from .pw import weak_passwords
from utils.msglog import log_att_process


# Unauthorized Access Attack
class BACAttackScenario:
    def __init__(self, target, protocol, use_encryption):
        self.target_protocol = protocol  # Attack target protocol
        self.target = target
        self.current_state = None
        self.success = False
        self.username = None
        self.password = None
        self.use_encryption = use_encryption
        self.file_path = LogConfig.RUNTIME_REPORT

        # Attack states
        self.states = {
            S.A0: self.scan,  # Step1. Information Gathering/Scanning------Assuming success
            S.A1: self.login_attempt,  # Step2. Unauthorized Access / Login attempt
            S.A2: self.lateral_movement,  # Step3. Lateral movement to target system
            S.A3: self.privilege_escalation,  # Step4. Privilege Escalation
            S.A4: self.malicious_activities,  # Step5. Malicious activities
        }

    def start_attack(self):
        self.current_state = S.A0
        while self.current_state in self.states:
            self.states[self.current_state]()

    def scan(self):
        if self.current_state == S.A0:
            print("->Scanning target............")
            msg = f"->Scanning target:{self.target}"
            log_att_process(self.file_path, msg)
            self.current_state = S.A1

    def login_attempt(self):
        if self.current_state == S.A1:
            print("->Attempting unauthorized access via login...")
            msg = f"->Attempting unauthorized access via login..."
            log_att_process(self.file_path, msg)
            login_successful = self.perform_login()
            if login_successful:
                print("->Login successful. BAC achieved.....")
                msg = "->Login successful. BAC achieved....."
                log_att_process(self.file_path, msg)
                self.success = True
                self.current_state = S.A2  # Proceed to lateral movement
            else:
                print("------>Login failed. Attack unsuccessful.")
                msg = "------>Login failed. Attack unsuccessful."
                log_att_process(self.file_path, msg)
                self.success = False
                self.current_state = None

    def perform_login(self):
        if self.target in weak_passwords:
            password = weak_passwords[self.target]
            if self.use_encryption:
                return False
            else:
                return password == weak_passwords[self.target]

        return False

    def lateral_movement(self):
        if self.current_state == S.A2:
            print(f"->Moving laterally through the network on target: {self.target}")
            msg = f"->Moving laterally through the network on target: {self.target}"
            log_att_process(self.file_path, msg)

            self.current_state = S.A3  # Move to privilege escalation

    def privilege_escalation(self):
        if self.current_state == S.A3:
            print("->Attempting privilege escalation...")
            msg = "->Attempting privilege escalation..."
            log_att_process(self.file_path, msg)
            self.current_state = S.A4  # Move to malicious activities

    def malicious_activities(self):
        print(f"->Performing malicious activities on {self.target}")
        msg = f"->Performing malicious activities on {self.target}"
        log_att_process(self.file_path, msg)
        self.bos_mode, self.rpf_mode = Mode.mapping.get(("BAC", self.target), (Mode.Normal, Mode.Normal))
        self.success = True
        self.current_state = None
        return self.bos_mode, self.rpf_mode
