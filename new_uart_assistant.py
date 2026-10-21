"""串口调试助手 —— PyQt5 图形界面主程序。

覆盖验收单要求的五项界面能力：
    选择端口、连接状态显示、发送框、接收窗口、清空窗口
另外实现：接收数据带时间戳显示、HEX 显示、保存为 txt、循环发送、在线改参数、
以及基于 pyqtgraph 的实时曲线（对应 README 里"用 PyQtGraph 绘制曲线"的设想）。

运行：
    python uart_assistant.py                 # 正常启动
    python uart_assistant.py --port VIRTUAL:RADAR --baudrate 115200
    python uart_assistant.py --demo          # 直接连上模拟雷达，方便演示/截图
"""

from __future__ import annotations

import argparse
import datetime
import itertools
import os
import sys
import time
from collections import deque

from PyQt5 import QtCore, QtGui, QtWidgets

from uart_core import (
    ChannelManager,
    LineAssembler,
    RadarSeries,
    SerialChannel,
    format_ascii,
    format_hex,
    list_ports,
    parse_hex,
    parse_radar_frame,
    save_text,
)
from uart_core.channel import ChannelError
from uart_core.qtplugin import ensure_qt_plugin_path

from imu_frame_parser import IMUFrameParser
from imu_parser import parse_imu_frame
import struct

ensure_qt_plugin_path()

try:
    import pyqtgraph as pg
except Exception:  # noqa: BLE001 - 没有 pyqtgraph 时只隐藏绘图页
    pg = None

APP_TITLE = "串口调试助手 · basic-uart"
MAX_RECORDS = 5000
BAUDRATE_CHOICES = ["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"]
PARITY_CHOICES = [("无 (N)", "N"), ("偶校验 (E)", "E"), ("奇校验 (O)", "O"), ("标记 (M)", "M"), ("空格 (S)", "S")]
BYTESIZE_CHOICES = [("8", 8), ("7", 7), ("6", 6), ("5", 5)]
STOPBITS_CHOICES = [("1", 1), ("1.5", 1.5), ("2", 2)]
FLOW_CHOICES = [("无", (False, False)), ("RTS/CTS 硬件", (True, False)), ("DSR/DTR 硬件", (False, True)), ("XON/XOFF 软件", (False, False))]
NEWLINE_CHOICES = [("无", b""), ("\\n (LF)", b"\n"), ("\\r\\n (CRLF)", b"\r\n")]
QUICK_COMMANDS = ["HELLO", "STATUS", "RATE=5", "RATE=50", "NOISE=0.05", "NOISE=0.8"]


