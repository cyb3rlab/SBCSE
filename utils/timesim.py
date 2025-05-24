"""
Allowing time to pass faster/slower than real-life time.
"""
# import time as real_time
import time as real_time
from threading import Lock
from datetime import datetime, timedelta, timezone


class TimeSim:
    def __init__(self, time_scale):
        self.time_scale = time_scale
        self.start_time = real_time.time()

    def time(self):
        # return scaled time
        return (real_time.time()) * self.time_scale

    def current_timestamp(self):
        # return the current timestamp based on the scaled time
        current_time = self.start_time + (real_time.time() - self.start_time) * self.time_scale
        return current_time

    def current_utc_datetime(self):
        # return current UTC datetime
        # utc_time = datetime.fromtimestamp(self.current_timestamp(), tz=timezone.utc)
        utc_time = datetime.utcfromtimestamp(self.current_timestamp())
        return utc_time

    def current_jst_datetime(self):
        # return current JST datetime
        jst_time = self.current_utc_datetime() + timedelta(hours=9)
        # datetime.fromtimestamp(self.current_timestamp(), tz=timezone(timedelta(hours=+9), 'JST'))
        return jst_time

    def sleep(self, seconds):
        scaled_time = seconds / self.time_scale
        real_time.sleep(scaled_time)

    def now(self):
        # return current datetime based on the scaled time
        return self.current_utc_datetime()

if __name__ == "__main__":
    timesim_singleton = TimeSim()
    print(f"Scaled Time: {timesim_singleton.time()}")
    print(f"Current Timestamp: {timesim_singleton.current_timestamp()}")
    print(f"Current UTC Datetime: {timesim_singleton.current_utc_datetime()}")
    print(f"Current JST Datetime: {timesim_singleton.current_jst_datetime()}")
    print("Sleeping for 2 scaled seconds...")
    timesim_singleton.sleep(2)
    print("OK!")
