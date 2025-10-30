import random
import time as real_time
import os
import types
# from mqtt_communication_module import mqtt_msghandler
import gc
from mqtt_communication_module.mqtt_msghandler import MessageHandler
from utils.timesim import TimeSim

# 网络干扰状态
NETWORK_DISTURBANCE_STATUS = {
    "enabled": False,
    "packet_loss": 0.0,
    "delay_range": None,
    "delay_chance": 1.0,
    "use_timesim": None,
    "log_file": None
}

def _log_network_event(topic, message_id, event, delay):
    """记录每条消息的网络状态"""
    if NETWORK_DISTURBANCE_STATUS["log_file"] is None:
        return
    os.makedirs(os.path.dirname(NETWORK_DISTURBANCE_STATUS["log_file"]), exist_ok=True)

    # 使用 current_timestamp() 替代 current_time()
    if NETWORK_DISTURBANCE_STATUS["use_timesim"]:
        current_time = NETWORK_DISTURBANCE_STATUS["use_timesim"].current_timestamp()
    else:
        current_time = real_time.time()

    with open(NETWORK_DISTURBANCE_STATUS["log_file"], 'a') as f:
        f.write(f"{current_time:.3f},{topic},{message_id},{event},{delay:.3f}\n")

def _patched_send(original_send):
    def wrapper(self, data, topic, time_sim=None, file_path=None, qos=1, *args, **kwargs):
        delay = 0
        if NETWORK_DISTURBANCE_STATUS["enabled"]:
            # 丢包逻辑
            if random.random() < NETWORK_DISTURBANCE_STATUS["packet_loss"]:
                _log_network_event(topic, getattr(data, 'id', 'N/A'), 'dropped', 0)
                print(f"[NetworkDisturb] Dropped message on topic: {topic}")
                return

            if NETWORK_DISTURBANCE_STATUS["delay_range"] and random.random() < NETWORK_DISTURBANCE_STATUS["delay_chance"]:
                delay = random.uniform(*NETWORK_DISTURBANCE_STATUS["delay_range"])
                NETWORK_DISTURBANCE_STATUS["use_timesim"].sleep(delay)

        _log_network_event(topic, getattr(data, 'id', 'N/A'), 'sent', delay)
        return original_send(self, data, topic, time_sim, file_path, qos, *args, **kwargs)
    return wrapper

def _patched_rob_com_send(original_send):
    def wrapper(self, data, topic, time_sim=None, file_path=None, qos=1, *args, **kwargs):
        delay = 0
        if NETWORK_DISTURBANCE_STATUS["enabled"]:
            if random.random() < NETWORK_DISTURBANCE_STATUS["packet_loss"]:
                _log_network_event(topic, getattr(data, 'id', 'N/A'), 'dropped', 0)
                print(f"[NetworkDisturb] Dropped ROB message on topic: {topic}")
                return

            if NETWORK_DISTURBANCE_STATUS["delay_range"] and random.random() < NETWORK_DISTURBANCE_STATUS["delay_chance"]:
                delay = random.uniform(*NETWORK_DISTURBANCE_STATUS["delay_range"])
                NETWORK_DISTURBANCE_STATUS["use_timesim"].sleep(delay)


        _log_network_event(topic, getattr(data, 'id', 'N/A'), 'sent', delay)
        return original_send(self, data, topic, time_sim, file_path, qos, *args, **kwargs)
    return wrapper

def _patch_on_message_with_delay(handler_instance):
    """delay injection patch"""
    if not hasattr(handler_instance, "server"):
        print("[NetworkDisturb] No server found in handler, skip recv patch.")
        return

    original_on_message = handler_instance.server.on_message

    def delayed_on_message(client, userdata, msg):
        delay = 0
        if NETWORK_DISTURBANCE_STATUS["enabled"]:
            if random.random() < NETWORK_DISTURBANCE_STATUS["packet_loss"]:
                _log_network_event(msg.topic, getattr(msg, 'mid', 'N/A'), 'recv_dropped', 0)
                print(f"[NetworkDisturb] Dropped incoming message on topic: {msg.topic}")
                return

            if NETWORK_DISTURBANCE_STATUS["delay_range"] and random.random() <= NETWORK_DISTURBANCE_STATUS["delay_chance"]:
                delay = random.uniform(*NETWORK_DISTURBANCE_STATUS["delay_range"])

                NETWORK_DISTURBANCE_STATUS["use_timesim"].sleep(delay)

                _log_network_event(msg.topic, getattr(msg, 'mid', 'N/A'), 'recv_delayed', delay)
        return original_on_message(client, userdata, msg)

    handler_instance.server.on_message = delayed_on_message
    handler_instance.client.on_message = delayed_on_message
    print(f"[NetworkDisturb] recv delay patched for {handler_instance.__class__.__name__}")

