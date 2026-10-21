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

from PyQt5.QtCore import pyqtSignal

from PyQt5.QtGui import QCursor

from serial_logger import Logger


class SerialAssistWindow(QWidget):

    on_recv_msg_signal = pyqtSignal(bytes)

    def set_properties(self, properties_dict):
        for key in properties_dict:
            self._serial_properties[key] = properties_dict[key]

    def set_default_properties(self):
        self.set_properties(serial_io_core.SerialIOCore.SerialIO.get_default_properties())

    def __init__(self):
        super().__init__()
        self._width = 800
        self._height = 600
        self._serial_io_core = serial_io_core.SerialIOCore()
        self._serial_io_object = self._serial_io_core.new_serial_io()
        self._serial_properties = serial_io_core.SerialIOCore.SerialIO.get_default_properties()
        self._show_format = "ASCII"
        self._serial_properties = serial_io_core.SerialIOCore.SerialIO.get_default_properties()

        self.on_recv_msg_signal.connect(self._on_recv_msg)
        
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Serial Assist Demo")
        self.setGeometry(100, 100, self._width, self._height)

        self._port_select_box = QComboBox(self)
        self._port_select_box.addItems(list(serial_io_core.list_serial_ports().keys()))
        self._serial_properties["port"] = self._port_select_box.currentText()
        self._port_select_box.setGeometry(0, 0, 80, 30)
        self._port_select_box.currentTextChanged.connect(self._on_port_selected)
        self._port_select_box.highlighted[str].connect(self._on_port_highlight)

        self._port_refresh_btn = QPushButton("Refresh", self)
        self._port_refresh_btn.setGeometry(90, 0, 80, 30)
        self._port_refresh_btn.clicked.connect(self._on_refresh_ports)

        self._baudrate_label = QLabel("Baudrate:", self)
        self._baudrate_label.setGeometry(0, 40, 80, 30)

        self._baudrate_edit = QLineEdit(self)
        self._baudrate_edit.setGeometry(90, 40, 80, 30)
        self._baudrate_edit.setText(str(self._serial_properties["baudrate"]))
        self._baudrate_edit.editingFinished.connect(self._on_baudrate_changed)

        self._bytesize_label = QLabel("Bytesize:", self)
        self._bytesize_label.setGeometry(0, 80, 80, 30)

        self._bytesize_box = QComboBox(self)
        self._bytesize_box.addItems(["5", "6", "7", "8"])
        self._bytesize_box.setCurrentIndex(3)
        self._bytesize_box.setGeometry(90, 80, 80, 30)
        self._bytesize_box.currentTextChanged.connect(self._on_bytesize_changed)

        self._parity_label = QLabel("Parity:", self)
        self._parity_label.setGeometry(0, 120, 80, 30)

        self._parity_box = QComboBox(self)
        self._parity_box.addItems(["None", "Even", "Odd", "Mark", "Space"])
        self._parity_box.setGeometry(90, 120, 80, 30)
        self._parity_box.currentTextChanged.connect(self._on_parity_changed)
        self._parity_box.highlighted[str].connect(self._on_parity_highlight)

        self._stopbits_label = QLabel("Stopbits:", self)
        self._stopbits_label.setGeometry(0, 160, 80, 30)

        self._stopbits_box = QComboBox(self)
        self._stopbits_box.addItems(["1", "1.5", "2"])
        self._stopbits_box.setGeometry(90, 160, 80, 30)
        self._stopbits_box.currentTextChanged.connect(self._on_stopbits_changed)
        self._stopbits_box.setCurrentText(str(self._serial_properties["stopbits"]))

        self._open_serial_btn = QPushButton("Open Serial", self)
        self._open_serial_btn.setGeometry(0, 200, 170, 30)
        self._open_serial_btn.clicked.connect(self._on_open_serial)

        self._close_serial_btn = QPushButton("Close Serial", self)
        self._close_serial_btn.setGeometry(0, 240, 170, 30)
        self._close_serial_btn.clicked.connect(self._on_close_serial)

        self._default_send_btn = QPushButton("Send Default", self)
        self._default_send_btn.setGeometry(0, 280, 170, 30)
        self._default_send_btn.clicked.connect(self._on_default_send)

        self._show_format_label = QLabel("Format:", self)
        self._show_format_label.setGeometry(0, 320, 80, 30)

        self._show_format_box = QComboBox(self)
        self._show_format_box.addItems(["ASCII", "Hex"])
        self._show_format_box.setGeometry(90, 320, 80, 30)
        self._show_format_box.currentTextChanged.connect(self._on_show_format_changed)
        self._show_format_box.setCurrentText(self._show_format)

        self._send_msg_label = QLabel("Send UART message:", self)
        self._send_msg_label.setGeometry(0, 420, 170, 30)

        self._send_msg_edit = QPlainTextEdit(self)
        self._send_msg_edit.setGeometry(10, 450, 690, 140)

        self._send_msg_btn = QPushButton("Send", self)
        self._send_msg_btn.setGeometry(710, 450, 80, 140)
        self._send_msg_btn.clicked.connect(self._on_send_msg)

        self._recv_msg_edit = QPlainTextEdit(self)
        self._recv_msg_edit.setGeometry(190, 0, 600, 430)
        self._recv_msg_edit.setReadOnly(True)
    
    def closeEvent(self, event):
        self._on_close_serial()
        event.accept()

    def _on_port_selected(self, port):  # 选择串口
        self._serial_properties["port"] = port
    
    def _on_port_highlight(self, port): # 高亮串口时显示提示信息
        QToolTip.showText(QCursor.pos(), serial_io_core.list_serial_ports()[port], self._port_select_box)

    def _on_refresh_ports(self): # 刷新串口列表
        self._port_select_box.clear()
        self._port_select_box.addItems(list(serial_io_core.list_serial_ports().keys()))

    def _on_baudrate_changed(self):  # 波特率改变
        baudrate = self._baudrate_edit.text()
        if baudrate.isdigit():
            self._serial_properties["baudrate"] = int(baudrate)
        else:
            self._serial_properties["baudrate"] = 115200
            self._baudrate_edit.setText("115200")
    
    def _on_bytesize_changed(self, bytesize):  # 数据位改变
        self._serial_properties["bytesize"] = int(bytesize)

    def _on_parity_changed(self, parity):  # 校验位改变
        self._serial_properties["parity"] = {
            "None": "N",
            "Even": "E",
            "Odd": "O",
            "Mark": "M",
            "Space": "S"
        }[parity]

    def _on_parity_highlight(self, parity):  # 校验位高亮
        help_message = {
            "None": "无校验位",
            "Even": "偶校验位",
            "Odd": "奇校验位",
            "Mark": "1 固定校验位",
            "Space": "0 固定校验位"
        }[parity]
        QToolTip.showText(QCursor.pos(), help_message, self._parity_box)

    def _on_stopbits_changed(self, stopbits):  # 停止位改变
        self._serial_properties["stopbits"] = float(stopbits)

    def _on_open_serial(self):
        try:
            if self._serial_io_object is None:
                self._serial_io_object = self._serial_io_core.new_serial_io()
            if self._serial_io_object.is_open():
                Logger.i("interface", "串口已经打开")
                return
            if self._serial_properties.get("port") is None:
                Logger.e("interface", "No serial port selected.")
                return
            self._serial_io_object.set_properties(self._serial_properties)
            self._serial_io_object.open(
                new_console_output = True,
                file_output = True,
                normal_output = False,
                hex_output = True if self._show_format == "Hex" else False
            )
            @self._serial_io_object.register_recv_trigger("get_show_data")
            def signal_emit(data):
                self.on_recv_msg_signal.emit(data)
        except Exception as e:
            Logger.e("interface", f"exception in _on_open_serial: {e}")

    def _on_close_serial(self):
        try:
            if self._serial_io_object:
                self._serial_io_object.close()
                self._serial_io_object = None
        except Exception as e:
            Logger.e("interface", f"exception in _on_close_serial: {e}")

    def _on_default_send(self):
        try:
            self._serial_io_object.send(b"Default message.")
        except Exception as e:
            Logger.e("interface", f"exception in _on_default_send: {e}")

    def _on_send_msg(self):
        try:
            msg = self._send_msg_edit.toPlainText()
            self._serial_io_object.send(msg.encode("utf-8"))
        except Exception as e:
            print(f"Exception in _on_send_msg: {e}")
    
    def _on_recv_msg(self, data):
        self._recv_msg_edit.appendPlainText(data.decode("utf-8", errors="ignore"))
    
    def _on_show_format_changed(self, format):
        self._show_format = format
        self._serial_io_object.set_output_format(format)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SerialAssistWindow()
    window.show()
    app.exec_()
        