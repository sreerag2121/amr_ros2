#include <micro_ros_arduino.h>
#include <WiFi.h>
#include <rcl/rcl.h>
#include <rcl/error_handling.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <std_msgs/msg/int32.h>

// -------------------- ENCODER PINS --------------------
#define ENC_A 18
#define ENC_B 19

volatile long encoder_ticks = 0;

// -------------------- ISR --------------------
void IRAM_ATTR encoderISR() {
  if (digitalRead(ENC_B) == HIGH)
    encoder_ticks++;
  else
    encoder_ticks--;
}

// -------------------- ROS VARIABLES --------------------
rcl_publisher_t publisher;
rcl_timer_t timer;
rclc_executor_t executor;
rclc_support_t support;
rcl_allocator_t allocator;
rcl_node_t node;
std_msgs__msg__Int32 msg;

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
void error_loop() {
  Serial.println("ERROR — check agent and WiFi");
  while (1) { delay(100); }
}

// -------------------- TIMER CALLBACK --------------------
void timer_callback(rcl_timer_t * timer, int64_t last_call_time) {
  RCLC_UNUSED(last_call_time);
  if (timer != NULL) {
    msg.data = (int32_t)encoder_ticks;
    Serial.print("Ticks: ");
    Serial.println(encoder_ticks);
    RCSOFTCHECK(rcl_publish(&publisher, &msg, NULL));
  }
}

// -------------------- SETUP --------------------
void setup() {
  Serial.begin(115200);
  delay(3000);
  Serial.println("Booting...");

  // Encoder pins
  pinMode(ENC_A, INPUT_PULLUP);
  pinMode(ENC_B, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(ENC_A), encoderISR, RISING);

  // WiFi transport
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  delay(1000);

  Serial.println("Starting WiFi...");
  set_microros_wifi_transports(
    "Dilshad",
    "12345678",
    "10.70.192.214",
    8888);

  delay(3000);
  Serial.println("WiFi configured");

  allocator = rcl_get_default_allocator();

  // Wait for agent
  Serial.println("Waiting for agent...");
  while (rclc_support_init(&support, 0, NULL, &allocator) != RCL_RET_OK) {
    Serial.println("Retrying...");
    delay(1000);
  }
  Serial.println("Agent connected!");

  RCCHECK(rclc_node_init_default(&node, "encoder_node", "", &support));

  RCCHECK(rclc_publisher_init_default(
    &publisher,
    &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
    "/encoder_ticks"));

  RCCHECK(rclc_timer_init_default(
    &timer,
    &support,
    RCL_MS_TO_NS(50),
    timer_callback));

  RCCHECK(rclc_executor_init(&executor, &support.context, 1, &allocator));
  RCCHECK(rclc_executor_add_timer(&executor, &timer));

  Serial.println("Publishing to /encoder_ticks");
}

// -------------------- LOOP --------------------
void loop() {
  rclc_executor_spin_some(&executor, RCL_MS_TO_NS(10));
  delay(10);
}