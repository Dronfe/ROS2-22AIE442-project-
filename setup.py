from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'ping_pong_robot'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'urdf'), glob('urdf/*.xacro') + glob('urdf/*.urdf')),
        (os.path.join('share', package_name, 'worlds'), glob('worlds/*.world')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='arwin',
    maintainer_email='user@todo.todo',
    description='ROS 2 ping pong interception robot',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'decision_node = ping_pong_robot.decision_node:main',
            'mecanum_motor_node = ping_pong_robot.mecanum_motor_node:main',
            'camera_node = ping_pong_robot.camera_node:main',
            'ball_spawner_node = ping_pong_robot.ball_spawner_node:main',
            'screen_node = ping_pong_robot.screen_node:main',
            'throw_catch_node = ping_pong_robot.throw_catch_node:main',
            'gui_teleop_node = ping_pong_robot.gui_teleop_node:main',
            'summon_ball = ping_pong_robot.summon_ball:main',
        ],
    },
)