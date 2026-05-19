import os
from utils.timesim import TimeSim

LOAD_SCALABILITY_STATUS = {
    "enabled": False,
    "devices": 1,
    "duration": 0,
    "time_sim": None,
    "log_file": None
}


def enable_load_scalability(devices=1, duration=60, time_sim=None, log_file=None):
    """
    Enable scalability experiment metadata logging only.

    NOTE:
    Real load comes from increasing robot/device count in scenario.
    This module DOES NOT generate fake traffic.
    """

    LOAD_SCALABILITY_STATUS.update({
        "enabled": True,
        "devices": devices,
        "duration": duration,
        "time_sim": time_sim,
        "log_file": log_file
    })

    _log_status()

    print(
        f"[LoadScalability] Enabled | devices={devices}, duration={duration}s"
    )


def _log_status():
    log_file = LOAD_SCALABILITY_STATUS["log_file"]

    if log_file is None:
        return

    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    if LOAD_SCALABILITY_STATUS["time_sim"]:
        ts = LOAD_SCALABILITY_STATUS["time_sim"].current_timestamp()
    else:
        ts = 0

    with open(log_file, "a") as f:
        f.write(
            f"{ts}, devices={LOAD_SCALABILITY_STATUS['devices']}, "
            f"duration={LOAD_SCALABILITY_STATUS['duration']}\n"
        )