# def _patched_recv_thread(original_recv_thread):
#     def wrapper(self, server, port, *args, **kwargs):
#         print(f"[NetworkDisturb] Patched recv_thread running on port {port}")
#         try:
#             server.connect(self.broker, port, 60)
#             while True:
#                 if NETWORK_DISTURBANCE_STATUS["enabled"]:
#                     if (NETWORK_DISTURBANCE_STATUS["delay_range"] and
#                         random.random() < NETWORK_DISTURBANCE_STATUS["delay_chance"]):
#                         delay = random.uniform(*NETWORK_DISTURBANCE_STATUS["delay_range"])
#                         if NETWORK_DISTURBANCE_STATUS["use_timesim"]:
#                             NETWORK_DISTURBANCE_STATUS["use_timesim"].sleep(delay)
#                         else:
#                             real_time.sleep(delay)
#                         _log_network_event("recv_thread", "N/A", "recv_delay", delay)
#
#                     if random.random() < NETWORK_DISTURBANCE_STATUS["packet_loss"]:
#                         _log_network_event("recv_thread", "N/A", "recv_dropped", 0)
#                         print("[NetworkDisturb] Dropped one incoming message (simulated packet loss)")
#                         continue
#
#                 server.loop(timeout=1.0)  # 非阻塞循环
#         except Exception as e:
#             print(f"Server connection failed: {e}")
#     return wrapper


def enable_network_disturbance(packet_loss=0.1, delay_range=(0.1, 0.5), delay_chance=1.0, use_timesim=None, log_file=None):
    """启用网络干扰，并打补丁"""
    NETWORK_DISTURBANCE_STATUS.update({
        "enabled": True,
        "packet_loss": packet_loss,
        "delay_range": delay_range,
        "delay_chance": delay_chance,
        "use_timesim": use_timesim,
        "log_file": log_file
    })

    # 打补丁
    if not hasattr(MessageHandler.send, "_patched"):
        MessageHandler.send = _patched_send(MessageHandler.send)
        MessageHandler.send._patched = True

    if not hasattr(MessageHandler.rob_com_send, "_patched"):
        MessageHandler.rob_com_send = _patched_rob_com_send(MessageHandler.rob_com_send)
        MessageHandler.rob_com_send._patched = True

    # # recv_thread
    # if not hasattr(MessageHandler.recv_thread, "_patched"):
    #     MessageHandler.recv_thread = _patched_recv_thread(
    #         MessageHandler.recv_thread)
    #   MessageHandler.recv_thread._patched = True
    for obj in gc.get_objects():
        # 查找所有 MessageHandler 子类实例
        if isinstance(obj, MessageHandler):
            try:
                _patch_on_message_with_delay(obj)
            except Exception as e:
                print(f"[NetworkDisturb] Failed to patch {obj.__class__.__name__}: {e}")

    print(f"[NetworkDisturb] Enabled: loss={packet_loss*100:.1f}%, delay={delay_range}s, delay_chance={delay_chance*100:.1f}%")

def log_network_disturb_status(file_path):
    """记录当前网络干扰的配置状态"""
    status = NETWORK_DISTURBANCE_STATUS
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'a') as f:
        f.write(f"[NetworkDisturb] Enabled={status['enabled']}, "
                f"PacketLoss={status['packet_loss']*100:.1f}%, "
                f"DelayRange={status['delay_range']}, "
                f"DelayChance={status['delay_chance']*100:.1f}%\n")
