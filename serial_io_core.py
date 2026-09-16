import sys
import os
import argparse
import serial
import subprocess
import threading
import serial.tools.list_ports
import time
import datetime

# 参考: pyserial API Reference: https://pyserial.readthedocs.io/en/latest/pyserial_api.html

def debug(x):
    print(f"[Debug] {x}")

def list_serial_ports():

    ports_list = list(serial.tools.list_ports.comports())
    if not ports_list:
        print("No serial ports found.")
        return []

    print("Available serial ports:")
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

class SerialIOCore: # 设计方向是: 一个内核同时跑多个串口 IO 线程

    def __init__(self):
        pass

    class SerialRecvThread(threading.Thread):

        _serial_object = None # serial.Serial 对象
        _recv_display_subprocess = None # 接收数据显示子进程
        _display_pipe = None # 子进程 stdin 管道

        _new_console_output = True # 串口接收的数据输出到新控制台窗口
        _file_output = True # 串口接收的数据输出到文件
        _normal_output = False # 串口接收的数据输出到主进程控制台

        _log_file = None # 日志文件

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

        def __init__(
            self, 
            serial_object: serial.Serial, 
            new_console_output = True, 
            file_output = True, 
            normal_output = False
        ):
            super().__init__()

            self._serial_object = serial_object
            self._new_console_output = new_console_output
            self._file_output = file_output
            self._normal_output = normal_output

        _trigger_list = {
            "test_1": [], 
            "test_2": []
        } # 事件触发列表


        def _trigger_test_1(self, data):
            for func in self._trigger_list["test_1"]:
                func(data)

        def _trigger_test_2(self, data):
            for func in self._trigger_list["test_2"]:
                func(data)

        def run(self):
            try:
                while True:
                    if self._serial_object.is_open:
                        try:
                            data = self._serial_object.read()
                        except Exception as e:
                            print(e)
                            return
                        if data:
                            data += self._serial_object.read_all()

                            self._trigger_test_1(data)
                            if self._new_console_output:
                                self._display_pipe.write(data)
                                self._display_pipe.flush()
                            if self._file_output:
                                self._log_file.write(data)
                                self._log_file.flush()
                            if self._normal_output:
                                sys.stdout.buffer.write(data)
                                sys.stdout.buffer.flush()
                    else:
                        print("串口已关闭")
                        return
            except Exception as e:
                print(e)
                self._display_pipe.write(f"{e}".encode())
                self._display_pipe.flush()
                return

    class SerialIO: # 单个串口 IO 实现
        _serial_object = None # serial.Serial
        _recv_thread = None # SerialRecvThread

        def __init__(self, serial_args):
            self._serial_object = serial.Serial()
            self._serial_object.port = serial_args["port"]
            self._serial_object.baudrate = serial_args["baudrate"]
            self._serial_object.bytesize = serial_args["bytesize"]
            self._serial_object.parity = serial_args["parity"]
            self._serial_object.stopbits = serial_args["stopbits"]
            self._serial_object.timeout = serial_args["timeout"]
            self._serial_object.xonxoff = serial_args["xonxoff"]
            self._serial_object.rtscts = serial_args["rtscts"]
            self._serial_object.write_timeout = serial_args["write_timeout"]
            self._serial_object.dsrdtr = serial_args["dsrdtr"]
        
        def open(
            self,
            new_console_output = True,
            file_output = True,
            normal_output = False
        ):
            self._serial_object.open()
            self._recv_thread = SerialIOCore.SerialRecvThread(
                self._serial_object,
                new_console_output = new_console_output,
                file_output = file_output,
                normal_output = normal_output
            )
            self._recv_thread.allocate_resources()
            self._recv_thread.start()
        
        def close(self):
            self._recv_thread.release_resources()
            self._serial_object.close()
        
        def send(self, data: bytes):
            self._serial_object.write(data)
            self._serial_object.flush()

        # 串口读取仅提供事件触发的封装.
        # 注册的函数参数列表必须为 func(data: bytes), data 为接收到的字节串
        def register_recv_trigger(self, trigger_tag):
            def decorator(func):
                self._recv_thread._trigger_list[trigger_tag].append(func)
                return func
            return decorator
    
    _serial_dict = {}
        
    def add_serial_io(self, serial_args):
        if self._serial_dict.get(serial_args["port"]) is None:
            self._serial_dict[serial_args["port"]] = self.SerialIO(serial_args)
        return self._serial_dict[serial_args["port"]]
    
    def get_serial_io(self, port):
        return self._serial_dict.get(port)
    
    def remove_serial_io(self, port):
        if self._serial_dict.get(port) is not None:
            self._serial_dict[port].release_resources()
            del self._serial_dict[port]


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
            print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Recv {len(data)} bytes\n{data.decode('utf-8')}")
        
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