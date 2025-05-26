from utils.storyboard import MqttConfig, CmdConfig
from mqtt_communication_module.elvmsghandler import ElvMessageHandler
from utils.msglog import action_log


class ElevatorSimulator:
    def __init__(self, send_topic, recv_topic, broker, port, elevators, time, enable_allowlist):
        self.time = time
        self.port = port
        self.broker = broker
        self.running = True
        self.elevators = elevators
        self.elevator = elevators[0]
        self.handler = ElvMessageHandler(send_topic, recv_topic, broker, port, self.elevator, self.time)
        self.handler.client_ip = self.handler.bind_client_to_port()
        self.handler.enable_allowlist = enable_allowlist
        self.client = self.handler.client
        self.client.on_connect = self.handler.on_connect
        self.client.on_message = self.handler.fm_message

    def init(self):
        self.handler.cmd_list = []

    def elv_move(self):
        if self.handler.cmd_list:
            cmd = self.handler.cmd_list[0]
            if self.elevator.move_floor(cmd[1]):
                if cmd[0] == CmdConfig.CALL:
                    self.handler.recv_command_response(CmdConfig.CALL, CmdConfig.ARRIVE)
                elif cmd[0] == CmdConfig.GO:
                    self.handler.recv_command_response(CmdConfig.GO, CmdConfig.ARRIVE)
                action_log(cmd[0]+" arrive: "+str(cmd[1])+" floor", self.elevator.current_floor, self.time, self.elevator.act_log)
                self.handler.cmd_list.pop(0)

    def start_simulation(self, stop_event):
        try:
            while not stop_event.is_set() and not self.handler.client.is_connected():
                self.time.sleep(1)

            self.client.loop_start()

            while self.running and not stop_event.is_set():

                if not self.client.is_connected():
                    self.client.connect(self.broker, self.port)
                self.handler.send_dt_elv()
                self.elv_move()
                for _ in range(5):
                    if stop_event.is_set():
                        break
                    self.time.sleep(1)
        except Exception as e:
            print(e)

        finally:
            self.stop_simulation()

    def stop_simulation(self):
        if self.running:
            self.running = False
            self.client.loop_stop()
            try:
                self.client.disconnect()
            except Exception as e:
                print(f"Error during disconnection: {e}")
            print("Elv stopped")