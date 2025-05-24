"""
This module provides functionality to
- Process MQTT-related configuration information.
- Manage log-related configuration information.
- Manage session-related configuration information.

Classes:
- MqttConfig: This class contains attributes for configuring MQTT connection parameters and topic configurations
- LogConfig: This class contains attributes for log file paths and send status
- ClientConfig: This class contains attributes for session ID, client ID, and access token

Attributes:
- MQTT_BROKER: MQTT broker address
- MQTT_PORT: MQTT broker port
- MQTT_QOS0, MQTT_QOS1: Quality of Service levels for MQTT messages
- TOPIC1, TOPIC2, TOPIC3...: MQTT topics for communication
- FILE1: Log file path for general time messages
- FILE2: Log file path for jpt time messages
- SEND: Send status
- RECV: Received status
- SESSION_ID: Session ID for the connection
- CLIENT_ID: Client ID for the connection
- TOKEN: Access token for authentication
"""

# use localhost test
# brew services start mosquitto
# from utils.utils import generate_file_path
from datetime import datetime
import os

class MqttConfig:

    # MQTT broker address
    MQTT_BROKER = "localhost" #"127.0.0.1"

    # MQTT broker port
    MQTT_PORT = 1883
    MQTTS_PORT = 8883

    # MQTT Qos levels
    MQTT_QOS0 = 0  # Qos 0: At most once delivery
    MQTT_QOS1 = 1  # Qos 1: At least once delivery

    MQTT = 'MQTT'
    MQTTS = 'MQTTS'

    # ALLOWLIST = ["127.0.0.1", "::1"]
    ALLOWLIST = ["192.168.0.102"]

    # client_ip = {
    #     "BOS": "192.168.0.102",
    #     "RPF": "192.168.0.102",
    #     "ELV": "192.168.0.102",
    #     "ROB": "192.168.0.102",
    #     "bot": "192.168.1.101",
    # }
    client_ip = {
        "BOS": "127.0.0.1",
        "RPF": "127.0.0.1",
        "ELV": "127.0.0.1",
        "ROB": "127.0.0.1",
        "bot": "192.168.1.101",
    }

    # Need to switch to path
    CA = "mqtt_communication_module/certs/ca.crt"
    CRT = "mqtt_communication_module/certs/client.crt"
    KEY = "mqtt_communication_module/certs/client.key"

    PUBLISHER_USERNAME = None
    PUBLISHER_PASSWORD = None
    SUBSCRIBER_USERNAME = None
    SUBSCRIBER_PASSWORD = None

    # MQTT topics (some unusual acronyms used for legacy reasons)  
    # RPF send
    # - B2D => RPF to BOS
    # - B2R => RPF to ROB
    TOPIC_B2D = '← cmd/***/elevator/test/req'
    TOPIC_B2R = '→ B2R/cmd/req'
    TOPIC_B2R_FORWARD_ELV = '→ Rpf/Forward/ELV_dt'  # forward elv dt data

    # BOS send
    # - D2B => BOS to RPF
    # - D2E => BOS to ELV
    TOPIC_D2B = '→ cmd/***/elevator/test/res'
    TOPIC_D2E = '← D2E/cmd/***/elevator/test/res'
    TOPIC_D2B_FORWARD_ELV = '→ Bos/Forward/ELV_dt'  # forward elv dt data

    # ELV recv cmd
    # - E2D => ELV to BOS
    TOPIC_E2D = '→ E2D/cmd/***/elevator/test/req'

    # ROB recv cmd
    # - R2B => ROB to RPF
    TOPIC_R2B = '← R2B/cmd/res'

    # dt data topic
    TOPIC_DOOR_DT = '→ dt/***/door'  # door_dt_data
    TOPIC_ELV_DT = '→ dt/***/elevator/test/res'  # ELV_dt_data (E2D)
    TOPIC_ROB_DT = '← rob/dt'
    
    ATT_TOPIC = '→ attack_topic'

    # Use wildcards to subscribe to multiple topics. This can only be used when subscribing.
    TOPIC_BOS = '+/BOS/ #'


