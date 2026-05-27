#include <micro_ros_arduino.h>
#include <WiFi.h>
#include <stdio.h>
#include <math.h>

#include <rcl/rcl.h>
#include <rcl/error_handling.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>

#include <nav_msgs/msg/odometry.h>

#if !defined(ESP32)
#error This example is only for ESP32
#endif

// -------------------- ROS VARIABLES --------------------

rcl_publisher_t publisher;
rcl_timer_t timer;
rclc_executor_t executor;
rclc_support_t support;
rcl_allocator_t allocator;
rcl_node_t node;

nav_msgs__msg__Odometry odom_msg;

// -------------------- ROBOT VARIABLES --------------------

float x = 0.0;
float y = 0.0;
float theta = 0.0;

float linear_velocity = 0.1;
float angular_velocity = 0.1;

// -------------------- ERROR MACROS --------------------

#define RCCHECK(fn) \
  { \
    rcl_ret_t temp_rc = fn; \
    if ((temp_rc != RCL_RET_OK)) { \
      error_loop(); \
    } \
  }

#define RCSOFTCHECK(fn) \
  { \
    rcl_ret_t temp_rc = fn; \
    if ((temp_rc != RCL_RET_OK)) { \
    } \
  }

// -------------------- ERROR LOOP --------------------

void error_loop()
{
  Serial.println("ERROR — stuck in error loop. Check agent IP and WiFi.");
  while (1)
  {
    delay(100);
  }
}

// -------------------- TIMER CALLBACK --------------------

void timer_callback(rcl_timer_t * timer, int64_t last_call_time)
{
  RCLC_UNUSED(last_call_time);

  if (timer != NULL)
  {
    float dt = 0.1;

    theta += angular_velocity * dt;
    x += linear_velocity * cos(theta) * dt;
    y += linear_velocity * sin(theta) * dt;

    // Position
    odom_msg.pose.pose.position.x = x;
    odom_msg.pose.pose.position.y = y;
    odom_msg.pose.pose.position.z = 0.0;

    // Quaternion from yaw
    odom_msg.pose.pose.orientation.x = 0.0;
    odom_msg.pose.pose.orientation.y = 0.0;
    odom_msg.pose.pose.orientation.z = sin(theta / 2.0);
    odom_msg.pose.pose.orientation.w = cos(theta / 2.0);

    // Velocity
    odom_msg.twist.twist.linear.x  = linear_velocity;
    odom_msg.twist.twist.angular.z = angular_velocity;

    Serial.print("Publishing X: ");
    Serial.print(x);
    Serial.print("  Y: ");
    Serial.print(y);
    Serial.print("  Theta: ");
    Serial.println(theta);

    RCSOFTCHECK(rcl_publish(&publisher, &odom_msg, NULL));
  }
}

// -------------------- SETUP --------------------
void setup()
{
  Serial.begin(115200);
  delay(3000);

  Serial.println("Booting...");

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  delay(1000);

  Serial.println("Starting WiFi transport...");

  set_microros_wifi_transports(
    "Dilshad",
    "12345678",
    "10.80.47.214",
    8888);

  delay(3000);  // increased from 2000
  Serial.println("WiFi transport configured");

  allocator = rcl_get_default_allocator();

  // Keep retrying until agent is ready
  Serial.println("Waiting for agent...");
  while (rclc_support_init(&support, 0, NULL, &allocator) != RCL_RET_OK) {
    Serial.println("Agent not ready, retrying...");
    delay(1000);
  }
  Serial.println("Agent connected!");

  RCCHECK(rclc_node_init_default(&node, "esp32_odom_node", "", &support));

  RCCHECK(rclc_publisher_init_default(
    &publisher,
    &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(nav_msgs, msg, Odometry),
    "/odom"));

  RCCHECK(rclc_timer_init_default(
    &timer,
    &support,
    RCL_MS_TO_NS(100),
    timer_callback));

  RCCHECK(rclc_executor_init(&executor, &support.context, 1, &allocator));
  RCCHECK(rclc_executor_add_timer(&executor, &timer));

  Serial.println("microROS fully started!");
}
// -------------------- LOOP --------------------

void loop()
{
  rclc_executor_spin_some(&executor, RCL_MS_TO_NS(10));
  delay(10);
}