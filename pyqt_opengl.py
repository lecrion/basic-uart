from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QOpenGLWidget,
    QLabel
)
from PyQt5.QtCore import (
    QTimer,
    QElapsedTimer,
    Qt
)
import numpy
from OpenGL import GL
import time
import sys
import threading
import math
import ctypes

class OpenGLTest(QOpenGLWidget):

    vert_shader_src = """
    #version 330 core
    layout(location = 0) in vec3 position;
    layout(location = 1) in vec3 color;
    out vec3 frag_color;
    uniform mat4 pvm_matrix;
    void main() {
        frag_color = color;
        gl_Position = pvm_matrix * vec4(position, 1.0);
    }
    """

    frag_shader_src = """
    #version 330 core
    in vec3 frag_color;
    out vec4 final_color;
    void main() {
        final_color = vec4(frag_color, 1.0);}
    """

    def _compile_shader(self, shader_type, source):
        shader = GL.glCreateShader(shader_type)
        GL.glShaderSource(shader, source)
        GL.glCompileShader(shader)
        if not GL.glGetShaderiv(shader, GL.GL_COMPILE_STATUS):
            log = GL.glGetShaderInfoLog(shader)
            raise RuntimeError(f"shader compile failed: {log}")
        return shader

    def __init__(self, parent = None):
        super().__init__(parent)
        self._program = None
        self._vao = None
        self._vbo = None

        self._near_z = 0.1
        self._far_z = 100.0
        self._aspect_ratio = self.width() / self.height()
        self._fov = 45.0

        self._rot_angle = 0.0
        self._elapsed_timer = QElapsedTimer()
        self._elapsed_timer.start()
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.PreciseTimer)
        self._timer.timeout.connect(self.update_rot)
        self._timer.start(16)

        self._vertices = numpy.array([
            1.0, -1.0, 0.0, 1.0, 0.0, 0.0,
            1.0, 1.0, 0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 1.0, 0.0, 0.0, 1.0
        ], dtype = numpy.float32)
        self._model_matrix = self._make_model_matrix()
        self._view_matrix = numpy.array([
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [1.0, 0.0, 0.0, -8.0],
            [0.0, 0.0, 0.0, 1.0]
        ], dtype = numpy.float32)
        self._proj_matrix = self._make_proj_matrix()
    
    def update_rot(self):
        elapsed = self._elapsed_timer.elapsed() / 1000.0
        self._rot_angle = elapsed * 8
        self._model_matrix = self._make_model_matrix()
        self.update()

    def initializeGL(self):
        GL.glClearColor(0.0, 0.0, 0.0, 1.0)
        GL.glEnable(GL.GL_DEPTH_TEST)

        self._program = GL.glCreateProgram()
        self._vert_shader = self._compile_shader(GL.GL_VERTEX_SHADER, self.vert_shader_src)
        self._frag_shader = self._compile_shader(GL.GL_FRAGMENT_SHADER, self.frag_shader_src)
        GL.glAttachShader(self._program, self._vert_shader)
        GL.glAttachShader(self._program, self._frag_shader)
        GL.glLinkProgram(self._program)
        GL.glDeleteShader(self._vert_shader)
        GL.glDeleteShader(self._frag_shader)

        if not GL.glGetProgramiv(self._program, GL.GL_LINK_STATUS):
            log = GL.glGetProgramInfoLog(self._program)
            raise RuntimeError(f"shader link failed: {log}")

        self._vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self._vao)

        self._vbo = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self._vertices.nbytes, self._vertices, GL.GL_STATIC_DRAW)

        GL.glVertexAttribPointer(
            0, 
            3, 
            GL.GL_FLOAT, 
            GL.GL_FALSE, 
            24, 
            None
        )
        GL.glEnableVertexAttribArray(0)

        GL.glVertexAttribPointer(
            1,
            3,
            GL.GL_FLOAT,
            GL.GL_FALSE,
            24,
            ctypes.c_void_p(12)
        )
        GL.glEnableVertexAttribArray(1)

        GL.glBindVertexArray(0)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
    
    def _make_model_matrix(self):
        mat = numpy.zeros((4, 4), dtype = numpy.float32)
        mat[0, 0] = math.cos(self._rot_angle)
        mat[0, 1] = math.sin(self._rot_angle)
        mat[1, 0] = -math.sin(self._rot_angle)
        mat[1, 1] = math.cos(self._rot_angle)
        mat[2, 2] = 1
        mat[3, 3] = 1
        return mat

    def _make_proj_matrix(self):
        mat = numpy.zeros((4, 4), dtype = numpy.float32)
        mat[0, 0] = 1.0 / self._aspect_ratio / math.tan(math.radians(self._fov) / 2.0)
        mat[1, 1] = 1 / math.tan(math.radians(self._fov) / 2.0)
        mat[2, 2] = (self._far_z + self._near_z) / (self._near_z - self._far_z)
        mat[2, 3] = (2 * self._far_z * self._near_z) / (self._near_z - self._far_z)
        mat[3, 2] = -1.0
        return mat

    def resizeGL(self, width, height):
        dpr = self.devicePixelRatioF()
        self._aspect_ratio = width / height
        GL.glViewport(0, 0, int(width * dpr), int(height * dpr))
        self._proj_matrix = self._make_proj_matrix()
    
    def paintGL(self):
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        # self._proj_matrix = self._make_proj_matrix()
        # self._model_matrix = self._make_model_matrix()
        pvm_matrix = self._proj_matrix @ self._view_matrix @ self._model_matrix
        GL.glUseProgram(self._program)
        GL.glUniformMatrix4fv(
            GL.glGetUniformLocation(self._program, "pvm_matrix"),
            1, GL.GL_FALSE, pvm_matrix.T
        )
        GL.glBindVertexArray(self._vao)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, len(self._vertices) // 3)
        GL.glBindVertexArray(0)
        GL.glUseProgram(0)

    def cleanup(self):
        self.makeCurrent()
        if self._vbo:
            GL.glDeleteBuffers(1, [self._vbo])
        if self._vao:
            GL.glDeleteVertexArrays(1, [self._vao])
        if self._program:
            GL.glDeleteProgram(self._program)
        self.doneCurrent()

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)
    
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MainWindow")
        self.setGeometry(100, 100, 800, 600)
        self.test_label = QLabel(self)
        self.test_label.setText("Label")
        self.test_label.setGeometry(0, 0, 800, 50)
        self.opengl_widget = OpenGLTest(self)
        self.opengl_widget.setGeometry(0, 50, 800, 550)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec_()