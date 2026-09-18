import sys
import serial_io_core
from PyQt5.QtWidgets import (
    QApplication,
    QVBoxLayout,
    QWidget,
    QLabel,
    QPushButton,
    QPlainTextEdit,
    QComboBox,
    QLineEdit,
    QToolTip
)

from PyQt5.QtGui import QCursor


class SerialAssistWindow(QWidget):
    def __init__(self):
        super().__init__()
        self._width = 800
        self._height = 600
        self._port_name = None
        self._baudrate_value = 115200
        self._bytesize_value = 8
        self._parity_value = "N"
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Serial Assist Demo")
        self.setGeometry(100, 100, self._width, self._height)

        self._port_select_box = QComboBox(self)
        self._port_select_box.addItems(list(serial_io_core.list_serial_ports().keys()))
        self._port_select_box.setGeometry(0, 0, 80, 30)
        self._port_select_box.currentTextChanged.connect(self._on_port_selected)
        self._port_select_box.highlighted[str].connect(self._on_port_highlight)

        self._port_refresh_btn = QPushButton("Refresh", self)
        self._port_refresh_btn.setGeometry(90, 0, 80, 30)
        self._port_refresh_btn.clicked.connect(self._refresh_ports)

        self._baudrate_label = QLabel("Baudrate:", self)
        self._baudrate_label.setGeometry(0, 40, 80, 30)

        self._baudrate_edit = QLineEdit(self)
        self._baudrate_edit.setGeometry(90, 40, 80, 30)
        self._baudrate_edit.editingFinished.connect(self._on_baudrate_changed)

        self._bytesize_label = QLabel("Bytesize:", self)
        self._bytesize_label.setGeometry(0, 80, 80, 30)

        self._bytesize_box = QComboBox(self)
        self._bytesize_box.addItems(["5", "6", "7", "8"])
        self._bytesize_box.setCurrentIndex(3)
        self._bytesize_box.setGeometry(90, 80, 80, 30)
        self._bytesize_box.currentTextChanged[str].connect(self._on_bytesize_changed)

        self._parity_label = QLabel("Parity:", self)
        self._parity_label.setGeometry(0, 120, 80, 30)

        self._parity_box = QComboBox(self)
        self._parity_box.addItems(["None", "Even", "Odd", "Mark", "Space"])
        self._parity_box.setGeometry(90, 120, 80, 30)
        self._parity_box.currentTextChanged[str].connect(self._on_parity_changed)

        self._stopbits_label = QLabel("Stopbits:", self)
        self._stopbits_label.setGeometry(0, 160, 80, 30)

        self._stopbits_box = QComboBox(self)
        self._stopbits_box.addItems(["1", "1.5", "2"])
        self._stopbits_box.setGeometry(90, 160, 80, 30)
        self._stopbits_box.currentTextChanged[str].connect(self._on_stopbits_changed)


    

    def _on_port_selected(self, port):  # 选择串口
        # print(f"Selected port: {port}")
        self._port_name = port
        
    
    def _on_port_highlight(self, port): # 高亮串口时显示提示信息
        # print(f"Highlighted port: {port}")
        QToolTip.showText(QCursor.pos(), serial_io_core.list_serial_ports()[port], self._port_select_box)

    def _refresh_ports(self): # 刷新串口列表
        self._port_select_box.clear()
        self._port_select_box.addItems(list(serial_io_core.list_serial_ports().keys()))

    def _on_baudrate_changed(self):  # 波特率改变
        baudrate = self._baudrate_edit.text()
        if baudrate.isdigit():
            self._baudrate_value = int(baudrate)
        else:
            self._baudrate_value = 115200
            self._baudrate_edit.setText("115200")
        print(f"Baudrate changed to: {self._baudrate_edit.text()}")
    
    def _on_bytesize_changed(self, bytesize):  # 数据位改变
        self._bytesize_value = int(bytesize)
        print(f"Bytesize changed to: {bytesize}")

    def _on_parity_changed(self, parity):  # 校验位改变
        self._parity_value = {"None": "N", "Even": "E", "Odd": "O", "Mark": "M", "Space": "S"}[parity]
        print(f"Parity changed to: {parity}")

    def _on_stopbits_changed(self, stopbits):  # 停止位改变
        self._stopbits_value = float(stopbits)
        print(f"Stopbits changed to: {stopbits}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SerialAssistWindow()
    window.show()
    app.exec_()
        