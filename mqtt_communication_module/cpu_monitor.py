import psutil
from utils.msglog import log_cpu


# CPU
class MonitorCPU:
    def __init__(self, file_path, target_process_name="mosquitto", interval=0.5, time_sim=None):
        self.log_file = file_path
        self.running = True
        self.time = time_sim
        self.is_monitoring = False
        self.interval = interval
        self.target = target_process_name

    def monitor_cpu(self):
        """Monitor the CPU usage"""
        self.is_monitoring = True
        while self.is_monitoring:
            try:
                # Get all matching processes
                for proc in psutil.process_iter(['name']):
                    if proc.info['name'] == self.target:
                        proc.cpu_percent()
                        cpu_usage = proc.cpu_percent(interval=self.interval)
                        log_cpu(self.log_file, self.target, cpu_usage, self.time)
                        break
            except Exception as e:
                print(f"Error monitoring CPU: {e}")
            self.time.sleep(self.interval)

    def start_monitoring(self):
        if self.is_monitoring:
            print("Monitoring CPU is already running+++++++++++++++")
            return
        self.is_monitoring = True
        self.monitor_cpu()

    def stop_monitoring(self):
        self.is_monitoring = False
        print("Monitoring CPU stopped---------------")