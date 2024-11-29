import math
import numpy as np
import glm
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLUT.freeglut import *
from OpenGL.GLU import *
from data_loader import *
import camera
import time  # FPS 계산용 모듈

# Global Variables
width, height = 800, 600
program = None
last_time = time.time()  # 이전 프레임 시간
frame_count = 0         # 프레임 카운트

# Compile Shaders
def compile_shader(shader_code, shader_type):
    shader = glCreateShader(shader_type)
    glShaderSource(shader, shader_code)
    glCompileShader(shader)
    if not glGetShaderiv(shader, GL_COMPILE_STATUS):
        raise RuntimeError(glGetShaderInfoLog(shader))
    return shader

def load_shader_source(file_path):
    with open(file_path, 'r') as file:
        return file.read()
    
# OpenGL Initialization
def init_opengl():
    global program
    glDisable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFuncSeparate(
        GL_DST_ALPHA,
        GL_ONE_MINUS_SRC_ALPHA,
        GL_ZERO,
        GL_ONE_MINUS_SRC_ALPHA,
    )    
    glBlendEquationSeparate(GL_FUNC_ADD, GL_FUNC_ADD)

    # Vertex and Fragment Shader
    vertex_shader_code = load_shader_source("splat_vertex.glsl")
    fragment_shader_code = load_shader_source("splat_fragment.glsl")
    # Compile and Link Shaders
    vertex_shader = compile_shader(vertex_shader_code, GL_VERTEX_SHADER)
    fragment_shader = compile_shader(fragment_shader_code, GL_FRAGMENT_SHADER)

    program = glCreateProgram()
    glAttachShader(program, vertex_shader)
    glAttachShader(program, fragment_shader)
    glLinkProgram(program)
    if not glGetProgramiv(program, GL_LINK_STATUS):
        raise RuntimeError(glGetProgramInfoLog(program))
    glUseProgram(program)

def set_attrib(a_index, b_index, vertices, size):
    glVertexAttribPointer(a_index, size, GL_FLOAT, GL_FALSE, vertices.shape[1]*vertices.itemsize, ctypes.c_void_p(b_index*4))
    glEnableVertexAttribArray(a_index)
    glVertexAttribDivisor(a_index, 1)
    return b_index + size

# Set Up Buffers
def setup_buffers(vertices):    
    # VAO, VBO 생성
    vao = glGenVertexArrays(1)
    vbo_quad = glGenBuffers(1)  # 사각형 정점 VBO
    vbo_instance = glGenBuffers(1)  # 인스턴스 데이터 VBO

    glBindVertexArray(vao)

    # 사각형 정점 데이터 설정
    quad_vertices = np.array([
        -1.0, -1.0,  # 왼쪽 아래
        1.0, -1.0,  # 오른쪽 아래
        -1.0,  1.0,  # 왼쪽 위
        1.0,  1.0,  # 오른쪽 위
    ], dtype=np.float32)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_quad)
    glBufferData(GL_ARRAY_BUFFER, quad_vertices.nbytes, quad_vertices, GL_STATIC_DRAW)
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 2 * 4, ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)

    # 인스턴스 데이터 설정
    glBindBuffer(GL_ARRAY_BUFFER, vbo_instance)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
    # 인스턴스 변수 속성
    b_index = 0
    b_index = set_attrib(1, b_index, vertices, 3) # position    
    b_index = set_attrib(2, b_index, vertices, 4) # color
    b_index = set_attrib(3, b_index, vertices, 3) # covA
    b_index = set_attrib(4, b_index, vertices, 3) # covB    

    return vao

# Render Function
def render(vao, vertices):   
    global last_time, frame_count

    # FPS 계산
    current_time = time.time()
    frame_count += 1
    if current_time - last_time >= 1.0:  # 매 1초마다 출력
        fps = frame_count / (current_time - last_time)
        print(f"FPS: {fps:.2f}")
        frame_count = 0
        last_time = current_time

    W = width
    H = height    
    fov_y = glm.radians(45)    
    c = camera.camera
    view = glm.lookAt(c.eye, c.center, c.up)    
    projection = glm.perspective(glm.radians(45), width / height, 0.1, 100.0)    
    
    tan_fovy = math.tan(fov_y * 0.5)
    tan_fovx = tan_fovy * (W / H)
    focal_y = H / (2 * tan_fovy)
    focal_x = W / (2 * tan_fovx)

    # Pass Parameters to Shader
    glUniform1f(glGetUniformLocation(program, 'W'), W)
    glUniform1f(glGetUniformLocation(program, 'H'), H)
    glUniform1f(glGetUniformLocation(program, 'focal_x'), focal_x)
    glUniform1f(glGetUniformLocation(program, 'focal_y'), focal_y)
    glUniform1f(glGetUniformLocation(program, 'tan_fovx'), tan_fovx)
    glUniform1f(glGetUniformLocation(program, 'tan_fovy'), tan_fovy)
    glUniform1f(glGetUniformLocation(program, 'scale_modifier'), 1)    
    glUniformMatrix4fv(glGetUniformLocation(program, 'viewmatrix'), 1, GL_FALSE, glm.value_ptr(view))
    glUniformMatrix4fv(glGetUniformLocation(program, 'projmatrix'), 1, GL_FALSE, glm.value_ptr(projection))    

    # Clear Screen
    glClearColor(0, 0, 0, 1.0)
    glClear(GL_COLOR_BUFFER_BIT)
    
    # Draw Elements   
    glBindVertexArray(vao)    
    glDrawArraysInstanced(GL_TRIANGLE_STRIP, 0, 4, len(vertices))

    glutSwapBuffers()

# Window Reshape Callback
def reshape(w, h):
    global width, height
    width, height = w, h
    glViewport(0, 0, w, h)

# Main Function
def main():
    global program

    # Load PLY Data
    vertices = load_ply("playroom.ply", -1)  # Replace with your PLY file path

    # Initialize GLUT
    glutInit()
    glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH)
    glutInitWindowSize(width, height)
    glutCreateWindow(b"Gaussian Splatting")

    # Initialize OpenGL and Buffers
    init_opengl()
    vao = setup_buffers(vertices)

    # GLUT Callbacks
    glutDisplayFunc(lambda: render(vao, vertices))
    glutReshapeFunc(reshape)
    glutIdleFunc(lambda: render(vao, vertices))
    camera.register_callbacks()
    # Main Loop
    glutMainLoop()

if __name__ == "__main__":
    main()
