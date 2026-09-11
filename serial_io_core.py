import sys
import argparse
import serial
import subprocess
import threading
import serial.tools.list_ports
import time

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

class SerialIOCore: # 一个 Core 跑多个串口 IO 线程

    class SerialRecvThread(threading.Thread): # 单个串口 IO 线程类 通过轮询实现

        serial_port = None
        recv_display_subprocess = None
        display_pipe = None

        def __init__(self, command_serial_args):
            super().__init__()

            self.serial_port = serial.Serial(
                port = command_serial_args.port,
                baudrate = command_serial_args.baudrate,
                bytesize = command_serial_args.bytesize,
                parity = command_serial_args.parity,
                stopbits = command_serial_args.stopbits,
                timeout = command_serial_args.timeout,
                xonxoff = command_serial_args.xonxoff,
                rtscts = command_serial_args.rtscts,
                write_timeout = command_serial_args.write_timeout,
                dsrdtr = command_serial_args.dsrdtr
            )

            self.recv_display_subprocess = subprocess.Popen(
                [sys.executable, "./serial_recv_display.py"],
                stdin = subprocess.PIPE,
                creationflags = subprocess.CREATE_NEW_CONSOLE
            )

            self.display_pipe = self.recv_display_subprocess.stdin

        def run(self):
            while True:
                time.sleep(0.05)
                data = self.serial_port.read_all()
                print(data)
                self.display_pipe.write(data)
                self.display_pipe.flush()




def main():
    # 使用命令行传参开启主程序, 默认只开一个串口进行 IO 
    # 参数完整含义可查阅 pyserial 官方 API Reference: https://www.pyserial.com/docs/api-reference

    parser = argparse.ArgumentParser(description = "串口 IO 底层封装核心模块")
    parser.add_argument("--port", type = str, default = None, help = "需要开启的端口号, 如 COM3. 不指定此参数或使用 \"--port list\", 只输出所有串口信息. 使用 \"--port choose\" 输出所有串口信息后选择串口号并打开.")
    parser.add_argument("--baudrate", type = int, default = 9600, help = "指定串口的波特率, 默认值 9600.")
    parser.add_argument("--bytesize", type = int, default = 8, choices = [5, 6, 7, 8], help = "指定串口的数据位, 默认值 8 (EIGHTBITS).")
    parser.add_argument("--parity", type = str, default = "N", choices = ["N", "E", "O", "M", "S"], help = "指定串口校验方式, 默认值 N (PARITY_NONE).")
    parser.add_argument("--stopbits", type = float, default = 1, choices = [1, 1.5, 2], help = "指定串口的停止位, 默认值 1 (STOPBITS_ONE).")
    parser.add_argument("--timeout", type = float, default = None, help = "串口读取数据的超时时间. 默认 None 代表持续阻塞模式.")
    parser.add_argument("--xonxoff", action = "store_true", help = "软件流控 Xon/Xoff, 默认为 False.")
    parser.add_argument("--rtscts", action = "store_true", help = "硬件流控 RTS/CTS, 默认为 False.")
    parser.add_argument("--write_timeout", type = float, default = None, help = "串口写入数据的超时时间. 默认 None 代表持续阻塞模式.")
    parser.add_argument("--dsrdtr", action = "store_true", help = "硬件流控 DSR/DTR, 默认为 False.")
    command_serial_args = parser.parse_args()

    if command_serial_args.port is None or command_serial_args.port.lower() == "list":
        list_serial_ports()
    elif command_serial_args.port.lower() == "choose":
        list_serial_ports()
        command_serial_args.port = input("需要开启的端口号(格式 COMx): ")
        test_recv_thread = SerialIOCore.SerialRecvThread(command_serial_args)
        test_recv_thread.start()
    else:
        test_recv_thread = SerialIOCore.SerialRecvThread(command_serial_args)
        test_recv_thread.start()


if __name__ == "__main__":
    main()