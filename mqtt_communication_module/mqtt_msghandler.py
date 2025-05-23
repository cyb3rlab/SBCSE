import json
import ssl
import threading
import paho.mqtt.client as mqtt
from utils.storyboard import MqttConfig, LogConfig
from utils.msglog import msg_log

# Define the MessageHandler class for basic MQTT client setup and handling
# MessageBaseHandler
class MessageHandler:
    def __init__(self, send_topic, recv_topic, broker, port, use_mqtts=False, enable_allowlist=False, cert_path=None, key_path=None, ca_path=None, client_ip=None):
        self.client = mqtt.Client()
        self.client_topic = send_topic
        self.server_topic = recv_topic
        self.broker = broker
        self.port = port
        self.allowlist = MqttConfig.ALLOWLIST

        self.use_mqtts = use_mqtts
        self.enable_allowlist = enable_allowlist or False
        self.cert_path = cert_path
        self.key_path = key_path
        self.ca_path = ca_path
        self.building_file = LogConfig.FILE_BUILDING_LOG
        self.client_ip = client_ip
        self.client_connect = False

        if self.use_mqtts:
            print(f"Using MQTTS with cert_path={self.cert_path}, key_path={self.key_path}, ca_path={self.ca_path}")
            self.client.tls_set(certfile=self.cert_path, keyfile=self.key_path, ca_certs=self.ca_path,
                                cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS)
            self.client.tls_insecure_set(False)

        if self.enable_allowlist:
            # allowlist check: reject connections that are not in the allowlist
            if not self.check_ip_in_allowlist(self.client_ip):
                print(f"Connection from {self.client_ip} denied. Not in allowlist.")
                self.client.disconnect()
                return

            if self.client_ip is None:
                print("Client IP is None, rejecting connection.")
                self.client.disconnect()
                return

        print(f"Client connected in {self.client_ip}")
        self.client_connect = True

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.send_init()
        self.recv_init()


    def check_ip_in_allowlist(self, client_ip):
        if client_ip in self.allowlist:
            return True
        return False

    def on_connect(self, client, userdata, flags, rc):

        pass

    def on_message(self, client, userdata, msg):
        # self.client.subscribe(msg.topic)
        # msg_log(msg.topic, file_path=self.building_file)
        print(f"Received message on topic {msg.topic}:{msg.payload}")

    def recv_thread(self, server, port):
        print(f"Server starting on port {self.port}...")
        try:
            server.connect(self.broker, port, 60)
            server.loop_forever()
        except Exception as e:
            print(f"Server connection failed: {e}")

    def recv_init(self):
        self.server = mqtt.Client()
        if self.use_mqtts:
            print(f"Using MQTTS for server with cert_path={self.cert_path}, key_path={self.key_path}, ca_path={self.ca_path}")
            self.server.tls_set(certfile=self.cert_path, keyfile=self.key_path, ca_certs=self.ca_path, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS)
            self.server.tls_insecure_set(False)
        self.server.on_connect = self.on_connect
        self.server.on_message = self.on_message
        threading.Thread(target=self.recv_thread, args=(self.server, self.port), daemon=True).start()

    def send_init(self):
        try:

            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
        except Exception as e:
            print(f"Client connection failed: {e}")

    def send(self, data, topic, time_sim, file_path, qos=MqttConfig.MQTT_QOS1):
        msg = json.dumps(data)
        try:

            if not self.client.is_connected():
                print("Reconnecting to the broker++++++")
                self.client.reconnect()

            if topic is None:
                topic = self.client_topic

            result = self.client.publish(topic, msg, qos=qos)
            status = result.rc

            if status == mqtt.MQTT_ERR_SUCCESS:
                print(f"{topic}: '{msg}'")
                msg_log(topic, data, time_sim, file_path=self.building_file)
                msg_log(topic, data, time_sim, file_path=file_path)
            else:
                print(status)
                print(f"Failed to send message to {self.client_topic}.Error code:{result.rc}")
        except (TimeoutError, ConnectionError, mqtt.MQTTException) as e:
            print("Publish operation time out.Retrying.....")

    def rob_com_send(self, data, topic, time_sim, file_path=None, qos=MqttConfig.MQTT_QOS1):
        msg = json.dumps(data)
        try:
            if not self.client.is_connected():
                print("Reconnecting to the broker-----")
                self.client.reconnect()

            if topic is None:
                topic = self.client_topic

            result = self.client.publish(topic, msg, qos=qos)
            status = result.rc

            if status == mqtt.MQTT_ERR_SUCCESS:
                print(f"{topic}: `{msg}`")
                msg_log(topic, data, time_sim, file_path=file_path)
            else:
                print(status)
                print(f"Failed to send message to {self.client_topic}.Error code:{result.rc}")
        except TimeoutError:
            print("Publish operation time out.Retrying.....")





