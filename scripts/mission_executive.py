#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from nav2_msgs.srv import ClearEntireCostmap
from std_msgs.msg import Float64
from sensor_msgs.msg import JointState
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Polygon, Point32
import yaml
import math
import subprocess
import time

class MissionExecutive(Node):
    def __init__(self):
        super().__init__('mission_executive')

        self.declare_parameter('zones_file', '')
        yaml_path = self.get_parameter('zones_file').value
        self.get_logger().info(f"Loading zones from: {yaml_path}")
        with open(yaml_path, 'r') as f:
            self.zones = yaml.safe_load(f)

        self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.lift_pub = self.create_publisher(
            Float64, '/bcr_bot/lift_joint/cmd_pos', 10)
        self.global_footprint_pub = self.create_publisher(
            Polygon, '/global_costmap/footprint', 10)
        self.local_footprint_pub = self.create_publisher(
            Polygon, '/local_costmap/footprint', 10)

        self.current_x = None
        self.current_y = None
        self.current_yaw = None
        self.lift_position = None

        self.odom_sub = self.create_subscription(
            Odometry, '/bcr_bot/odom', self.odom_callback, 10)
        self.joint_sub = self.create_subscription(
            JointState, '/bcr_bot/joint_states', self.joint_callback, 10)

        self.state = 'IDLE'

        # Footprint definitions
        self.footprint_robot = [
            ( 0.450,  0.000), ( 0.318,  0.318), ( 0.000,  0.450),
            (-0.318,  0.318), (-0.450,  0.000), (-0.318, -0.318),
            ( 0.000, -0.450), ( 0.318, -0.318)
        ]
        # Full assembly: pillar outer edge 0.925m + 0.10m margin
        self.footprint_loaded = [
            ( 0.550,  1.025),
            ( 0.550, -1.025),
            (-0.550, -1.025),
            (-0.550,  1.025)
        ]

    def odom_callback(self, msg):
        self.current_x = msg.pose.pose.position.x
        self.current_y = msg.pose.pose.position.y
        q = msg.pose.pose.orientation
        self.current_yaw = math.atan2(2*(q.w*q.z + q.x*q.y), 1 - 2*(q.y*q.y + q.z*q.z))

    def joint_callback(self, msg):
        if 'lift_joint' in msg.name:
            idx = msg.name.index('lift_joint')
            self.lift_position = msg.position[idx]

    def wait_for_odom(self):
        self.get_logger().info("Waiting for odometry...")
        while self.current_x is None:
            rclpy.spin_once(self, timeout_sec=0.1)
        self.get_logger().info(
            f"Position: x={self.current_x:.3f}, y={self.current_y:.3f}")

    def set_costmap_params(self, inflation_radius):
        """Update inflation radius on both costmaps."""
        for node_name in [
            '/global_costmap/global_costmap',
            '/local_costmap/local_costmap'
        ]:
            subprocess.run([
                'ros2', 'param', 'set', node_name,
                'inflation_layer.inflation_radius', str(inflation_radius)
            ], check=False, capture_output=True)

        self.get_logger().info(f"Costmap params: inflation={inflation_radius}m")

    def normalize_angle(self, angle):
        while angle > math.pi:
            angle -= 2 * math.pi
        while angle < -math.pi:
            angle += 2 * math.pi
        return angle

    def pick_equivalent_yaw(self, target_qz, target_qw):
        target_yaw = 2 * math.atan2(target_qz, target_qw)
        alt_yaw = self.normalize_angle(target_yaw + math.pi)

        current_yaw = self.current_yaw
        diff_target = abs(self.normalize_angle(target_yaw - current_yaw))
        diff_alt = abs(self.normalize_angle(alt_yaw - current_yaw))

        chosen_yaw = target_yaw if diff_target <= diff_alt else alt_yaw
        qz = math.sin(chosen_yaw / 2)
        qw = math.cos(chosen_yaw / 2)
        return qz, qw

    def set_footprint(self, footprint_points, inflation_radius):
        """Switch footprint and inflation — then clear costmaps."""
        polygon = Polygon()
        for x, y in footprint_points:
            pt = Point32()
            pt.x = float(x)
            pt.y = float(y)
            pt.z = 0.0
            polygon.points.append(pt)

        self.global_footprint_pub.publish(polygon)
        self.local_footprint_pub.publish(polygon)

        self.set_costmap_params(inflation_radius)

        # Clear costmaps to rebuild with new params
        for srv_name in [
            '/global_costmap/clear_entirely_global_costmap',
            '/local_costmap/clear_entirely_local_costmap'
        ]:
            client = self.create_client(ClearEntireCostmap, srv_name)
            if client.wait_for_service(timeout_sec=2.0):
                future = client.call_async(ClearEntireCostmap.Request())
                rclpy.spin_until_future_complete(self, future, timeout_sec=3.0)
            else:
                self.get_logger().warn(f"Clear service unavailable: {srv_name}")

        width = 2 * max(abs(p[1]) for p in footprint_points)
        self.get_logger().info(
            f"Footprint: width={width:.2f}m | inflation={inflation_radius}m")
        time.sleep(1.0)

    def set_lift(self, target_position, tolerance=0.02):
        msg = Float64()
        msg.data = target_position
        self.lift_pub.publish(msg)
        self.get_logger().info(f"Lift → {target_position}m")

        timeout = 10.0
        start = self.get_clock().now().nanoseconds / 1e9
        while True:
            rclpy.spin_once(self, timeout_sec=0.1)
            if self.lift_position is not None:
                error = abs(self.lift_position - target_position)
                self.get_logger().info(
                    f"Lift: {self.lift_position:.4f} | "
                    f"target: {target_position} | error: {error:.4f}")
                if error < tolerance:
                    self.get_logger().info("Lift reached target.")
                    break
            if self.get_clock().now().nanoseconds / 1e9 - start > timeout:
                self.get_logger().warn("Lift timeout — proceeding anyway.")
                break

    def go_to_pose(self, zone_name):
        zone = self.zones[zone_name]
        target_x = float(zone['x'])
        target_y = float(zone['y'])

        self.wait_for_odom()
        dist = math.sqrt(
            (target_x - self.current_x)**2 +
            (target_y - self.current_y)**2)
        self.get_logger().info(f"Distance to {zone_name}: {dist:.3f}m")

        if dist < 0.1:
            self.get_logger().warn(f"Already at {zone_name} — skipping.")
            return True

        self.get_logger().info(
            f"Navigating to {zone_name}: x={target_x:.3f}, y={target_y:.3f}")

        qz, qw = self.pick_equivalent_yaw(float(zone['qz']), float(zone['qw']))

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = target_x
        goal_msg.pose.pose.position.y = target_y
        goal_msg.pose.pose.position.z = float(zone.get('z', 0.0))
        goal_msg.pose.pose.orientation.x = float(zone['qx'])
        goal_msg.pose.pose.orientation.y = float(zone['qy'])
        goal_msg.pose.pose.orientation.z = qz
        goal_msg.pose.pose.orientation.w = qw

        self.nav_client.wait_for_server()
        send_goal_future = self.nav_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, send_goal_future)
        goal_handle = send_goal_future.result()

        if not goal_handle.accepted:
            self.get_logger().error("Goal rejected by Nav2!")
            return False

        result_future = goal_handle.get_result_async()
        while not result_future.done():
            rclpy.spin_once(self, timeout_sec=0.5)
            if self.current_x is not None:
                remaining = math.sqrt(
                    (target_x - self.current_x)**2 +
                    (target_y - self.current_y)**2)
                self.get_logger().info(f"Remaining: {remaining:.3f}m")

        self.get_logger().info(
            f"Arrived at {zone_name}: "
            f"x={self.current_x:.3f}, y={self.current_y:.3f}")
        return True


