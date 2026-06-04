# my_amr_description

A differential drive AMR robot simulation built with ROS 2 Humble and Gazebo Fortress, featuring 2 drive wheels, 4 castor wheels, and a 2D LiDAR. Supports SLAM-based mapping and autonomous navigation with Nav2.

---

## ⚙️ Prerequisites

### 1. Install ROS 2 Humble
Follow the official installation guide:
```
https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debians.html
```

### 2. Install Gazebo Fortress
```bash
sudo apt install ignition-fortress
```

### 3. Add ROS 2 to bashrc
```bash
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

### 4. Create workspace and clone repo
```bash
mkdir -p ~/amr_ws/src
cd ~/amr_ws/src
git clone <your_repo_url>
cd ~/amr_ws
```

### 5. Install dependencies
```bash
rosdep install --from-paths src --ignore-src -r -y
```

### 6. Install additional packages
```bash
sudo apt install ros-humble-slam-toolbox \
                 ros-humble-navigation2 \
                 ros-humble-nav2-bringup \
                 ros-humble-teleop-twist-keyboard \
                 ros-humble-ros-ign-gazebo \
                 ros-humble-ros-ign-bridge \
                 ros-humble-robot-state-publisher \
                 ros-humble-joint-state-publisher-gui \
                 ros-humble-xacro \
                 ros-humble-tf2-tools \
                 ros-humble-ros2topic \
                 ros-humble-ros2action
```

### 7. Build workspace
```bash
cd ~/amr_ws
colcon build
source install/setup.bash
```

> Add workspace to bashrc so it auto-sources on every terminal:
> ```bash
> echo "source ~/amr_ws/install/setup.bash" >> ~/.bashrc
> source ~/.bashrc
> ```

---

## 🤖 Robot Specs

- Chassis: 0.60 x 0.46 x 0.15m
- 2 driven wheels (differential drive)
- 4 castor wheels at corners
- 2D LiDAR on top
- Simulated with Gazebo Fortress (`ign gazebo`)

---

## 🚀 Getting Started

### Step 1 — Launch Gazebo Simulation

```bash
# Terminal 1
source /opt/ros/humble/setup.bash && source ~/amr_ws/install/setup.bash
ros2 launch my_amr_description gazebo.launch.py
```

Wait for Gazebo to fully open and the robot to spawn before proceeding.

---

### Step 2 — Build a Map using SLAM

```bash
# Terminal 2
source /opt/ros/humble/setup.bash && source ~/amr_ws/install/setup.bash
ros2 launch my_amr_description slam.launch.py
```

```bash
# Terminal 3
source /opt/ros/humble/setup.bash && source ~/amr_ws/install/setup.bash
ros2 run rviz2 rviz2 -d ~/amr_ws/src/my_amr_description/rviz/slam_rviz.rviz
```

```bash
# Terminal 4 — drive the robot to explore the environment
source /opt/ros/humble/setup.bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

> In RViz, set **Fixed Frame** to `map`. Drive the robot around using the keyboard until the full environment is mapped.
>
> Teleop keys: `i` = forward, `j` = turn left, `l` = turn right, `k` = stop

---

### Step 3 — Save the Map

Once mapping is complete, run in a new terminal:

```bash
source /opt/ros/humble/setup.bash && source ~/amr_ws/install/setup.bash
ros2 run nav2_map_server map_saver_cli -f ~/amr_ws/src/my_amr_description/maps/my_map
```

This saves:
- `maps/my_map.pgm` — map image
- `maps/my_map.yaml` — map metadata

> Stop SLAM (Terminal 2) and teleop (Terminal 4) after saving.

---

### Step 4 — Autonomous Navigation with Nav2

```bash
# Terminal 2 (restart with Nav2)
source /opt/ros/humble/setup.bash && source ~/amr_ws/install/setup.bash
ros2 launch my_amr_description nav2.launch.py
```

```bash
# Terminal 3 (restart with Nav2 RViz)
source /opt/ros/humble/setup.bash && source ~/amr_ws/install/setup.bash
ros2 run rviz2 rviz2 -d $(ros2 pkg prefix nav2_bringup)/share/nav2_bringup/rviz/nav2_default_view.rviz
```

> In RViz:
> 1. Click **2D Pose Estimate** → click where the robot is on the map → drag to set its direction
> 2. Wait for AMCL to localize (green particles appear around robot)
> 3. Click **Nav2 Goal** → click destination on the map → drag to set orientation
> 4. Robot navigates autonomously 🤖

---

## 🗂 Package Structure

```
my_amr_description/
├── urdf/
│   ├── robot.urdf.xacro        ← top level, includes all
│   ├── inertial_macros.xacro   ← inertia helper macros
│   ├── robot_base.xacro        ← chassis + 4 castor wheels
│   ├── drive_wheels.xacro      ← left/right drive wheels
│   ├── lidar.xacro             ← lidar link + sensor plugin
│   └── gazebo_control.xacro    ← diff drive + joint state plugins
├── launch/
│   ├── display.launch.py       ← RViz only (URDF visualization)
│   ├── gazebo.launch.py        ← Gazebo simulation
│   ├── slam.launch.py          ← SLAM mapping
│   └── nav2.launch.py          ← autonomous navigation
├── config/
│   ├── slam_toolbox_params.yaml
│   └── nav2_params.yaml
├── worlds/
│   └── amr_world.sdf           ← 10x10 room with 4 walls
├── maps/
│   ├── my_map.pgm
│   └── my_map.yaml
└── rviz/
    └── slam_rviz.rviz
```

---

## 📡 Topic Reference

| Topic | Type | Description |
|-------|------|-------------|
| `/cmd_vel` | `geometry_msgs/Twist` | Velocity commands |
| `/odom` | `nav_msgs/Odometry` | Wheel odometry |
| `/scan` | `sensor_msgs/LaserScan` | LiDAR scan data |
| `/map` | `nav_msgs/OccupancyGrid` | Occupancy grid map |
| `/amcl_pose` | `geometry_msgs/PoseStamped` | Robot localization |
| `/tf` | `tf2_msgs/TFMessage` | Transform tree |

---

## 🛠 Built With

- ROS 2 Humble
- Gazebo Fortress (Ignition Gazebo 6)
- slam_toolbox
- Nav2
- Ubuntu 22.04
