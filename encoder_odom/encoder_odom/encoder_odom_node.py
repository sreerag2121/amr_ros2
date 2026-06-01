import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from std_msgs.msg import Int32
from nav_msgs.msg import Odometry
import math

class EncoderOdomNode(Node):
    def __init__(self):
        super().__init__('encoder_odom_node')

        # -------------------- PARAMETERS --------------------
        self.TPR         = 1565       # ticks per revolution
        self.WHEEL_RADIUS = 0.05      # meters (10cm diameter / 2)
        self.DIST_PER_TICK = (2 * math.pi * self.WHEEL_RADIUS) / self.TPR

        # -------------------- STATE --------------------
        self.prev_ticks = None
        self.x     = 0.0
        self.y     = 0.0
        self.theta = 0.0  # single wheel = straight line, theta stays 0

        # -------------------- QoS --------------------
        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        # -------------------- SUBSCRIBER --------------------
        self.subscription = self.create_subscription(
            Int32,
            '/encoder_ticks',
            self.tick_callback,
            qos)

        # -------------------- PUBLISHER --------------------
        self.odom_pub = self.create_publisher(Odometry, '/odom', 10)

        self.get_logger().info(
            f'Encoder odom node started | TPR: {self.TPR} | '
            f'Wheel radius: {self.WHEEL_RADIUS}m | '
            f'Dist/tick: {self.DIST_PER_TICK:.6f}m')

    def tick_callback(self, msg):
        current_ticks = msg.data

        # First message — just store, don't compute
        if self.prev_ticks is None:
            self.prev_ticks = current_ticks
            return

        # Delta ticks since last message
        delta_ticks = current_ticks - self.prev_ticks
        self.prev_ticks = current_ticks

        # Distance travelled
        distance = delta_ticks * self.DIST_PER_TICK

        # Update position (single wheel = straight line)
        self.x += distance * math.cos(self.theta)
        self.y += distance * math.sin(self.theta)

        # Publish odometry
        odom = Odometry()
        odom.header.stamp = self.get_clock().now().to_msg()
        odom.header.frame_id = 'odom'
        odom.child_frame_id  = 'base_link'

        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.position.z = 0.0

        odom.pose.pose.orientation.x = 0.0
        odom.pose.pose.orientation.y = 0.0
        odom.pose.pose.orientation.z = math.sin(self.theta / 2.0)
        odom.pose.pose.orientation.w = math.cos(self.theta / 2.0)

        self.odom_pub.publish(odom)

        self.get_logger().info(
            f'Ticks: {current_ticks} | Delta: {delta_ticks} | '
            f'Distance: {distance:.4f}m | X: {self.x:.4f}m')

def main(args=None):
    rclpy.init(args=args)
    node = EncoderOdomNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
