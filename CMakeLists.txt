cmake_minimum_required(VERSION 3.5)
project(bcr_bot)

find_package(ament_cmake REQUIRED)

install(DIRECTORY launch meshes models urdf worlds rviz config
    DESTINATION share/${PROJECT_NAME}/
)
install(PROGRAMS
  scripts/lift_control.py
  DESTINATION lib/${PROJECT_NAME}
)
install(PROGRAMS
  scripts/mission_executive.py
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY launch config
  DESTINATION share/${PROJECT_NAME}
)
       
ament_package()