class LogConfig:
    # time
    speed = 10

    def generate_dir(output_dir):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        directory = f'{output_dir}/{timestamp}'
        os.makedirs(directory, exist_ok=True)
        return directory

    OUTPUT_DIR = 'database/Log'
    Generate_DIR = generate_dir(OUTPUT_DIR)

    FILE_ELV_LOG = os.path.join(Generate_DIR, 'elv_log.txt')
    FILE_BOS_LOG = os.path.join(Generate_DIR, 'bos_log.txt')
    FILE_RPF_BOS_LOG = os.path.join(Generate_DIR, 'rpf_bos_log.txt')
    FILE_RPF_ROB_LOG = os.path.join(Generate_DIR, 'rpf_%s_log.txt')
    FILE_ROB_JP_LOG = os.path.join(Generate_DIR, '%s_jp_log.txt')
    FILE_ROB_LOG = os.path.join(Generate_DIR, '%s_log.txt')
    FILE_BUILDING_LOG = os.path.join(Generate_DIR, 'building_msg_log.txt')
    RUNTIME_REPORT = os.path.join(Generate_DIR, 'runtime_report.txt')
    COM_TRAFFIC_LOG = os.path.join(Generate_DIR, 'traffic.csv')
    CONNECTIONS_LOG = os.path.join(Generate_DIR, 'connections_log.csv')
    CPU_LOG = os.path.join(Generate_DIR, 'cpu.csv')
    BROKER_LOG = os.path.join(Generate_DIR, 'broker_log.csv')
    FILE_ROB_POSITION_LOG = os.path.join(Generate_DIR, '%s_position.txt')
    FILE_ELV_ACT_LOG = os.path.join(Generate_DIR, '%s_elv_act.txt')
    FILE_ROB_ACT_LOG = os.path.join(Generate_DIR, '%s_rob_act.txt')


    # datetime format
    DATETIME = '%Y-%m-%d %H:%M:%S.%f'
    DATETIME_I = '%Y/%m/%d %H:%M:%S'
    SEND = 'sent'
    RECV = 'received'

    # Send and recv corresponding to different topics
    topic_file_action_mapping = {
        # B2D
        MqttConfig.TOPIC_B2D: {
            FILE_RPF_BOS_LOG: SEND,
            FILE_BOS_LOG: RECV,
            FILE_BUILDING_LOG: SEND,
        },

        MqttConfig.TOPIC_B2R: {
            FILE_RPF_BOS_LOG: SEND,
            FILE_ROB_LOG: RECV,
        },

        MqttConfig.TOPIC_R2B: {
            FILE_RPF_BOS_LOG: RECV,
            FILE_ROB_LOG: SEND,
        },

        # D2B
        MqttConfig.TOPIC_D2B: {
            FILE_RPF_BOS_LOG: RECV,
            FILE_BOS_LOG: SEND,
            FILE_BUILDING_LOG: RECV,
        },
        # dt data
        MqttConfig.TOPIC_ELV_DT: {
            FILE_RPF_BOS_LOG: RECV,
            FILE_BOS_LOG: RECV,
            FILE_ELV_LOG: SEND,
            FILE_BUILDING_LOG: SEND,

        },
        # E2D
        MqttConfig.TOPIC_E2D: {
            FILE_BOS_LOG: RECV,
            FILE_ELV_LOG: SEND,
            FILE_BUILDING_LOG: RECV,
        },
        # D2E
        MqttConfig.TOPIC_D2E: {
            FILE_BOS_LOG: SEND,
            FILE_ELV_LOG: RECV,
            FILE_BUILDING_LOG: SEND,
        },
        # D2B
        MqttConfig.TOPIC_D2B_FORWARD_ELV: {
            FILE_BOS_LOG: SEND,
            FILE_RPF_BOS_LOG: RECV,
        },
        # B2R
        MqttConfig.TOPIC_B2R_FORWARD_ELV: {
            FILE_RPF_ROB_LOG: SEND,
            FILE_ROB_JP_LOG: RECV,
            FILE_ROB_LOG: RECV,
        }
    }


class ClientConfig:
    # client info elv
    SESSION_ID = 'cc1d39f4-9e3f-49c0-9c66-544bbadce981'
    CLIENT_ID = 'elevator'
    TOKEN = 'xxx'
    SCENARIO_FILE = 'utils/scenario.yaml'


