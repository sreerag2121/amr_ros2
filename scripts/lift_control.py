#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
import argparse
import time

class LiftControlNode(Node):
    def __init__(self):
        super().__init__('lift_control_node')
        # Publish to the topic we remapped in the bridge
        self.publisher_ = self.create_publisher(Float64, '/bcr_bot/lift_joint/cmd_pos', 10)

    def publish_command(self, position):
        msg = Float64()
        msg.data = position
        self.publisher_.publish(msg)
        self.get_logger().info(f'Published lift position command: {position} m')

def main(args=None):
    parser = argparse.ArgumentParser(description='Control the BCR Bot lift tray.')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--raise', action='store_true', dest='raise_lift', help='Raise the lift to maximum height')
    group.add_argument('--lower', action='store_true', dest='lower_lift', help='Lower the lift to home position')

    parsed_args = parser.parse_args()

    rclpy.init(args=args)
    node = LiftControlNode()

    target_pos = 0.35 if parsed_args.raise_lift else 0.0

    # Wait for the bridge to connect (ROS 2 discovery)
    print("Waiting for bridge to connect...")
    while node.publisher_.get_subscription_count() == 0:
        time.sleep(0.1)
        rclpy.spin_once(node, timeout_sec=0.1)
        
    print("Connected! Publishing command.")
    node.publish_command(target_pos)
    
    time.sleep(0.2)
    node.destroy_node()
    rclpy.shutdown()
if __name__ == '__main__':
    main()
