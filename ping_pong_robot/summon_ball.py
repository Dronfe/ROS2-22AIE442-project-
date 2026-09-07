#!/usr/bin/env python3
import sys
import random
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Point, Vector3
from std_msgs.msg import String
from gazebo_msgs.srv import SetEntityState

class BallSummonerCLI(Node):
    def __init__(self):
        super().__init__('ball_summoner_cli')
        self.client_set_state = self.create_client(SetEntityState, '/gazebo/set_entity_state')
        self.pub_trigger = self.create_publisher(String, '/decision_trigger', 10)

    def summon(self, x, y, vx, vy, vz):
        if not self.client_set_state.wait_for_service(timeout_sec=3.0):
            print("❌ Error: /gazebo/set_entity_state service not available!")
            return False

        req = SetEntityState.Request()
        req.state.name = 'incoming_ping_pong_ball'
        req.state.pose.position = Point(x=float(x), y=float(y), z=0.5)
        req.state.twist.linear = Vector3(x=float(vx), y=float(vy), z=float(vz))
        req.state.reference_frame = 'world'

        future = self.client_set_state.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        res = future.result()
        if res and res.success:
            print(f"✅ Summoned ping pong ball at ({x:.2f}, {y:.2f}) with velocity ({vx:.2f}, {vy:.2f}, {vz:.2f})!")
            return True
        else:
            print("❌ Failed to summon ball in Gazebo.")
            return False

    def trigger(self, cmd):
        msg = String()
        msg.data = cmd
        self.pub_trigger.publish(msg)
        print(f"📣 Sent command to robot: {cmd}")

def print_help():
    print("""
==================================================
🏓 Ping Pong Robot - Ball Summoner & Controller
==================================================
Usage: ros2 run ping_pong_robot summon_ball [command]

Commands:
  center   - Summon ball straight ahead (Center)
  right    - Summon ball to the right of robot
  left     - Summon ball to the left of robot
  random   - Summon ball at a surprise random angle/speed
  playful  - Trigger the robot's Playful Celebration Dance!
  home     - Command robot to return to room center (0, 0)
  throw    - Command robot to launch the ball back
==================================================
""")

def main(args=None):
    rclpy.init(args=args)
    cli = BallSummonerCLI()

    cmd = "interactive"
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower().strip()

    if cmd in ["-h", "--help"]:
        print_help()
    elif cmd == "center":
        cli.summon(1.6, 0.0, -1.2, 0.0, 0.8)
    elif cmd == "right":
        cli.summon(1.6, -0.6, -1.0, 0.2, 0.8)
    elif cmd == "left":
        cli.summon(1.6, 0.6, -1.0, -0.2, 0.8)
    elif cmd == "random":
        y = random.uniform(-0.7, 0.7)
        vx = random.uniform(-1.4, -0.9)
        vy = -y * 0.35
        vz = random.uniform(0.7, 1.1)
        cli.summon(1.7, y, vx, vy, vz)
    elif cmd in ["playful", "dance"]:
        cli.trigger("PLAYFUL")
    elif cmd in ["home", "center_home"]:
        cli.trigger("RETURN_HOME")
    elif cmd == "throw":
        cli.trigger("THROW")
    else:
        # Interactive Mode
        print_help()
        print("Type a command (center, right, left, random, playful, home, quit):")
        try:
            while True:
                choice = input("summon> ").strip().lower()
                if choice in ["q", "quit", "exit"]:
                    break
                elif choice == "center":
                    cli.summon(1.6, 0.0, -1.2, 0.0, 0.8)
                elif choice == "right":
                    cli.summon(1.6, -0.6, -1.0, 0.2, 0.8)
                elif choice == "left":
                    cli.summon(1.6, 0.6, -1.0, -0.2, 0.8)
                elif choice == "random":
                    y = random.uniform(-0.7, 0.7)
                    vx = random.uniform(-1.4, -0.9)
                    vy = -y * 0.35
                    vz = random.uniform(0.7, 1.1)
                    cli.summon(1.7, y, vx, vy, vz)
                elif choice in ["playful", "dance"]:
                    cli.trigger("PLAYFUL")
                elif choice in ["home", "center_home"]:
                    cli.trigger("RETURN_HOME")
                elif choice == "throw":
                    cli.trigger("THROW")
                else:
                    print("Unknown command. Try: center, right, left, random, playful, home, quit")
        except (KeyboardInterrupt, EOFError):
            pass

    cli.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