#  StateMachine
class StateMachineConfig:
    INVALID = 'Invalid state: '

    # elv_states
    E0 = 'e0'
    E1 = 'e1'
    E2 = 'e2'
    E3 = 'e3'
    E4 = 'e4'
    E5 = 'e5'
    E6 = 'e6'
    E7 = 'e7'
    E8 = 'e8'
    E9 = 'e9'
    COMPLETED = 'completed'

    r0e0 = 'r0e0'
    r1e0 = 'r1e0'
    r1e1 = 'r1e1'
    r1e2 = 'r1e2'
    r1e3 = 'r1e3'
    r1e4 = 'r1e4'
    r2e4 = 'r2e4'
    r2e5 = 'r2e5'
    r2e6 = 'r2e6'
    r2e7 = 'r2e7'
    r2e8 = 'r2e8'
    r3e8 = 'r3e8'
    r3e9 = 'r3e9'
    calling = 'calling'

    # rob_status
    R0 = 'r0'
    R1 = 'r1'
    R2 = 'r2'
    R3 = 'r3'

    A0 = 'a0'
    A1 = 'a1'
    A2 = 'a2'
    A3 = 'a3'
    A4 = 'a4'
    A5 = 'a5'

    # for close Elv door
    STATE_MAP = {
            'e4': 'e5',
            'e8': 'e9'
        }


class ELVConfig:
    elvq0 = 'elvq0'
    elvq1 = 'elvq1'
    elvq2 = 'elvq2'
    elvq3 = 'elvq3'
    elvq4 = 'elvq4'
    elvq5 = 'elvq5'
    elvq6 = 'elvq6'
    elvq7 = 'elvq7'
    elvq8 = 'elvq8'
    elvq9 = 'elvq9'
    elvq10 = 'elvq10'

    # PERFLOORMOVETIME = -10
    PERFLOORMOVETIME = -1

    NAME = 'name'
    FLOOR = 'floor'
    TARGET_FLOOR = 'target_floor'
    STATE = 'state'
    DOOR = "door"
    OPEN = 'open'
    CLOSE = 'close'
    UP = 'up'
    DOWN = 'down'
    STAY = 'stay'
    DIRECTION = "direction"
    INDRIVING_PERMISSION = "inDrivingPermission"
    MOVINGSTATUS = 'movingStatus'
    INTERLOCK = 'interlock'
    INSERVICE = 'inService'
    ANSERBACK = 'answerBack'
    TROUBLE = 'trouble'
    TIME = 'time'

    # INTERLOCK_SUCCESS = 'interlock_success'
    INTERLOCK_TRUE_SUCCESS = 'interlock_true_success'
    INTERLOCK_FALSE_SUCCESS = 'interlock_false_success'
    CALL_ACCEPT = 'call_accept'
    CALL_ARRIVE = 'call_arrive'
    OPEN_SUCCESS = 'open_success'
    CLOSE_SUCCESS = 'close_success'
    GO_ACCEPT = 'go_accept'
    GO_ARRIVE = 'go_arrive'

    method_map = {
        'interlock': 'interlock_command_success',
        'open': 'open_command_success',
        'close': 'close_command_success',
        'call': ('call_command_accept', 'call_command_arrive'),
        'go': ('go_command_accept', 'go_command_arrive')
    }


