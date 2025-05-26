import yaml
import signal
import json
import sys
from datetime import datetime
from device_motion_module.elevator import Elevator, ElvHandler
from device_motion_module.servicerobot import ServiceRobot, RobotHandler


def generate_file_path(output_dir, perfix, extension):
    timestamp = datetime.now().strftime('%m%d---%H')
    return f'{output_dir}/{perfix}_{timestamp}.{extension}'

def clear_file(file_path):
    # clear the content of the file
    with open(file_path, 'w')as f:
        f.write("")

def write_file(file_path, content):
    # write content to a file
    with open(file_path, 'a')as F:
        F.write(content)

def load_scenario(file_path, sim_speed, protocol, robs, tasks, elvs, scenario, rob_name, priority, time=None, fuzz_target=None):
    # Load yaml file
    with open(file_path, 'r') as f:
        scenario_data = yaml.safe_load(f)

    service_robot_data = scenario_data.get(robs, [])
    TASKS = scenario_data.get(tasks, [])

    elevator_data = scenario_data.get(elvs, [])
    Rob = [ServiceRobot(robot, time) for robot in service_robot_data]
    ELV = [Elevator(elv, time) for elv in elevator_data]
    Sim_Speed = scenario_data.get(sim_speed, [])
    PROTOCOL = scenario_data.get(protocol, [])
    attck_scenario = scenario_data.get(scenario, [])
    FUZZING_SCENARIO = scenario_data.get(fuzz_target, [])
    SCENARIO_NAME = None
    TARGET = None

    for scenario in attck_scenario:
        SCENARIO_NAME = scenario['scenario_name']
        TARGET = scenario['target']


    robothandler = RobotHandler()
    elvhandler = ElvHandler()
    for robot in Rob:
        robothandler.add_rob(robot.name, robot)
    for elv in ELV:
        elvhandler.add_elv(elv.name, elv)

    return Sim_Speed, PROTOCOL, Rob, TASKS, ELV, SCENARIO_NAME, TARGET, FUZZING_SCENARIO

def update_scenario(file_path, data):
    with open(file_path, 'w') as file:
        yaml.safe_dump(data, file)

def handle_keyboard_exit(self):
    # Stopping the server using Ctrl+C
    signal.signal(signal.SIGINT, lambda sig, frame: self.stop_server())

    while self.running:
        pass  # Keep the server running until an exit signal is captured

def load_ip_config(filename="config.json"):
    """Loading a static IP configuration"""
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as e:
        print(f"Failed to load configuration: {e}")
        return {}

