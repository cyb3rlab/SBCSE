import copy
from utils.storyboard import LogConfig, ELVConfig
from formal_verification.FV import maude_class_monitor

# @maude_class_monitor(PID='ELV', ocom_statuses=['state', 'movingStatus'])
class Elevator:
    def __init__(self, elv, time):
        self.name = elv[ELVConfig.NAME]
        self.current_floor = -1 if not elv.get(ELVConfig.FLOOR) else elv[ELVConfig.FLOOR]
        self.door = ELVConfig.CLOSE if not elv.get(ELVConfig.DOOR) else elv[ELVConfig.DOOR]
        self.movingStatus = ELVConfig.STAY if not elv.get(ELVConfig.MOVINGSTATUS) else elv[ELVConfig.MOVINGSTATUS]
        self.state = ELVConfig.elvq0
        self.inService = True
        self.inDrivingPermission = False if not elv.get(ELVConfig.INDRIVING_PERMISSION) else elv[ELVConfig.INDRIVING_PERMISSION]
        self.interlock = False if not elv.get(ELVConfig.INTERLOCK) else elv[ELVConfig.INTERLOCK]
        self.answerBack = False
        self.trouble = False
        self.count_time = 10
        self.direction = 0
        self.door_open = False
        self.time = time
        self.act_log = LogConfig.FILE_ELV_ACT_LOG % self.name
        self.last_move_function_time = None

    def wait_seconds(self, seconds):
        self.time.sleep(seconds)

    def set_interlock(self, value):
        # Set to AGV mode
        if self.state == ELVConfig.elvq0 and value:
            self.inDrivingPermission = value
            self.state = ELVConfig.elvq1
            return True

        # Set to leave AGV mode
        elif self.state == ELVConfig.elvq7 and not value:
            self.inDrivingPermission = value
            self.state = ELVConfig.elvq0
            return True

        elif self.inDrivingPermission == value:
            return True

    def call_elv(self, target_floor, movingStatus):
        if self.state == ELVConfig.elvq1:
            if movingStatus == self.calculate_direction(target_floor):
                self.movingStatus = movingStatus
                self.direction = self.set_direction(movingStatus)
                self.last_move_function_time = self.time.current_timestamp()
                self.state = ELVConfig.elvq2
                return True
        return False

    def elv_go(self, target_floor):
        if self.state == ELVConfig.elvq4:
            self.movingStatus = self.calculate_direction(target_floor)
            self.direction = self.set_direction(self.movingStatus)
            self.last_move_function_time = self.time.current_timestamp()
            self.state = ELVConfig.elvq5
            return True
        else:
            return False

    def get_door_status(self):
        if self.door == ELVConfig.OPEN:
            self.door_open = True
        elif self.door == ELVConfig.CLOSE:
            self.door_open = False
        return self.door_open

    def close_door(self):
        if self.state == ELVConfig.elvq3:
            self.door = ELVConfig.CLOSE
            self.state = ELVConfig.elvq4
            return True
        elif self.state == ELVConfig.elvq6:
            self.door = ELVConfig.CLOSE
            self.state = ELVConfig.elvq7
            return True
        if self.door == ELVConfig.CLOSE:
            return True
        else:
            return False

    def open_door(self):
        if self.state == ELVConfig.elvq2:
            if self.movingStatus != ELVConfig.STAY:
                return
            self.door = ELVConfig.OPEN
            self.state = ELVConfig.elvq3
            return True
        elif self.state == ELVConfig.elvq5:
            if self.movingStatus != ELVConfig.STAY:
                return
            self.door = ELVConfig.OPEN
            self.state = ELVConfig.elvq6
            return True
        elif self.door == ELVConfig.OPEN:
            return True
        else:
            return False


    def calculate_direction(self, target_floor):
        if self.current_floor < target_floor:
            return ELVConfig.UP
        elif self.current_floor > target_floor:
            return ELVConfig.DOWN
        else:
            return ELVConfig.STAY
    
    def move_floor(self, target_floor):
        if self.state == ELVConfig.elvq2 or self.state == ELVConfig.elvq5:
            time = self.last_move_function_time - self.time.current_timestamp()
            door = self.get_door_status()
            if door:
                self.close_door()
            direction = self.set_direction(self.movingStatus)
            if self.current_floor != target_floor:
                if time < ELVConfig.PERFLOORMOVETIME:
                    self.current_floor += direction
            else:
                self.last_move_function_time = None
                self.movingStatus = ELVConfig.STAY
                return True
        return False

    def get_elv_status(self):
        return {
            ELVConfig.FLOOR: self.current_floor,
            ELVConfig.DOOR: self.door,
            ELVConfig.MOVINGSTATUS: self.movingStatus,
            ELVConfig.INSERVICE: self.inService,
            ELVConfig.INDRIVING_PERMISSION: self.inDrivingPermission,
            ELVConfig.ANSERBACK: self.answerBack,
            ELVConfig.TROUBLE: self.trouble,
            ELVConfig.STATE: self.state,
            ELVConfig.TIME: self.time if self.time is not None else 0
        }

    def set_direction(self, moving_status):
        if moving_status == ELVConfig.UP:
            return 1
        elif moving_status == ELVConfig.DOWN:
            return -1
        elif moving_status == ELVConfig.STAY:
            return 0

class ElvHandler():
    """ A singleton to handle ELV class instances """
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ElvHandler, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.elv_dict = {}
            self._elv_copy = None
            self._initialized = True

    def init(self):
        for elv in self.elv_dict.values():
            elv['elv'].init()

    def add_elv(self, elv_name, elv, priority=0):
        """Add a new elv name:elv instance pair to elv dictionary"""
        self.elv_dict[elv_name] = {'elv':elv}

    def copy_elv(self):
        """Save a copy of the elevator instance"""
        self.elv_copy = copy.deepcopy(self.find_elv())

    def paste_elv(self):
        """Replace the elevator instance with the saved copy"""
        if not self._elv_copy:
            return
        for name in self.elv_dict.keys():
            del self.elv_dict[name]['elv']
            self.elv_dict[name] = {'elv': self._elv_copy}

    def find_elv(self, elv_name=None):
        """Return the elevator instance"""
        if not elv_name:
            for elv in self.elv_dict.values():
                return elv['elv']
        return self.elv_dict[elv_name]

    def delete_elv(self, elv_name):
        """Delete the elevator from the dict by name"""
        self.rob_dict.pop(self.find_elv(elv_name))
        self.elv_dict[elv_name] = None


