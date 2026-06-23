# ODrive v3.6 + Maxon EC 60 Flat 100W — Complete Setup Reference

## Hardware Specs
| Component | Details |
|---|---|
| ODrive | v3.6-56V, firmware v0.5.6 |
| Motor | Maxon EC 60 flat, 68mm, 100W, 24V, BLDC (part 411678) |
| Encoder | Maxon MILE, 4096 CPT, 2 channel, line driver (differential) |
| Max motor speed | ~4270 RPM = ~71 turns/sec |
| Phase resistance | ~0.21 Ω (healthy range: 0.15–0.21 Ω) |

---

## Wiring
### Motor Phases (M0 / M1 terminals)
- 3 phase wires (A, B, C) → ODrive motor terminals
- Wire order does not matter for BLDC calibration
- All 3 must be firmly screwed in

### Encoder (J3 = axis0, J4 = axis1)
| Pin | Signal |
|---|---|
| 1 | 5V |
| 2 | GND |
| 3 | A+ |
| 4 | A- |
| 5 | B+ |
| 6 | B- |

### Axis Assignment
| Axis | Wheel |
|---|---|
| axis0 | LEFT wheel |
| axis1 | RIGHT wheel |

---

## Saved Configuration (both axes identical)
| Parameter | Value |
|---|---|
| motor_type | 0 (HIGH_CURRENT) |
| pole_pairs | 7 |
| torque_constant | 0.0534 Nm/A |
| current_lim | 10.0 A |
| calibration_current | 3.0 A |
| resistance_calib_max_voltage | 2.0 V |
| encoder_mode | 0 (INCREMENTAL) |
| encoder_cpr | 4096 |
| use_index | False |
| vel_limit | 70.0 turns/sec |
| control_mode | 2 (VELOCITY) |
| input_mode | 1 (VEL_RAMP) |
| inverter_temp_limit_lower | 100.0 °C |
| inverter_temp_limit_upper | 120.0 °C |
| motor_thermistor.enabled | False |

---

