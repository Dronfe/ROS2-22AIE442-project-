#!/usr/bin/env python3
"""
GUI Teleop & Autonomous Interception Node for Ping Pong Robot.
Tkinter runs on the main thread; ROS SingleThreadedExecutor runs in a background thread.
"""
import random
import threading
import time
import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from std_msgs.msg import String
from geometry_msgs.msg import Twist, Point, Vector3
from gazebo_msgs.srv import SetEntityState
import tkinter as tk
from tkinter import font as tkfont


class GUITeleopNode(Node):
    def __init__(self):
        super().__init__('gui_teleop_node')
        
        # Publishers & Subscribers
        self.pub_trigger = self.create_publisher(String, '/decision_trigger', 10)
        self.pub_screen  = self.create_publisher(String, '/screen_state', 10)
        self.pub_cmd_vel = self.create_publisher(Twist, '/cmd_vel', 10)
        
        self.sub_ball = self.create_subscription(
            Point, '/detected_ball', self._ball_cb, 10)
        self.sub_trigger = self.create_subscription(
            String, '/decision_trigger', self._trigger_cb, 10)

        # Service Client for Gazebo Ball Summoner
        self.client_set = self.create_client(
            SetEntityState, '/gazebo/set_entity_state')

        # Internal State Management
        self._mode = 'IDLE'          # IDLE, CATCHING, PLAYFUL, RETURNING
        self._screen_text = "READY_AT_CENTER ^_^"
        self._status_var = None      # Updated once GUI runs

        # Timer for Autonomous Control Loop (20 Hz)
        self.create_timer(0.05, self._control_loop)
        
        # Ball Tracking Cache
        self._last_ball_pos = None
        self._last_ball_time = 0.0

    # ------------------------------------------------------------------ #
    #  ROS Callbacks & Control Mechanics                                  #
    # ------------------------------------------------------------------ #
    def _ball_cb(self, msg: Point):
        """Triggered whenever camera_node detects the ping pong ball."""
        self._last_ball_pos = msg
        self._last_ball_time = time.time()
        
        # Auto-switch to CATCHING mode if ball is moving toward robot
        if self._mode in ['IDLE', 'PLAYFUL'] and msg.x > 0.2:
            self._mode = 'CATCHING'
            self._update_screen("CATCHING BALL! 🏓")

    def _trigger_cb(self, msg: String):
        """Processes autonomous action triggers."""
        cmd = msg.data
        if cmd == 'PLAYFUL':
            self._mode = 'PLAYFUL'
            self._update_screen("DANCING 🐶")
            threading.Thread(target=self._playful_dance, daemon=True).start()
        elif cmd == 'RETURN_HOME':
            self._mode = 'RETURNING'
            self._update_screen("RETURNING HOME 🏠")
        elif cmd == 'THROW':
            self._update_screen("BALL THROWN! 🚀")

    def _control_loop(self):
        """Main autonomous execution loop running at 20 Hz."""
        now = time.time()
        
        # Reset to IDLE if no ball seen for over 1.5 seconds during catch
        if self._mode == 'CATCHING' and (now - self._last_ball_time > 1.5):
            self._mode = 'IDLE'
            self.move(0.0, 0.0, 0.0)
            self._update_screen("READY_AT_CENTER ^_^")
            return

        # Execute Autonomous Interception Logic
        if self._mode == 'CATCHING' and self._last_ball_pos is not None:
            target_y = self._last_ball_pos.y
            error_y = target_y
            kp = 1.8
            vy = max(min(kp * error_y, 1.2), -1.2)
            self.move(0.0, vy, 0.0)

    def _playful_dance(self):
        """Executes a wiggle dance sequence in background thread."""
        for _ in range(3):
            if self._mode != 'PLAYFUL':
                break
            self.move(0.0, 0.4, 0.0); time.sleep(0.2)
            self.move(0.0, -0.4, 0.0); time.sleep(0.2)
        
        if self._mode == 'PLAYFUL':
            self.move(0.0, 0.0, 1.5); time.sleep(0.5)
            self.move(0.0, 0.0, 0.0)
            self._mode = 'IDLE'
            self._update_screen("READY_AT_CENTER ^_^")

    def _update_screen(self, text: str):
        self._screen_text = text
        msg = String(); msg.data = text
        self.pub_screen.publish(msg)
        if self._status_var is not None:
            try:
                self._status_var.set(f"🤖  {text}")
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    #  GUI Helper Actions                                                 #
    # ------------------------------------------------------------------ #
    def summon_ball(self, x, y, vx, vy, vz):
        if not self.client_set.service_is_ready():
            self.get_logger().warn('/gazebo/set_entity_state not ready — is Gazebo running?')
            return
        req = SetEntityState.Request()
        req.state.name = 'incoming_ping_pong_ball'
        req.state.pose.position = Point(x=float(x), y=float(y), z=0.5)
        req.state.twist.linear = Vector3(x=float(vx), y=float(vy), z=float(vz))
        req.state.reference_frame = 'world'
        self.client_set.call_async(req)
        self.get_logger().info(f'Ball summoned at ({x:.2f},{y:.2f}) vel=({vx:.2f},{vy:.2f},{vz:.2f})')

    def summon_random(self):
        y = random.uniform(-0.7, 0.7)
        vx = random.uniform(-1.4, -0.9)
        vy = -y * 0.35
        vz = random.uniform(0.7, 1.1)
        self.summon_ball(1.7, y, vx, vy, vz)

    def send_trigger(self, cmd: str):
        msg = String(); msg.data = cmd
        self.pub_trigger.publish(msg)

    def move(self, vx, vy, wz):
        t = Twist()
        t.linear.x = float(vx)
        t.linear.y = float(vy)
        t.angular.z = float(wz)
        self.pub_cmd_vel.publish(t)

    # ------------------------------------------------------------------ #
    #  Tkinter GUI Loop                                                  #
    # ------------------------------------------------------------------ #
    def run_gui(self):
        BG, PANEL = '#1e1e2e', '#181825'
        ACC1, ACC2, ACC3, ACC4, ACC5 = '#89b4fa', '#a6e3a1', '#f9e2af', '#f38ba8', '#fab387'
        TXT, DARK = '#cdd6f4', '#11111b'

        root = tk.Tk()
        root.title('🏓 Ping Pong Robot Controller')
        root.geometry('440x400')
        root.resizable(False, False)
        root.configure(bg=BG)

        bold14 = tkfont.Font(family='Helvetica', size=14, weight='bold')
        bold10 = tkfont.Font(family='Helvetica', size=10, weight='bold')
        mono11 = tkfont.Font(family='Courier', size=11, weight='bold')

        # Header
        tk.Label(root, text='🏓 PING PONG ROBOT CONTROLLER 🏓',
                 font=bold14, fg=TXT, bg=BG).pack(pady=10)

        # Live Status
        sf = tk.LabelFrame(root, text=' Live Robot Status (OLED) ',
                           font=bold10, fg=ACC1, bg=PANEL, padx=8, pady=6)
        sf.pack(fill='x', padx=14, pady=4)
        self._status_var = tk.StringVar(value=f'🤖  {self._screen_text}')
        tk.Label(sf, textvariable=self._status_var, font=mono11, fg=ACC2, bg=PANEL).pack()

        # Ball Summoner
        bf = tk.LabelFrame(root, text=' 🎾  Summon Ping Pong Ball ',
                           font=bold10, fg=ACC3, bg=PANEL, padx=8, pady=6)
        bf.pack(fill='x', padx=14, pady=6)

        def mk_btn(parent, txt, color, cmd, r, c, colspan=1):
            b = tk.Button(parent, text=txt, font=bold10, bg=color, fg=DARK,
                          activebackground=color, relief='flat', padx=4, pady=6, command=cmd)
            b.grid(row=r, column=c, columnspan=colspan, padx=4, pady=3, sticky='ew')
            return b

        mk_btn(bf, '🎯 Summon Center', ACC1, lambda: self.summon_ball(1.6, 0.0, -1.2, 0.0, 0.8), 0, 0)
        mk_btn(bf, '👉 Summon Right', ACC5, lambda: self.summon_ball(1.6, -0.6, -1.0, 0.2, 0.8), 0, 1)
        mk_btn(bf, '👈 Summon Left', ACC5, lambda: self.summon_ball(1.6, 0.6, -1.0, -0.2, 0.8), 1, 0)
        mk_btn(bf, '🎲 Surprise Throw', ACC4, self.summon_random, 1, 1)
        bf.columnconfigure(0, weight=1); bf.columnconfigure(1, weight=1)

        # Autonomous Actions
        af = tk.LabelFrame(root, text=' 🤖  Autonomous Behaviours ',
                           font=bold10, fg=ACC2, bg=PANEL, padx=8, pady=6)
        af.pack(fill='x', padx=14, pady=4)

        for txt, color, cmd in [
            ('🐶  Act Playful! (Wiggle Dance + Spin)', ACC2, 'PLAYFUL'),
            ('🏠  Return Robot to Room Center (0,0)', ACC1, 'RETURN_HOME'),
            ('🚀  Throw Ball Back', ACC3, 'THROW'),
        ]:
            tk.Button(af, text=txt, font=bold10, bg=color, fg=DARK, activebackground=color,
                      relief='flat', padx=4, pady=6, command=lambda c=cmd: self.send_trigger(c)).pack(fill='x', pady=3)

        root.mainloop()


def main(args=None):
    rclpy.init(args=args)
    node = GUITeleopNode()

    executor = SingleThreadedExecutor()
    executor.add_node(node)
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()

    node.run_gui()

    executor.shutdown()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
