#!/usr/bin/env python3
"""
Warehouse Delivery — Pick up cart_1, deliver to dock_1, return home.

Uses RELATIVE ODOM DISTANCE for blind drives (immune to AMCL offset).
Nav2 handles long-range navigation, odom handles precision short drives.
"""

import time, math, rclpy
from geometry_msgs.msg import PoseStamped, Twist
from std_msgs.msg import Float64
from nav_msgs.msg import Odometry
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult

import tf2_ros
from tf2_ros import Buffer, TransformListener

# ── Odom state (for relative distance measurement) ──
ox = oy = oyaw = 0.0
# ── Map state (for TF-based absolute position) ──
mx = my = myaw = 0.0
tf_buffer = None


def _q2yaw(x, y, z, w):
    return math.atan2(2*(w*z + x*y), 1 - 2*(y*y + z*z))

def _norm(a):
    while a > math.pi:  a -= 2*math.pi
    while a < -math.pi: a += 2*math.pi
    return a

def _odom_cb(msg):
    global ox, oy, oyaw
    ox = msg.pose.pose.position.x
    oy = msg.pose.pose.position.y
    q = msg.pose.pose.orientation
    oyaw = _q2yaw(q.x, q.y, q.z, q.w)

def update_map_pose(node):
    global mx, my, myaw, tf_buffer
    try:
        t = tf_buffer.lookup_transform('map', 'base_footprint', rclpy.time.Time())
        mx = t.transform.translation.x
        my = t.transform.translation.y
        q = t.transform.rotation
        myaw = _q2yaw(q.x, q.y, q.z, q.w)
    except Exception:
        pass


# ── Motion primitives using RELATIVE ODOM DISTANCE ──

def rotate_to_map(node, pub, goal, tol=0.03):
    """Rotate in place using MAP frame heading."""
    tw = Twist()
    node.get_logger().info(f"  ROTATE → {math.degrees(goal):.0f}°")
    for _ in range(3000):
        rclpy.spin_once(node, timeout_sec=0.05)
        update_map_pose(node)
        e = _norm(goal - myaw)
        if abs(e) < tol: break
        tw.angular.z = max(min(2.0*e, 0.4), -0.4)
        pub.publish(tw)
    tw.angular.z = 0.0; pub.publish(tw)
    time.sleep(0.5)
    node.get_logger().info(f"  Done. yaw={math.degrees(myaw):.1f}°")


def align_y_map(node, pub, target_y, tol=0.02):
    """Correct Nav2's XY tolerance error by explicitly aligning Y."""
    update_map_pose(node)
    y_err = target_y - my
    if abs(y_err) <= tol:
        return
        
    node.get_logger().info(f"  ALIGN Y → {target_y:.2f} (current {my:.2f}, err {y_err:.2f})")
    heading = math.pi/2 if y_err > 0 else -math.pi/2
    rotate_to_map(node, pub, heading)
    
    tw = Twist(); tw.linear.x = 0.1
    for _ in range(2000):
        rclpy.spin_once(node, timeout_sec=0.05)
        update_map_pose(node)
        if (y_err > 0 and my >= target_y) or (y_err < 0 and my <= target_y):
            break
        pub.publish(tw)
    tw.linear.x = 0.0; tw.angular.z = 0.0; pub.publish(tw)
    time.sleep(0.5)


