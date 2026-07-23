
import rclpy
import copy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from sensor_msgs.msg import JointState
from geometry_msgs.msg import PoseStamped


class XboxTeleop(Node):

    def __init__(self):
        super().__init__("xbox_teleop")
 
        self.prev_lb = 0
        self.prev_rb = 0
        self.prev_reset1 = 0
        self.prev_reset2 = 0
        self.jaw_open_angle = 0.5
        self.jaw_closed_angle = 0.0
        self.position_step = 0.0005 # meters

        # self.deadband = 0.1

        self.psm1_init_pose = None
        self.psm2_init_pose = None

        self.psm1_jaw_closed = False
        self.psm2_jaw_closed = False
        self.psm1_pose_initialized = False
        self.psm2_pose_initialized = False
        
        self.psm1_target_pose = PoseStamped()
        self.psm2_target_pose = PoseStamped()
    
        # Subscribe Joy as input
        self.joy_sub = self.create_subscription(Joy, "/joy", self.joy_cb, 10)
        # Subscribe PSM to get current pose
        self.psm1_cur_pose_sub = self.create_subscription(PoseStamped, "/CRTK/psm1/measured_cp", self.psm1_measured_pose_cb, 10)
        self.psm2_cur_pose_sub = self.create_subscription(PoseStamped, "/CRTK/psm2/measured_cp", self.psm2_measured_pose_cb, 10)

        # Publish PSM to command Cartesian pose and jaw position
        self.psm1_pose_pub = self.create_publisher(PoseStamped, "/CRTK/psm1/servo_cp", 10)
        self.psm1_jaw_pub = self.create_publisher(JointState, "/CRTK/psm1/jaw/servo_jp", 10)

        self.psm2_pose_pub = self.create_publisher(PoseStamped, "/CRTK/psm2/servo_cp", 10)
        self.psm2_jaw_pub = self.create_publisher(JointState, "/CRTK/psm2/jaw/servo_jp", 10)

        self.get_logger().info("Xbox teleop node started.")


    def joy_cb(self, msg):
        """Convert Xbox joystick input into a PSM Cartesian pose command"""
        if not (self.psm1_pose_initialized and self.psm2_pose_initialized):
            return

        # remapping
        x1 = msg.axes[0]
        y1 = msg.axes[1]
        lb = msg.buttons[4]
        reset1 = msg.buttons[0]
        lt_pressed = msg.axes[2] < 0.5 
        
        x2 = msg.axes[3]
        y2 = msg.axes[4]
        rb = msg.buttons[5]
        reset2 = msg.buttons[1]
        rt_pressed = msg.axes[5] < 0.5

        dx1 = x1 * self.position_step
        dy1 = y1 * self.position_step
        dx2 = x2 * self.position_step
        dy2 = y2 * self.position_step
                
        # move PSM
        if lt_pressed:
            self.psm1_target_pose.pose.position.z -= dy1
        else:
            self.psm1_target_pose.pose.position.x -= dx1
            self.psm1_target_pose.pose.position.y += dy1

        if rt_pressed:
            self.psm2_target_pose.pose.position.z -= dy2
        else:
            self.psm2_target_pose.pose.position.x -= dx2
            self.psm2_target_pose.pose.position.y += dy2

        # control and publish jaw
        if lb == 1 and self.prev_lb == 0: # initially, the jaw is open and lb=1
            self.psm1_jaw_closed = not self.psm1_jaw_closed
            self.publish_psm1_jaw()

        if rb == 1 and self.prev_rb == 0:
            self.psm2_jaw_closed = not self.psm2_jaw_closed
            self.publish_psm2_jaw()

        self.prev_lb = lb
        self.prev_rb = rb

        # reset PSM
        if reset1 == 1 and self.prev_reset1 == 0:
            self.psm1_pose_reset()

        if reset2 == 1 and self.prev_reset2 == 0:
            self.psm2_pose_reset()

        self.prev_reset1 = reset1
        self.prev_reset2 = reset2

        # add timestamp
        stamp = self.get_clock().now().to_msg()
        self.psm1_target_pose.header.stamp = stamp
        self.psm2_target_pose.header.stamp = stamp

        # publish PSM pose
        self.psm1_pose_pub.publish(self.psm1_target_pose)
        self.psm2_pose_pub.publish(self.psm2_target_pose)
        
       
    def psm1_measured_pose_cb(self, msg):
        if not self.psm1_pose_initialized:
            self.psm1_target_pose = copy.deepcopy(msg)
            self.psm1_init_pose = copy.deepcopy(msg)
            self.psm1_pose_initialized = True
            self.get_logger().info("PSM1 pose initialized.")

    def psm2_measured_pose_cb(self, msg):
        if not self.psm2_pose_initialized:
            self.psm2_target_pose = copy.deepcopy(msg)
            self.psm2_init_pose = copy.deepcopy(msg)
            self.psm2_pose_initialized = True
            self.get_logger().info("PSM2 pose initialized.")

    def publish_psm1_jaw(self):
        msg = JointState()

        if self.psm1_jaw_closed:
            msg.position = [self.jaw_closed_angle]
        else:
            msg.position = [self.jaw_open_angle]

        self.psm1_jaw_pub.publish(msg)

    def publish_psm2_jaw(self):
        msg = JointState()

        if self.psm2_jaw_closed:
            msg.position = [self.jaw_closed_angle]
        else:
            msg.position = [self.jaw_open_angle]

        self.psm2_jaw_pub.publish(msg)

    def psm1_pose_reset(self):
        if self.psm1_init_pose is None:
            self.get_logger().warning("PSM1 initial pose is not available.")
            return
        self.psm1_target_pose = copy.deepcopy(self.psm1_init_pose)
     
        self.get_logger().info("PSM1 pose reset.")

    def psm2_pose_reset(self):
        if self.psm2_init_pose is None:
            self.get_logger().warning("PSM2 initial pose is not available.")
            return
        self.psm2_target_pose = copy.deepcopy(self.psm2_init_pose)

        self.get_logger().info("PSM2 pose reset.")


def main():
    rclpy.init()
    node = XboxTeleop()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

    
if __name__ == '__main__':
    main()