import os
import subprocess
import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch_ros.actions import Node


def generate_launch_description():

    pkg_path = get_package_share_directory('my_amr_description')
    xacro_file = os.path.join(pkg_path, 'urdf', 'robot.urdf.xacro')
    world_file = os.path.join(pkg_path, 'worlds', 'warehouse.sdf')
    robot_description = xacro.process_file(xacro_file).toxml()

    # convert URDF to SDF so Ignition plugins are preserved
    urdf_path = '/tmp/my_amr.urdf'
    sdf_path = '/tmp/my_amr.sdf'
    with open(urdf_path, 'w') as f:
        f.write(robot_description)
    subprocess.run(
        ['ign', 'sdf', '-p', urdf_path],
        stdout=open(sdf_path, 'w'),
        stderr=subprocess.DEVNULL
    )

    gazebo = ExecuteProcess(
        cmd=['ign', 'gazebo', '-r', world_file],
        output='screen'
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': True
        }]
    )

    spawn_robot = Node(
        package='ros_ign_gazebo',
        executable='create',
        arguments=[
            '-file', sdf_path,
            '-name', 'my_amr',
            '-z', '0.3'
        ],
        output='screen'
    )

    bridge = Node(
        package='ros_ign_bridge',
        executable='parameter_bridge',
        arguments=[
            '/cmd_vel@geometry_msgs/msg/Twist@ignition.msgs.Twist',
            '/odom@nav_msgs/msg/Odometry@ignition.msgs.Odometry',
            '/scan@sensor_msgs/msg/LaserScan@ignition.msgs.LaserScan',
            '/clock@rosgraph_msgs/msg/Clock@ignition.msgs.Clock',
            '/tf@tf2_msgs/msg/TFMessage@ignition.msgs.Pose_V',
            '/world/warehouse_world/model/my_amr/joint_state@sensor_msgs/msg/JointState[ignition.msgs.Model',
            '/lift_cmd@std_msgs/msg/Float64]ignition.msgs.Double',
        ],
        remappings=[
            ('/world/warehouse_world/model/my_amr/joint_state', '/joint_states'),
        ],
        output='screen'
    )

    odom_tf_broadcaster = Node(
        package='my_amr_description',
        executable='odom_tf_broadcaster.py',
        output='screen',
        parameters=[{'use_sim_time': True}]
    )

    return LaunchDescription([
        gazebo,
        robot_state_publisher,
        spawn_robot,
        bridge,
        odom_tf_broadcaster,
    ])