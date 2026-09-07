#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class ThrowCatchNode(Node):
    def __init__(self):
        super().__init__('throw_catch_node')
        self.subscription = self.create_subscription(String, '/actuator_cmd', self.actuator_callback, 10)

    def actuator_callback(self, msg):
        self.get_logger().info(f'Actuator Action: {msg.data}')

def main(args=None):
    rclpy.init(args=args)
    node = ThrowCatchNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()