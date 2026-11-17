from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QOpenGLWidget,
    QLabel
)
import numpy
from OpenGL import GL
import time
import sys
import threading
import math

class OpenGLTest(QOpenGLWidget):

    vert_shader_src = """
    #version 330 core
    layout(location = 0) in vec3 position;
    uniform mat4 pvm_matrix;
    void main() {
        gl_Position = pvm_matrix * vec4(position, 1.0);
    }
    """

    frag_shader_src = """
    #version 330 core
    out vec4 frag_color;
    void main() {
        frag_color = vec4(1.0, 0.0, 0.0, 1.0);}
    """

    def _compile_shader(self, shader_type, source):
        shader = GL.glCreateShader(shader_type)
        GL.glShaderSource(shader, source)
        GL.glCompileShader(shader)
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

        self._vertices = numpy.array([
            -1.0, -1.0, -1.0,
            1.0, -1.0, -1.0,
            1.0, 1.0, 1.0
        ], dtype = numpy.float32)
        self._model_matrix = numpy.identity(4, dtype = numpy.float32)
        self._view_matrix = numpy.array([
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [1.0, 0.0, 0.0, -3.0],
            [0.0, 0.0, 0.0, 1.0]
        ], dtype = numpy.float32)
        self._proj_matrix = self._make_proj_matrix()

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

        self._vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self._vao)
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
        GL.glEnableVertexAttribArray(0)

        self._vbo = GL.glGenBUffers(GL.GL_ARRAY_BUFFER, 1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self._vertices.nbytes, self._vertices, GL.GL_STATIC_DRAW)

        GL.glBindVertexArray(0)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
    
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
        GL.glViewPort(0, 0, int(width * dpr), int(height * dpr))
        self._proj_matrix = self._make_proj_matrix()
    
    def paintGL(self):
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        pvm_matrix = self._proj_matrix @ self._view_matrix @ self._model_matrix
        GL.glUseProgram(self._program)
        GL.glUniformMatrix4fv(
            GL.glGetUniformLocation(self._program, "pvm_matrix"),
            1, GL.GL_TRUE, pvm_matrix
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
        self.opengl_widget = QOpenGLWidget(self)
        self.opengl_widget.setGeometry(0, 50, 800, 550)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec_()