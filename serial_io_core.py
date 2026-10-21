import sys
import os
import argparse
import serial
import subprocess
import threading
import serial.tools.list_ports
import time
import datetime

from serial_logger import Logger

# pyserial API Reference: https://pyserial.readthedocs.io/en/latest/pyserial_api.html

def get_current_time():
    return datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S.%f]")

def add_timestamp(data, data_length = -1, time = "default_time"):
    return time.encode("utf-8") + f" Recv {data_length} bytes\n".encode("utf-8") + data + b"\n"

def to_hex(data):
    return data.hex(" ").upper().encode("utf-8")

def list_serial_ports_print():

    ports_list = list(serial.tools.list_ports.comports())
    if not ports_list:
        print("未找到可用的 COM 端口.")
        return []

    print("可用的 COM 端口:")
    for port in ports_list:
        print(f"\nDevice: {port.device}")
        print(f"  Name: {port.name}")
        print(f"  Description: {port.description}")
        print(f"  Hardware ID: {port.hwid}")
        print(f"  VID: {port.vid}")
        print(f"  PID: {port.pid}")
        print(f"  Serial number: {port.serial_number}")
        print(f"  Location: {port.location}")
        print(f"  Manufacturer: {port.manufacturer}")
        print(f"  Product: {port.product}")
        print(f"  Interface: {port.interface}")

def list_serial_ports():
    ports_list = list(serial.tools.list_ports.comports())
    result = {}
    for port in ports_list:
        result[port.name] = port.description
    return result

class SerialIOCore: # 设计方向是: 一个内核同时跑多个串口 IO 线程

    class SerialRecvThread(threading.Thread):

        def __init__(
            self, 
            serial_object, 
            new_console_output = True, 
            file_output = True, 
            normal_output = False,
            hex_output = False
        ):
            super().__init__()

            self._serial_object = serial_object
            self._new_console_output = new_console_output
            self._file_output = file_output
            self._normal_output = normal_output
            self._hex_output = hex_output

            self._recv_display_subprocess = None
            self._display_pipe = None
            self._log_file = None

        def allocate_resources(self):
            self._recv_display_subprocess = subprocess.Popen(
                [
                    sys.executable, 
                    "./serial_recv_display_utf8.py",
                    f"{self._serial_object.port} Recv"
                ],
                stdin = subprocess.PIPE,
                creationflags = subprocess.CREATE_NEW_CONSOLE
            )
            self._display_pipe = self._recv_display_subprocess.stdin
            if self._file_output:
                os.makedirs(f"./log/{self._serial_object.port}", exist_ok = True)
                self._log_file = open(
                    f"./log/{self._serial_object.port}/serial_recv_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log", "ab")

        def release_resources(self):
            if self._log_file:
                self._log_file.close()
            if self._display_pipe:
                self._display_pipe.close()
            if self._recv_display_subprocess:
                self._recv_display_subprocess.terminate()

        _trigger_list = {
            "test_1": [], 
            "test_2": [],
            "get_raw_data": [],
            "get_show_data": []
        } # 事件触发列表


        def _trigger_test_1(self, data):
            for func in self._trigger_list["test_1"]:
                func(data)

        def _trigger_test_2(self, data):
            for func in self._trigger_list["test_2"]:
                func(data)

        def _trigger_get_raw_data(self, data):
            for func in self._trigger_list["get_raw_data"]:
                func(data)
        
        def _trigger_get_show_data(self, data):
            for func in self._trigger_list["get_show_data"]:
                func(data)

        def run(self):
            while True:
                try:
                    if self._serial_object.is_open:
                        raw_data = self._serial_object.read()
                        if raw_data:
                            raw_data += self._serial_object.read_all()
                            data_length = len(raw_data)
                            show_data = raw_data
                            if self._hex_output:
                                show_data = to_hex(show_data)
                            show_data = add_timestamp(show_data, data_length, get_current_time())
                            
                            self._trigger_get_raw_data(raw_data)
                            self._trigger_get_show_data(show_data)

                            if self._new_console_output:
                                self._display_pipe.write(show_data)
                                self._display_pipe.flush()
                            if self._file_output:
                                self._log_file.write(show_data)
                                self._log_file.flush()
                            if self._normal_output:
                                sys.stdout.buffer.write(show_data)
                                sys.stdout.buffer.flush()
                        else:
                            Logger.i("SerialRecvThread", "退出接收线程")
                            self.release_resources()
                            return
                    else:
                        Logger.d("SerialRecvThread", "串口已关闭")
                        return
                except Exception as e:
                    Logger.e("SerialRecvThread", e)
                    self.release_resources()
                    return

    class SerialIO: # 单个串口 IO 
        _serial_properties = {}

        _serial_object = serial.Serial()
        _recv_thread = None # SerialRecvThread
        _is_open = False

        def __init__(self, serial_properties):
            self.set_default_properties()
            self.set_properties(serial_properties)

        @staticmethod
        def get_default_properties():
            return {
                "port": None,
                "baudrate": 9600,
                "bytesize": 8,
                "parity": "N",
                "stopbits": 1,
                "timeout": None,
                "xonxoff": False,
                "rtscts": False,
                "write_timeout": None,
                "dsrdtr": False
            }
        
        def get_properties(self):
            return self._serial_properties.copy()
        
        # 传入字典中包含的键值对覆盖原键值对, 原字典中其他键值对不变
        # 只能通过 set_properties 来修改串口参数, 因为这个方法同时维护 self._serial_properties 字典和 self._serial_object 的属性
        def set_properties(self, serial_properties):
            for key in serial_properties:
                self._serial_properties[key] = serial_properties[key]
                match key:
                    case "port": self._serial_object.port = serial_properties[key]
                    case "baudrate": self._serial_object.baudrate = serial_properties[key]
                    case "bytesize": self._serial_object.bytesize = serial_properties[key]
                    case "parity": self._serial_object.parity = serial_properties[key]
                    case "stopbits": self._serial_object.stopbits = serial_properties[key]
                    case "timeout": self._serial_object.timeout = serial_properties[key]
                    case "xonxoff": self._serial_object.xonxoff = serial_properties[key]
                    case "rtscts": self._serial_object.rtscts = serial_properties[key]
                    case "write_timeout": self._serial_object.write_timeout = serial_properties[key]
                    case "dsrdtr": self._serial_object.dsrdtr = serial_properties[key]
        
        def set_default_properties(self):
            self.set_properties(self.get_default_properties())

        def is_open(self):
            return self._is_open

        def open(
            self,
            new_console_output = True,
            file_output = True,
            normal_output = False,
            hex_output = False
        ):
            if self.is_open():
                return
            if self._serial_object is None:
                serial_logger.Logger.e("SerialIO", "串口对象为空")
                return
            self._serial_object.open()
            self._recv_thread = SerialIOCore.SerialRecvThread(
                self._serial_object,
                new_console_output = new_console_output,
                file_output = file_output,
                normal_output = normal_output,
                hex_output = hex_output
            )
            self._recv_thread.allocate_resources()
            self._recv_thread.start()
            self._is_open = True
        
        def close(self):
            if self._is_open is False:
                return
            if self._recv_thread:
                self._recv_thread.release_resources()
                self._recv_thread = None
            self._serial_object.close()
            self._is_open = False
        
        def send(self, data: bytes):
            self._serial_object.write(data)
            self._serial_object.flush()

        # 串口读取仅提供事件触发的封装.
        # 注册的函数参数列表必须为 func(data: bytes), data 为接收到的字节串
        def register_recv_trigger(self, trigger_tag):
            def decorator(func):
                if func not in self._recv_thread._trigger_list[trigger_tag]:
                    self._recv_thread._trigger_list[trigger_tag].append(func)
                else:
                    Logger.i("register_recv_trigger", "已经注册函数")
                return func
            return decorator
        
        def set_output_format(self, format):
            if self._recv_thread is None:
                Logger.e("SerialIO.set_output_format", "接收线程为空")
                return
            self._recv_thread._hex_output = True if format == "Hex" else False

    # 为了保持优雅, 我们允许在不传入端口号的情况下新建 SerialIO 实例, 但此时 SerialIOCore 无法根据端口号管理所有 SerialIO 实例
    # 所以我们采用 new-delete 的逻辑, SerialIOCore 只负责分发实例, 此后实例只由申请者持有和释放.
        
    def new_serial_io(self, serial_args = {}):
        return self.SerialIO(serial_args)


