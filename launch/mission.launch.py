import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    bcr_bot_dir = get_package_share_directory('bcr_bot')
    zones_yaml_path = os.path.join(bcr_bot_dir, 'config', 'zones.yaml')

    mission_node = Node(
        package='bcr_bot',
        executable='mission_executive.py',
        name='mission_executive',
        output='screen',
        parameters=[{'zones_file': zones_yaml_path}]
    )

    return LaunchDescription([
        mission_node
    ])
