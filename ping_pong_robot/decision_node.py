#!/usr/bin/env python3
import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Point, Twist, Vector3
from nav_msgs.msg import Odometry
from std_msgs.msg import String
from gazebo_msgs.srv import SetEntityState

def get_yaw_from_quaternion(q):
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)

def clamp(val, min_val, max_val):
    return max(min_val, min(val, max_val))

class DecisionNode(Node):
    def __init__(self):
        super().__init__('decision_node')

        # Subscriptions
        self.sub_ball = self.create_subscription(
            Point, '/ball_location', self.ball_callback, 10)
        self.sub_odom = self.create_subscription(
            Odometry, '/odom', self.odom_callback, 10)
        self.sub_trigger = self.create_subscription(
            String, '/decision_trigger', self.trigger_callback, 10)

        # Publishers
        self.pub_cmd_vel = self.create_publisher(Twist, '/cmd_vel', 10)
        self.pub_screen = self.create_publisher(String, '/screen_state', 10)
        self.pub_actuators = self.create_publisher(String, '/actuator_cmd', 10)

        # Gazebo Service Client for Ball Launching
        self.client_set_state = self.create_client(SetEntityState, '/gazebo/set_entity_state')

        # State Machine: SEARCHING, CHASING, CATCHING, PLAYFUL, THROWING, RETURNING
        self.state = "SEARCHING"
        self.center_x = 0.0
        self.kp_strafe = -0.003
        self.kp_yaw = 0.004

        # Odometry tracking (Center of room is 0.0, 0.0)
        self.current_x = 0.0
        self.current_y = 0.0
        self.current_yaw = 0.0

        # State Timing
        self.last_ball_time = self.get_clock().now()
        self.state_start_time = self.get_clock().now()
        self.standalone_playful = False

        # Main Loop Timer (20Hz)
        self.timer = self.create_timer(0.05, self.control_loop)
        self.get_logger().info("Decision Node Initialized - Ready for Ping Pong Action!")
        self.publish_screen("READY_AT_CENTER ^_^")

    def publish_screen(self, text):
        msg = String()
        msg.data = text
        self.pub_screen.publish(msg)

    def odom_callback(self, msg: Odometry):
        self.current_x = msg.pose.pose.position.x
        self.current_y = msg.pose.pose.position.y
        self.current_yaw = get_yaw_from_quaternion(msg.pose.pose.orientation)

    def trigger_callback(self, msg: String):
        cmd = msg.data.upper().strip()
        self.get_logger().info(f"Received Trigger Command: {cmd}")

        if cmd in ["PLAYFUL", "DANCE"]:
            self.standalone_playful = True
            self.transition_to("PLAYFUL")
        elif cmd in ["RETURN_HOME", "HOME", "CENTER"]:
            self.transition_to("RETURNING")
        elif cmd == "THROW":
            self.transition_to("THROWING")
        elif cmd == "CATCH":
            self.transition_to("CATCHING")
        elif cmd == "RESET":
            self.transition_to("SEARCHING")

    def transition_to(self, new_state):
        self.get_logger().info(f"State Transition: {self.state} -> {new_state}")
        self.state = new_state
        self.state_start_time = self.get_clock().now()

        if new_state == "SEARCHING":
            self.publish_screen("SEARCHING_BALL O_O")
            self.pub_cmd_vel.publish(Twist())
        elif new_state == "CATCHING":
            self.publish_screen("CATCHING! ^o^")
            act_msg = String()
            act_msg.data = "CATCH_BALL"
            self.pub_actuators.publish(act_msg)
            self.pub_cmd_vel.publish(Twist())
        elif new_state == "PLAYFUL":
            self.publish_screen("HAPPY_WIGGLE :3")
        elif new_state == "THROWING":
            self.publish_screen("LAUNCHING_BALL! >:D")
        elif new_state == "RETURNING":
            self.publish_screen("RETURNING_HOME =3")

    def ball_callback(self, msg: Point):
        self.last_ball_time = self.get_clock().now()

        if self.state in ["SEARCHING", "CHASING"]:
            if self.state != "CHASING":
                self.transition_to("CHASING")

            self.publish_screen("CHASING_BALL :D")
            error_x = msg.x - self.center_x

            twist = Twist()
            # Mecanum lateral strafe + forward drive + yaw alignment
            twist.linear.y = clamp(self.kp_strafe * msg.x, -0.4, 0.4)
            twist.angular.z = clamp(-self.kp_yaw * error_x, -0.6, 0.6)
            twist.linear.x = 0.35
            self.pub_cmd_vel.publish(twist)

            # Ball close enough to basket (radius fills frame)
            if msg.z > 22.0:
                self.transition_to("CATCHING")

    def launch_ball_forward(self):
        if not self.client_set_state.service_is_ready():
            self.get_logger().warn("SetEntityState service not ready, skipping ball physical throw")
            return

        # Compute position just at robot's launcher barrel
        forward_dist = 0.25
        ball_x = self.current_x + forward_dist * math.cos(self.current_yaw)
        ball_y = self.current_y + forward_dist * math.sin(self.current_yaw)
        ball_z = 0.25

        # Launch velocity directed forward-upward from robot
        launch_speed = 2.4
        vel_x = launch_speed * math.cos(self.current_yaw)
        vel_y = launch_speed * math.sin(self.current_yaw)
        vel_z = 1.6

        req = SetEntityState.Request()
        req.state.name = 'incoming_ping_pong_ball'
        req.state.pose.position.x = float(ball_x)
        req.state.pose.position.y = float(ball_y)
        req.state.pose.position.z = float(ball_z)
        req.state.twist.linear = Vector3(x=float(vel_x), y=float(vel_y), z=float(vel_z))
        req.state.reference_frame = 'world'

        self.client_set_state.call_async(req)
        self.get_logger().info(f"Ball fired forward from robot at ({ball_x:.2f}, {ball_y:.2f})!")

        act_msg = String()
        act_msg.data = "FIRE_LAUNCHER"
        self.pub_actuators.publish(act_msg)

    def control_loop(self):
        now = self.get_clock().now()
        dt_state = (now - self.state_start_time).nanoseconds / 1e9

        # Watchdog: if chasing and ball vanished for > 1.2s, stop and return
        if self.state == "CHASING":
            dt_ball = (now - self.last_ball_time).nanoseconds / 1e9
            if dt_ball > 1.2:
                self.get_logger().info("Ball lost during chase! Returning home.")
                self.transition_to("RETURNING")

        # Catching state: hold for 1 second, then celebrate playfully!
        elif self.state == "CATCHING":
            if dt_state > 1.0:
                self.transition_to("PLAYFUL")

        # Playful state: cute celebration dance!
        elif self.state == "PLAYFUL":
            twist = Twist()
            if dt_state < 0.4:
                # Wiggle left
                twist.linear.y = 0.4
                self.publish_screen("WIGGLE_LEFT :3")
            elif dt_state < 0.8:
                # Wiggle right
                twist.linear.y = -0.4
                self.publish_screen("WIGGLE_RIGHT :3")
            elif dt_state < 1.2:
                # Wiggle left again
                twist.linear.y = 0.4
                self.publish_screen("HAPPY_DANCE \o/")
            elif dt_state < 1.6:
                # Wiggle right again
                twist.linear.y = -0.4
                self.publish_screen("HAPPY_DANCE \o/")
            elif dt_state < 2.6:
                # Victory 360 spin!
                twist.angular.z = 3.0
                self.publish_screen("VICTORY_SPIN! ;D")
            else:
                # Dance finished!
                self.pub_cmd_vel.publish(Twist())
                if self.standalone_playful:
                    self.standalone_playful = False
                    self.transition_to("RETURNING")
                else:
                    self.transition_to("THROWING")
            self.pub_cmd_vel.publish(twist)

        # Throwing state: launch ball forward, pause, then return home
        elif self.state == "THROWING":
            if dt_state < 0.1:
                self.launch_ball_forward()
            elif dt_state > 1.2:
                self.transition_to("RETURNING")

        # Returning state: drive back to room center (0, 0)
        elif self.state == "RETURNING":
            # World frame errors
            error_x = 0.0 - self.current_x
            error_y = 0.0 - self.current_y
            error_yaw = 0.0 - self.current_yaw
            dist = math.hypot(error_x, error_y)

            # Normalize yaw error [-pi, pi]
            while error_yaw > math.pi:
                error_yaw -= 2.0 * math.pi
            while error_yaw < -math.pi:
                error_yaw += 2.0 * math.pi

            if dist < 0.08 and abs(error_yaw) < 0.15:
                # Arrived at center!
                self.pub_cmd_vel.publish(Twist())
                self.get_logger().info("Successfully returned to room center (0,0)!")
                self.publish_screen("READY_AT_CENTER ^_^")
                self.transition_to("SEARCHING")
            else:
                # Transform world errors into robot local frame for omnidirectional driving
                cos_yaw = math.cos(self.current_yaw)
                sin_yaw = math.sin(self.current_yaw)

                v_local_x = error_x * cos_yaw + error_y * sin_yaw
                v_local_y = -error_x * sin_yaw + error_y * cos_yaw

                kp_pos = 0.7
                kp_rot = 0.8

                twist = Twist()
                twist.linear.x = clamp(kp_pos * v_local_x, -0.35, 0.35)
                twist.linear.y = clamp(kp_pos * v_local_y, -0.35, 0.35)
                twist.angular.z = clamp(kp_rot * error_yaw, -0.5, 0.5)
                self.pub_cmd_vel.publish(twist)

def main(args=None):
    rclpy.init(args=args)
    node = DecisionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()