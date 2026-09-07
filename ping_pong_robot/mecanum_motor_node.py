#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

class MecanumMotorNode(Node):
    def __init__(self):
        super().__init__('mecanum_motor_node')
        self.subscription = self.create_subscription(Twist, '/cmd_vel', self.cmd_vel_callback, 10)

    def cmd_vel_callback(self, msg):
        vx = msg.linear.x
        vy = msg.linear.y
        wz = msg.angular.z

        w_fl = vx - vy - wz
        w_fr = vx + vy + wz
        w_rl = vx + vy - wz
        w_rr = vx - vy + wz
        self.get_logger().info(f"FL: {w_fl:.2f}, FR: {w_fr:.2f}, RL: {w_rl:.2f}, RR: {w_rr:.2f}")

def main(args=None):
    rclpy.init(args=args)
    node = MecanumMotorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()