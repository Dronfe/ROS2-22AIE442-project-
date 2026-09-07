#!/usr/bin/env python3
import os
import rclpy
from rclpy.node import Node
from gazebo_msgs.srv import SpawnEntity
from geometry_msgs.msg import Pose, Point
from ament_index_python.packages import get_package_share_directory

class BallSpawnerNode(Node):
    def __init__(self):
        super().__init__('ball_spawner_node')
        self.client = self.create_client(SpawnEntity, '/spawn_entity')
        
        self.get_logger().info('Connecting to /spawn_entity service...')
        retry_count = 0
        while not self.client.wait_for_service(timeout_sec=2.0):
            retry_count += 1
            self.get_logger().info(f'Waiting for /spawn_entity service... (attempt {retry_count})')
            if retry_count >= 15:
                self.get_logger().error('/spawn_entity service unavailable after 30 seconds! Make sure gazebo_ros_factory plugin is loaded.')
                return
            
        self.spawn_ball()

    def spawn_ball(self):
        pkg_share = get_package_share_directory('ping_pong_robot')
        urdf_path = os.path.join(pkg_share, 'urdf', 'ping_pong_ball.urdf')
        if not os.path.exists(urdf_path):
            alt_path = os.path.join(pkg_share, 'urdf', 'ping_pong_ball.urdf.xacro')
            if os.path.exists(alt_path):
                urdf_path = alt_path

        if os.path.exists(urdf_path):
            with open(urdf_path, 'r') as f:
                ball_xml = f.read()
        else:
            ball_xml = """<?xml version="1.0"?>
<robot name="ping_pong_ball">
  <link name="ball_link">
    <visual>
      <geometry><sphere radius="0.02"/></geometry>
      <material name="orange"><color rgba="1.0 0.5 0.0 1.0"/></material>
    </visual>
    <collision>
      <geometry><sphere radius="0.02"/></geometry>
    </collision>
    <inertial>
      <mass value="0.0027"/>
      <inertia ixx="0.00000072" ixy="0" ixz="0" iyy="0.00000072" iyz="0" izz="0.00000072"/>
    </inertial>
  </link>
  <gazebo reference="ball_link">
    <material>Gazebo/Orange</material>
    <mu1>0.5</mu1>
    <mu2>0.5</mu2>
    <kp>1000000.0</kp>
    <kd>1.0</kd>
    <maxVel>10.0</maxVel>
    <minDepth>0.001</minDepth>
  </gazebo>
</robot>"""

        request = SpawnEntity.Request()
        request.name = 'incoming_ping_pong_ball'
        request.xml = ball_xml
        request.initial_pose = Pose()
        request.initial_pose.position = Point(x=1.5, y=-0.5, z=0.5)

        future = self.client.call_async(request)
        rclpy.spin_until_future_complete(self, future)
        if future.result() is not None:
            self.get_logger().info(f'Ball Spawn Result: {future.result().status_message}')
        else:
            self.get_logger().error('Failed to receive spawn entity response')

def main(args=None):
    rclpy.init(args=args)
    node = BallSpawnerNode()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()