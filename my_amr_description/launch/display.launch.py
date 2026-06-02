import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
import xacro

def generate_launch_description():

    # get the xacro file path
    pkg_path = get_package_share_directory('my_amr_description')
    xacro_file = os.path.join(pkg_path, 'urdf', 'robot.urdf.xacro')

    # convert xacro → urdf string
    robot_description = xacro.process_file(xacro_file).toxml()

    return LaunchDescription([

        # publishes all TF transforms based on URDF
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            parameters=[{'robot_description': robot_description}]
        ),

        # lets you manually move joints via sliders
        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            name='joint_state_publisher_gui',
        ),

        # RViz2 for visualization
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen'
        ),

    ])