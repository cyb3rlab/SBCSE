"""
Logging MQTT communications

This module provides functionality to log messages to two different Log files.

Functions:
- determine_action: Determines whether a message was sent or received based on the topic.
- msg_log: Logs the msg with its topic and timestamp to the specified files.
"""
import json
import csv
from datetime import datetime
from utils.storyboard import LogConfig, RobotConfig, CmdConfig
from utils.utils import write_file

formatted_datetime = LogConfig.DATETIME

FILE_ELV_LOG = LogConfig.FILE_ELV_LOG
FILE_BOS_LOG = LogConfig.FILE_BOS_LOG
FILE_RPF_BOS_LOG = LogConfig.FILE_RPF_BOS_LOG
FILE_RPF_ROB_LOG = LogConfig.FILE_RPF_ROB_LOG
FILE_ROB_JP_LOG = LogConfig.FILE_ROB_JP_LOG
FILE_ROB_LOG = LogConfig.FILE_ROB_LOG
FILE_BUILDING_LOG = LogConfig.FILE_BUILDING_LOG
FILE_ROB_POSITION_LOG = LogConfig.FILE_ROB_POSITION_LOG
RUNTIME_REPORT = LogConfig.RUNTIME_REPORT


def determine_action(topic, file_path):
    """
    Determine the action of the message (sent or received) based on the topic and file path.

    :param topic: MQTT topic.
    :param file_path: Path of the file.
    :return:
        'send' if the message was sent,
        'recv' if the message was received.
    """
    topic_actions = LogConfig.topic_file_action_mapping.get(topic, {})
    return topic_actions.get(file_path, None)


# elv,prf,prf cmd log
def msg_log(topic, message, time_sim, file_path):
    try:
        action = determine_action(topic, file_path)
        timesim = time_sim.current_jst_datetime()

        # Format messages with jst time
        jst_time_msg = f"{timesim.strftime(formatted_datetime)} {topic} was {action}:\n{timesim.strftime(formatted_datetime)} {{\n"
        # Add message content to formatted messages

        for key, value in message.items():
            jst_time_msg += f"{timesim.strftime(formatted_datetime)}\t {key}: {value}\n"
        # Add closing brackets and newline to formatted messages
        jst_time_msg += f"{timesim.strftime(formatted_datetime)} }}\n\n"
        # Write formatted messages to FILE1 using jst time

        if topic == 'attack_topic':
            attack_details = f"DDOS Attack Detected---------\nTopic: {topic}\nMessage:\n"
            for key, value in message.items():
                attack_details += f"\t{key}: {value}\n"
            jst_time_msg += attack_details + "\n"

        if file_path == None:
            return

        write_file(file_path, jst_time_msg)

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        print(f"Topic: {topic}")
        print(f"Message: {message}")


# rob position log
def rob_position_log(data, time_sim, file_path):
    timesim = time_sim.current_jst_datetime()
    map_no = data.get('map_no')
    status = data.get('状態')
    position = data.get('position')

    with open(file_path, 'a') as file:
        fieldnames = ['timestamp', 'map_no', '状態', 'X', 'Y', 'Radian']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        # Check if the file is empty and write header if needed
        if file.tell() == 0:
            writer.writeheader()
        writer.writerow({'timestamp': timesim.strftime("%Y/%m/%d %H:%M:%S"),
                         'map_no': map_no,
                         '状態': status,
                         'X': position[0],
                         'Y': position[1],
                         'Radian': position[2]})


