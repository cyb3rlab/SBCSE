import psutil
import time
import csv
from datetime import datetime
# from scapy.all import sniff, Raw
# from scapy.layers.inet import TCP
from utils.storyboard import MqttConfig, LogConfig
import paho.mqtt.client as mqtt
from utils.msglog import log_traffic, log_connection

class ConnectionMonitor:
    def __init__(self, broker, port, monitor_interval=1, log_file=LogConfig.CONNECTIONS_LOG, time_sim=None):
        self.broker = broker
        self.port = port
        self.monitor_interval = monitor_interval
        self.log_file = log_file
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.connected_clients = 0
        self.disconnected_clients = 0
        self.time = time_sim
        self.running = True

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("C-Monitor Connected to MQTT Broker successfully")
        else:
            print(f"C-Monitor Failed to connect, return code {rc}")

    def on_message(self, client, userdata, message):
        topic = message.topic
        try:
            payload = int(message.payload.decode())
            if topic == "$SYS/broker/clients/connected":
                self.connected_clients = int(payload)
            elif topic == "$SYS/broker/clients/disconnected":
                self.disconnected_clients = int(payload)
        except ValueError:
            print(f"Failed to decode payload for topic {topic}: {message.payload}")

    def start_monitoring(self):
        self.client.connect(self.broker, self.port)
        self.client.subscribe("$SYS/broker/clients/connected")  # Current active connections
        self.client.subscribe("$SYS/broker/clients/disconnected")
        self.client.loop_start()
        # self.client.loop_forever()

        while self.running:
            log_connection(self.log_file, self.connected_clients, self.time)
            time.sleep(self.monitor_interval)

    def stop_monitoring(self):
        self.running = False
        self.client.loop_stop()
        self.client.disconnect()

class MQTTBrokerMonitor:
    def __init__(self, broker_address, broker_port=1883, data_file=LogConfig.BROKER_LOG, interval=1):
        self.broker_address = broker_address
        self.broker_port = broker_port
        self.data_file = data_file
        self.interval = interval
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.last_received = 0
        self.last_sent = 0
        self.last_stats = {}

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker successfully")
            client.subscribe("$SYS/broker/messages/sent")
            client.subscribe("$SYS/broker/messages/received")

        else:
            print(f"Failed to connect, return code {rc}")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()
        try:
            if topic == "$SYS/broker/messages/received":  # Counts the number of PUBLISH messages received by the Broker.
                self.last_received = int(payload)
            elif topic == "$SYS/broker/messages/sent":   #"$SYS/broker/messages/sent":
                self.last_sent = int(payload)
        except ValueError:
            print(f"Invalid payload received on topic {topic}: {payload}")

    def calculate_success_rate(self):
        if self.last_received > 0:
            return min((self.last_sent / self.last_received) * 100, 100)
        return None

    def log_success_rate(self):
        success_rate = self.calculate_success_rate()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if success_rate is not None:
            with open(self.data_file, 'a', newline='') as file:
                writer = csv.writer(file)
                if file.tell() == 0:
                    writer.writerow(["Timestamp", "Messages Received", "Messages Sent", "Success Rate"])
                writer.writerow([timestamp, self.last_received, self.last_sent, f"{success_rate:.2f}%"])


    def start_monitoring(self):
            self.client.connect(self.broker_address, self.broker_port)
            self.client.loop_start()
            try:
                while True:
                    time.sleep(self.interval)
                    self.log_success_rate()
            except KeyboardInterrupt:
                print("Monitoring stopped by user")
            finally:
                self.client.loop_stop()
                self.client.disconnect()

