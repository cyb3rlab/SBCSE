import threading
import concurrent.futures
import socket
import time
import random
import paho.mqtt.client as mqtt
from mqtt_communication_module.mqtt_msghandler import MessageHandler
from utils.storyboard import LogConfig, RobotConfig, CmdConfig, ELVConfig, MqttConfig
from utils.msglog import log_id
import json


class BotnetClient(MessageHandler):
    def __init__(self, send_topic, recv_topic, broker, port, time, enable_allowlist=None):
        # def __init__(self, broker, port, topic, message=None, frequency=None):
        self.client = mqtt.Client()
        self.time = time
        self.port = port
        self.broker = broker
        self.send_topic = send_topic[0]
        self.recv_topic = None
        self.enable_allowlist = enable_allowlist
        self.client_ip_list = MqttConfig.client_ip
        self.bot_id = "bot"
        self.client_ip = self.generate_random_ip()
        self.allowlist = MqttConfig.ALLOWLIST

        self.file_path = LogConfig.RUNTIME_REPORT
        use_mqtts = None
        cert_path = key_path = ca_path = None

        # Setting callbacks
        self.client.on_connect = self.on_connect
        self.client.on_publish = self.on_publish
        self.client.on_disconnect = self.on_disconnect

        if self.enable_allowlist and not self.is_valid():
            log_id(self.file_path, f"Client IP {self.client_ip} is not in allowlist. Disconnecting.")
            self.disconnect()
            self.is_connected = False
            return

        super().__init__(send_topic, recv_topic, broker, port, use_mqtts, enable_allowlist, cert_path, key_path,
                         ca_path, self.client_ip)
        self.is_connected = True

    def is_valid(self):
        """Check if the client IP is in the allowlist"""
        return self.client_ip in self.allowlist

    def bind_client_to_port(self):
        """Bind the client to a static IP"""
        try:
            local_ip = self.client_ip_list.get(self.bot_id, "192.168.1.101" )

            local_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            local_socket.bind((local_ip, 0))
            ip = local_socket.getsockname()[0]

            #self.client_ip, self.client_port = local_socket.getsockname()
            client_info = f"Bot Connect to {ip} ++++++++++++++++"
            print(client_info)
            return ip

        except Exception as e:
            print(f"Error binding client {self.bot_id}: {e}")
            return None

    def generate_random_ip(self):
        # Generate a random IP address
        # return f"192.168.100.{random.randint(1, 254)}"
        return f"192.168.100.{random.randint(1, 254)}"

    def on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            # print("BOT——Connected successfully")
            print(f"{client._client_id.decode()} connected successfully")
            client.publish(self.send_topic, "connect", qos=1)
        else:
            print(f"Connection failed with code {rc}")

    def on_disconnect(self, client, userdata, rc):
        print(f"{client._client_id.decode()} disconnected with result code " + str(rc))
        try:
            time.sleep(3)  # Prevent infinite reconnection from causing CPU 100%
            client.reconnect()
        except Exception as e:
            print(f"Reconnection failed: {e}")
        print("Disconnected with result code " + str(rc))

    def connect(self):
        self.client_ip = self.bind_client_to_port()
        if self.client_ip:
            try:
                self.client.connect(self.broker, self.port, 10)
                self.client.loop_start()
            except Exception as e:
                print(f"Client connection failed: {e}")
        else:
            print("Failed to bind client IP, aborting connection.")

    def on_publish(self, client, userdata, mid, properties=None):
        print(f"Message {mid} published.....")

    def send_ATT(self):
        payload = "connect" * 10000
        while True:
            try:
                self.client.publish(self.send_topic, payload, qos=1)
                time.sleep(0.01)
            except Exception as e:
                print(f"Error publishing message: {e}")

    def disconnect(self):
        """Disconnect Client"""
        self.client.disconnect()


if __name__ == "__main__":
    send_topic = [MqttConfig.ATT_TOPIC]
    recv_topic = []
    enable_allowlist = True
    test_client = BotnetClient(send_topic, recv_topic, "localhost", 1883, time=None, enable_allowlist=enable_allowlist)
    test_client.bind_client_to_port()