# rob communication log
def rob_communication_log(cmd, target_floor, data, time_sim, file_path, message_type):
    # self.initial_get_on = False
    # self.initial_get_off = True

    with open(file_path, 'a') as file:
        fieldnames = ['timestamp', 'message']
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        # Get the current timestamp
        timestamp = time_sim.current_jst_datetime().strftime("%Y/%m/%d %H:%M:%S.%f")[:-3]

        if message_type == 'elv':
            if data['inDrivingPermission']:
                agv_mode = 'ON'
            else:
                agv_mode = 'OFF'
            if data['door'] == 'close':
                door = 'Close'
            elif data['door'] == 'open':
                door = 'Open'
            else:
                door = data['door']

            message = f"AGVモード:{agv_mode}, エレベータ現在階:{data['floor']}, エレベータ扉状態:{door}"

        elif message_type == 'rob':
            movingStatus = data.get("movingStatus")
            cmd = cmd

            if movingStatus == RobotConfig.WAIT:
                message = f"ロボット現在フロア = {data['floor']}, ロボット状態 = {movingStatus}"

            elif cmd == RobotConfig.CALLING:
                message = [f"エレベータ呼出し 目的階: {data['floor']}", f"ロボット現在フロア = {data['floor']}, ロボット状態 = {movingStatus}"]

            elif cmd == CmdConfig.GETTING_ON:
                message = ["乗車準備完了", f"ロボット現在フロア = {data['floor']}, ロボット状態 = {movingStatus}"]

            elif cmd == CmdConfig.GETTING_OFF:
                message = ["降車準備完了", f"ロボット現在フロア = {target_floor}, ロボット状態 = {movingStatus}"]
            elif movingStatus == None:
                pass
            else:
                message = f"ロボット現在フロア = {data['floor']}, ロボット状態 = {movingStatus}"


        # Check if the file is empty and write the header if needed
        if file.tell() == 0:
            writer.writeheader()
        # Write the row with timestamp and message
        if type(message) == str:
            timestamp = time_sim.current_jst_datetime().strftime("%Y/%m/%d %H:%M:%S.%f")[:-3]
            writer.writerow({'timestamp': timestamp, 'message': message})
        else:
            for msg in message:
                timestamp = time_sim.current_jst_datetime().strftime("%Y/%m/%d %H:%M:%S.%f")[:-3]
                writer.writerow({'timestamp': timestamp, 'message': msg})

def action_log(action_data, floor, time_sim, path):
    timestamp = time_sim.current_jst_datetime()
    if isinstance(timestamp, float):
        pass
    else:
        timestamp = timestamp.strftime("%Y/%m/%d %H:%M:%S")
    with open(path, 'a') as file:
        fieldnames = ['timestamp', 'floor', 'action']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        # Check if the file is empty and write header if needed
        if file.tell() == 0:
            writer.writeheader()
        writer.writerow({'timestamp': timestamp,
                         'floor': floor,
                         'action': action_data})

def generate_runtime_report(file_path, run_parameters, use_encryption, use_allowlist):
    with open(file_path, 'w') as file:
        file.write(f"-----------------------------Runtime Report---------------------------------\n")
        file.write(f"Date and Time: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}\n\n")

        for param, value in run_parameters.items():
            file.write(f"-{param}: {value}\n")
        file.write(f"-Use_Encryption: {use_encryption}\n")
        file.write(f"-Use_Allowlist: {use_allowlist}\n")

        file.write(f"----------------------------------------------------------------------------\n")


def log_att_process(file_path, message):
    with open(file_path, 'a') as file:
        file.write(f"{message}\n")


def log_id(file_path, client_id_msg):
    with open(file_path, 'a') as file:
        file.write(f"{client_id_msg}\n")


def log_traffic(file_path, sent_bytes, recv_bytes, time_sim):
    with open(file_path, 'a') as file:
        fieldnames = ["timestamp", "bytes_sent", "bytes_recv"]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        timesim = time_sim.current_jst_datetime()
        timestamp = timesim.strftime(formatted_datetime)

        if file.tell() == 0:
            writer.writeheader()
        writer.writerow({'timestamp': timestamp,
                         'bytes_sent': sent_bytes,
                         'bytes_recv': recv_bytes,
                         })
        # print(f"{timestamp} | Sent: {sent_bytes} bytes, Received: {recv_bytes} bytes")

def log_connection(file_path, connections, time_sim):
    # Start recording the number of connections
    with open(file_path, 'a') as file:
        writer = csv.writer(file)
        fieldnames = ["timestamp", "connections"]
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        timesim = time_sim.current_jst_datetime()
        timestamp = timesim.strftime(formatted_datetime)

        if file.tell() == 0:
            writer.writeheader()
        writer.writerow({'timestamp': timestamp, 'connections': connections})


# Record the number of connections and cpu
def log_cpu(file_path, target, cpu_usage, time_sim):
    try:
        timesim = time_sim.current_jst_datetime()
        timestamp = timesim.strftime(formatted_datetime)
        formatted_cpu_usage = f"{cpu_usage:.2f}%"
        #with open(file_path, 'a', newline='') as file:
        with open(file_path, 'a') as file:
            fieldnames = ["timestamp", "target", "cpu_usage"]
            writer = csv.DictWriter(file, fieldnames=fieldnames)

            if file.tell() == 0:
                writer.writeheader()
            writer.writerow({'timestamp': timestamp,
                             'target': target,
                             #'cpu_usage': cpu_usage,
                             'cpu_usage': formatted_cpu_usage,
                             })
    except json.JSONDecodeError as e:
        print(f"Error writing to log file: {e}")