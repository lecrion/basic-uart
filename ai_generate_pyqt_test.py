import sys
import time
from PyQt5.QtWidgets import (
    QApplication,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QLabel,
    QPushButton,
    QPlainTextEdit,
    QComboBox,
    QLineEdit
)

class TestWindow_1(QWidget):
    def __init__(self):
        super().__init__()
        self.label = QLabel(self)
        self.label.setText("test")
        self.label.setGeometry(0, 0, 300, 100)
        self.button = QPushButton(self)
        self.button.setText("test")
        self.button.setGeometry(0, 100, 300, 100)

class TestWindow_2(QWidget):
    def __init__(self):
        super().__init__()
        for i in range(5):
            label = QLabel(self)
            label.setText(f"test {i}")
            label.setGeometry(0, i * 100, 300, 100)

class TestWindow_3(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        for i in range(5):
            line_edit = QLineEdit(self)
            line_edit.setText(f"test {i}")
            self.layout.addWidget(line_edit)

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setGeometry(100, 100, 1000, 800)
        self.buttons = []
        for i in range(3):
            self.buttons.append(QPushButton(f"Button {i}"))
            self.buttons[i].setParent(self)
            self.buttons[i].setGeometry(0, i * 50, 100, 50)
        self.buttons[0].clicked.connect(self.show_1)
        self.buttons[1].clicked.connect(self.show_2)
        self.buttons[2].clicked.connect(self.show_3)
        self.test_1 = TestWindow_1()
        self.test_1.setParent(self)
        self.test_1.setGeometry(0, 150, 600, 600)
        self.test_2 = TestWindow_2()
        self.test_2.setParent(self)
        self.test_2.setGeometry(0, 150, 600, 600)
        self.test_2.hide()
        self.test_3 = TestWindow_3()
        self.test_3.setParent(self)
        self.test_3.setGeometry(0, 150, 600, 600)
        self.test_3.hide()
    def show_1(self):
        self.test_1.show()
        self.test_2.hide()
        self.test_3.hide()
    def show_2(self):
        self.test_1.hide()
        self.test_2.show()
        self.test_3.hide()
    def show_3(self):
        self.test_1.hide()
        self.test_2.hide()
        self.test_3.show()
    
        
        

    def func_1(self):
        self.test_layout.removeWidget()
    

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec_())