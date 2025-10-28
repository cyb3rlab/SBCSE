import random
import time as real_time
import os
from mqtt_communication_module import mqtt_msghandler
from utils.timesim import TimeSim

# 网络干扰状态
NETWORK_DISTURBANCE_STATUS = {
    "enabled": False,
    "packet_loss": 0.0,
    "delay_range": None,
    "delay_chance": 1.0,  # 新增：默认所有消息都会延迟
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

            # 延迟逻辑（只有一定概率才触发）
            if NETWORK_DISTURBANCE_STATUS["delay_range"] and random.random() < NETWORK_DISTURBANCE_STATUS["delay_chance"]:
                delay = random.uniform(*NETWORK_DISTURBANCE_STATUS["delay_range"])
                if NETWORK_DISTURBANCE_STATUS["use_timesim"]:
                    NETWORK_DISTURBANCE_STATUS["use_timesim"].sleep(delay)
                else:
                    real_time.sleep(delay)

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
                if NETWORK_DISTURBANCE_STATUS["use_timesim"]:
                    NETWORK_DISTURBANCE_STATUS["use_timesim"].sleep(delay)
                else:
                    real_time.sleep(delay)

        _log_network_event(topic, getattr(data, 'id', 'N/A'), 'sent', delay)
        return original_send(self, data, topic, time_sim, file_path, qos, *args, **kwargs)
    return wrapper

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
    if not hasattr(mqtt_msghandler.MessageHandler.send, "_patched"):
        mqtt_msghandler.MessageHandler.send = _patched_send(mqtt_msghandler.MessageHandler.send)
        mqtt_msghandler.MessageHandler.send._patched = True

    if not hasattr(mqtt_msghandler.MessageHandler.rob_com_send, "_patched"):
        mqtt_msghandler.MessageHandler.rob_com_send = _patched_rob_com_send(mqtt_msghandler.MessageHandler.rob_com_send)
        mqtt_msghandler.MessageHandler.rob_com_send._patched = True

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
