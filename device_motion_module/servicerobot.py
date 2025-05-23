import os
import heapq
import csv
import math
import heapq
import copy
import numpy as np
from scipy.spatial import cKDTree
from utils.storyboard import RobotConfig, LogConfig, ELVConfig
from formal_verification.FV import maude_class_monitor

# @maude_class_monitor(PID='ROB', ocom_statuses=['state', 'movingStatus'])
class ServiceRobot():
    def __init__(self, robot_data, time=None, mode=False):
        self.time = time
        self.name = robot_data[RobotConfig.NAME]
        self.position = [0, 0, 0] if not robot_data.get(RobotConfig.POSITION) else robot_data[RobotConfig.POSITION]
        self.logpos = [0, 0, 0] if not robot_data.get(RobotConfig.POSITION) else robot_data[RobotConfig.POSITION]
        self.pathidx = 0
        self.posidx = 5
        self.floor = -1 if not robot_data.get(RobotConfig.FLOOR) else robot_data[RobotConfig.FLOOR]
        self.initfloor = -1 if not robot_data.get(RobotConfig.FLOOR) else robot_data[RobotConfig.FLOOR]
        self.next_floor = -1
        self.map_no = -1 if self.floor == -1 else self.floormap(self.floor) 
        self.next_map_no = self.floormap(self.next_floor)
        self.status = RobotConfig.STATUS_0
        self.movingStatus = RobotConfig.WAIT
        self.state = RobotConfig.robq0
        self.width = 10
        self.path = []
        self.points = []
        self.realfloor = self.floor
        self.stop = False

        self.cmd_interrupt = False

        # self.task_completed = False
        self.elv_preparation = RobotConfig.ELV_PREPARATION_Preparing
        self.gettingon_completed = False
        self.gettingoff_completed = True
        self.work_completed = False
        self.go_to_charge_completed = False

        self.bot_dt_send_time = 10
        self.bot_pos_log_time = 5
        self.bot_cam_time = 2

        self.test_protocol_mode = mode
        self.last_action_function_time = None
        self.simulating_entry = False

        self.rpf_rob_comfile = LogConfig.FILE_RPF_ROB_LOG % self.name
        self.communication_file_name =  LogConfig.FILE_ROB_JP_LOG % self.name
        self.position_file_name = LogConfig.FILE_ROB_POSITION_LOG % self.name
        self.act_file_name = LogConfig.FILE_ROB_ACT_LOG % self.name
        self.com_file_name = LogConfig.FILE_ROB_LOG % self.name
        self.last_dt_time = 0
        self.last_log_time = 0
        self.last_cam_time = 0

        self.elv = None
        self.elv_status = None
        self.elv_door_status = None
        self.elv_floor_status = None



    def set_testmode(self, mode):
        """ protorocol test mode """
        self.test_protocol_mode = mode

    def floormap(self, floor: int):
        return floor

    def init_rob_Status(self):
        self.elv_preparation = False
        self.gettingon_completed = False
        self.gettingoff_completed = True
        self.work_completed = False

    def load_route(self, filename):
        if self.path != []:
            self.path = []
            self.pathidx = 0
        with open(filename, 'r') as f:
            route_file_rows = csv.reader(f)
            for row in route_file_rows:
                x, y, angle = map(float, row)
                self.path.append((x, y, angle))
        return self.path

    def cal_dist(self, pos1, pos2):
        return math.sqrt((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2)

    def cal_ang(self, ang1, ang2):
        diff = abs(ang1 - ang2)
        return min(diff, 2 * math.pi - diff)

    def heuristic(self, pos1, pos2):
        return self.cal_dist(pos1, pos2) + self.cal_ang(pos1[2], pos2[2]) * 10

    def find_shortest_path(self, path, start_idx, end_idx):
        start_pos = path[start_idx]
        end_pos = path[end_idx]
        open_list = []
        came_from = {}
        reconstruct_path = []
        tree = cKDTree([(pos[0], pos[1]) for pos in path])
        heapq.heappush(open_list, (0, start_idx))
        g_score = {start_idx: 0}
        f_score = {start_idx: self.heuristic(start_pos, end_pos)}
        
        while open_list:
            current_idx = heapq.heappop(open_list)[1]
            if current_idx == end_idx:
                while current_idx in came_from:
                    reconstruct_path.append(path[current_idx])
                    current_idx = came_from[current_idx]
                reconstruct_path.append(start_pos)
                return reconstruct_path[::-1]
            
            current_pos = path[current_idx]
            _, neighbor_idxs = tree.query((current_pos[0], current_pos[1]), 10)
            for neighbor_idx in neighbor_idxs:
                if neighbor_idx == current_idx:
                    continue
                if neighbor_idx >= len(path):
                    continue
                neighbor_pos = path[neighbor_idx]
                t = g_score[current_idx] + self.cal_dist(current_pos, neighbor_pos)
                if neighbor_idx not in g_score or t < g_score[neighbor_idx]:
                    came_from[neighbor_idx] = current_idx
                    g_score[neighbor_idx] = t
                    f_score[neighbor_idx] = g_score[neighbor_idx] + self.heuristic(neighbor_pos, end_pos)
                    heapq.heappush(open_list, (f_score[neighbor_idx], neighbor_idx))
        return None
    
    def smooth_path(self, path, num_points=5):
        num = int(np.ceil(num_points))
        if num <= 2:
            num = 2
        if len(path) == 1:
            x, y, theta = path[0]
            return [(x, y, round(theta, 4))] * num
        elif len(path) == 2:
            (x1, y1, theta1), (x2, y2, theta2) = path
            t = np.linspace(0, 1, num)
            x_interp = [int(x1 + (x2 - x1) * t_i) for t_i in t]
            y_interp = [int(y1 + (y2 - y1) * t_i) for t_i in t]
            theta_interp = np.round(theta1 + (theta2 - theta1) * t, 4)
            return list(zip(x_interp, y_interp, theta_interp))
        return path

    def set_go_to_elv_status(self):
        if self.state == RobotConfig.robq0 or self.state == RobotConfig.robq6:
            self.state = RobotConfig.robq0
            self.stop = False
            if not self.map_no or self.map_no < 1 or self.map_no > 13:
                return False
            self.status = RobotConfig.STATUS_1
            self.movingStatus = RobotConfig.GO_TO_ELV
            self.elv_preparation = RobotConfig.ELV_PREPARATION_InProgress
            if not self.path:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                route_file_name = os.path.join(base_dir, "routes", "moving.csv")
                self.load_route(route_file_name)
            else:
                if 0 <= self.pathidx - 1 < len(self.path):
                    self.path = self.find_shortest_path(self.path, self.pathidx-1, 0)
                else:
                    self.path = []
            self.pathidx = 0
            self.last_action_function_time = self.time.current_timestamp()
            return True
        else:
            return False

    def go_to_elv(self):
        if self.state == RobotConfig.robq0:
            if self.execute_route():
                self.elv_preparation = RobotConfig.ELV_PREPARATION_Completed
                self.state = RobotConfig.robq1
                return True
        else:
            pass

    def set_elv_getting_on(self):
        if self.state == RobotConfig.robq1 or self.state == RobotConfig.robq7:
            self.state = RobotConfig.robq1
            self.stop = False
            self.status = RobotConfig.STATUS_1
            self.movingStatus = RobotConfig.GET_ON
            self.logpos = [0, 0, 0]
            self.position = [1, 1, 1]
            self.last_action_function_time = self.time.current_timestamp()
            return True
        return False

    def elv_getting_on(self):
        if self.state == RobotConfig.robq1:
            current_time = self.time.current_timestamp()
            self.map_no = -1
            self.position = [0, 0, 0]
            self.logpos = [0, 0, 0]
            self.simulating_entry = False
            self.update_config_status()
            if self.elv_door_status == ELVConfig.OPEN and self.elv_floor_status == self.floor:
                if not self.simulating_entry:
                    if current_time - self.last_action_function_time >= RobotConfig.ELV_GETTING_ON_TIME:
                        self.status = RobotConfig.STATUS_0
                        self.movingStatus = RobotConfig.MOVING_STATUS_STOP
                        self.gettingon_completed = True
                        self.simulating_entry = True
                        self.last_action_function_time = None
                        self.state = RobotConfig.robq2
                        return True
                    else:
                        return False
                else:
                    self.last_action_function_time = current_time
                    return False
            elif self.elv_door_status == ELVConfig.CLOSE or self.elv_floor_status != self.floor:
                self.state = RobotConfig.robq7
                self.stop = True
                self.movingStatus = RobotConfig.E004
                self.gettingoff_completed = False
                return False

    def set_elv_stay_status(self):
        self.status = RobotConfig.STATUS_1
        self.movingStatus = RobotConfig.MOVING_STATUS_STOP
        return True

    def stay(self, seconds):
        self.stop = True
        self.time.sleep(seconds)
        self.stop = False

    def set_elv_getting_off_status(self):
        if self.state == RobotConfig.robq2 or self.state == RobotConfig.robq7:
            self.state = RobotConfig.robq2
            self.stop = False
            self.status = RobotConfig.STATUS_1
            self.movingStatus = RobotConfig.GET_OFF
            self.last_action_function_time = self.time.current_timestamp()
            self.simulating_entry = False
            return True
        return False

    def elv_getting_off(self):
        if self.state == RobotConfig.robq2:
            current_time = self.time.current_timestamp()
            self.logpos = [0, 0, 0]
            self.position = [1, 1, 1]
            self.simulating_entry = False
            self.update_config_status()
            if self.elv_door_status == ELVConfig.OPEN:
                if not self.simulating_entry:
                    if current_time - self.last_action_function_time >= RobotConfig.ELV_GETTING_ON_TIME:
                        self.status = RobotConfig.STATUS_0
                        self.floor = self.next_floor
                        self.map_no = self.floormap(self.next_floor)
                        self.realfloor = self.elv_floor_status
                        self.movingStatus = RobotConfig.Waiting
                        self.gettingoff_completed = True
                        self.simulating_entry = True
                        self.last_action_function_time = None
                        self.state = RobotConfig.robq0
                        return True
                    else:
                        return False
                else:
                    self.last_action_function_time = current_time
                    return False
            elif self.elv_door_status == ELVConfig.CLOSE:
                self.state = RobotConfig.robq7
                self.stop = True
                self.movingStatus = RobotConfig.E004
                self.gettingon_completed = False
                return False


    def set_elv_call_status(self, next_floor):
        if self.state == RobotConfig.robq1:
            self.status = RobotConfig.STATUS_1
            # self.logpos = [0, 0, 0]
            self.next_floor = next_floor
            self.next_map_no = self.floormap(next_floor)
            self.movingStatus = RobotConfig.CALLING
            return True

    def execute_route(self):
        if self.stop:
            return
        if self.test_protocol_mode:
            current_time = self.time.current_timestamp()
            if current_time - self.last_action_function_time >= RobotConfig.PROTOCOL_TEST_TIME:
                self.last_action_function_time = None
                return True
        else:
            current_time = self.time.current_timestamp()
            if current_time - self.last_action_function_time >= RobotConfig.LOAD_ROUTE_TIME:
                if self.posidx == 5 / RobotConfig.LOAD_ROUTE_TIME:
                    if self.pathidx != len(self.path):
                        self.position = self.path[self.pathidx]
                        self.logpos = self.position
                        self.points = self.smooth_path(self.path[self.pathidx : self.pathidx+2], 5 / RobotConfig.LOAD_ROUTE_TIME)
                        self.pathidx += 1
                        self.posidx = 1
                        self.last_action_function_time = current_time
                    else:
                        self.last_action_function_time = None
                        return True
                else:
                    self.position = self.points[self.posidx]
                    self.logpos = self.position
                    self.posidx += 1
                    self.last_action_function_time = current_time

    def set_go_to_charge_status(self):
        if self.state == RobotConfig.robq0:
            if not self.map_no or self.map_no < 1 or self.map_no > 13:
                return False
            self.status = RobotConfig.STATUS_1
            self.movingStatus = RobotConfig.WAIT
            base_dir = os.path.dirname(os.path.abspath(__file__))
            route_file_name = os.path.join(base_dir, "routes", f"charge.csv")
            self.load_route(route_file_name)
            self.last_action_function_time = self.time.current_timestamp()
            self.state = RobotConfig.robq4
            return True
        return False

    def go_to_charge(self):
        if self.state == RobotConfig.robq4:
            self.next_map_no = self.floormap(self.next_floor)
            if self.execute_route():
                self.go_to_charge_completed = True
                self.last_action_function_time = None
                self.state = RobotConfig.robq0
                return True

    def set_schedule_work_status(self):
        if self.state == RobotConfig.robq0:
            if not self.map_no or self.map_no < 1 or self.map_no > 13:
                return False
            self.status = RobotConfig.STATUS_5
            self.movingStatus = RobotConfig.WAIT
            base_dir = os.path.dirname(os.path.abspath(__file__))
            route_file_name = os.path.join(base_dir, "routes", "schedule.csv")
            self.load_route(route_file_name)
            self.last_action_function_time = self.time.current_timestamp()
            self.state = RobotConfig.robq3
            return True
        return False

    def schedule_work(self):
        if self.state == RobotConfig.robq3:
            if self.execute_route():
                self.status = RobotConfig.STATUS_1
                self.work_completed = True
                self.state = RobotConfig.robq0
                return True
        else:
            return False

    # GET robot status
    def get_rob_status(self):
        return {
            "name": self.name,
            "floor": self.floor,
            "map_no": self.map_no,
            "status": self.status,
            "movingStatus": self.movingStatus,
            "position": self.position,
            "logpos": self.logpos,
            "elv_preparation": self.elv_preparation,
            "time": self.time
        }

    def set_rob_camera(self, elv):
        self.elv = elv

    def update_config_status(self):
        if self.elv is not None:
            new_status = self.elv.get_elv_status()
            self.elv_status = new_status
            self.elv_door_status = new_status[ELVConfig.DOOR]
            self.elv_floor_status = new_status[ELVConfig.FLOOR]

        if self.floor != self.realfloor:
            self.floor = self.realfloor
            self.map_no = self.floormap(self.floor)
            self.movingStatus = RobotConfig.E002
            self.state = RobotConfig.robq6
            self.stop = True

    def stop_update_timer(self):
        self.update_status_timer.cancel()

    def rob_camera(self):
        if self.elv is not None:
            with self.elv_status_lock:
                return self.elv_status
        else:
            return None

class RobotHandler():
    """ A singleton to handle robot class instances """
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.rob_dict = {}
            self._queue = []
            self._index = 0
            self._initialized = True

    def add_rob(self, rob_name, rob, priority=0):
        self.rob_dict[rob_name] = {
                                'rob': rob,
                                'task': None,
                                'priority': 1,
                                'rcp_state_machine': None,
                                'copy': None
                                }

    def init(self):
        for bot in self.rob_dict.values():
            bot['rob'].init()

    def find_bot(self, rob_name):
        """Find the robot instance by name"""
        if rob_name in self.rob_dict:
            return self.rob_dict[rob_name]['rob']

    def find_bots(self):
        """Return all the robot instances"""
        bot_list = []
        for rob_name in self.rob_dict:
            bot_list.append(self.find_bot(rob_name))
        return bot_list

    def copy_bot(self, rob_name):
        """Save a copy of the instance of the robot"""
        self.rob_dict[rob_name]['copy'] = copy.deepcopy(self.find_bot(rob_name))

    def paste_bot(self, rob_name):
        """Replace the robot instance with the saved copy"""
        if not self.rob_dict[rob_name]['copy']:
            return
        del self.rob_dict[rob_name]['rob']
        self.rob_dict[rob_name].update({'rob': self.rob_dict[rob_name]['copy']})

    def del_paste(self, rob_name):
        """Delete the saved copy of the robot instance"""
        if not self.rob_dict[rob_name]['copy']:
            return
        del self.rob_dict[rob_name]['copy']
        self.rob_dict[rob_name].update({'copy': None})

    def get_last_dt_time(self, rob_name):
        if rob_name in self.rob_dict:
            return self.find_bot(rob_name).last_dt_time

    def update_last_dt_time(self, rob_name, new_time):
        if rob_name in self.rob_dict:
            self.find_bot(rob_name).last_dt_time = new_time

    def get_last_log_time(self, rob_name):
        if rob_name in self.rob_dict:
            return self.find_bot(rob_name).last_log_time

    def update_last_log_time(self, rob_name, new_time):
        if rob_name in self.rob_dict:
            self.find_bot(rob_name).last_log_time = new_time

    def get_position_file_name(self, rob_name):
        if rob_name in self.rob_dict:
            return self.find_bot(rob_name).position_file_name

    def get_communication_file_name(self, rob_name):
        if rob_name in self.rob_dict:
            return self.find_bot(rob_name).communication_file_name

    def get_com_file_name(self, rob_name):
        if rob_name in self.rob_dict:
            return self.find_bot(rob_name).com_file_name

    def get_rpf_rob_comfile(self, rob_name):
        if rob_name in self.rob_dict:
            return self.find_bot(rob_name).rpf_rob_comfile

    def get_act_file_name(self, rob_name):
        if rob_name in self.rob_dict:
            return self.find_bot(rob_name).act_file_name

    def arrangement(self, tasks, name=None, priority=None):
        robs_num = len(self.rob_dict)
        if robs_num == 0:
            return
        task_arrangement = ''.join(str(i % robs_num) for i in range(len(tasks)))
        task_num = len(task_arrangement)
        rob_names = list(self.rob_dict.keys())

        for i, task in enumerate(tasks):
            idx = int(task_arrangement[i % task_num])
            rob_name = rob_names[idx]

            if self.rob_dict[rob_name].get('task') is None:
                self.rob_dict[rob_name]['task'] = []
            self.rob_dict[rob_name]['task'].append(task)

    def enqueue(self, name, priority=None):
        if priority is None:
            priority = self.rob_dict[name][RobotConfig.PRIORITY]
        heapq.heappush(self._queue, (-priority, self._index, name))
        self._index += 1

    def peek(self):
        if self._queue:
            return self._queue[0][-1]
    
    def istop(self, name):
        if self._queue[0][-1] == name:
            return True
        else:
            return False

    def pop(self):
        return heapq.heappop(self._queue)[-1]