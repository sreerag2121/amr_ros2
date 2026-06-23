#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist, TransformStamped
from tf2_ros import TransformBroadcaster
import math
import odrive

# ─────────────────────────────────────────────
#  CHANGE THESE VALUES WHEN HARDWARE IS FINALIZED
WHEEL_RADIUS  = 0.05   # meters
WHEEL_BASE    = 0.40   # meters — left-to-right wheel center distance
PUBLISH_RATE  = 50.0   # Hz
MAX_VEL       = 70.0   # turns/sec — ODrive vel_limit
# ─────────────────────────────────────────────

class ODriveOdomNode(Node):

    def __init__(self):
        super().__init__('odrive_odom_node')

        # Publishers
        self.odom_pub = self.create_publisher(Odometry, '/odom', 10)
        self.tf_broadcaster = TransformBroadcaster(self)

        # Subscriber — cmd_vel from joy_to_cmd_vel
        self.cmd_vel_sub = self.create_subscription(
            Twist, '/cmd_vel', self.cmd_vel_callback, 10)

        # Robot state
        self.x     = 0.0
        self.y     = 0.0
        self.theta = 0.0

        self.prev_left_turns  = None
        self.prev_right_turns = None

        # Connect to ODrive
        self.get_logger().info('Connecting to ODrive...')
        self.odrv = odrive.find_any()
        self.get_logger().info('ODrive connected!')

        # Timer for odometry at 50Hz
        self.timer = self.create_timer(1.0 / PUBLISH_RATE, self.timer_callback)

    def cmd_vel_callback(self, msg):
        """Convert /cmd_vel Twist → left/right wheel velocities → ODrive"""
        linear  = msg.linear.x   # m/s
        angular = msg.angular.z  # rad/s

        # Differential drive inverse kinematics
        # v_left  = (linear - angular * WHEEL_BASE / 2) / WHEEL_RADIUS  → turns/sec
        # v_right = (linear + angular * WHEEL_BASE / 2) / WHEEL_RADIUS  → turns/sec
        v_left  = (linear - angular * WHEEL_BASE / 2.0) / WHEEL_RADIUS
        v_right = (linear + angular * WHEEL_BASE / 2.0) / WHEEL_RADIUS

        # Clamp to vel_limit
        v_left  = max(-MAX_VEL, min(MAX_VEL, v_left))
        v_right = max(-MAX_VEL, min(MAX_VEL, v_right))

        try:
            # axis0 = LEFT, axis1 = RIGHT
            self.odrv.axis0.controller.input_vel = v_left
            self.odrv.axis1.controller.input_vel = v_right
        except Exception as e:
            self.get_logger().warn(f'ODrive write error: {e}')

    def timer_callback(self):
        try:
            left_turns  = self.odrv.axis0.encoder.pos_estimate
            right_turns = self.odrv.axis1.encoder.pos_estimate
            left_vel    = self.odrv.axis0.encoder.vel_estimate * 2.0 * math.pi * WHEEL_RADIUS
            right_vel   = self.odrv.axis1.encoder.vel_estimate * 2.0 * math.pi * WHEEL_RADIUS
        except Exception as e:
            self.get_logger().warn(f'ODrive read error: {e} — retrying...')
            return

        # First reading — just store
        if self.prev_left_turns is None:
            self.prev_left_turns  = left_turns
            self.prev_right_turns = right_turns
            return

        # Delta turns → delta meters
        delta_left  = (left_turns  - self.prev_left_turns)  * 2.0 * math.pi * WHEEL_RADIUS
        delta_right = (right_turns - self.prev_right_turns) * 2.0 * math.pi * WHEEL_RADIUS

        self.prev_left_turns  = left_turns
        self.prev_right_turns = right_turns

        # Differential drive odometry
        delta_s     = (delta_right + delta_left) / 2.0
        delta_theta = (delta_right - delta_left) / WHEEL_BASE

        self.x     += delta_s * math.cos(self.theta + delta_theta / 2.0)
        self.y     += delta_s * math.sin(self.theta + delta_theta / 2.0)
        self.theta += delta_theta

        lin_vel = (right_vel + left_vel) / 2.0
        ang_vel = (right_vel - left_vel) / WHEEL_BASE

        now = self.get_clock().now().to_msg()

        # ── Publish Odometry ──
        odom_msg = Odometry()
        odom_msg.header.stamp    = now
        odom_msg.header.frame_id = 'odom'
        odom_msg.child_frame_id  = 'base_link'

        odom_msg.pose.pose.position.x = self.x
        odom_msg.pose.pose.position.y = self.y
        odom_msg.pose.pose.position.z = 0.0

        odom_msg.pose.pose.orientation.z = math.sin(self.theta / 2.0)
        odom_msg.pose.pose.orientation.w = math.cos(self.theta / 2.0)

        odom_msg.twist.twist.linear.x  = lin_vel
        odom_msg.twist.twist.angular.z = ang_vel

        self.odom_pub.publish(odom_msg)

        # ── Broadcast TF odom → base_link ──
        tf_msg = TransformStamped()
        tf_msg.header.stamp    = now
        tf_msg.header.frame_id = 'odom'
        tf_msg.child_frame_id  = 'base_link'

        tf_msg.transform.translation.x = self.x
        tf_msg.transform.translation.y = self.y
        tf_msg.transform.translation.z = 0.0

        tf_msg.transform.rotation.z = math.sin(self.theta / 2.0)
        tf_msg.transform.rotation.w = math.cos(self.theta / 2.0)

        self.tf_broadcaster.sendTransform(tf_msg)


def main(args=None):
    rclpy.init(args=args)
    node = ODriveOdomNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Stop motors on shutdown
        try:
            node.odrv.axis0.controller.input_vel = 0.0
            node.odrv.axis1.controller.input_vel = 0.0
        except:
            pass
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