class CmdConfig:
    COMMAND = "command"
    TASK = "task"
    STATUS = 'status'

    # Elv cmd
    INTERLOCK = "interlock"
    INTERLOCK_TRUE = "interlock_true"
    INTERLOCK_FALSE = "interlock_false"
    CALL = "call"
    OPEN = "open"
    CLOSE = "close"
    GO = "go"

    # Rob cmd
    GO_TO_ELV = "GoToELV"
    GETTING_ON = "GettingOn"
    GETTING_OFF = "GettingOff"
    CHARGE = 'Charge'
    SCHEDULE_WORK = 'Schedule_Work'
    GO_TO_ELV_COMPLETED = 'GoToELV_completed'
    GETTING_OFF_COMPLETED = "GettingOff_completed"
    GETTING_ON_COMPLETED = "GettingOn_completed"
    SCHEDULE_WORK_COMPLETED = 'Schedule_Work_completed'
    CHARGE_COMPLETED = 'Charge_completed'

    # Cmd result
    SUCCESS = "success"
    FAILURE = "failure"
    ACCEPT = "accept"
    ARRIVE = "arrive"
    COMPLETED = "completed"
    NOT_COMPLETED = "not_completed"
    RESULT = "result"
    REASON = "reason"

    # command execution status
    GO_TO_ELV_SUCCESS = 'GoToELV_success'
    WAIT_SUCCESS = 'Wait_success'
    STAY_SUCCESS = 'Stay_success'
    CALL_SUCCESS = 'Calling_success'
    GETTING_ON_SUCCESS = 'GettingOn_success'
    GETTING_OFF_SUCCESS = 'GettingOff_success'
    STOP_SUCCESS = 'Stopping_success'
    GETTING_OFF_COMPLETED_SUCCESS = "GettingOff_completed_success"
    GETTING_ON_COMPLETED_SUCCESS = "GettingOn_completed_success"
    ERROR = 'error'

    # for elvmessagehandler
    METHOD_MAP = {
        'interlock_true': 'interlock_true_command_success',
        'interlock_false': 'interlock_false_command_success',
        'open': 'open_command_success',
        'close': 'close_command_success',
        'call': ('call_command_accept', 'call_command_arrive'),
        'go': ('go_command_accept', 'go_command_arrive')
    }

    STATE_ATTR_MAP = {
        StateMachineConfig.r1e0: ELVConfig.INTERLOCK_TRUE_SUCCESS,
        StateMachineConfig.r1e1: ELVConfig.CALL_ACCEPT,
        StateMachineConfig.r1e2: ELVConfig.CALL_ARRIVE,
        StateMachineConfig.r1e3: ELVConfig.OPEN_SUCCESS,
        StateMachineConfig.r2e4: ELVConfig.CLOSE_SUCCESS,
        StateMachineConfig.r2e5: ELVConfig.GO_ACCEPT,
        StateMachineConfig.r2e6: ELVConfig.GO_ARRIVE,
        StateMachineConfig.r2e7: ELVConfig.OPEN_SUCCESS,
        StateMachineConfig.r3e8: ELVConfig.CLOSE_SUCCESS,
        StateMachineConfig.r3e9: ELVConfig.INTERLOCK_FALSE_SUCCESS
    }


class ScenarioConfig:
    Service_Robots = 'service_robots'
    Service_Robot_Name = 'name'
    Service_Robot_Floor = 'floor'
    Service_Robot_Position = 'position'
    Service_Robot_Status = 'status'
    Service_Robot_PRIORITY = 'priority'
    Sim_Speed = 'sim_speed'

    Tasks = 'tasks'
    Task_No = 'task_no'
    Task_Floor = 'task_floor'
    Task_Name = 'task_name'
    Task_Schedule_Work = 'schedule_work'
    Task_Charge = 'charge'

    Elevators = 'elevators'
    Elevator_Name = 'name'
    Elevator_Floor = 'floor'
    Elevator_door = 'door'
    Elevator_door_open = 'open'
    Elevator_door_close = 'close'
    Elevator_movingStatus = 'movingStatus'
    Elevator_movingStatus_up = 'up'
    Elevator_movingStatus_down = 'down'
    Elevator_movingStatus_stay = 'stay'
    Elevator_inDrivingP = 'inDrivingPermission'

    SCENARIO = 'scenario'
    ATT_SCENARIO = 'attack_scenario'
    SCENARIO_NAME = 'scenario_name'
    TARGET = 'target'

    PROTOCOL = 'protocol'

    scenarios = [
        {
            "attack_scenario": "None",
            "target": ["None"]
        },
        {
            "attack_scenario": "MITM",
            "target": ["BOS", "RPF"]
        },
        {
            "attack_scenario": "DDoS",
            "target": ["C", "P"]
        },
        {
            "attack_scenario": "BAC",
            "target": ["BOS", "RPF"]
        },
    ]

    protocol = ["MQTT", "MQTTS"]

    FUZZER = 'fuzzer'



class Mode:
    DEFAULT = "Default"
    Normal = "Normal"
    MITM = "MITM"
    BAC = "BAC"
    
    FUZZING = "Fuzzing"
    FUZZING2 = "Fuzzing2"

    BOS = "BOS"
    RPF = "RPF"

    mapping = {
        (DEFAULT, DEFAULT): (Normal, Normal),
        (None, None): (Normal, Normal),
        (Normal, Normal): (Normal, Normal),
        (MITM, BOS): (MITM, Normal),
        (MITM, RPF): (Normal, MITM),
        (BAC, BOS): (BAC, Normal),
        (BAC, RPF): (Normal, BAC),
    }

class CER:
    U_RPF = "RPF"
    PW_RPF = "123"
    U_BOS = "BOS"
    PW_BOS = "456"
    U_ROB = "ROB11"


