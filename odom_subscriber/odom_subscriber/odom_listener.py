import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from nav_msgs.msg import Odometry

class OdomListener(Node):
    def __init__(self):
        super().__init__('odom_listener')

        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        self.subscription = self.create_subscription(
            Odometry,
            '/odom',
            self.odom_callback,
            qos)

        self.get_logger().info('Subscribed to /odom')

    def odom_callback(self, msg):
        import math
        x     = msg.pose.pose.position.x
        y     = msg.pose.pose.position.y
        z_ori = msg.pose.pose.orientation.z
        w_ori = msg.pose.pose.orientation.w
        theta = 2.0 * math.atan2(z_ori, w_ori)

        self.get_logger().info(
            f'X: {x:.3f}  Y: {y:.3f}  Theta: {theta:.3f} rad'
        )

def main(args=None):
    rclpy.init(args=args)
    node = OdomListener()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()



