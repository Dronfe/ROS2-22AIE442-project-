import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
import xacro

def generate_launch_description():
    pkg_share = get_package_share_directory('ping_pong_robot')
    pkg_gazebo_ros = get_package_share_directory('gazebo_ros')

    world_file = os.path.join(pkg_share, 'worlds', 'ping_pong_world.world')
    xacro_file = os.path.join(pkg_share, 'urdf', 'ping_pong_robot.urdf.xacro')

    robot_description_raw = xacro.process_file(xacro_file).toxml()

    # 1. Gazebo Launch loading ping_pong_world.world
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_gazebo_ros, 'launch', 'gazebo.launch.py')
        ),
        launch_arguments={'world': world_file, 'verbose': 'true'}.items()
    )

    # 2. Robot State Publisher with use_sim_time: True
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description_raw,
            'use_sim_time': True
        }]
    )

    # 3. Spawn ping_pong_robot using gazebo_ros/spawn_entity.py
    spawn_robot = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-topic', 'robot_description', '-entity', 'ping_pong_robot', '-z', '0.1'],
        output='screen'
    )

    # Common parameters for sim time
    sim_time_param = {'use_sim_time': True}

    # 4. Ball spawner, vision, motor, and decision nodes with use_sim_time: True
    ball_spawner_node = Node(
        package='ping_pong_robot',
        executable='ball_spawner_node',
        output='screen',
        parameters=[sim_time_param]
    )

    camera_node = Node(
        package='ping_pong_robot',
        executable='camera_node',
        output='screen',
        parameters=[sim_time_param]
    )

    mecanum_motor_node = Node(
        package='ping_pong_robot',
        executable='mecanum_motor_node',
        output='screen',
        parameters=[sim_time_param]
    )

    decision_node = Node(
        package='ping_pong_robot',
        executable='decision_node',
        output='screen',
        parameters=[sim_time_param]
    )

    # 5. 5-second TimerAction to execute service call triggering /gazebo/set_entity_state
    throw_ball_action = TimerAction(
        period=5.0,
        actions=[
            ExecuteProcess(
                cmd=[
                    'ros2', 'service', 'call',
                    '/gazebo/set_entity_state',
                    'gazebo_msgs/srv/SetEntityState',
                    '{state: {name: "incoming_ping_pong_ball", pose: {position: {x: 1.5, y: -0.5, z: 0.5}}, twist: {linear: {x: -1.0, y: 0.2, z: 0.8}}}}'
                ],
                output='screen'
            )
        ]
    )

    gui_teleop_node = Node(
        package='ping_pong_robot',
        executable='gui_teleop_node',
        output='screen',
        parameters=[sim_time_param]
    )

    screen_node = Node(
        package='ping_pong_robot',
        executable='screen_node',
        output='screen',
        parameters=[sim_time_param]
    )

    throw_catch_node = Node(
        package='ping_pong_robot',
        executable='throw_catch_node',
        output='screen',
        parameters=[sim_time_param]
    )

    return LaunchDescription([
        gazebo,
        robot_state_publisher,
        spawn_robot,
        ball_spawner_node,
        camera_node,
        mecanum_motor_node,
        decision_node,
        screen_node,
        throw_catch_node,
        gui_teleop_node,
        throw_ball_action
    ])