class RobotConfig:
    robq0 = 'robq0'
    robq1 = 'robq1'
    robq2 = 'robq2'
    robq3 = 'robq3'  # work
    robq4 = 'robq4'  # charge
    robq5 = 'robq5'
    robq6 = 'robq6'  # floor error
    robq7 = 'robq7'  # door error

    ERROR = 'error'
    E002 = 'E002'  # floor error
    E004 = 'E004'  # door error

    NAME = 'name'
    TASK = 'task'
    POSITION = 'position'
    MOVING_STATUS = 'Moving_Status'
    WAIT = 'Wait'
    END = 'end'
    STATE = 'state'
    Waiting = 'Waiting'
    ELVStay = 'ELVStay'
    CALLING = 'Calling'
    GET_ON = 'GettingOn'
    GO_TO_ELV = 'GoToELV'
    GET_OFF = 'GettingOff'
    MOVING_STATUS_STOP = 'Stopping'
    CHARGE = 'Charge'
    Schedule_Work = 'Schedule_Work'

    # command execution status
    GO_TO_ELV_SUCCESS = 'GoToELV_success'
    WAIT_SUCCESS = 'Wait_success'
    CALL_SUCCESS = 'Calling_success'
    GETTING_ON_SUCCESS = 'GettingOn_success'
    GETTING_OFF_SUCCESS = 'GettingOff_success'
    STOP_SUCCESS = 'Stopping_success'
    GO_TO_ELV_COMPLETED = 'GoToELV_completed'
    GETTING_OFF_COMPLETED = "GettingOff_completed"
    GETTING_ON_COMPLETED = "GettingOn_completed"

    # rob Status
    STATUS_0 = '待機'
    STATUS_1 = '移動中'
    STATUS_2 = '充電中'
    STATUS_3 = '不定'
    STATUS_4 = '設定操作中'
    STATUS_5 = '清掃_スケジュール'

    ELV_GETTING_ON_TIME = 30
    ELV_GETTING_OFF_TIME = 30
    PROTOCOL_TEST_TIME = 30

    LOAD_ROUTE_TIME = 1
    CAMERA_UPDATE_TIME = 5

    MOVE_TO_ELV = 'move_to_elevator'
    ENTER_ELV = 'enter_elevator'
    EXIT_ELV = 'exit_elevator'

    NAME = 'name'
    PRIORITY = 'priority'
    FLOOR = 'floor'
    TASK_FLOOR = 'task_floor'
    ELV_PREPARATION = 'elv_preparation'
    ELV_PREPARATION_Preparing = 'preparing'
    ELV_PREPARATION_InProgress = 'InProgress'
    ELV_PREPARATION_Completed = 'Completed'
    WORK_COMPLETED = 'work_completed'
    CHARGE_COMPLETED = 'charge_completed'

    rob_status0 = {
        CmdConfig.GO_TO_ELV_SUCCESS: False,
        CmdConfig.GO_TO_ELV_COMPLETED: False,
        CmdConfig.CALL_SUCCESS: False,
        CmdConfig.WAIT_SUCCESS: False,
        CmdConfig.STAY_SUCCESS: False,
        CmdConfig.GETTING_ON_SUCCESS: False,
        CmdConfig.GETTING_ON_COMPLETED: False,
        CmdConfig.STOP_SUCCESS: False,
        CmdConfig.GETTING_OFF_SUCCESS: False,
        CmdConfig.GETTING_OFF_COMPLETED: False,
        CmdConfig.SCHEDULE_WORK_COMPLETED: False,
        CmdConfig.CHARGE_COMPLETED: False,
        ERROR: False,
        ELVConfig.INTERLOCK_TRUE_SUCCESS: False,
        ELVConfig.INTERLOCK_FALSE_SUCCESS: False,
        ELVConfig.OPEN_SUCCESS: False,
        ELVConfig.CLOSE_SUCCESS: True,
        ELVConfig.CALL_ACCEPT: False,
        ELVConfig.CALL_ARRIVE: False,
        ELVConfig.GO_ACCEPT: False,
        ELVConfig.GO_ARRIVE: False
    }

class FuzzingConfig:
    ELVSIM = 'elvsim'
    BOSSIM = 'bossim'
    RPFSIM = 'rpfsim'
    ROBSIM = 'robsim'
