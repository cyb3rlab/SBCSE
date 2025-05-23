from utils.storyboard import LogConfig, MqttConfig, ClientConfig, RobotConfig, ScenarioConfig, Mode, StateMachineConfig
from device_motion_module.servicerobot import RobotHandler
from mqtt_communication_module.rpfmsghandler import RpfMessageHandler
from database.user_management import db
from mqtt_communication_module.Authenticator.login_authen import Authenticator


class RpfSimulator:
    def __init__(self, send_topic, recv_topic, broker, port, tasks, time, user, pw, use_encryption, enable_allowlist):
        self.time = time
        self.port = port
        self.mode = Mode.Normal
        self.broker = broker
        self.running = True
        self.token = ClientConfig.TOKEN
        self.client_id = ClientConfig.CLIENT_ID
        self.session_id = ClientConfig.SESSION_ID
        self.task_complete = False

        # db.authenticate_user(user,pw,use_encryption)
        # # Initialize the authentication module and perform authentication
        # self.authenticator = Authenticator()
        if not Authenticator.authenticate(user, pw, use_encryption):
            print("RPF authentication failed. Cannot start simulation.")
            return

        self.handler = RpfMessageHandler(send_topic, recv_topic, broker, port, self.time)
        self.handler.client_ip_port = self.handler.bind_client_to_port()
        self.handler.enable_allowlist = enable_allowlist
        self.client = self.handler.client
        self.client.on_connect = self.handler.on_connect
        self.client.on_message = self.handler.on_message

        self.robothandler = RobotHandler()

        self.tasks = tasks
        self.handler.tasks = tasks


    def start_simulation(self, stop_event):
        try:
            # Wait bot_dt_data
            while not stop_event.is_set() and not all(value is not None for value in self.handler.rob_dt_data_dict.values()):
                self.time.sleep(0.5)

            while not stop_event.is_set() and not self.handler.client.is_connected():
                self.time.sleep(1)

            self.client.loop_start()

            self.robothandler.arrangement(self.handler.tasks)

            while self.running and not stop_event.is_set():

                if not self.client.is_connected():
                    self.client.connect(self.broker, self.port)


                if not self.handler.tasks:
                    self.stop_simulation()
                    self.task_complete = True
                    break

                # change mode
                if self.handler.mode in self.handler.mode_handlers:
                    self.handler.mode_handlers[self.handler.mode].handle_task()

                for _ in range(10):
                    if stop_event.is_set():
                        break
                    self.time.sleep(1)
        except Exception as e:
            print(e)

        finally:
            self.stop_simulation()

    def stop_simulation(self):
        for rob_name in self.robothandler.rob_dict.keys():
            self.robothandler.rob_dict[rob_name]['rcp_state_machine'].rcp_status = StateMachineConfig.COMPLETED
        if self.running:
            self.running = False
            self.client.loop_stop()
            self.handler.stop_system()
            try:
                self.client.disconnect()
            except Exception as e:
                print(f"Error during disconnection: {e}")
            print("RPF stopped")


