"""
The basic function is consistent with simulator/bossim,py.
"""
import sys
from simulator.bossim import BosSimulator
from fuzzer.bosfuzzer.fbosmsghandler import FBosMessageHandler
from utils.storyboard import MqttConfig, ClientConfig, Mode

class FBosSimulator(BosSimulator):
    def __init__(self, send_topic, recv_topic, broker, port, time, user, pw, use_encryption, enable_allowlist):
        self.time = time
        self.port = port
        self.mode = Mode.FUZZING
        self.broker = broker
        self.running = True
        self.token = ClientConfig.TOKEN
        self.client_id = ClientConfig.CLIENT_ID
        self.session_id = ClientConfig.SESSION_ID

        # if not Authenticator.authenticate(user, pw, use_encryption):
        #     print("BOS authentication failed. Cannot start simulation.")
        #     return

        self.handler = FBosMessageHandler(send_topic, recv_topic, broker, port, self.time)
        # self.handler.client_ip_port = self.handler.bind_client_to_port()
        # self.handler.enable_allowlist = enable_allowlist
        self.client = self.handler.client
        self.client.on_connect = self.handler.on_connect
        self.client.on_message = self.handler.on_message


    def start_simulation(self, stop_event):
        self.handler.stop_event = stop_event
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
            print("FBOS: "+e, sys.stderr)
        finally:
            self.stop_simulation()