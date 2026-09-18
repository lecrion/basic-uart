import serial_io_core
import time
import traceback

test_core = serial_io_core.SerialIOCore()

serial_channel_com7 = test_core.add_serial_io(
    {
        "port": "COM7",
        "baudrate": 115200
    }
)

serial_channel_com10 = test_core.add_serial_io(
    {
        "port": "COM10",
        "baudrate": 115200
    }
)

while True:
    try:
        cmd = input().split(" ")
        if cmd[0] == "send":
            if cmd[1] == "com7":
                serial_channel_com7.send(cmd[2].encode())
            elif cmd[1] == "com10":
                serial_channel_com10.send(cmd[2].encode())
        if cmd[0] == "close":
            if cmd[1] == "com7":
                serial_channel_com7.close()
            elif cmd[1] == "com10":
                serial_channel_com10.close()
        if cmd[0] == "open":
            if cmd[1] == "com7":
                serial_channel_com7.open()
            elif cmd[1] == "com10":
                serial_channel_com10.open()
    except Exception as e:
        print(f"Exception in core_test.py: {e}")
        continue
    

