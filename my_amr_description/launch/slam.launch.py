import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    pkg_share = get_package_share_directory('my_amr_description')
    
    # Path to the slam toolbox parameters file
    slam_params_file = os.path.join(pkg_share, 'config', 'slam_toolbox_params.yaml')

    # Declare launch argument to allow overriding the params file
    declare_params_file_cmd = DeclareLaunchArgument(
        'slam_params_file',
        default_value=slam_params_file,
        description='Full path to the ROS2 parameters file to use for the slam_toolbox node'
    )

    # Launch slam_toolbox node
    start_async_slam_toolbox_node = Node(
        parameters=[
            LaunchConfiguration('slam_params_file'),
            {'use_sim_time': True}
        ],
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen'
    )

    ld = LaunchDescription()
    ld.add_action(declare_params_file_cmd)
    ld.add_action(start_async_slam_toolbox_node)

    return ld