def drive_forward_distance(node, pub, distance, heading, speed=0.12):
    """
    Drive FORWARD exactly `distance` meters, measured by odom.
    Uses odom heading for lane-keeping (keeps driving straight).
    """
    tw = Twist(); tw.linear.x = abs(speed)
    
    # Snapshot current odom position
    # Flush odom to current position (critical!)
    for _ in range(30):
        rclpy.spin_once(node, timeout_sec=0.05)
    start_ox, start_oy = ox, oy
    start_yaw = oyaw
    
    node.get_logger().info(
        f"  FWD {distance:.2f}m from odom ({start_ox:.2f}, {start_oy:.2f})")
    
    while rclpy.ok():
        rclpy.spin_once(node, timeout_sec=0.05)
        # Distance traveled (odom frame, always accurate for short drives)
        dx = ox - start_ox
        dy = oy - start_oy
        traveled = math.sqrt(dx*dx + dy*dy)
        
        if traveled >= distance:
            break
        
        # Keep heading straight using odom yaw
        yaw_err = _norm(start_yaw - oyaw)
        tw.angular.z = 2.0 * yaw_err
        pub.publish(tw)
    
    tw.linear.x = 0.0; tw.angular.z = 0.0; pub.publish(tw)
    time.sleep(0.5)
    update_map_pose(node)
    node.get_logger().info(
        f"  Stopped. Traveled {traveled:.2f}m. Map pos: ({mx:.2f}, {my:.2f})")


def drive_backward_distance(node, pub, distance, heading, speed=0.12):
    """
    Drive BACKWARD exactly `distance` meters, measured by odom.
    """
    tw = Twist(); tw.linear.x = -abs(speed)
    
    # Flush odom to current position (critical!)
    for _ in range(30):
        rclpy.spin_once(node, timeout_sec=0.05)
    start_ox, start_oy = ox, oy
    start_yaw = oyaw
    
    node.get_logger().info(f"  BWD {distance:.2f}m from odom ({start_ox:.2f}, {start_oy:.2f})")
    
    while rclpy.ok():
        rclpy.spin_once(node, timeout_sec=0.05)
        dx = ox - start_ox
        dy = oy - start_oy
        traveled = math.sqrt(dx*dx + dy*dy)
        
        if traveled >= distance:
            break
        
        yaw_err = _norm(start_yaw - oyaw)
        tw.angular.z = 2.0 * yaw_err
        pub.publish(tw)
    
    tw.linear.x = 0.0; tw.angular.z = 0.0; pub.publish(tw)
    time.sleep(0.5)
    update_map_pose(node)
    node.get_logger().info(
        f"  Stopped. Traveled {traveled:.2f}m. Map pos: ({mx:.2f}, {my:.2f})")


# ── Nav2 helper ──

def goto(node, nav, x, y, yaw, label):
    p = PoseStamped()
    p.header.frame_id = 'map'
    p.header.stamp = nav.get_clock().now().to_msg()
    p.pose.position.x = x; p.pose.position.y = y
    p.pose.orientation.z = math.sin(yaw/2)
    p.pose.orientation.w = math.cos(yaw/2)
    node.get_logger().info(f"NAV2 → {label} ({x:.1f}, {y:.1f})")
    nav.goToPose(p)
    while not nav.isTaskComplete():
        rclpy.spin_once(node, timeout_sec=0.1)  # keep odom alive!
        time.sleep(0.4)
    ok = nav.getResult() == TaskResult.SUCCEEDED
    if not ok: node.get_logger().error(f"FAILED → {label}")
    else:
        update_map_pose(node)
        node.get_logger().info(f"  Arrived at map ({mx:.2f}, {my:.2f})")
    return ok


# ── Main mission ──

