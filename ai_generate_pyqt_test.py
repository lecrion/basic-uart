import sys
from PyQt5.QtWidgets import QApplication, QWidget, QStackedWidget, QPushButton, QVBoxLayout, QLabel

class Page1(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("这是页面 1"))

class Page2(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("这是页面 2"))

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.stack = QStackedWidget()
        self.page1 = Page1()
        self.page2 = Page2()
        self.stack.addWidget(self.page1)  # index 0
        self.stack.addWidget(self.page2)  # index 1
        self.page_state = 0

        btn_switch = QPushButton("切换页面")
        btn_switch.clicked.connect(self.switch_page)

        layout = QVBoxLayout(self)
        layout.addWidget(self.stack)
        layout.addWidget(btn_switch)
    
    def switch_page(self):
        self.stack.setCurrentIndex(1 - self.page_state)  # 切换页面
        self.page_state = 1 - self.page_state  # 更新页面状态

app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec_())