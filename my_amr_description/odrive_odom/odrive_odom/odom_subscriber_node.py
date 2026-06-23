#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
import math


class OdomSubscriberNode(Node):

    def __init__(self):
        super().__init__('odom_subscriber_node')
        self.subscription = self.create_subscription(
            Odometry,
            '/odom',
            self.odom_callback,
            10
        )
        self.get_logger().info('Listening to /odom ...')

    def odom_callback(self, msg):
        # Position
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y

        # Yaw from quaternion
        qz = msg.pose.pose.orientation.z
        qw = msg.pose.pose.orientation.w
        yaw = math.atan2(2.0 * qw * qz, 1.0 - 2.0 * qz * qz)
        yaw_deg = math.degrees(yaw)

        # Velocity
        lin_vel = msg.twist.twist.linear.x
        ang_vel = msg.twist.twist.angular.z

        print(
            f"POS → x: {x:7.4f} m  y: {y:7.4f} m  yaw: {yaw_deg:7.2f}°  |  "
            f"VEL → linear: {lin_vel:6.3f} m/s  angular: {ang_vel:6.3f} rad/s"
        )


def main(args=None):
    rclpy.init(args=args)
    node = OdomSubscriberNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