def main():
    global tf_buffer

    rclpy.init()
    node = rclpy.create_node('task_orchestrator_node')
    lift_pub = node.create_publisher(Float64, '/lift_cmd', 10)
    vel_pub  = node.create_publisher(Twist,   '/cmd_vel', 10)
    node.create_subscription(Odometry, '/odom', _odom_cb, 10)

    tf_buffer = Buffer()
    tf_listener = TransformListener(tf_buffer, node)

    nav = BasicNavigator()
    node.get_logger().info("Waiting for Nav2 ...")
    nav.waitUntilNav2Active(localizer='bt_navigator')
    node.get_logger().info("Nav2 ready.")

    time.sleep(2.0)
    for _ in range(20): rclpy.spin_once(node, timeout_sec=0.1)
    update_map_pose(node)
    node.get_logger().info(f"Start position: map({mx:.2f}, {my:.2f})")

    # ════════════════════════════════════════════════════════
    # DISTANCES (from warehouse.sdf):
    #   Cart_1 is at (-6.0, -4.5). Pre-align at (-3.0, -4.5).
    #   Distance from pre-align to cart = 3.0m
    #   Dock_1 is at (10.5, 1.8). Pre-align at (9.5, 1.8).
    #   Distance from pre-dock to dock = 1.0m
    # ════════════════════════════════════════════════════════

    CART_DRIVE_DIST = 0.91   # meters forward from pre-align to cart
    DOCK_DRIVE_DIST = 0.85  # meters forward from pre-dock to dock centre
    
    PRE_CART_X = -5.5       # 0.5m east of cart_1 (-6.0)
    CART_Y = -4.5

    # ═══════════════════════════════════════════════
    # PHASE 1: PICK UP box from cart_1
    # ═══════════════════════════════════════════════

    # 1a. Nav2 → just in front of cart
    if not goto(node, nav, PRE_CART_X, CART_Y, math.pi, "Pre-Cart"):
        node.get_logger().error("Abort."); rclpy.shutdown(); return

    # 1b. Fix Nav2's 15cm tolerance error — align exactly to Y=-4.5
    align_y_map(node, vel_pub, CART_Y)

    # 1c. Precision rotate to EXACTLY west
    rotate_to_map(node, vel_pub, math.pi)

    # 1d. Drive FORWARD exactly 0.75m (odom-measured) into the cart
    node.get_logger().info("══ Driving into cart ══")
    drive_forward_distance(node, vel_pub, CART_DRIVE_DIST, math.pi)

    # 1e. LIFT
    node.get_logger().info("══ LIFTING BOX ══")
    lm = Float64(); lm.data = 0.07
    for _ in range(10): lift_pub.publish(lm); time.sleep(0.2)
    time.sleep(2.0)

    # 1f. Drive BACKWARD exactly 3.5m back to highway
    node.get_logger().info("══ Backing out ══")
    drive_backward_distance(node, vel_pub, CART_DRIVE_DIST, math.pi)

    # ═══════════════════════════════════════════════
    # PHASE 2: DELIVER box to dock_1
    # ═══════════════════════════════════════════════

    DOCK_X, DOCK_Y = 10.5, 1.8

    # 2a. Nav2 → pre-dock, facing EAST
    if not goto(node, nav, 9.5, 1.8, 0.0, "Pre-Dock"):
        node.get_logger().error("Abort."); rclpy.shutdown(); return

    # 2b. Fix Nav2 tolerance — align exactly to Y=1.8
    align_y_map(node, vel_pub, DOCK_Y)

    # 2c. Precision rotate to EXACTLY east
    rotate_to_map(node, vel_pub, 0.0)

    # 2d. Drive FORWARD exactly 1.0m into dock
    node.get_logger().info("══ Driving into dock ══")
    drive_forward_distance(node, vel_pub, DOCK_DRIVE_DIST, 0.0)

    # 2d-2. Hardcode small 5-degree right turn to compensate for skewed box pickup
    node.get_logger().info("══ Hardcoded 5-degree right turn ══")
    rotate_to_map(node, vel_pub, math.radians(-5))

    # 2e. LOWER
    node.get_logger().info("══ LOWERING BOX ══")
    lm.data = 0.0
    for _ in range(10): lift_pub.publish(lm); time.sleep(0.2)
    time.sleep(2.0)

    # 2e. Drive BACKWARD exactly 1.0m out of dock
    drive_backward_distance(node, vel_pub, DOCK_DRIVE_DIST, 0.0)

    # ═══════════════════════════════════════════════
    # PHASE 3: RETURN HOME
    # ═══════════════════════════════════════════════
    goto(node, nav, 0.0, 0.0, 0.0, "Home")
    node.get_logger().info("═══ MISSION COMPLETE ═══")

    node.destroy_node(); rclpy.shutdown()


if __name__ == '__main__':
    main()
