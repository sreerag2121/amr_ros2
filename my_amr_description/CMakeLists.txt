cmake_minimum_required(VERSION 3.8)
project(my_amr_description)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY urdf launch config rviz worlds
  DESTINATION share/${PROJECT_NAME}
)

install(
  PROGRAMS 
    scripts/odom_tf_broadcaster.py
    scripts/joy_to_cmd_vel.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