class SerialBridge(QtCore.QObject):
    """把工作线程里的回调转成 Qt 信号，保证界面更新只发生在主线程。"""

    dataReceived = QtCore.pyqtSignal(object)   # bytes
    stateChanged = QtCore.pyqtSignal(bool, str)
    errorRaised = QtCore.pyqtSignal(str)

    def attach(self, channel: SerialChannel) -> list:
        """把本桥接对象挂到一个通道上，返回取消注册的函数列表。"""
        return [
            channel.add_recv_callback(self.dataReceived.emit, tag="gui"),
            channel.add_state_callback(lambda is_open, reason: self.stateChanged.emit(is_open, reason)),
            channel.add_error_callback(lambda exc, ctx: self.errorRaised.emit(f"{ctx}: {exc}")),
        ]


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, manager: ChannelManager, preset_port: str | None = None, preset_baud: int | None = None):
        super().__init__()
        self.manager = manager
        self.channel: SerialChannel | None = None
        self.bridge = SerialBridge()
        self.bridge.dataReceived.connect(self._on_data)
        self.bridge.stateChanged.connect(self._on_state)
        self.bridge.errorRaised.connect(self._on_error)

        self._records: deque[tuple[datetime.datetime, bytes]] = deque(maxlen=MAX_RECORDS)
        self._rendered = 0
        self._assembler = LineAssembler()
        self._plot_buffer = bytearray()
        self._series = RadarSeries(capacity=800)
        self._detach: list = []
        self._paused = False
        self._plot_dirty = False
        
        self.imu_frame_parser = IMUFrameParser()
        self.latest_imu_data = None

        self.setWindowTitle(APP_TITLE)
        self.resize(1180, 760)
        self._build_ui()
        self._build_timers()
        self.refresh_ports()
        if preset_port:
            self._select_port(preset_port)
        if preset_baud:
            self.baud_combo.setCurrentText(str(preset_baud))
        self._set_connected(False, "未连接")

    # ================================================================== 界面
    def _build_ui(self) -> None:
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        root.addWidget(self._build_toolbar())

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.addWidget(self._build_settings_panel())
        splitter.addWidget(self._build_receive_panel())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([300, 880])
        root.addWidget(splitter, 1)

        root.addWidget(self._build_send_panel())
        self.statusBar().showMessage("就绪。没有硬件时可直接选 VIRTUAL:ECHO 或 VIRTUAL:RADAR。")

    # ------------------------------------------------------------ 工具栏
    def _build_toolbar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout(bar)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        self.clear_button = QtWidgets.QPushButton("清空窗口")
        self.clear_button.setToolTip("清空接收窗口的内容（快捷键 Ctrl+L）")
        self.clear_button.clicked.connect(self.clear_receive)
        row.addWidget(self.clear_button)

        self.save_button = QtWidgets.QPushButton("保存接收为 txt")
        self.save_button.setToolTip("把接收窗口的内容保存成 txt 文件")
        self.save_button.clicked.connect(self.save_receive)
        row.addWidget(self.save_button)

        row.addSpacing(12)

        self.timestamp_check = QtWidgets.QCheckBox("显示时间戳")
        self.timestamp_check.setChecked(True)
        self.timestamp_check.stateChanged.connect(lambda _: self._rerender())
        row.addWidget(self.timestamp_check)

        self.hex_view_check = QtWidgets.QCheckBox("HEX 显示")
        self.hex_view_check.setToolTip("在 ASCII 与十六进制之间切换显示方式")
        self.hex_view_check.stateChanged.connect(lambda _: self._rerender())
        row.addWidget(self.hex_view_check)

        self.control_check = QtWidgets.QCheckBox("显示控制符")
        self.control_check.setToolTip("勾选后把 \\r \\n 等不可见字符显式显示出来，便于确认帧结束符")
        self.control_check.stateChanged.connect(lambda _: self._rerender())
        row.addWidget(self.control_check)

        self.pause_check = QtWidgets.QCheckBox("暂停显示")
        self.pause_check.setToolTip("暂停刷新界面，但串口仍在接收")
        self.pause_check.stateChanged.connect(self._on_pause_toggled)
        row.addWidget(self.pause_check)

        self.autoscroll_check = QtWidgets.QCheckBox("自动滚动")
        self.autoscroll_check.setChecked(True)
        row.addWidget(self.autoscroll_check)

        row.addStretch(1)

        self.count_label = QtWidgets.QLabel("收 0 B / 发 0 B")
        self.count_label.setStyleSheet("color:#555;")
        row.addWidget(self.count_label)
        return bar

    # ------------------------------------------------------- 左侧串口设置
    def _build_settings_panel(self) -> QtWidgets.QWidget:
        box = QtWidgets.QGroupBox("串口设置")
        form = QtWidgets.QGridLayout(box)
        form.setVerticalSpacing(6)

        self.port_combo = QtWidgets.QComboBox()
        self.port_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.refresh_button = QtWidgets.QPushButton("刷新")
        self.refresh_button.setFixedWidth(56)
        self.refresh_button.clicked.connect(self.refresh_ports)

        port_row = QtWidgets.QHBoxLayout()
        port_row.addWidget(self.port_combo, 1)
        port_row.addWidget(self.refresh_button)
        form.addWidget(QtWidgets.QLabel("端口"), 0, 0)
        form.addLayout(port_row, 0, 1, 1, 2)

        self.baud_combo = QtWidgets.QComboBox()
        self.baud_combo.setEditable(True)
        self.baud_combo.addItems(BAUDRATE_CHOICES)
        self.baud_combo.setCurrentText("115200")
        self.baud_combo.currentTextChanged.connect(self._on_baud_changed)
        form.addWidget(QtWidgets.QLabel("波特率"), 1, 0)
        form.addWidget(self.baud_combo, 1, 1, 1, 2)

        self.bytesize_combo = QtWidgets.QComboBox()
        for text, value in BYTESIZE_CHOICES:
            self.bytesize_combo.addItem(text, value)
        form.addWidget(QtWidgets.QLabel("数据位"), 2, 0)
        form.addWidget(self.bytesize_combo, 2, 1, 1, 2)

        self.parity_combo = QtWidgets.QComboBox()
        for text, value in PARITY_CHOICES:
            self.parity_combo.addItem(text, value)
        form.addWidget(QtWidgets.QLabel("校验位"), 3, 0)
        form.addWidget(self.parity_combo, 3, 1, 1, 2)

        self.stopbits_combo = QtWidgets.QComboBox()
        for text, value in STOPBITS_CHOICES:
            self.stopbits_combo.addItem(text, value)
        form.addWidget(QtWidgets.QLabel("停止位"), 4, 0)
        form.addWidget(self.stopbits_combo, 4, 1, 1, 2)

        self.flow_combo = QtWidgets.QComboBox()
        for text, _ in FLOW_CHOICES:
            self.flow_combo.addItem(text)
        form.addWidget(QtWidgets.QLabel("流控制"), 5, 0)
        form.addWidget(self.flow_combo, 5, 1, 1, 2)

        self.connect_button = QtWidgets.QPushButton("打开串口")
        self.connect_button.setMinimumHeight(34)
        self.connect_button.clicked.connect(self.toggle_connection)
        form.addWidget(self.connect_button, 6, 0, 1, 3)

        self.state_dot = QtWidgets.QLabel("●")
        self.state_dot.setStyleSheet("color:#b00; font-size:20px;")
        self.state_label = QtWidgets.QLabel("未连接")
        self.state_label.setStyleSheet("font-weight:bold;")
        state_row = QtWidgets.QHBoxLayout()
        state_row.addWidget(self.state_dot)
        state_row.addWidget(self.state_label, 1)
        form.addLayout(state_row, 7, 0, 1, 3)

        self.info_label = QtWidgets.QLabel("—")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color:#555; font-size:11px;")
        form.addWidget(self.info_label, 8, 0, 1, 3)

        self.log_label = QtWidgets.QLabel("日志: 未开始")
        self.log_label.setWordWrap(True)
        self.log_label.setStyleSheet("color:#777; font-size:11px;")
        form.addWidget(self.log_label, 9, 0, 1, 3)
        form.setRowStretch(10, 1)

        hint = QtWidgets.QLabel(
            "没有硬件也能演示：\n"
            "VIRTUAL:ECHO  —— 发送什么就收回什么\n"
            "VIRTUAL:RADAR —— 周期输出雷达遥测帧\n"
            "支持 HELLO / RATE= / NOISE= 命令"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#0a5; font-size:11px; background:#f2fbf5; padding:6px; border-radius:4px;")
        form.addWidget(hint, 11, 0, 1, 3)
        return box

    # ------------------------------------------------------- 右侧接收窗口
    def _build_receive_panel(self) -> QtWidgets.QWidget:
        self.tabs = QtWidgets.QTabWidget()

        self.recv_view = QtWidgets.QPlainTextEdit()
        self.recv_view.setReadOnly(True)
        self.recv_view.setMaximumBlockCount(MAX_RECORDS + 100)
        self.recv_view.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self.recv_view.setPlaceholderText("接收窗口：打开串口后，收到的数据会带时间戳显示在这里。")
        font = QtGui.QFont("Consolas")
        font.setStyleHint(QtGui.QFont.Monospace)
        font.setPointSize(10)
        self.recv_view.setFont(font)
        self.tabs.addTab(self.recv_view, "接收窗口")

        if pg is not None:
            pg.setConfigOptions(antialias=True, background="w", foreground="k")
            plot_box = QtWidgets.QWidget()
            plot_layout = QtWidgets.QVBoxLayout(plot_box)
            plot_layout.setContentsMargins(0, 4, 0, 0)

            options = QtWidgets.QHBoxLayout()
            options.addWidget(QtWidgets.QLabel("绘图字段:"))
            self.plot_checks = {}
            colors = {"range": "#1f77b4", "vel": "#d62728", "snr": "#2ca02c"}
            names = {"range": "距离 range", "vel": "速度 vel", "snr": "信噪比 snr"}
            for field in RadarSeries.FIELDS:
                check = QtWidgets.QCheckBox(names[field])
                check.setChecked(True)
                check.setStyleSheet(f"color:{colors[field]};")
                check.stateChanged.connect(lambda _: self._refresh_plot(force=True))
                self.plot_checks[field] = check
                options.addWidget(check)
            options.addSpacing(16)
            options.addWidget(QtWidgets.QLabel("（解析 $RADAR 遥测帧，配合 VIRTUAL:RADAR 使用）"))
            options.addStretch(1)
            self.plot_stats = QtWidgets.QLabel("帧 0 / 丢帧 0")
            options.addWidget(self.plot_stats)
            plot_layout.addLayout(options)

            self.plot_widget = pg.PlotWidget()
            self.plot_widget.addLegend()
            self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
            self.plot_widget.setLabel("bottom", "帧序号")
            self.plot_curves = {}
            for field in RadarSeries.FIELDS:
                self.plot_curves[field] = self.plot_widget.plot(
                    [], [], pen=pg.mkPen(colors[field], width=2), name=names[field]
                )
            plot_layout.addWidget(self.plot_widget, 1)
            self.tabs.addTab(plot_box, "数据绘图")
        else:
            self.plot_widget = None
            self.plot_curves = {}
            self.plot_checks = {}
            self.plot_stats = QtWidgets.QLabel("未安装 pyqtgraph")
            
        # 新增 IMU 数据显示页
        self.tabs.addTab(self._build_imu_panel(), "IMU 数据")
        
        return self.tabs
    
    def _build_imu_panel(self) -> QtWidgets.QWidget:
        """创建 IMU 解析数据展示页。"""

        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)

        title = QtWidgets.QLabel("IMU 实时数据")
        title.setStyleSheet("font-size:18px; font-weight:bold;")
        layout.addWidget(title)

        self.imu_status_label = QtWidgets.QLabel(
            "等待接收 IMU 数据……"
        )
        layout.addWidget(self.imu_status_label)

        # 字段名称、字典键、单位
        groups = {
            "帧信息": [
                ("帧头", "frame_header", ""),
                ("帧长", "frame_length", "字节"),
                ("帧识别字", "frame_id", ""),
                ("帧计数器", "frame_counter", ""),
            ],

            "姿态信息": [
                ("IMU状态字", "imu_status", ""),
                ("俯仰角", "pitch", "rad"),
                ("横滚角", "roll", "rad"),
                ("航向角", "yaw", "rad"),
                ("GPS航迹向", "yaw_gps", "度"),
            ],

            "角速度": [
                ("俯仰角速度", "pitch_rate", "rad/s"),
                ("横滚角速度", "roll_rate", "rad/s"),
                ("航向角速度", "yaw_rate", "rad/s"),
            ],

            "位置与高度": [
                ("经度", "lon", "度"),
                ("纬度", "lat", "度"),
                ("原始气压高度", "alt_baro", "m"),
                ("原始GPS高度", "alt_gps", "m"),
                ("海拔", "alt", "m"),
            ],

            "速度信息": [
                ("正北向速度", "velocity_n", "m/s"),
                ("正东向速度", "velocity_e", "m/s"),
                ("正地向速度", "velocity_d", "m/s"),
                ("空速", "velocity_air", "m/s"),
            ],

            "加速度信息": [
                ("正北向加速度", "accel_n", "m/s²"),
                ("正东向加速度", "accel_e", "m/s²"),
                ("正地向加速度", "accel_d", "m/s²"),
            ],

            "GPS信息": [
                ("卫星数", "satellite_num", "个"),
                ("水平精度因子", "hdop", ""),
                ("垂直精度因子", "vdop", ""),
                ("GPS状态字", "gps_status", ""),
                ("GPS时", "gps_hh", ""),
                ("GPS分", "gps_mm", ""),
                ("GPS秒", "gps_ss", ""),
            ],

            "温度与航向": [
                ("温度", "temperature", "℃"),
                ("双天线航向", "HDT", "（0.1度）"),
                ("天线航向标准差", "HDG_Dev", "（0.1度）"),
            ],

            "传感器与采样": [
                ("各传感器使用状态", "redundancy", ""),
                ("GPS内部采样间隔", "GPSO_DT", "(100ms)"),
                ("GPS外部采样间隔", "GPS1DT", "(100ms)"),
            ],

            "GPS速度与时间": [
                ("GPS正北向速度", "GPS_vn", "m/s"),
                ("GPS正东向速度", "GPS_ve", "m/s"),
                ("GPS正地向速度", "GPS_vd", "m/s"),
                ("GPS秒内毫秒", "gps_ms", "ms"),
                ("GPS周内天", "gps_day", ""),
                ("GPS周", "gps_week", ""),
            ],
        }

        self.imu_value_labels = {}

        # 滚动区域，避免字段过多时显示不全
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)

        content = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content)

        for group_name, fields in groups.items():
            group = QtWidgets.QGroupBox(group_name)
            grid = QtWidgets.QGridLayout(group)

            for index, (label_text, key, unit) in enumerate(fields):
                row = index // 2
                col = (index % 2) * 2

                name_label = QtWidgets.QLabel(label_text)
                value_label = QtWidgets.QLabel("--")
                value_label.setTextInteractionFlags(
                    QtCore.Qt.TextSelectableByMouse
                )
                value_label.setStyleSheet(
                    "font-size:14px; font-weight:bold;"
                )

                grid.addWidget(name_label, row, col)
                grid.addWidget(value_label, row, col + 1)

                self.imu_value_labels[key] = (value_label, unit)

            content_layout.addWidget(group)

        content_layout.addStretch(1)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
 
        return panel
    
    def _update_imu_display(self, data: dict) -> None:
        """用最新解析结果更新 IMU 面板。"""

        self.latest_imu_data = data

        for key, (label, unit) in self.imu_value_labels.items():
            if key not in data:
                continue

            value = data[key]

            # 浮点数显示两位小数，避免丢失末尾的 0
            if key in ("lon", "lat"):
                text = f"{value:.7f}"
            elif isinstance(value, float):
                text = f"{value:.2f}"
            else:
                text = str(value)

            if unit:
                text = f"{text} {unit}"

            label.setText(text)

        self.imu_status_label.setText(
            f"已解析 IMU 数据帧，帧计数：{data['frame_counter']}"
        )

    # --------------------------------------------------------- 底部发送框
    def _build_send_panel(self) -> QtWidgets.QWidget:
        box = QtWidgets.QGroupBox("发送")
        layout = QtWidgets.QVBoxLayout(box)

        self.send_edit = QtWidgets.QPlainTextEdit()
        self.send_edit.setPlaceholderText("在这里输入要发送的内容，Ctrl+Enter 发送。")
        self.send_edit.setFixedHeight(64)
        self.send_edit.setFont(self.recv_view.font())
        layout.addWidget(self.send_edit)

        controls = QtWidgets.QHBoxLayout()
        self.send_button = QtWidgets.QPushButton("发送")
        self.send_button.setMinimumWidth(90)
        self.send_button.clicked.connect(self.send_once)
        controls.addWidget(self.send_button)

        self.hex_send_check = QtWidgets.QCheckBox("HEX 发送")
        self.hex_send_check.setToolTip('把发送框内容当成十六进制，例如 "48 65 6C 6C 6F"')
        controls.addWidget(self.hex_send_check)

        controls.addWidget(QtWidgets.QLabel("换行"))
        self.newline_combo = QtWidgets.QComboBox()
        for text, _ in NEWLINE_CHOICES:
            self.newline_combo.addItem(text)
        self.newline_combo.setCurrentIndex(2)   # 默认 CRLF
        controls.addWidget(self.newline_combo)

        controls.addSpacing(12)
        self.cyclic_check = QtWidgets.QCheckBox("循环发送")
        self.cyclic_check.stateChanged.connect(self._on_cyclic_toggled)
        controls.addWidget(self.cyclic_check)
        controls.addWidget(QtWidgets.QLabel("间隔"))
        self.cyclic_interval = QtWidgets.QSpinBox()
        self.cyclic_interval.setRange(10, 60000)
        self.cyclic_interval.setValue(500)
        self.cyclic_interval.setSuffix(" ms")
        self.cyclic_interval.valueChanged.connect(self._on_cyclic_interval_changed)
        controls.addWidget(self.cyclic_interval)
        controls.addStretch(1)
        layout.addLayout(controls)

        quick = QtWidgets.QHBoxLayout()
        quick.addWidget(QtWidgets.QLabel("演示快捷命令:"))
        for command in QUICK_COMMANDS:
            button = QtWidgets.QPushButton(command)
            button.setFixedHeight(24)
            button.clicked.connect(lambda _, cmd=command: self._send_quick(cmd))
            quick.addWidget(button)
        quick.addStretch(1)
        layout.addLayout(quick)

        shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Return"), self)
        shortcut.activated.connect(self.send_once)
        clear_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+L"), self)
        clear_shortcut.activated.connect(self.clear_receive)
        return box

    # ================================================================ 定时器
    def _build_timers(self) -> None:
        self.stats_timer = QtCore.QTimer(self)
        self.stats_timer.setInterval(300)
        self.stats_timer.timeout.connect(self._refresh_stats)
        self.stats_timer.start()

        self.plot_timer = QtCore.QTimer(self)
        self.plot_timer.setInterval(200)
        self.plot_timer.timeout.connect(self._refresh_plot)
        self.plot_timer.start()

    # ============================================================ 端口与连接
    def refresh_ports(self) -> None:
        current = self.port_combo.currentData()
        self.port_combo.clear()
        ports = list_ports()
        for info in ports:
            self.port_combo.addItem(info.label, info.device)
            self.port_combo.setItemData(self.port_combo.count() - 1, info.detail(), QtCore.Qt.ToolTipRole)
        if current:
            self._select_port(current)
        real = sum(1 for info in ports if not info.is_virtual)
        self.statusBar().showMessage(
            f"发现 {len(ports)} 个端口（{real} 个真实串口 + {len(ports) - real} 个内置虚拟串口）"
        )

    def _select_port(self, device: str) -> None:
        index = self.port_combo.findData(device)
        if index >= 0:
            self.port_combo.setCurrentIndex(index)

    def _current_settings(self) -> dict:
        rtscts, dsrdtr = FLOW_CHOICES[self.flow_combo.currentIndex()][1]
        try:
            baudrate = int(self.baud_combo.currentText().strip())
        except ValueError:
            baudrate = 115200
            self.baud_combo.setCurrentText("115200")
        return {
            "baudrate": baudrate,
            "bytesize": self.bytesize_combo.currentData(),
            "parity": self.parity_combo.currentData(),
            "stopbits": self.stopbits_combo.currentData(),
            "xonxoff": self.flow_combo.currentIndex() == 3,
            "rtscts": rtscts,
            "dsrdtr": dsrdtr,
        }

    def toggle_connection(self) -> None:
        if self.channel is not None and self.channel.is_open:
            self.close_port()
        else:
            self.open_port()

    def open_port(self) -> None:
        device = self.port_combo.currentData()
        if not device:
            QtWidgets.QMessageBox.warning(self, "无法打开", "请先选择一个端口。")
            return
        settings = self._current_settings()
        try:
            channel = self.manager.open_channel(device, **settings)
        except (ChannelError, Exception) as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(self, "打开串口失败", f"{device}\n\n{exc}")
            self.statusBar().showMessage(f"打开 {device} 失败: {exc}")
            return

        self.channel = channel
        self._detach = self.bridge.attach(channel)
        self._assembler = LineAssembler()
        self._plot_buffer.clear()
        self._series.clear()
        self.imu_frame_parser.reset()
        self.latest_imu_data = None
        self._set_connected(True, f"已连接 {device}")
        self.statusBar().showMessage(f"已打开 {channel.describe()}，日志: {channel.log_path}")

    def close_port(self) -> None:
        channel = self.channel
        if channel is None:
            return
        self._flush_pending()
        for detach in self._detach:
            try:
                detach()
            except Exception:  # noqa: BLE001
                pass
        self._detach = []
        self.manager.close_channel(channel.port, reason="用户关闭")
        self.channel = None
        self._set_connected(False, "未连接")
        self.statusBar().showMessage(f"已关闭 {channel.port}")

    def _set_connected(self, is_open: bool, text: str) -> None:
        self.state_label.setText(text)
        self.state_dot.setStyleSheet(f"color:{'#0a0' if is_open else '#b00'}; font-size:20px;")
        self.connect_button.setText("关闭串口" if is_open else "打开串口")
        for widget in (
            self.port_combo,
            self.refresh_button,
            self.bytesize_combo,
            self.parity_combo,
            self.stopbits_combo,
            self.flow_combo,
        ):
            widget.setEnabled(not is_open)
        if self.channel is not None and is_open:
            info = self.channel.snapshot()
            self.info_label.setText(
                f"{info['baudrate']} / {info['bytesize']}{info['parity']}{info['stopbits']}"
            )
            self.log_label.setText(f"日志: {info['log_path'] or '未启用'}")
        elif not is_open:
            self.info_label.setText("—")

    # ================================================================ 接收侧
    def _on_data(self, data: bytes) -> None:
        now_mono = time.monotonic()
        now_wall = datetime.datetime.now()
        for started, chunk in self._assembler.feed(data, now_mono):
            stamp = now_wall - datetime.timedelta(
                seconds=now_mono - started
            )
            self._records.append((stamp, chunk))
        
            
        # 新增功能：解析 IMU 二进制数据
        try:
            frames = self.imu_frame_parser.feed(data)

            for frame in frames:
                imu_data = parse_imu_frame(frame)
                self._update_imu_display(imu_data)

        except (ValueError, TypeError, struct.error) as exc:
            self.imu_status_label.setText(
                f"IMU 数据解析失败：{exc}"
            )
            
        self._feed_plot(data)
        if not self._paused:
            self._append_latest()

    def _flush_pending(self) -> None:
        for started, chunk in self._assembler.flush():
            self._records.append((datetime.datetime.now(), chunk))
        if not self._paused:
            self._append_latest()

    def _format_record(self, stamp: datetime.datetime, chunk: bytes) -> str:
        prefix = f"[{stamp.strftime('%H:%M:%S.%f')[:-3]}] " if self.timestamp_check.isChecked() else ""
        if self.hex_view_check.isChecked():
            body = format_hex(chunk)
        elif self.control_check.isChecked():
            # 把 \r \n \t 等控制符显式转义出来，便于确认帧结束符到底是 CRLF 还是 LF
            body = format_ascii(chunk)
        else:
            text = format_ascii(chunk, escape_controls=False).rstrip("\r\n")
            body = "".join(ch if (ch == "\t" or ch >= " ") else f"\\x{ord(ch):02X}" for ch in text)
        return prefix + body

    def _append_latest(self) -> None:
        """只把还没显示过的记录追加到窗口末尾。"""
        total = len(self._records)
        if self._rendered > total:
            # 环形缓冲已经覆盖掉了旧记录，只能整体重画
            self._rendered = 0
            self._rerender()
            return
        if self._rendered == total:
            return
        new = list(itertools.islice(self._records, self._rendered, total))
        self._rendered = total
        text = "\n".join(self._format_record(*record) for record in new)
        cursor = self.recv_view.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertText(text + "\n")
        if self.autoscroll_check.isChecked():
            self.recv_view.verticalScrollBar().setValue(self.recv_view.verticalScrollBar().maximum())

    def _rerender(self) -> None:
        """显示模式或时间戳开关变化时，用历史记录整体重画。"""
        if self._paused:
            return
        self.recv_view.setUpdatesEnabled(False)
        self.recv_view.clear()
        lines = [self._format_record(*record) for record in self._records]
        self.recv_view.setPlainText("\n".join(lines))
        self.recv_view.setUpdatesEnabled(True)
        self._rendered = len(self._records)
        if self.autoscroll_check.isChecked():
            self.recv_view.verticalScrollBar().setValue(self.recv_view.verticalScrollBar().maximum())

    def clear_receive(self) -> None:
        self._records.clear()
        self._rendered = 0
        self._assembler = LineAssembler()
        self.recv_view.clear()
        
        self.imu_frame_parser.reset()
        self.latest_imu_data = None
        for label, _unit in self.imu_value_labels.values():
            label.setText("--")
        self.imu_status_label.setText("等待接收 IMU 数据……")
        
        self._series.clear()
        self._plot_buffer.clear()
        self._refresh_plot(force=True)
        self.statusBar().showMessage("已清空接收窗口")

    def save_receive(self) -> None:
        text = self.recv_view.toPlainText()
        if not text.strip():
            QtWidgets.QMessageBox.information(self, "没有内容", "接收窗口还是空的，先收一点数据再保存。")
            return
        default = os.path.join(
            os.getcwd(), f"recv_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "保存接收内容", default, "文本文件 (*.txt);;所有文件 (*)")
        if not path:
            return
        try:
            absolute = save_text(path, text)
        except OSError as exc:
            QtWidgets.QMessageBox.critical(self, "保存失败", str(exc))
            return
        self.statusBar().showMessage(f"已保存到 {absolute}")

    def _on_pause_toggled(self, state: int) -> None:
        self._paused = state == QtCore.Qt.Checked
        if not self._paused:
            self._rerender()
            self.statusBar().showMessage("已恢复显示")

    def _on_error(self, message: str) -> None:
        self.statusBar().showMessage(f"错误: {message}", 8000)

    def _on_state(self, is_open: bool, reason: str) -> None:
        if not is_open and self.channel is not None and not self.channel.is_open:
            self._set_connected(False, f"已断开（{reason}）")

    # ================================================================ 发送侧
    def _payload(self) -> bytes | None:
        text = self.send_edit.toPlainText()
        if not text:
            self.statusBar().showMessage("发送框是空的")
            return None
        if self.hex_send_check.isChecked():
            try:
                data = parse_hex(text)
            except ValueError as exc:
                QtWidgets.QMessageBox.warning(self, "HEX 格式错误", str(exc))
                return None
        else:
            data = text.encode("utf-8")
        newline = NEWLINE_CHOICES[self.newline_combo.currentIndex()][1]
        return data + newline

    def send_once(self) -> None:
        channel = self.channel
        if channel is None or not channel.is_open:
            self.statusBar().showMessage("请先打开串口")
            return
        data = self._payload()
        if data is None:
            return
        try:
            channel.send(data)
        except ChannelError as exc:
            QtWidgets.QMessageBox.critical(self, "发送失败", str(exc))
            return
        self.statusBar().showMessage(f"已发送 {len(data)} 字节: {format_hex(data[:16])}")

    def _send_quick(self, command: str) -> None:
        self.send_edit.setPlainText(command)
        self.hex_send_check.setChecked(False)
        self.send_once()

    def _on_cyclic_toggled(self, state: int) -> None:
        channel = self.channel
        if state == QtCore.Qt.Checked:
            if channel is None or not channel.is_open:
                self.cyclic_check.setChecked(False)
                self.statusBar().showMessage("请先打开串口再启动循环发送")
                return
            data = self._payload()
            if data is None:
                self.cyclic_check.setChecked(False)
                return
            interval = self.cyclic_interval.value() / 1000.0
            try:
                channel.start_cyclic_send(data, interval)
            except (ChannelError, ValueError) as exc:
                self.cyclic_check.setChecked(False)
                QtWidgets.QMessageBox.critical(self, "循环发送失败", str(exc))
                return
            self.statusBar().showMessage(f"循环发送中，间隔 {self.cyclic_interval.value()} ms")
        else:
            if channel is not None:
                channel.stop_cyclic_send()
            self.statusBar().showMessage("已停止循环发送")

    def _on_cyclic_interval_changed(self, value: int) -> None:
        if self.cyclic_check.isChecked() and self.channel is not None and self.channel.is_open:
            self._on_cyclic_toggled(QtCore.Qt.Checked)

    def _on_baud_changed(self, text: str) -> None:
        """串口已打开时，改波特率立即生效（对应 README 里"临时改变串口参数"的设想）。"""
        channel = self.channel
        if channel is None or not channel.is_open:
            return
        try:
            baudrate = int(text.strip())
        except ValueError:
            return
        try:
            applied = channel.reconfigure(baudrate=baudrate)
        except Exception as exc:  # noqa: BLE001
            self.statusBar().showMessage(f"修改波特率失败: {exc}")
            return
        self.info_label.setText(
            f"{applied['baudrate']} / {channel.snapshot()['bytesize']}"
            f"{channel.snapshot()['parity']}{channel.snapshot()['stopbits']}"
        )
        self.statusBar().showMessage(f"已在运行中把波特率改为 {applied['baudrate']}")

    # ================================================================ 绘图页
    def _feed_plot(self, data: bytes) -> None:
        if not self.plot_curves:
            return
        self._plot_buffer += data
        while True:
            index = self._plot_buffer.find(b"\n")
            if index < 0:
                break
            line = bytes(self._plot_buffer[: index + 1])
            del self._plot_buffer[: index + 1]
            frame = parse_radar_frame(line)
            if frame is not None:
                self._series.add(frame)
                self._plot_dirty = True
        if len(self._plot_buffer) > 8192:
            del self._plot_buffer[:-1024]

    def _refresh_plot(self, force: bool = False) -> None:
        if not self.plot_curves:
            return
        if not (self._plot_dirty or force):
            return
        self._plot_dirty = False
        xs = list(self._series.seq)
        for field, curve in self.plot_curves.items():
            if self.plot_checks[field].isChecked():
                curve.setData(xs, self._series.series(field))
            else:
                curve.setData([], [])
        self.plot_stats.setText(f"帧 {self._series.frames} / 丢帧 {self._series.gaps}")

    # ================================================================ 状态栏
    def _refresh_stats(self) -> None:
        channel = self.channel
        if channel is None:
            return
        info = channel.snapshot()
        self.count_label.setText(f"收 {info['bytes_rx']} B / 发 {info['bytes_tx']} B")

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802 - Qt 命名
        self.stats_timer.stop()
        self.plot_timer.stop()
        for detach in self._detach:
            try:
                detach()
            except Exception:  # noqa: BLE001
                pass
        self.manager.close_all(reason="界面关闭")
        event.accept()


def build_app(argv: list[str] | None = None) -> tuple[QtWidgets.QApplication, MainWindow]:
    """创建 QApplication 和主窗口（自检脚本也复用这个入口）。"""
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(argv or sys.argv[:1])
    app.setApplicationName(APP_TITLE)

    parser = argparse.ArgumentParser(description="串口调试助手")
    parser.add_argument("--port", "-p", default=None, help="启动时自动选中的端口，例如 COM3 或 VIRTUAL:RADAR")
    parser.add_argument("--baudrate", "-r", type=int, default=None, help="启动时选中的波特率")
    parser.add_argument("--demo", action="store_true", help="直接连上 VIRTUAL:RADAR 并开始循环发送，方便演示")
    parser.add_argument("--log-dir", default="log", help="收发日志目录，默认 ./log")
    args, _ = parser.parse_known_args(argv if argv is not None else sys.argv[1:])

    manager = ChannelManager(log_dir=args.log_dir)
    window = MainWindow(manager, preset_port=args.port, preset_baud=args.baudrate)
    if args.demo:
        window._select_port("VIRTUAL:RADAR")
        window.open_port()
    return app, window


def main() -> int:
    app, window = build_app()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())