#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Point
from cv_bridge import CvBridge
import cv2
import numpy as np

class CameraNode(Node):
    def __init__(self):
        super().__init__('camera_node')
        self.sub_target = self.create_subscription(Image, '/target_detection_image', self.image_callback, 10)
        self.sub_esp32 = self.create_subscription(Image, '/esp32_camera/image_raw', self.image_callback, 10)
        self.publisher_ = self.create_publisher(Point, '/ball_location', 10)
        self.bridge = CvBridge()
        self.get_logger().info("Camera Node Started, waiting for frames...")

    def image_callback(self, msg):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)

            # Very broad HSV range for any Orange/Red/Yellow ball in Gazebo
            lower_bound = np.array([0, 50, 50])
            upper_bound = np.array([35, 255, 255])
            mask = cv2.inRange(hsv, lower_bound, upper_bound)

            contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                c = max(contours, key=cv2.contourArea)
                ((x, y), radius) = cv2.minEnclosingCircle(c)
                
                if radius > 1: # Capture even tiny distant balls
                    ball_point = Point()
                    height, width, _ = cv_image.shape
                    ball_point.x = float(x - (width / 2))
                    ball_point.y = float(y - (height / 2))
                    ball_point.z = float(radius)
                    
                    self.publisher_.publish(ball_point)
                    self.get_logger().info(f"Target Found! Offset X: {ball_point.x:.1f}, Radius: {ball_point.z:.1f}")
        except Exception as e:
            self.get_logger().error(f"Error processing frame: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = CameraNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()