def main():
    # 使用命令行传参开启主程序, 默认只开一个串口进行 IO 
    # 参数完整含义可查阅 pyserial 官方 API Reference: https://www.pyserial.com/docs/api-reference

    parser = argparse.ArgumentParser(description = "串口 IO 底层封装核心模块")
    parser.add_argument("--port", "-p", type = str, default = None, help = "需要开启的端口号, 如 COM3. 不指定此参数或使用 \"--port list\", 只输出所有串口信息. 使用 \"--port choose\" 输出所有串口信息后选择串口号并打开.")
    parser.add_argument("--baudrate", "-r", type = int, default = 9600, help = "指定串口的波特率, 默认值 9600.")
    parser.add_argument("--bytesize", "-s", type = int, default = 8, choices = [5, 6, 7, 8], help = "指定串口的数据位, 默认值 8 (EIGHTBITS).")
    parser.add_argument("--parity", "-P", type = str, default = "N", choices = ["N", "E", "O", "M", "S"], help = "指定串口校验方式, 默认值 N (PARITY_NONE).")
    parser.add_argument("--stopbits", "-S", type = float, default = 1, choices = [1, 1.5, 2], help = "指定串口的停止位, 默认值 1 (STOPBITS_ONE).")
    parser.add_argument("--timeout", "-t", type = float, default = None, help = "串口读取数据的超时时间. 默认 None 代表持续阻塞模式.")
    parser.add_argument("--xonxoff", "-x", action = "store_true", help = "软件流控 Xon/Xoff, 默认为 False.")
    parser.add_argument("--rtscts", "-c", action = "store_true", help = "硬件流控 RTS/CTS, 默认为 False.")
    parser.add_argument("--write_timeout", "-w", type = float, default = None, help = "串口写入数据的超时时间. 默认 None 代表持续阻塞模式.")
    parser.add_argument("--dsrdtr", "-d", action = "store_true", help = "硬件流控 DSR/DTR, 默认为 False.")
    command_serial_args = parser.parse_args()

    serial_io_core = SerialIOCore()
    test_io_object = None

    if command_serial_args.port is None or command_serial_args.port.lower() == "list":
        list_serial_ports()
    elif command_serial_args.port.lower() == "choose":
        list_serial_ports()
        command_serial_args.port = input("需要开启的端口号(格式 COMx): ")
        test_io_object = serial_io_core.add_serial_io(vars(command_serial_args).copy())
        test_io_object.open(
            new_console_output = True,
            file_output = True,
            normal_output = False
        )
        
        @test_io_object.register_recv_trigger("test_1")
        def on_recv_test(data: bytes):
            print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}] Recv {len(data)} bytes\n{data.decode('utf-8')}")
        
        while True:
            test_io_object.send(b"Hello from SerialIOCore!\n")
            time.sleep(3)
    else:
        test_io_object = serial_io_core.add_serial_io(vars(command_serial_args).copy())
        test_io_object.open(
            new_console_output = True,
            file_output = True,
            normal_output = False
        )


if __name__ == "__main__":
    main()