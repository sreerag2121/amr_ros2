#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from geometry_msgs.msg import Twist

class JoyToCmdVel(Node):
    def __init__(self):
        super().__init__('joy_to_cmd_vel')
        
        # Declare parameters for axes and scales
        self.declare_parameter('axis_linear', 1)  # Left stick up/down
        self.declare_parameter('axis_angular', 3) # Right stick left/right (or 0 for left stick)
        self.declare_parameter('scale_linear', 0.5)
        self.declare_parameter('scale_angular', 1.0)
        
        self.axis_linear = self.get_parameter('axis_linear').value
        self.axis_angular = self.get_parameter('axis_angular').value
        self.scale_linear = self.get_parameter('scale_linear').value
        self.scale_angular = self.get_parameter('scale_angular').value
        
        self.publisher_ = self.create_publisher(Twist, '/cmd_vel', 10)
        self.subscription = self.create_subscription(
            Joy,
            '/joy',
            self.joy_callback,
            10)

    def joy_callback(self, msg):
        twist = Twist()
        
        if self.axis_linear < len(msg.axes):
            twist.linear.x = msg.axes[self.axis_linear] * self.scale_linear
        
        if self.axis_angular < len(msg.axes):
            twist.angular.z = msg.axes[self.axis_angular] * self.scale_angular
            
        self.publisher_.publish(twist)

def main(args=None):
    rclpy.init(args=args)
    node = JoyToCmdVel()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
