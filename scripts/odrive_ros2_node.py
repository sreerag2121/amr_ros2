#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from tf2_ros import TransformBroadcaster
from geometry_msgs.msg import TransformStamped

import serial
import math
import time
import threading

# ── Robot parameters ── tune these to your hardware ──────────────────────────
WHEEL_RADIUS  = 0.05    # metres
WHEEL_BASE    = 0.30    # metres (centre-to-centre)
ENCODER_CPR   = 4096     # counts per revolution (ODrive axis0.encoder.config.cpr)
SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE     = 115200
CMD_TIMEOUT   = 0.5         # seconds — stop motors if no cmd_vel received
ODOM_RATE     = 50.0    # Hz
# ─────────────────────────────────────────────────────────────────────────────


class ODriveNode(Node):

    def __init__(self):
        super().__init__('odrive_ros2_node')

        # Serial
        self.ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
        time.sleep(0.5)
        self.get_logger().info(f'ODrive connected on {SERIAL_PORT}')

        # State
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.last_pos_l = None
        self.last_pos_r = None
        self.last_cmd_time = self.get_clock().now()
        self.lock = threading.Lock()

        # Publishers / subscribers
        self.odom_pub = self.create_publisher(Odometry, '/odom', 10)
        self.tf_broadcaster = TransformBroadcaster(self)
        self.cmd_sub = self.create_subscription(
            Twist, '/cmd_vel', self.cmd_vel_callback, 10)

        # Timers
        self.create_timer(1.0 / ODOM_RATE, self.odom_loop)
        self.create_timer(0.1, self.watchdog)

        self.get_logger().info('ODrive ROS 2 node ready')

    # ── ODrive serial helpers ─────────────────────────────────────────────────

    def odrive_write(self, cmd: str):
        self.ser.write((cmd + '\n').encode())

    def odrive_read_float(self, cmd: str) -> float:
        with self.lock:
            self.ser.reset_input_buffer()
            self.ser.write((cmd + '\n').encode())
            resp = self.ser.readline().decode().strip()
        try:
            return float(resp)
        except ValueError:
            self.get_logger().warn(f'Bad ODrive response to "{cmd}": "{resp}"')
            return 0.0

    def set_motor_velocity(self, axis: int, vel_turns_s: float):
        # v f axis vel   (ODrive ASCII velocity command)
        with self.lock:
            self.odrive_write(f'v {axis} {vel_turns_s:.4f}')

    # ── /cmd_vel callback ─────────────────────────────────────────────────────

    def cmd_vel_callback(self, msg: Twist):
        self.last_cmd_time = self.get_clock().now()

        v = msg.linear.x    # m/s
        w = msg.angular.z   # rad/s

        # Differential drive: wheel velocities in m/s
        v_l = v - (w * WHEEL_BASE / 2.0)
        v_r = v + (w * WHEEL_BASE / 2.0)

        # Convert m/s → turns/s
        turns_l = v_l / (2.0 * math.pi * WHEEL_RADIUS)
        turns_r = v_r / (2.0 * math.pi * WHEEL_RADIUS)

        # axis0 = left, axis1 = right
        # Negate axis1 if motors are mirrored (flip sign if robot spins wrong way)
        self.set_motor_velocity(0,  turns_l)
        self.set_motor_velocity(1, -turns_r)

    # ── Odometry loop ─────────────────────────────────────────────────────────

    def odom_loop(self):
        # Read encoder positions (turns, continuous)
        pos_l =  self.odrive_read_float('r axis0.encoder.pos_estimate')
        pos_r = -self.odrive_read_float('r axis1.encoder.pos_estimate')

        # Read velocities for twist field
        vel_l =  self.odrive_read_float('r axis0.encoder.vel_estimate')
        vel_r = -self.odrive_read_float('r axis1.encoder.vel_estimate')

        if self.last_pos_l is None:
            self.last_pos_l = pos_l
            self.last_pos_r = pos_r
            return

        # Delta turns → metres
        d_l = (pos_l - self.last_pos_l) * 2.0 * math.pi * WHEEL_RADIUS
        d_r = (pos_r - self.last_pos_r) * 2.0 * math.pi * WHEEL_RADIUS
        self.last_pos_l = pos_l
        self.last_pos_r = pos_r

        # RK2 integration
        d_center = (d_r + d_l) / 2.0
        d_theta  = (d_r - d_l) / WHEEL_BASE
        self.x     += d_center * math.cos(self.theta + d_theta / 2.0)
        self.y     += d_center * math.sin(self.theta + d_theta / 2.0)
        self.theta += d_theta

        # Twist (body frame)
        v_l_ms = vel_l * 2.0 * math.pi * WHEEL_RADIUS
        v_r_ms = vel_r * 2.0 * math.pi * WHEEL_RADIUS
        vx  = (v_r_ms + v_l_ms) / 2.0
        wz  = (v_r_ms - v_l_ms) / WHEEL_BASE

        now = self.get_clock().now().to_msg()

        # Publish /odom
        odom = Odometry()
        odom.header.stamp    = now
        odom.header.frame_id = 'odom'
        odom.child_frame_id  = 'base_footprint'

        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.orientation.z = math.sin(self.theta / 2.0)
        odom.pose.pose.orientation.w = math.cos(self.theta / 2.0)

        odom.twist.twist.linear.x  = vx
        odom.twist.twist.angular.z = wz

        self.odom_pub.publish(odom)

        # Broadcast odom → base_footprint TF
        tf = TransformStamped()
        tf.header.stamp    = now
        tf.header.frame_id = 'odom'
        tf.child_frame_id  = 'base_footprint'
        tf.transform.translation.x = self.x
        tf.transform.translation.y = self.y
        tf.transform.rotation.z    = math.sin(self.theta / 2.0)
        tf.transform.rotation.w    = math.cos(self.theta / 2.0)
        self.tf_broadcaster.sendTransform(tf)

    # ── Watchdog — stop if no cmd_vel ────────────────────────────────────────

    def watchdog(self):
        dt = (self.get_clock().now() - self.last_cmd_time).nanoseconds / 1e9
        if dt > CMD_TIMEOUT:
            self.set_motor_velocity(0, 0.0)
            self.set_motor_velocity(1, 0.0)

    def destroy_node(self):
        self.set_motor_velocity(0, 0.0)
        self.set_motor_velocity(1, 0.0)
        self.ser.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ODriveNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()