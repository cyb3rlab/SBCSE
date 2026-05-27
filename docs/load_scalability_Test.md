
## load_scalability_Test

`load_scalability_Test` is used for load and scalability testing of the simulator environment.

This script starts multiple simulators and generates MQTT communication traffic in order to evaluate:

- MQTT broker load
- CPU usage
- communication stability
- scalability with multiple robots
- high-frequency robot telemetry behavior

The test environment can be scaled by increasing the number of simulated robots.

---

# How to Use

## 1. Configure number of robots and test duration

Edit the following parameters:

```python
DEVICES = 1
DURATION = 200
```

- `DEVICES`
  - Number of simulated robots
- `DURATION`
  - Test duration in seconds

Example:

```python
DEVICES = 50
DURATION = 600
```

This runs 50 robots for 10 minutes.

---

## 2. Configure robot telemetry frequency

Update frequencies can be adjusted in:

```python
simulator/robsim.py
```

Examples:

```python
rob.bot_dt_send_time = 10
rob.bot_pos_log_time = 5
rob.bot_cam_time = 2
```

- `rob.bot_dt_send_time`
  - Controls robot telemetry (`rob_dt`) sending frequency.

- `rob.bot_pos_log_time`
  - Controls position log update frequency.

- `rob.bot_cam_time`
  - Controls robot status/configuration update frequency.

Higher frequency example:

```python
rob.bot_dt_send_time = 0.1
```

Reducing these values increases MQTT communication traffic and simulator workload, and can be used for load/stress testing.

---

## 3. Run the test

```bash
python load_scalability_Test.py
```

---

# Notes

- Higher update frequencies generate significantly more MQTT traffic and simulator workload.
- Large `DEVICES` values may increase CPU and memory usage.
- The script also monitors:
  - MQTT broker traffic
  - mosquitto CPU usage
  - runtime statistics

---
