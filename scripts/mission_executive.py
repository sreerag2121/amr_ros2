#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from std_msgs.msg import Float64
from sensor_msgs.msg import JointState
from nav_msgs.msg import Odometry
import yaml
import math

class MissionExecutive(Node):
    def __init__(self):
        super().__init__('mission_executive')
        
        self.declare_parameter('zones_file', '')
        yaml_path = self.get_parameter('zones_file').value
        
        self.get_logger().info(f"Loading zones from: {yaml_path}")
        with open(yaml_path, 'r') as f:
            self.zones = yaml.safe_load(f)
            
        self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.lift_pub = self.create_publisher(Float64, '/bcr_bot/lift_joint/cmd_pos', 10)
        
        self.current_x = None
        self.current_y = None
        self.lift_position = None
        
        self.odom_sub = self.create_subscription(
            Odometry, '/bcr_bot/odom', self.odom_callback, 10)
        self.joint_sub = self.create_subscription(
            JointState, '/bcr_bot/joint_states', self.joint_callback, 10)
        
        self.state = 'IDLE'

    def odom_callback(self, msg):
        self.current_x = msg.pose.pose.position.x
        self.current_y = msg.pose.pose.position.y

    def joint_callback(self, msg):
        if 'lift_joint' in msg.name:
            idx = msg.name.index('lift_joint')
            self.lift_position = msg.position[idx]

    def wait_for_odom(self):
        self.get_logger().info("Waiting for odometry...")
        while self.current_x is None:
            rclpy.spin_once(self, timeout_sec=0.1)
        self.get_logger().info(f"Current position: x={self.current_x:.3f}, y={self.current_y:.3f}")

    def set_lift(self, target_position, tolerance=0.02):
        msg = Float64()
        msg.data = target_position
        self.lift_pub.publish(msg)
        self.get_logger().info(f"Lift commanded to {target_position}m. Waiting for joint to reach target...")

        timeout = 10.0
        start = self.get_clock().now().nanoseconds / 1e9

        while True:
            rclpy.spin_once(self, timeout_sec=0.1)
            if self.lift_position is not None:
                error = abs(self.lift_position - target_position)
                self.get_logger().info(f"Lift: {self.lift_position:.4f} → target: {target_position} | error: {error:.4f}")
                if error < tolerance:
                    self.get_logger().info("Lift reached target.")
                    break
            elapsed = self.get_clock().now().nanoseconds / 1e9 - start
            if elapsed > timeout:
                self.get_logger().warn("Lift timeout — proceeding anyway.")
                break

    def go_to_pose(self, zone_name):
        zone = self.zones[zone_name]
        target_x = float(zone['x'])
        target_y = float(zone['y'])

        self.wait_for_odom()
        dist = math.sqrt((target_x - self.current_x)**2 + (target_y - self.current_y)**2)
        self.get_logger().info(f"Distance to {zone_name}: {dist:.3f}m")

        if dist < 0.1:
            self.get_logger().warn(f"Already within 0.1m of {zone_name} — skipping navigation!")
            return True

        self.get_logger().info(f"Routing to {zone_name} -> x:{target_x}, y:{target_y}")

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = target_x
        goal_msg.pose.pose.position.y = target_y
        goal_msg.pose.pose.position.z = float(zone.get('z', 0.0))
        goal_msg.pose.pose.orientation.x = float(zone['qx'])
        goal_msg.pose.pose.orientation.y = float(zone['qy'])
        goal_msg.pose.pose.orientation.z = float(zone['qz'])
        goal_msg.pose.pose.orientation.w = float(zone['qw'])

        self.get_logger().info("Waiting for Nav2 action server...")
        self.nav_client.wait_for_server()

        send_goal_future = self.nav_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, send_goal_future)
        goal_handle = send_goal_future.result()

        if not goal_handle.accepted:
            self.get_logger().error("Nav2 rejected the goal!")
            return False

        self.get_logger().info("Goal accepted. Robot is driving...")
        result_future = goal_handle.get_result_async()

        while not result_future.done():
            rclpy.spin_once(self, timeout_sec=0.5)
            if self.current_x is not None:
                remaining = math.sqrt((target_x - self.current_x)**2 + (target_y - self.current_y)**2)
                self.get_logger().info(f"Distance remaining: {remaining:.3f}m")

        self.get_logger().info(f"Arrived at {zone_name}! Final pos: x={self.current_x:.3f}, y={self.current_y:.3f}")
        return True

def main(args=None):
    rclpy.init(args=args)
    node = MissionExecutive()

    try:
        node.state = 'NAVIGATING_TO_PICKUP'
        node.get_logger().info(f"--- STATE: {node.state} ---")
        if node.go_to_pose('pickup_zone'):

            node.state = 'RAISING_LIFT'
            node.get_logger().info(f"--- STATE: {node.state} ---")
            node.set_lift(0.35)

            node.state = 'NAVIGATING_TO_STORAGE'
            node.get_logger().info(f"--- STATE: {node.state} ---")
            node.go_to_pose('storage_zone')

            node.state = 'LOWERING_LIFT'
            node.get_logger().info(f"--- STATE: {node.state} ---")
            node.set_lift(0.0)

            node.state = 'IDLE'
            node.get_logger().info(f"--- STATE: {node.state}. Mission Complete! ---")

    except KeyboardInterrupt:
        node.get_logger().info("Mission aborted by user.")

    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()