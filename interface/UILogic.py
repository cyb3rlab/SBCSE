import os
import yaml
import webbrowser
from threading import Thread
from kivy.lang import Builder
from kivy.uix.gridlayout import GridLayout
from kivy.core.window import Window
from kivy.properties import ObjectProperty, ListProperty, StringProperty
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from device_motion_module.servicerobot import ServiceRobot
from device_motion_module.elevator import Elevator
from kivy.clock import Clock
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.behaviors import DragBehavior
from kivy.properties import NumericProperty, BooleanProperty
from utils.storyboard import MqttConfig, ClientConfig, ScenarioConfig, Mode
from utils.utils import load_scenario


class UILogic(BoxLayout):
    robot_spinner = ObjectProperty(None)
    task_spinner = ObjectProperty(None)
    elevator_spinner = ObjectProperty(None)
    scenario_spinner = ObjectProperty(None)
    target_spinner = ObjectProperty(None)
    measure_spinner = ObjectProperty(None)
    protocol_spinner = ObjectProperty(None)
    terminal_output = ObjectProperty(None)
    start_button = ObjectProperty(None)
    stop_button = ObjectProperty(None)
    reset_button = ObjectProperty(None)
    output_container = ObjectProperty(None)
    toggle_button = ObjectProperty(None)
    collapsible_panel = ObjectProperty(None)

    robot_list = ListProperty([])
    task_list = ListProperty([])
    elevator_list = ListProperty([])
    scenario_list = ListProperty([])
    target_list = ListProperty([])
    protocol_list = ListProperty([])
    measures_list = ListProperty([])

    output_file = StringProperty('')
    data = ObjectProperty(None)
    # panel_height = NumericProperty(0)  # Panel height
    panel_width = NumericProperty(500)
    panel_visible = BooleanProperty(False)
    initial_width = NumericProperty(700)
    initial_height = NumericProperty(500)

    def __init__(self, main_program, **kwargs):
        super().__init__(**kwargs)
        self.main_program = main_program
        self.time = self.main_program.time
        self.main_program.set_log_callback(self.combined_log_callback)
        self.load_scenario()
        # self.update_target_list(self.ids.scenario_spinner.text)
        self.update_target_list(self.scenario_list[0])
        self.selected_tasks = []
        self.selected_robs = []
        self.selected_elvs = []
        # self.rpf_protocol_list = []
        # self.rob_protocol_list = []
        self.panel_visible = False
        Window.size = (self.initial_width, self.initial_height)

    def on_start_button_click(self):
        # scenario_file = self.ids.scenario_file_input.text
        # self.main_program.load_and_start(scenario_file)
        self.resetting = False
        Thread(target=self.start_simulation_async).start()

    def set_button_state(self, start_button_enabled=True, stop_button_enabled=False, reset_button_enabled=True, toggle_button_enabled=True):
        """
        Set the state of the start and stop buttons.
        Parameters:
        - start_button_enabled (bool): True。
        - stop_button_enabled (bool): False。
        """
        self.ids.start_button.disabled = not start_button_enabled
        self.ids.stop_button.disabled = not stop_button_enabled
        self.ids.reset_button.disabled = not reset_button_enabled
        self.ids.toggle_button.disabled = not toggle_button_enabled

    def start_simulation_async(self):
        # Asynchronous thread methods
        self.run_simulation()

    def run_simulation(self):
        # Using Clock.schedule_once for UI updates
        # Clock.schedule_once(self.update_terminal_output_start)
        self.scheduled_event = Clock.schedule_once(self.update_terminal_output_start)
        self.simulation_thread = Thread(target=self.start_simulation, daemon=True)
        self.simulation_thread.start()

    def update_terminal_output_start(self, dt):
        self.ids.start_button.disabled = True
        self.ids.reset_button.disabled = True
        self.ids.stop_button.disabled = False
        self.ids.toggle_button.disabled = False
        self.ids.terminal_output.text += "Running simulation with selected options...\n"

    def start_simulation(self):
        selected_robot_name = self.ids.robot_spinner.text
        selected_task_name = self.ids.task_spinner.text
        selected_elevator_name = self.ids.elevator_spinner.text
        selected_scenario = self.ids.scenario_spinner.text
        selected_target = self.ids.target_spinner.text
        selected_protocol = self.ids.protocol_spinner.text

        # Check that all necessary options are set
        if (selected_robot_name == "Select Robot" and selected_task_name == "Select Task" and
                selected_elevator_name == "Select Elevator" and selected_scenario == "Select Scenario" and
                selected_target == "Select Target" and selected_protocol == "Select Protocol" ):

            self.main_program.settings(protocol=None, rob=None, elv=None, task=None, scenario=None, target=None)
            self.update_terminal_output(f"Running simulation with Ymal options...\n")
        else:
            if not self.selected_tasks:
                selected_task = next((task for task in self.data['tasks'] if task['task_name'] == selected_task_name), None)
                if selected_task:
                    self.selected_tasks.append(selected_task)
            # Handling robots
            if not self.selected_robs:
                # Select the robot name from the drop-down menu to create the object
                selected_robots = [robot for robot in self.data['service_robots'] if robot['name'] == selected_robot_name]
                self.selected_robs = [ServiceRobot(robot_data, self.time) for robot_data in selected_robots]
            # Handling elevators
            if not self.selected_elvs:
                # Select the elevator name from the drop-down menu to create the object
                selected_elevators = [elevator for elevator in self.data['elevators'] if elevator['name'] == selected_elevator_name]
                self.selected_elvs = [Elevator(elv_data, self.time) for elv_data in selected_elevators]

            # if self.selected_protocol:
            #     self.selected_protocol.append(selected_protocol)


            elv = self.selected_elvs
            rob = self.selected_robs  # Directly use the created object list

            robot_names = [robot.name for robot in rob]
            elevator_names = [elevator.name for elevator in elv]
            task_names = [task['task_name'] for task in self.selected_tasks]
            task_target_floor = [task['task_floor'] for task in self.selected_tasks]
            protocol_name = selected_protocol

            self.update_terminal_output(f"Protocol: {protocol_name}")
            self.update_terminal_output(f"Rob: {robot_names}")
            self.update_terminal_output(f"Elv: {elevator_names}")
            self.update_terminal_output(f"Task: {task_names} ,TargetFloor{task_target_floor}")
            self.update_terminal_output(f"Scenario: {selected_scenario}")
            self.update_terminal_output(f"Target: {selected_target}")
            self.main_program.settings(selected_protocol, rob, elv, self.selected_tasks, selected_scenario, selected_target)

        # Set the button state
        self.set_button_state(start_button_enabled=False, stop_button_enabled=True, reset_button_enabled=False,
                              toggle_button_enabled=True)
        self.main_program.setup_simulators()
        self.main_program.start_server()

    def stop_simulation(self):
        self.update_terminal_output("Stopping simulation...\n")
        self.main_program.stop_server()

        # Wait for the simulation thread to stop
        if hasattr(self, 'simulation_thread') and self.simulation_thread.is_alive():
            self.simulation_thread.join(timeout=5)

        if self.main_program.mqtt_client:  # Check if mqtt_client is initialized
            self.main_program.mqtt_client.disconnect()

        Clock.schedule_once(lambda dt: self.update_terminal_output("Simulation stopped. Logs are available for viewing.\n"))

        #self.update_terminal_output("Simulation stopped. Logs are available for viewing.\n")
        self.set_button_state(start_button_enabled=True, stop_button_enabled=False, reset_button_enabled=True, toggle_button_enabled=True)

    def combined_log_callback(self, log_files):
        print(f"log_files type: {type(log_files)}")
        if isinstance(log_files, dict):
            self.update_terminal_output("Generated file...\n")
            self.handle_log_files(log_files)
        else:
            print("Received non-dict log files data:", log_files)

    def reset_simulation(self):

        print("Resetting simulation...")

        # Cancel all scheduled events
        if hasattr(self, 'scheduled_event'):
            self.scheduled_event.cancel()

        # Setting the Flag
        self.resetting = True

        # self.stop_simulation()
        self.ids.terminal_output.text = ""
        self.ids.output_container.clear_widgets()
        self.ids.robot_spinner.text = "Select Robot"
        self.ids.task_spinner.text = "Select Task"
        self.ids.elevator_spinner.text = "Select Elevator"
        self.ids.scenario_spinner.text = "Select Scenario"
        self.ids.target_spinner.text = "Select Target"
        self.ids.protocol_spinner.text = "Select Protocol"
        self.selected_tasks = []
        self.selected_robs = []
        self.selected_elvs = []
        # self.selected_protocol = []
        self.set_button_state(start_button_enabled=True, stop_button_enabled=False, reset_button_enabled=True, toggle_button_enabled=True)

        print("Simulation reset complete.")

    def handle_log_files(self, log_files):
        self.show_results_link(log_files)

    def show_results_link(self, log_files):
        self.ids.output_container.clear_widgets()  # Clear all previous parts

        for log_name, log_path in log_files.items():
            button = Button(text=log_name, size_hint=(1, None), height=30, background_normal='', background_color=((0.1, 0.1, 0.3, 1)))
            button.bind(on_press=lambda instance, path=log_path: self.open_file(path))
            self.ids.output_container.add_widget(button)

    def open_file(self, path):
        if os.path.exists(path):
            os.system(f"open {path}")
        else:
            print(f"File not found: {path}")

    def update_terminal_output(self, message):
        # Make sure to update the UI in the main thread
        def update_text(dt):
            if self.ids.terminal_output:
                self.ids.terminal_output.text += message + "\n"
            else:
                print("Error: Terminal output not found")

        Clock.schedule_once(update_text)

    # Multitasking
    def add_task(self):
        selected_task_name = self.ids.task_spinner.text
        if selected_task_name != "Select Task" and selected_task_name not in self.selected_tasks:
            # Get selected task information from YAML data
            selected_task = next((task for task in self.data['tasks'] if task['task_name'] == selected_task_name), None)
            if selected_task:
                self.selected_tasks.append(selected_task)
                self.update_terminal_output(f"Added task: {selected_task_name}\n")
            else:
                self.update_terminal_output(f"Task {selected_task_name} not found in the data.\n")
        else:
            self.update_terminal_output("Please select a valid task to add.\n")

    def add_robot(self):
        selected_robot_name = self.ids.robot_spinner.text
        if selected_robot_name != "Select Robot" and not any(robot.name == selected_robot_name for robot in self.selected_robs):
            selected_robot = next((robot for robot in self.data['service_robots'] if robot['name'] == selected_robot_name), None)
            if selected_robot:
                new_robot = ServiceRobot(selected_robot, self.time)
                self.selected_robs.append(new_robot)
                self.update_terminal_output(f"Robot '{selected_robot_name}' added.")
            else:
                self.update_terminal_output(f"Robot {selected_robot_name} not found in the data.\n")
        else:
            self.update_terminal_output("Please select a valid robot to add.\n")

    def add_elevator(self):
        selected_elevator_name = self.ids.elevator_spinner.text
        if selected_elevator_name != "Select Elevator" and not any(
                elv.name == selected_elevator_name for elv in self.selected_elvs):
            selected_elevator = next(
                (elevator for elevator in self.data['elevators'] if elevator['name'] == selected_elevator_name), None)
            if selected_elevator:
                new_elevator = Elevator(selected_elevator, self.time)
                self.selected_elvs.append(new_elevator)
                self.update_terminal_output(f"Elevator '{selected_elevator_name}' added.")
            else:
                self.update_terminal_output(f"Elevator {selected_elevator_name} not found in the data.\n")
        else:
            self.update_terminal_output("Please select a valid elevator to add.\n")

    def load_results(self):
        # Clock.schedule_once(lambda dt: self.update_terminal_output("Loading results...\n"))
        self.update_terminal_output("Loading results...\n")

    def show_popup(self, title, message):
        popup = Popup(title=title, content=Label(text=message), size_hint=(None, None), size=(400, 200))
        popup.open()

    def toggle_window(self):
        #For folding panels
        if self.panel_visible:
            Window.size = (self.initial_width, self.initial_height)
        else:
           # Window.size = (self.initial_width + self.panel_width, self.initial_height)
            Window.size = (self.initial_width + 300, self.initial_height)

        self.panel_visible = not self.panel_visible

    def load_scenario(self):
        with open('./utils/scenario.yaml', 'r') as file:
            data = yaml.safe_load(file)
            self.data = data
            self.robot_list = [robot['name'] for robot in data['service_robots']]
            self.task_list = [task['task_name'] for task in data['tasks']]
            self.elevator_list = [elevator['name'] for elevator in data['elevators']]

        scenarios = ScenarioConfig.scenarios
        self.scenario_list = [scenario['attack_scenario'] for scenario in scenarios]
        self.update_target_list(self.scenario_list[0])

        self.protocol_list = ScenarioConfig.protocol

    def update_target_list(self, selected_scenario):
        for scenario in ScenarioConfig.scenarios:
            if scenario['attack_scenario'] == selected_scenario:
                self.target_list = scenario['target'] if isinstance(scenario['target'], list) else [scenario['target']]
                break

    def on_scenario_spinner_select(self, spinner, text):
        self.update_target_list(text)
        # Updating the target drop-down list
        self.ids.target_spinner.values = self.target_list
        if self.target_list:
            self.ids.target_spinner.text = self.target_list[0]
        else:
            self.ids.target_spinner.text = 'Select Target'

    def open_yaml_file(self):
        path = './utils/scenario.yaml'
        if os.path.exists(path):
            os.system(f"open {path}")
        else:
            print(f"File not found: {path}")
