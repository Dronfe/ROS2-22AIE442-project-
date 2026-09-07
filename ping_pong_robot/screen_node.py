#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class ScreenNode(Node):
    def __init__(self):
        super().__init__('screen_node')
        self.subscription = self.create_subscription(String, '/screen_state', self.screen_callback, 10)

    def screen_callback(self, msg):
        self.get_logger().info(f'OLED Display: [{msg.data}]')

def main(args=None):
    rclpy.init(args=args)
    node = ScreenNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()