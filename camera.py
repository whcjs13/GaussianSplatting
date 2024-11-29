from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import glm

class Camera:
    def __init__(self, eye=None, center=None, up=None):
        self.eye = eye if eye is not None else glm.vec3(0, 0, -10)
        self.center = center if center is not None else glm.vec3(0, 0, 0)
        self.up = up if up is not None else glm.vec3(0, 1, 0)
        self.last_x = 0
        self.last_y = 0
        self.is_rotating = False
        self.is_translating = False

    def start_rotation(self, x, y):
        self.is_rotating = True
        self.last_x = x
        self.last_y = y

    def start_translation(self, x, y):
        self.is_translating = True
        self.last_x = x
        self.last_y = y

    def stop_action(self):
        self.is_rotating = False
        self.is_translating = False

    def motion(self, x, y):
        dx = x - self.last_x
        dy = y - self.last_y
        self.last_x = x
        self.last_y = y

        if self.is_rotating:  # Orbit rotation
            forward = glm.normalize(self.center-self.eye)
            right = glm.normalize(glm.cross(forward, self.up))
            up = glm.normalize(glm.cross(right, forward))

            center2eye = self.center - self.eye
            factor = 0.005
            rotation = glm.rotate(glm.mat4(1.0), -dx * factor, up)
            rotation = glm.rotate(rotation, dy * factor, right)
            rotated = glm.vec3(rotation * glm.vec4(center2eye, 1.0))
            self.center = self.eye + rotated

        elif self.is_translating:  # Pan translation
            forward = glm.normalize(self.center-self.eye)
            right = glm.normalize(glm.cross(forward, self.up))
            up = glm.normalize(glm.cross(right, forward))

            translation = (-right*dx - up*dy)*0.01
            self.eye += translation
            self.center += translation

    def zoom(self, direction):
        zoom_speed = 1 if direction > 0 else -1
        move = glm.normalize(self.center - self.eye) * zoom_speed * 0.2
        self.eye = self.eye + move
        self.center = self.center + move

    def translate(self, direction):
        forward = glm.normalize(self.center - self.eye)
        right = glm.normalize(glm.cross(forward, self.up))
        up = glm.normalize(glm.cross(right, forward))

        # Movement vector based on direction
        if direction == "forward":  # Move forward
            movement = forward * 0.5
        elif direction == "backward":  # Move backward
            movement = -forward * 0.5
        elif direction == "left":  # Move left
            movement = -right * 0.5
        elif direction == "right":  # Move right
            movement = right * 0.5
        elif direction == "down":  # Move down
            movement = up * 0.5
        elif direction == "up":  # Move up
            movement = -up * 0.5
        else:
            return

        # Update eye and center
        self.eye += movement
        self.center += movement

    def get_view_matrix(self):
        return glm.lookAt(self.eye, self.center, self.up)

# 글로벌 변수로 카메라 인스턴스 생성
camera = Camera()

# GLUT 콜백 함수 정의
def mouse(button, state, x, y):
    """GLUT 마우스 버튼 콜백"""
    if button == GLUT_LEFT_BUTTON:
        if state == GLUT_DOWN:
            camera.start_rotation(x, y)
        elif state == GLUT_UP:
            camera.stop_action()
    elif button == GLUT_RIGHT_BUTTON:
        if state == GLUT_DOWN:
            camera.start_translation(x, y)
        elif state == GLUT_UP:
            camera.stop_action()

def motion(x, y):
    """GLUT 마우스 드래그 콜백"""
    camera.motion(x, y)

def mouse_wheel(button, direction, x, y):
    """GLUT 마우스 휠 콜백"""
    camera.zoom(direction)

def keyboard(key, x, y):
    """GLUT 키보드 콜백"""
    if key == b'w':  # Move forward
        camera.translate("forward")
    elif key == b's':  # Move backward
        camera.translate("backward")
    elif key == b'a':  # Move left
        camera.translate("left")
    elif key == b'd':  # Move right
        camera.translate("right")
    elif key == b'q':  # Move down
        camera.translate("down")
    elif key == b'e':  # Move up
        camera.translate("up")

def register_callbacks():
    """
    Register GLUT callbacks for mouse and motion handling.
    """
    glutMouseFunc(mouse)
    glutMotionFunc(motion)
    glutMouseWheelFunc(mouse_wheel)
    glutKeyboardFunc(keyboard)
