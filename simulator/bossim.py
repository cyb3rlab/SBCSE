import sys
from mqtt_communication_module.bosmsghandler import BosMessageHandler
from utils.storyboard import MqttConfig, ClientConfig, Mode
from mqtt_communication_module.Authenticator.login_authen import Authenticator


class BosSimulator:
    def __init__(self, send_topic, recv_topic, broker, port, time, user, pw, use_encryption, enable_allowlist):
        self.time = time
        self.port = port
        self.mode = Mode.Normal
        self.broker = broker
        self.running = True
        self.token = ClientConfig.TOKEN
        self.client_id = ClientConfig.CLIENT_ID
        self.session_id = ClientConfig.SESSION_ID

        if not Authenticator.authenticate(user, pw, use_encryption):
            print("BOS authentication failed. Cannot start simulation.")
            return

        self.handler = BosMessageHandler(send_topic, recv_topic, broker, port, self.time)
        self.handler.client_ip_port = self.handler.bind_client_to_port()
        self.handler.enable_allowlist = enable_allowlist
        self.client = self.handler.client
        self.client.on_connect = self.handler.on_connect
        self.client.on_message = self.handler.on_message

    def observe_dt_status(self):
        self.handler.observe_dt_status(self.time)

    def start_simulation(self, stop_event):
        # Add the callbacks
        try:
            while not stop_event.is_set() and not self.handler.client.is_connected():
                self.time.sleep(1)

            self.client.loop_start()

            while self.running and not stop_event.is_set():

                if not self.client.is_connected():
                    self.client.reconnect()

                for _ in range(10):
                    if stop_event.is_set():
                        break
                    self.time.sleep(1)
        except Exception as e:
            print(e)

        finally:
            self.stop_simulation()

    def stop_simulation(self):
        if self.running:
            self.running = False
            self.client.loop_stop()
            try:
                self.client.disconnect()

            except Exception as e:
                print(f"Error during disconnection: {e}")
            print("BOS stopped")