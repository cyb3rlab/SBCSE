import psutil
import csv
from utils.msglog import log_cpu, log_cpu_row
from datetime import datetime

# CPU
class MonitorCPU:
    def __init__(self, file_path, target_process_name="mosquitto", interval=0.5, time_sim=None):
        self.log_file = file_path
        self.running = True
        self.time = time_sim
        self.is_monitoring = False
        self.interval = interval
        self.target = target_process_name

        self._proc = None # cache target process

    def _find_target_proc(self):
        for p in psutil.process_iter(['name']):
            if p.info.get('name') == self.target:
                return p
        return None

    def monitor_cpu(self):
        """Monitor the CPU usage"""
        self.is_monitoring = True

        psutil.cpu_percent(interval=None)
        self._proc = self._find_target_proc()
        if self._proc is not None:
            try:
                self._proc.cpu_percent(interval=None)
            except Exception:
                self._proc = None

        while self.is_monitoring:
            try:
                system_cpu = psutil.cpu_percent(interval=self.interval)

                if self._proc is None or not self._proc.is_running():
                    self._proc = self._find_target_proc()
                    if self._proc is not None:
                        self._proc.cpu_percent(interval=None)

                if self._proc is not None:
                    proc_cpu = self._proc.cpu_percent(interval=None)

                log_cpu_row(self.log_file, self.target, system_cpu, proc_cpu, self.time)

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                log_cpu_row(self.log_file, self.target, system_cpu, proc_cpu, self.time)
                self._proc = None
            except Exception as e:
                print(f"Error monitoring CPU: {e}")

            if self.time is not None:
                self.time.sleep(0)

    def start_monitoring(self):
        if self.is_monitoring:
            print("Monitoring CPU is already running+++++++++++++++")
            return
        # self.is_monitoring = True
        self.monitor_cpu()

    def stop_monitoring(self):
        self.is_monitoring = False
        print("Monitoring CPU stopped---------------")