
## About

This repository contains a [Gazebo](https://gazebosim.org/home) and [Isaac Sim](https://developer.nvidia.com/isaac/sim) simulation for a differential drive robot, equipped with an IMU, a depth camera, stereo camera and a 2D LiDAR. ROS2 versions also include [Nav2](https://docs.nav2.org/) and [SLAM Tool Box](https://github.com/SteveMacenski/slam_toolbox) support. Currently, the project supports the following combinations - 

1. [ROS Noetic + Gazebo Classic 11 (branch ros1)](https://github.com/blackcoffeerobotics/bcr_bot/tree/ros1?tab=readme-ov-file#noetic--classic-ubuntu-2004)
2. [ROS2 Humble + Gazebo Classic 11 (branch ros2)](https://github.com/blackcoffeerobotics/bcr_bot/tree/ros2?tab=readme-ov-file#humble--classic-ubuntu-2204)
3. [ROS2 Humble + Gazebo Fortress (branch ros2)](https://github.com/blackcoffeerobotics/bcr_bot/tree/ros2?tab=readme-ov-file#humble--fortress-ubuntu-2204)
4. [ROS2 Humble + Gazebo Harmonic (branch ros2)](https://github.com/blackcoffeerobotics/bcr_bot/tree/ros2?tab=readme-ov-file#humble--harmonic-ubuntu-2204)
5. [ROS2 Humble + Isaac Sim (branch ros2)](https://github.com/blackcoffeerobotics/bcr_bot/tree/ros2?tab=readme-ov-file#humble--isaac-sim-ubuntu-2204)
6. [ROS2 Jazzy + Gazebo Harmonic (branch ros2-jazzy)](https://github.com/blackcoffeerobotics/bcr_bot/tree/ros2-jazzy?tab=readme-ov-file#jazzy--harmonic-ubuntu-2404)
7. [ROS2 Jazzy + Isaac Sim (branch ros2-jazzy)](https://github.com/blackcoffeerobotics/bcr_bot/tree/ros2-jazzy?tab=readme-ov-file#jazzy--isaac-sim-ubuntu-2404)

Each of the following sections describes depedencies, build and run instructions for the combinations supported by the `ros2-jazzy` branch.

## Jazzy + Harmonic (Ubuntu 24.04)

### Dependencies

Install Gazebo harmonic using ROS2 binaries:
```bash
sudo apt install ros-jazzy-ros-gz-sim ros-jazzy-ros-gz-bridge ros-jazzy-ros-gz-interfaces
```

Install other dependencies with [rosdep](http://wiki.ros.org/rosdep).
```bash
# From the root directory of the workspace. This will install everything mentioned in package.xml
rosdep install --from-paths src --ignore-src -r -y
```

### Build

```bash
colcon build --packages-select bcr_bot
```

### Run

To launch the robot in Gazebo,
```bash
ros2 launch bcr_bot gz.launch.py
```
To view in rviz,
```bash
ros2 launch bcr_bot rviz.launch.py
```

### Configuration

The launch file accepts multiple launch arguments,
```bash
ros2 launch bcr_bot gz.launch.py \
	camera_enabled:=True \
	stereo_camera_enabled:=False \
	two_d_lidar_enabled:=True \
	position_x:=0.0 \
	position_y:=0.0  \
	orientation_yaw:=0.0 \
	odometry_source:=world \
	world_file:=small_warehouse.sdf
```
<!-- **Note:** 
1. To use stereo_image_proc with the stereo images excute following command: 
```bash
ros2 launch stereo_image_proc stereo_image_proc.launch.py left_namespace:=bcr_bot/stereo_camera/left right_namespace:=bcr_bot/stereo_camera/right
``` -->

### Jazzy + Isaac Sim (Ubuntu 24.04)

### Dependencies

In addition to ROS2 Humble [Isaac Sim installation](https://docs.omniverse.nvidia.com/isaacsim/latest/installation/index.html) with ROS2 extension is required. Remainder of bcr_bot specific dependencies can be installed with [rosdep](http://wiki.ros.org/rosdep)

```bash
# From the root directory of the workspace. This will install everything mentioned in package.xml
rosdep install --from-paths src --ignore-src -r -y
```

### Build

```bash
colcon build --packages-select bcr_bot
```

### Run

To launch the robot in Isaac Sim:
- Open Isaac Sim and load the `warehouse_scene.usd` or `scene.usd` from [here](usd). 
- Add in extra viewports for different camera views.
- Start the Simulation: Run the simulation directly within Isaac Sim.
- The following USDs are included in the package:
	- `warehouse_scene.usd` - Warehouse scene with a robot.
	- `scene.usd` - Scene with a robot in a empty world.
	- `bcr_bot.usd` - Robot model that can be imported into any scene.
	- `ActionGraphFull.usd` - Action graph for the robot to publish all the required topics.

To view in rviz:
```bash
ros2 launch bcr_bot rviz.launch.py
```
NOTE: The command to run mapping and navigation is common between all versions of gazebo and Isaac sim see [here](#mapping-with-slam-toolbox).

### Mapping with SLAM Toolbox

SLAM Toolbox is an open-source package designed to map the environment using laser scans and odometry, generating a map for autonomous navigation.

NOTE: The command to run mapping is common between all versions of gazebo.

To start mapping:
```bash
ros2 launch bcr_bot mapping.launch.py
```

Use the teleop twist keyboard to control the robot and map the area:
```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard cmd_vel:=/bcr_bot/cmd_vel
```

To save the map:
```bash
cd src/bcr_bot/config
ros2 run nav2_map_server map_saver_cli -f bcr_map
```

### Using Nav2 with bcr_bot

Nav2 is an open-source navigation package that enables a robot to navigate through an environment easily. It takes laser scan and odometry data, along with the map of the environment, as inputs.

NOTE: The command to run navigation is common between all versions of gazebo and Isaac sim.

To run Nav2 on bcr_bot:
```bash
ros2 launch bcr_bot nav2.launch.py
```

### Launch Sequence 

push from inside bcr_bot folder and push to a new branch (git checkout -b amr-simulation-bcr)

for users to setup, following bcr installation instruction is necessary
================================================================
BCR BOT - SLAM MAPPING FULL LAUNCH SEQUENCE
================================================================

----------------------------------------------------------------
ONE TIME SETUP - Add ROS sourcing to .bashrc
----------------------------------------------------------------

nano ~/.bashrc

Add these two lines at the bottom of the file:
    source /opt/ros/jazzy/setup.bash
    source ~/ros2_ws/install/setup.bash

Save: Ctrl+O → Enter → Ctrl+X

Apply immediately:
    source ~/.bashrc

Verify (open new terminal and run):
    echo $ROS_DISTRO
    Expected output: jazzy

----------------------------------------------------------------
PRE-FLIGHT - Run once before every mapping session // Prolly Wont Be necessary
----------------------------------------------------------------

    rm -f ~/.ros/*.posegraph ~/.ros/*.data
    mkdir -p ~/maps

----------------------------------------------------------------
TERMINAL 1 - Gazebo
----------------------------------------------------------------

    ros2 launch bcr_bot gz.launch.py \
      two_d_lidar_enabled:=true \
      world_file:=/home/dilshad/ros2_ws/install/bcr_bot/share/bcr_bot/worlds/small_warehouse.sdf

    WAIT until Gazebo window fully opens and robot is visible.

----------------------------------------------------------------
TERMINAL 2 - SLAM Toolbox
----------------------------------------------------------------

    ros2 launch slam_toolbox online_async_launch.py \
      use_sim_time:=true \
      slam_params_file:=$HOME/my_slam_toolbox_params.yaml

    WAIT until no errors appear in terminal.

    Verify SLAM is receiving laser (new terminal):
        ros2 topic info /scan
        Subscription count should be: 1

----------------------------------------------------------------
TERMINAL 3 - RViz (just running rviz2 also works but then u have to manually add the TF, RobotModel,LaserScan,Map,Odometry etc..
----------------------------------------------------------------

    rviz2 -d ~/bcr_bot_slam.rviz /

    Confirm before driving:
        - Fixed Frame = map 
        - Map starts GREY (not fully drawn)
        - LaserScan dots visible around robot
        - Robot model visible

    WARNING: If map appears fully drawn instantly,
    a pose graph was reloaded. Stop and run:
        rm -f ~/.ros/*.posegraph ~/.ros/*.data
    Then restart SLAM and RViz.

----------------------------------------------------------------
TERMINAL 4 - Teleop
----------------------------------------------------------------

    ros2 run teleop_twist_keyboard teleop_twist_keyboard \
      --ros-args --remap cmd_vel:=/bcr_bot/cmd_vel


__________________Running NAV 2_______________________

ros2 launch bcr_bot nav2.launch.py use_sim_time:=true

___Edit NAV2 Parameters___

nano ~/ros2_ws/src/bcr_bot/config/nav2_params.yaml

----------------------------------------------------------------
TERMINAL 5 - Save Map (Before closing anything)
----------------------------------------------------------------

    Save for Nav2:
        ros2 run nav2_map_server map_saver_cli \
          -f ~/maps/warehouse_map \
          --ros-args -p use_sim_time:=true

    Save SLAM pose graph:
        ros2 service call /slam_toolbox/save_map slam_toolbox/srv/SaveMap \
          "name: {data: '/home/dilshad/maps/warehouse_map'}"

    View map in WSL:
        eog ~/maps/warehouse_map.pgm

    Verify files saved:
        ls -lh ~/maps/

    Expected files:
        warehouse_map.pgm
        warehouse_map.yaml
        warehouse_map.posegraph
        warehouse_map.data

    Export to Windows Desktop (optional):
        cp ~/maps/warehouse_map.pgm /mnt/c/Users/Dilshad/Desktop/
        cp ~/maps/warehouse_map.yaml /mnt/c/Users/Dilshad/Desktop/



____________After Making changes build the project____
cd ~/ros2_ws
colcon build --packages-select bcr_bot --symlink-install
source install/setup.bash




----------------------------------------------------------------
THINGS TO BE CAREFUL ABOUT
----------------------------------------------------------------
    6. If Gazebo window does not open, check:
           echo $DISPLAY
           echo $WAYLAND_DISPLAY

================================================================
QUICK REFERENCE CHEAT SHEET
================================================================

    Gazebo:
        ros2 launch bcr_bot gz.launch.py two_d_lidar_enabled:=true world_file:=/home/dilshad/ros2_ws/install/bcr_bot/share/bcr_bot/worlds/small_warehouse.sdf

    SLAM:
        ros2 launch slam_toolbox online_async_launch.py use_sim_time:=true slam_params_file:=$HOME/my_slam_toolbox_params.yaml

    RViz:
        rviz2 -d ~/bcr_bot_slam.rviz

    Teleop:
        ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args --remap cmd_vel:=/bcr_bot/cmd_vel

    Save Map:
        ros2 run nav2_map_server map_saver_cli -f ~/maps/warehouse_map --ros-args -p use_sim_time:=true

================================================================
