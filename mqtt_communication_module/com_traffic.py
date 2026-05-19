import numpy as np
import csv, json, time
from datetime import datetime
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

        # message counters
        self.last_received = 0
        self.last_sent = 0

        # byte counters
        self.last_bytes_received = 0
        self.last_bytes_sent = 0
        self.last_stats = {}

        # for throughput
        self.prev_sent = None
        self.prev_received = None
        self.prev_bytes_sent = None
        self.prev_bytes_received = None
        self.prev_time = None

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker successfully")
            # message counts
            client.subscribe("$SYS/broker/messages/sent")
            client.subscribe("$SYS/broker/messages/received")

            # byte counts (NEW)
            client.subscribe("$SYS/broker/bytes/sent")
            client.subscribe("$SYS/broker/bytes/received")
        else:
            print(f"Failed to connect, return code {rc}")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode(errors="ignore").strip()
        try:
            val = int(payload)
        except ValueError:
            print(f"Invalid payload received on topic {topic}: {payload}")
            return

        if topic == "$SYS/broker/messages/received":  # Counts the number of PUBLISH messages received by the Broker.
            self.last_received = int(payload)
        elif topic == "$SYS/broker/messages/sent":
            self.last_sent = int(payload)
        elif topic == "$SYS/broker/bytes/received":
            self.last_bytes_received = val
        elif topic == "$SYS/broker/bytes/sent":
            self.last_bytes_sent = val

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

    def log_stats(self):
        success_rate = self.calculate_success_rate()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(self.data_file, "a", newline="") as file:
            writer = csv.writer(file)
            if file.tell() == 0:
                writer.writerow([
                    "Timestamp",
                    "Messages Received", "Messages Sent",
                    "Bytes Received", "Bytes Sent",  # NEW
                    "Success Rate"
                ])

            writer.writerow([
                timestamp,
                self.last_received, self.last_sent,
                self.last_bytes_received, self.last_bytes_sent,  # NEW
                f"{success_rate:.2f}%" if success_rate is not None else ""
            ])

    def log_throughput(self):
        now = time.time()

        if self.prev_time is None:
            self.prev_time = now
            self.prev_sent = self.last_sent
            self.prev_received = self.last_received
            self.prev_bytes_sent = self.last_bytes_sent
            self.prev_bytes_received = self.last_bytes_received
            return

        dt = now - self.prev_time
        if dt <= 0:
            return
        # message deltas
        d_sent = self.last_sent - (self.prev_sent or 0)
        d_recv = self.last_received - (self.prev_received or 0)

        # byte deltas
        d_bsent = self.last_bytes_sent - (self.prev_bytes_sent or 0)
        d_brecv = self.last_bytes_received - (self.prev_bytes_received or 0)

        if d_sent < 0: d_sent = 0
        if d_recv < 0: d_recv = 0
        if d_bsent < 0: d_bsent = 0
        if d_brecv < 0: d_brecv = 0

        thr_sent = d_sent / dt
        thr_recv = d_recv / dt
        thr_bsent = d_bsent / dt
        thr_brecv = d_brecv / dt

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

        with open(self.data_file.replace(".csv", "_throughput.csv"),
                  "a", newline="") as f:

            w = csv.writer(f)
            if f.tell() == 0:
                w.writerow([
                    "Timestamp",
                    "Delta Sent", "Delta Received",
                    "Throughput Sent (msg/s)",
                    "Throughput Received (msg/s)",
                    "Delta Bytes Sent", "Delta Bytes Received",
                    "Throughput Bytes Sent (B/s)", "Throughput Bytes Received (B/s)"
                ])

            w.writerow([
                timestamp,
                d_sent, d_recv,
                f"{thr_sent:.3f}",f"{thr_recv:.3f}",
                d_bsent, d_brecv,
                f"{thr_bsent:.3f}", f"{thr_brecv:.3f}"
            ])

        self.prev_time = now
        self.prev_sent = self.last_sent
        self.prev_received = self.last_received
        self.prev_bytes_sent = self.last_bytes_sent
        self.prev_bytes_received = self.last_bytes_received

    def start_monitoring(self):
            self.client.connect(self.broker_address, self.broker_port)
            self.client.loop_start()
            try:
                while True:
                    time.sleep(self.interval)
                    self.log_stats()
                    # self.log_success_rate()
                    self.log_throughput()
            except KeyboardInterrupt:
                print("Monitoring stopped by user")
            finally:
                self.client.loop_stop()
                self.client.disconnect()