"""
The basic function is consistent with simulator/rpfsim.py.
"""
import sys
from utils.storyboard import ClientConfig, StateMachineConfig, Mode
from device_motion_module.servicerobot import RobotHandler
from device_motion_module.elevator import ElvHandler
from fuzzer.rpffuzzer.frpfmsghandler import FRPFMsgHandler

class FRPFSimulator:
    def __init__(self, send_topic, recv_topic, broker, port, tasks, time, user, pw, use_encryption, enable_allowlist):
        self.time = time
        self.port = port
        self.mode = Mode.FUZZING
        self.broker = broker
        self.running = True
        self.token = ClientConfig.TOKEN
        self.client_id = ClientConfig.CLIENT_ID
        self.session_id = ClientConfig.SESSION_ID
        self.task_complete = False

        # if not Authenticator.authenticate(user, pw, use_encryption):
        #     print("RPF authentication failed. Cannot start simulation.")
        #     return

        self.handler = FRPFMsgHandler(send_topic, recv_topic, broker, port, self.time)
        # self.handler.client_ip_port = self.handler.bind_client_to_port()
        # self.handler.enable_allowlist = enable_allowlist
        # self.client = self.handler.client
        self.client = self.handler.client
        self.client.on_connect = self.handler.on_connect
        self.client.on_message = self.handler.on_message
        self.initialized = False
        
        self.robothandler = RobotHandler()
        self.elvhandler = ElvHandler()

        self.tasks = tasks
        self.handler.tasks = tasks
        self.handler.set_mode(self.mode)

    def fuzzing_msg(self, rob):
        self.handler.mode_handlers[self.handler.mode].start_RCPMachine(rob, self.stop_event)

    def start_simulation(self, stop_event):
        self.stop_event = stop_event
        try:
            while not stop_event.is_set() and not all(value is not None for value in self.handler.rob_dt_data_dict.values()):
                self.time.sleep(0.5)

            while not stop_event.is_set() and not self.handler.client.is_connected():
                self.time.sleep(1)

            self.client.loop_start()

            self.robothandler.arrangement(self.handler.tasks)
            self.initialized = True

            while self.running and not stop_event.is_set():

                if not self.client.is_connected():
                    self.stop_simulation()

                if not self.handler.tasks:
                    self.stop_simulation()
                    self.task_complete = True
                    break

                if self.handler.mode in self.handler.mode_handlers:
                    self.handler.mode_handlers[self.handler.mode].handle_task()
                    
                for _ in range(10):
                    if stop_event.is_set():
                        break
                    self.time.sleep(1)
        except Exception as e:
            print("FRPF: "+e, sys.stderr)
        finally:
            self.stop_simulation()

    def stop_simulation(self):
        for rob_name in self.robothandler.rob_dict.keys():
            if self.robothandler.rob_dict[rob_name]['rcp_state_machine']:
                self.robothandler.rob_dict[rob_name]['rcp_state_machine'].rcp_status = StateMachineConfig.COMPLETED
        if self.running:
            self.running = False
            self.client.loop_stop()
            self.handler.fdp = None
            self.handler.stop_system()
            try:
                self.client.disconnect()
            except Exception as e:
                print(f"Error during disconnection: {e}")
            print("RPF stopped")