## Key Notes
- CPR = 4096 NOT 16384 — ODrive handles quadrature internally
- Calibration is required every power cycle
- Motor thermistor must be disabled every session (save_configuration returns False — doesn't persist)
- phase_resistance 0.000125 = wiring issue, should be 0.15–0.21 Ω
- Brownout possible under dual motor high load — use adequate PSU

---

## Step 1 — Apply Full Config (run once after flashing or erase)

```python
import time

# ── AXIS 0 ──
odrv0.axis0.motor.config.motor_type = 0
odrv0.axis0.motor.config.pole_pairs = 7
odrv0.axis0.motor.config.torque_constant = 0.0534
odrv0.axis0.motor.config.current_lim = 10.0
odrv0.axis0.motor.config.calibration_current = 3.0
odrv0.axis0.motor.config.resistance_calib_max_voltage = 2.0
odrv0.axis0.encoder.config.mode = 0
odrv0.axis0.encoder.config.cpr = 4096
odrv0.axis0.encoder.config.use_index = False
odrv0.axis0.controller.config.vel_limit = 70.0
odrv0.axis0.controller.config.control_mode = 2
odrv0.axis0.controller.config.input_mode = 1
odrv0.axis0.motor.config.inverter_temp_limit_lower = 100.0
odrv0.axis0.motor.config.inverter_temp_limit_upper = 120.0

# ── AXIS 1 ──
odrv0.axis1.motor.config.motor_type = 0
odrv0.axis1.motor.config.pole_pairs = 7
odrv0.axis1.motor.config.torque_constant = 0.0534
odrv0.axis1.motor.config.current_lim = 10.0
odrv0.axis1.motor.config.calibration_current = 3.0
odrv0.axis1.motor.config.resistance_calib_max_voltage = 2.0
odrv0.axis1.encoder.config.mode = 0
odrv0.axis1.encoder.config.cpr = 4096
odrv0.axis1.encoder.config.use_index = False
odrv0.axis1.controller.config.vel_limit = 70.0
odrv0.axis1.controller.config.control_mode = 2
odrv0.axis1.controller.config.input_mode = 1
odrv0.axis1.motor.config.inverter_temp_limit_lower = 100.0
odrv0.axis1.motor.config.inverter_temp_limit_upper = 120.0

odrv0.save_configuration()
# ODrive will reboot — reconnect after
```

---

## Step 2 — Every Power Cycle Startup Sequence

```python
import time

# ── Clear errors ──
odrv0.axis0.error = 0
odrv0.axis0.motor.error = 0
odrv0.axis1.error = 0
odrv0.axis1.motor.error = 0

# ── Calibrate axis0 ──
odrv0.axis0.requested_state = 4   # motor calibration — wait for beep
time.sleep(10)
print("axis0 motor cal - error:", odrv0.axis0.motor.error)
odrv0.axis0.requested_state = 7   # encoder offset calibration — wait for stop
time.sleep(10)
print("axis0 encoder cal - error:", odrv0.axis0.encoder.error)

# ── Calibrate axis1 ──
odrv0.axis1.requested_state = 4
time.sleep(10)
print("axis1 motor cal - error:", odrv0.axis1.motor.error)
odrv0.axis1.requested_state = 7
time.sleep(10)
print("axis1 encoder cal - error:", odrv0.axis1.encoder.error)

# ── Disable thermistors (must do every session) ──
odrv0.axis0.motor.motor_thermistor.config.enabled = False
odrv0.axis1.motor.motor_thermistor.config.enabled = False

# ── Clear any post-cal errors ──
odrv0.axis0.error = 0
odrv0.axis0.motor.error = 0
odrv0.axis1.error = 0
odrv0.axis1.motor.error = 0

print("axis0 error:", odrv0.axis0.error)
print("axis1 error:", odrv0.axis1.error)
print("Ready for closed loop!")
```

---

## Step 3 — Enter Closed Loop

```python
import time

odrv0.axis0.requested_state = 8
odrv0.axis1.requested_state = 8
time.sleep(1)
print("axis0 state:", odrv0.axis0.current_state)   # should be 8
print("axis1 state:", odrv0.axis1.current_state)   # should be 8
```

---

## Step 4 — Spin Motors (indefinite, no timer)

```python
# Spin axis0 only
odrv0.axis0.controller.input_vel = 10.0

# Spin axis1 only
odrv0.axis1.controller.input_vel = 10.0

# Spin both
odrv0.axis0.controller.input_vel = 10.0
odrv0.axis1.controller.input_vel = 10.0
```

---

## Step 5 — Stop Motors (back to idle)

```python
odrv0.axis0.controller.input_vel = 0.0
odrv0.axis1.controller.input_vel = 0.0
odrv0.axis0.requested_state = 1
odrv0.axis1.requested_state = 1
print("Both motors idle.")
```

---

## Step 6 — Change Speed (motors already spinning)

```python
# Increase speed
odrv0.axis0.controller.input_vel = 30.0
odrv0.axis1.controller.input_vel = 30.0

# Decrease speed
odrv0.axis0.controller.input_vel = 10.0
odrv0.axis1.controller.input_vel = 10.0
```

---

## Step 7 — Restart After Stop (re-enter closed loop)

```python
import time

# Clear errors first
odrv0.axis0.error = 0
odrv0.axis0.motor.error = 0
odrv0.axis1.error = 0
odrv0.axis1.motor.error = 0

# Re-enter closed loop
odrv0.axis0.requested_state = 8
odrv0.axis1.requested_state = 8
time.sleep(1)
print("axis0 state:", odrv0.axis0.current_state)
print("axis1 state:", odrv0.axis1.current_state)

# Spin again
odrv0.axis0.controller.input_vel = 10.0
odrv0.axis1.controller.input_vel = 10.0
```

---

## Live Monitoring

```python
import time

for i in range(50):   # run for ~10 sec
    print(f"axis0 vel: {odrv0.axis0.encoder.vel_estimate:.2f}  "
          f"axis1 vel: {odrv0.axis1.encoder.vel_estimate:.2f}  |  "
          f"ax0 err: {odrv0.axis0.error}  ax1 err: {odrv0.axis1.error}")
    time.sleep(0.2)
```

---

## Error Codes Reference
| Code | Meaning |
|---|---|
| 0 | No error |
| 64 | MOTOR_FAILED |
| 4096 | MOTOR_THERMISTOR_OVER_TEMP |
| 67108864 | MOTOR_THERMISTOR_OVER_TEMP (motor level) |

---

## ROS 2 Odometry Node
- Package: `odrive_odom` under `~/amr_ws/src/`
- Node: `odrive_odom_node.py`
- Publishes: `/odom` (nav_msgs/Odometry) at 50Hz
- Broadcasts: TF `odom → base_link`
- axis0 = LEFT wheel, axis1 = RIGHT wheel
- WHEEL_RADIUS = 0.05 m (update when finalized)
- WHEEL_BASE = 0.40 m (update when finalized)

```bash
# Run odometry node
ros2 run odrive_odom odrive_odom_node

# Monitor odometry
ros2 topic echo /odom
ros2 topic hz /odom
ros2 run tf2_ros tf2_echo odom base_link
```

---

## ROS 2 Odometry Subscriber Node
- Node: `odom_subscriber_node.py`
- Subscribes: `/odom`
- Prints: position (x, y), yaw (degrees), linear and angular velocity

```bash
# Run subscriber node
ros2 run odrive_odom odom_subscriber_node
```

---

## Running Both Nodes Together

### Terminal 1 — Odometry Publisher (connect ODrive first, close odrivetool)
```bash
cd ~/amr_ws
source install/setup.bash
ros2 run odrive_odom odrive_odom_node
```

### Terminal 2 — Odometry Subscriber
```bash
cd ~/amr_ws
source install/setup.bash
ros2 run odrive_odom odom_subscriber_node
```

### Terminal 3 — Extra monitoring (optional)
```bash
ros2 topic echo /odom
ros2 topic echo /odom --field pose.pose.position
ros2 topic echo /odom --field twist.twist
ros2 topic hz /odom
ros2 run tf2_ros tf2_echo odom base_link
```

### Important — ODrive must be free before running nodes
- Close odrivetool completely before running odrive_odom_node
- Only one program can talk to ODrive over USB at a time
- Kill any leftover processes:
```bash
sudo pkill -f odrivetool
sudo pkill -f odrive
```

---

## Joystick Motor Control + Odometry Pipeline

### Overview
Joystick → joy_node → /joy → joy_to_cmd_vel → /cmd_vel → odrive_odom_node → motors + /odom → odom_subscriber_node

### Pre-requisites
- ODrive powered on and in closed loop (state 8) on both axes
- Joystick connected via USB
- odrivetool closed (only one program can use ODrive USB at a time)

### Terminal 1 — Build and Run ODrive Odometry Node
```bash
cd ~/amr_ws
colcon build --symlink-install --packages-select odrive_odom
source install/setup.bash
ros2 run odrive_odom odrive_odom_node
```

### Terminal 2 — Joystick Node
```bash
source ~/amr_ws/install/setup.bash
ros2 run joy joy_node
```

### Terminal 3 — Joy to Cmd Vel
```bash
source ~/amr_ws/install/setup.bash
ros2 run my_amr_description joy_to_cmd_vel
```

### Terminal 4 — Odometry Subscriber
```bash
source ~/amr_ws/install/setup.bash
ros2 run odrive_odom odom_subscriber_node
```

### Joystick Mapping
| Stick | Action |
|---|---|
| Left stick up/down | Forward / Backward |
| Right stick left/right | Turn left / Turn right |

### Notes
- Motors stop automatically when odrive_odom_node is killed (Ctrl+C)
- No rebuild needed for terminals 2, 3, 4 — just source
- If motors dont respond, check ODrive is in state 8 via odrivetool
