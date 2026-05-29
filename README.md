# amr_ros2

# AMR ROS2 Odometry Subscriber

This package subscribes to odometry messages published by the ESP32 over micro-ROS.

## Step 1: Start micro-ROS Agent

Open a terminal and keep it running throughout the session.

```bash
docker run -it --rm --net=host microros/micro-ros-agent:humble udp4 --port 8888 -v6
```
---

## Step 2: Clone Repository

Open a new terminal:

```bash
git clone https://github.com/sreerag2121/amr_ros2.git
```

---

## Step 3: Source ROS2 Workspace

```bash
source ~/ros2_ws/install/setup.bash
```

> **Note:** This assumes the workspace has already been built and the package is available in `~/ros2_ws/install`.

---

## Step 4: Run Subscriber

```bash
ros2 run odom_subscriber odom_listener
```

---

## Verify Communication

List available topics:

```bash
ros2 topic list
```

Check odometry messages:

```bash
ros2 topic echo /odom
```

View topic information:

```bash
ros2 topic info /odom
```

Check publishing frequency:

```bash
ros2 topic hz /odom
```

---
