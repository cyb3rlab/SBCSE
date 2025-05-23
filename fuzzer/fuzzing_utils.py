import random
import yaml
import string
import sys
from utils.storyboard import RobotConfig, ScenarioConfig, MqttConfig, FuzzingConfig

fuzzing_scenario = {
    ScenarioConfig.Service_Robots: [],
    ScenarioConfig.Tasks: [],
    ScenarioConfig.Elevators: [],
    ScenarioConfig.ATT_SCENARIO: [{ScenarioConfig.SCENARIO_NAME: None, ScenarioConfig.TARGET: None}],
    ScenarioConfig.PROTOCOL: MqttConfig.MQTT,
    ScenarioConfig.FUZZER:[],
    ScenarioConfig.Sim_Speed: 1
    }

def scenario_data(seed):
    random.seed(seed)
    task_num = random.randint(1,4)
    bot_num = random.randint(1,3)
    for i in range(bot_num):
        rob_name = 'bot'+str(i)
        rob_floor = random.randint(2, 11)
        rob_position1 = random.randint(0, 2000)
        rob_position2 = random.randint(0, 2000)
        rob_position3 = random.randint(0, 2000)
        fuzzing_scenario[ScenarioConfig.Service_Robots].append({ScenarioConfig.Service_Robot_Name: rob_name,
                                                    RobotConfig.FLOOR: rob_floor, 
                                                    ScenarioConfig.Service_Robot_Position: [rob_position1, 
                                                                                            rob_position2, 
                                                                                            rob_position3]})
    elv_name = 'elv1'
    elv_floor = random.randint(2, 11)
    elv_door = random.choice([ScenarioConfig.Elevator_door_open, 
                                    ScenarioConfig.Elevator_door_close, 
                                    ''.join(random.sample(string.ascii_letters + string.digits, random.randint(1, 12)))])
    elv_movingStatus = random.choice([ScenarioConfig.Elevator_movingStatus_up, 
                                            ScenarioConfig.Elevator_movingStatus_down, 
                                            ScenarioConfig.Elevator_movingStatus_stay,
                                            ''.join(random.sample(string.ascii_letters + string.digits, random.randint(1, 12)))])
    elv_inDrivingPermission = random.choice([False])
    fuzzing_scenario[ScenarioConfig.Elevators].append({ScenarioConfig.Elevator_Name: elv_name,
                                          ScenarioConfig.Elevator_Floor: elv_floor,
                                          ScenarioConfig.Elevator_door: elv_door,
                                          ScenarioConfig.Elevator_movingStatus: elv_movingStatus,
                                          ScenarioConfig.Elevator_inDrivingP: elv_inDrivingPermission
                                          })
    for i in range(task_num):
        task_no = i
        task_floor = random.randint(2, 11)
        task_name = random.choice([ScenarioConfig.Task_Schedule_Work, ScenarioConfig.Task_Charge, ''.join(random.sample(string.ascii_letters + string.digits, random.randint(1, 12)))])
        fuzzing_scenario[ScenarioConfig.Tasks].append({ScenarioConfig.Task_No: task_no,
                                           ScenarioConfig.Task_Floor: task_floor,
                                           ScenarioConfig.Task_Name: task_name})
    values = [False] * 4
    index = random.randint(0, 3)
    values[index] = True
    fuzzing_scenario[ScenarioConfig.FUZZER].append({
        FuzzingConfig.ELVSIM: values[0],
        FuzzingConfig.BOSSIM: values[1],
        FuzzingConfig.RPFSIM: values[2],
        FuzzingConfig.ROBSIM: values[3]
    })

    print(fuzzing_scenario, file=sys.stderr, flush=True)
    return fuzzing_scenario

def generate_scenario(seed):
    with open('fuzzer/fuzzing_scenario.yaml', 'w') as file:
        yaml.dump(scenario_data(seed), file)

def generate_libfuzzer_seed():
    return str(random.randint(0, 2**32 - 1))

def get_seed():
    for arg in sys.argv:
        if arg.startswith('-seed='):
            return arg.split('=')[1]        
    seed = generate_libfuzzer_seed()
    sys.argv.append('-seed='+str(seed)) 
    return seed