def main(args=None):
    rclpy.init(args=args)
    node = MissionExecutive()

    try:
        # ── PICKUP: unloaded robot, normal config ────────────────────────
        node.state = 'NAVIGATING_TO_PICKUP'
        node.get_logger().info(f"--- STATE: {node.state} ---")
    
        if not node.go_to_pose('pickup_zone'):
            raise RuntimeError("Failed to reach pickup zone")

        # ── RAISE LIFT — assembly lifts off pickup pillars ───────────────
        node.state = 'RAISING_LIFT'
        node.get_logger().info(f"--- STATE: {node.state} ---")
        node.set_lift(0.40)

        # ── ESCAPE: move to open space, still normal config ──────────────
        node.state = 'ESCAPING_PICKUP'
        node.get_logger().info(f"--- STATE: {node.state} ---")
        if not node.go_to_pose('pickup_escape'):
            raise RuntimeError("Failed to escape pickup zone")

        # ── SWITCH TO LOADED CONFIG — safe now, robot in open space ──────
        node.get_logger().info("Switching to loaded configuration...")
        node.set_footprint(node.footprint_loaded, inflation_radius=0.75)

        # ── TRANSIT: navigate to storage zone, loaded config ─────────────
        node.state = 'NAVIGATING_TO_STORAGE'
        node.get_logger().info(f"--- STATE: {node.state} ---")
        if not node.go_to_pose('storage_zone'):
            raise RuntimeError("Failed to reach storage zone")

        # ── DEPOSIT: lower tray, assembly rests on storage pillars ───────
        node.state = 'DEPOSITING'
        node.get_logger().info(f"--- STATE: {node.state} ---")
        node.set_lift(0.0)
        node.get_logger().info("Assembly deposited.")

        # ── SWITCH BACK TO UNLOADED CONFIG ────────────────────────────────
        node.get_logger().info("Switching to unloaded configuration...")
        node.set_footprint(node.footprint_robot, inflation_radius=0.5)

        # ── RETREAT: back to parking zone ─────────────────────────────────
        node.state = 'RETREATING_TO_PARKING'
        node.get_logger().info(f"--- STATE: {node.state} ---")
        node.go_to_pose('parking_zone')

        # ── DONE ─────────────────────────────────────────────────────────
        node.state = 'IDLE'
        node.get_logger().info(f"--- STATE: {node.state}. Mission Complete! ---")

    except KeyboardInterrupt:
        node.get_logger().info("Mission aborted.")
    except RuntimeError as e:
        node.get_logger().error(f"Mission failed: {e}")

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()