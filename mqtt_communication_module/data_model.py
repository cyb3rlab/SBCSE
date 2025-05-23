"""
CommandData classes define various data types and data formats for
constructing command data to be sent to or received

Classes:
- SendCommandData: Manage the construction of command data for sending commands.
- RecvCommandData: Manage the construction of command data for receive commands.
- DtData: IoT status data

Attributes:
- client_id: Client ID for authentication.
- token: Access token for authentication.
- session_id: Session ID for the connection.
"""

from utils.storyboard import ClientConfig


 # rpf cmd data to elv
class SendCommandData:
    def __init__(self,
                 client_id=ClientConfig.CLIENT_ID,
                 token=ClientConfig.TOKEN,
                 session_id=ClientConfig.SESSION_ID
                 ):

        self.client_id = client_id
        self.token = token
        self.session_id = session_id

    def interlock_command(self, value):
        """Construct a command data for setting interlock.

        :param value: The interlock status. (bool)
        :return: A dictionary containing the command data,
        """

        data = {
            "sessionId": self.session_id,
            "clientId": self.client_id,
            "token": self.token,
            "command": 'interlock',
            "interlock": value  # True or False
        }
        return data

    def call_command(self, floor, direction):
        """Construct a command for setting call.

        :param floor:
        :param direction:
        :return: A dictionary containing the command data,
        """

        data = {
            "sessionId": self.session_id,
            "clientId": self.client_id,
            "token": self.token,
            "command": 'call',
            "floor": floor,
            "direction": direction
        }
        return data

    def open_command(self):
        data = {
            "sessionId": self.session_id,
            "clientId": self.client_id,
            "token": self.token,
            "command": 'open',
        }
        return data

    def close_command(self):
        data = {
            "sessionId": self.session_id,
            "clientId": self.client_id,
            "token": self.token,
            "command": 'close',
        }
        return data

    def go_command(self, floor):
        data = {
            "sessionId": self.session_id,
            "clientId": self.client_id,
            "token": self.token,
            "command": 'go',
            "floor": floor,
        }
        return data


# bos recv data
class RecvCommandData:
    def __init__(self, session_id=ClientConfig.SESSION_ID):
        self.session_id = session_id

    def command_success(self, command, result):
        back_data = {
            "sessionId": self.session_id,
            "command": command,
            "result": result
        }
        return back_data

    def interlock_command_success(self):
        back_data = {
            "sessionId": self.session_id,
            "command": 'interlock',
            "result": 'success'
        }
        return back_data

    def interlock_true_command_success(self):
        back_data = {
            "sessionId": self.session_id,
            "command": 'interlock_true',
            "result": 'success'
        }
        return back_data

    def interlock_false_command_success(self):
        back_data = {
            "sessionId": self.session_id,
            "command": 'interlock_false',
            "result": 'success'
        }
        return back_data

    def call_command_accept(self):
        back_data = {
            "sessionId": self.session_id,
            "command": 'call',
            "result": 'accept'
        }
        return back_data

    def call_command_arrive(self):
        back_data = {
            "sessionId": self.session_id,
            "command": 'call',
            "result": 'arrive'
        }
        return back_data

    def open_command_success(self):
        back_data = {
            "sessionId": self.session_id,
            "command": 'open',
            "result": 'success'
        }
        return back_data

    def close_command_success(self):
        back_data = {
            "sessionId": self.session_id,
            "command": 'close',
            "result": 'success'
        }
        return back_data

    def go_command_accept(self):
        back_data = {
            "sessionId": self.session_id,
            "command": 'go',
            "result": 'accept'
        }
        return back_data

    def go_command_arrive(self):
        back_data = {
            "sessionId": self.session_id,
            "command": 'go',
            "result": 'arrive'
        }
        return back_data


# ELV dt data
class ElvDtData:
    def __init__(self, time):
        self.time = time

    def dt_elevator(self, elevator):
        """
        Construct data for elevator status.
        :param elevator: Elevator object
        :return: A dictionary containing the elevator status data
        """

        data = {
            "floor": elevator["floor"],
            "door": elevator["door"],
            "movingStatus": elevator["movingStatus"],
            "inService": elevator["inService"],
            "inDrivingPermission": elevator["inDrivingPermission"],
            "answerBack": elevator["answerBack"],
            "trouble": elevator["trouble"],
            "time": int(elevator["time"].current_timestamp()) if self.time is not None else 0
        }
        return data

    def dt_door(self, status, value):
        """
        Construct data for door status.

        :param status: The door status.
        :param value: (bool)
        :return: A dictionary containing the door status data.
        """
        data = {
            "status": status,
            "extendStatus": value,
            "time": self.time,
        }
        return data


# rob dt data
class RobotData:
    def __init__(self, time):
        self.time = time

    # rob send dt data to rpf
    def dt_robot(self, robot):
        data = {
            "name": robot["name"],
            "floor": robot["floor"],
            "status": robot["movingStatus"],    # GettingOn/Stopping
            "position": robot["position"],
            "elv_preparation": robot["elv_preparation"],
            "time": int(robot["time"].current_timestamp()) if self.time is not None else 0
        }
        return data
    
    def robot_position(self, robot):
        data = {
            'map_no': robot['map_no'],
            '状態': robot["status"],
            'position': robot["logpos"]
            }
        return data
    
    def robot_recv_command(self, command, result, reason=None, name=None):
        back_data = {
            "name": name,
            "command": command,
            "result": result,
            "reason": reason
        }
        return back_data




class B2R_cmdData:
    def __init__(self, session_id=ClientConfig.SESSION_ID):
        self.session_id = session_id

    def B2R_command(self, target_floor=None, command=None, status=None, rob_name=None):
        # Wait/GettingOn/GettingOff/Stopping
        data = {
            "name": rob_name,
            "command": command,
            "status": status,
        }

        data.update({"target_floor": target_floor}) if target_floor is not None else None
        return data


def set_run_parameters(speed, protocol, rob, elv, task, scenario, target):
    run_parameters = {
        'SIM_Speed': speed,
        'Selected Protocol': protocol,
        'Selected Rob': [robot.name for robot in rob],
        'Selected Elv': [elevator.name for elevator in elv],
        'Selected Tasks': task,
        'Attack_Scenario': scenario,
        'Attack Target': target,
    }
    return run_parameters
