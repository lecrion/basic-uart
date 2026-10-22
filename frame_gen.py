from serial_io_core import SerialIOCore
from serial_logger import Logger
import struct
import threading
import time

class TestIMUFrame:
    FRAME_LENGTH = 119
    FRAME_HEADER = b"\xEB\x90"
    FRAME_KEYS = (
        "frame_header", "frame_length", "frame_id", "frame_counter",
        "imu_status", "pitch", "roll", "yaw", "yaw_gps",
        "pitch_rate", "roll_rate", "yaw_rate", "lon", "lat",
        "alt_baro", "alt_gps", "alt", "velocity_n", "velocity_e",
        "velocity_d", "velocity_air", "accel_n", "accel_e", "accel_d",
        "satellite_num", "hdop", "vdop", "gps_status", "gps_hh",
        "gps_mm", "gps_ss", "temperature", "HDT", "HDG_Dev",
        "redundancy", "GPSO_DT", "GPS1DT", "GPS_vn", "GPS_ve",
        "GPS_vd", "gps_ms", "gps_day", "gps_week",
    )

    def __init__(self):
        self.frame_data = {
            "frame_header": "EB 90",
            "frame_length": self.FRAME_LENGTH,
            "frame_id": 0x61,
            "frame_counter": 0,
            "imu_status": 0,
            "pitch": 0.0,
            "roll": 0.0,
            "yaw": 0.0,
            "yaw_gps": 0.0,
            "pitch_rate": 0.0,
            "roll_rate": 0.0,
            "yaw_rate": 0.0,
            "lon": 0.0,
            "lat": 0.0,
            "alt_baro": 0.0,
            "alt_gps": 0.0,
            "alt": 0.0,
            "velocity_n": 0.0,
            "velocity_e": 0.0,
            "velocity_d": 0.0,
            "velocity_air": 0.0,
            "accel_n": 0.0,
            "accel_e": 0.0,
            "accel_d": 0.0,
            "satellite_num": 0,
            "hdop": 0.0,
            "vdop": 0.0,
            "gps_status": 0,
            "gps_hh": 0,
            "gps_mm": 0,
            "gps_ss": 0,
            "temperature": 25,
            "HDT": 0.0,
            "HDG_Dev": 0.0,
            "redundancy": 0,
            "GPSO_DT": 100,
            "GPS1DT": 100,
            "GPS_vn": 0.0,
            "GPS_ve": 0.0,
            "GPS_vd": 0.0,
            "gps_ms": 0,
            "gps_day": 0,
            "gps_week": 0,
        }
        self.frame_bytes = b""
        self.bytes_lock = threading.Lock()

        self.serial_io_core = SerialIOCore()
        self.serial_io_object = self.serial_io_core.new_serial_io()
        self.serial_io_object.set_properties({
            "port": "COM4",
            "baudrate": 115200
        })
        self.serial_io_object.open()
        self.encode_frame_to_bytes()
    
    def update_frame_data(self, key, value):
        if key not in self.FRAME_KEYS:
            raise KeyError(f"Unknown IMU frame field: {key}")
        self.frame_data[key] = value
    
    def encode_frame_to_bytes(self):
        missing_keys = set(self.FRAME_KEYS) - set(self.frame_data)
        if missing_keys:
            raise ValueError(f"Missing IMU frame fields: {sorted(missing_keys)}")

        frame = bytearray(self.FRAME_LENGTH)
        frame[:2] = self.FRAME_HEADER

        def integer(key, minimum, maximum):
            try:
                value = int(self.frame_data[key])
            except (TypeError, ValueError) as error:
                raise ValueError(f"{key} must be an integer") from error
            if not minimum <= value <= maximum:
                raise ValueError(f"{key} must be in [{minimum}, {maximum}]")
            return value

        def number(key):
            try:
                return float(self.frame_data[key])
            except (TypeError, ValueError) as error:
                raise ValueError(f"{key} must be numeric") from error

        def bits_or_integer(key):
            value = self.frame_data[key]
            if isinstance(value, str) and len(value) == 8 and set(value) <= {"0", "1"}:
                return int(value, 2)
            return integer(key, 0, 255)

        def pack(fmt, offset, value):
            try:
                struct.pack_into("<" + fmt, frame, offset, value)
            except (struct.error, OverflowError, ValueError) as error:
                raise ValueError(f"Invalid value for field at offset {offset}") from error

        if str(self.frame_data["frame_header"]).replace(" ", "").upper() != "EB90":
            raise ValueError("frame_header must be EB 90")
        if integer("frame_length", 0, 255) != self.FRAME_LENGTH:
            raise ValueError(f"frame_length must be {self.FRAME_LENGTH}")

        pack("B", 2, integer("frame_length", 0, 255))
        pack("B", 3, integer("frame_id", 0, 255))
        pack("I", 4, integer("frame_counter", 0, 0xFFFFFFFF))
        pack("B", 8, bits_or_integer("imu_status"))

        for offset, key in (
            (9, "pitch"), (13, "roll"), (17, "yaw"), (21, "yaw_gps"),
            (25, "pitch_rate"), (29, "roll_rate"), (33, "yaw_rate"),
        ):
            pack("f", offset, number(key))

        for offset, key, scale in (
            (37, "lon", 10000000), (41, "lat", 10000000),
            (45, "alt_baro", 100), (49, "alt_gps", 100), (53, "alt", 100),
        ):
            pack("i", offset, int(round(number(key) * scale)))

        for offset, key in (
            (57, "velocity_n"), (61, "velocity_e"), (65, "velocity_d"),
            (69, "velocity_air"), (73, "accel_n"), (77, "accel_e"),
            (81, "accel_d"),
        ):
            pack("f", offset, number(key))

        pack("B", 85, integer("satellite_num", 0, 255))
        pack("H", 86, int(round(number("hdop") * 100)))
        pack("H", 88, int(round(number("vdop") * 100)))
        pack("B", 90, integer("gps_status", 0, 255))
        pack("B", 91, integer("gps_hh", 0, 255))
        pack("B", 92, integer("gps_mm", 0, 255))
        pack("B", 93, integer("gps_ss", 0, 255))
        pack("b", 94, integer("temperature", -128, 127))
        pack("h", 95, int(round(number("HDT") * 10)))
        pack("h", 97, int(round(number("HDG_Dev") * 10)))
        pack("B", 99, bits_or_integer("redundancy"))
        pack("B", 100, int(round(number("GPSO_DT") / 100)))
        pack("B", 101, int(round(number("GPS1DT") / 100)))
        pack("f", 102, number("GPS_vn"))
        pack("f", 106, number("GPS_ve"))
        pack("f", 110, number("GPS_vd"))
        pack("H", 114, integer("gps_ms", 0, 0xFFFF))
        pack("B", 116, integer("gps_day", 0, 255))
        pack("H", 117, integer("gps_week", 0, 0xFFFF))

        self.frame_bytes = bytes(frame)
        return self.frame_bytes


    def serial_send_bytes(self):
        try:
            with self.bytes_lock:
                self.serial_io_object.send(self.frame_bytes)
        except Exception as e:
            Logger.e("TestIMUFrame", f"Failed to send bytes: {e}")
    
class CommandThread(threading.Thread):
    def __init__(self, test_imu_frame):
        super().__init__()
        self.test_imu_frame = test_imu_frame
    
    def run(self):
        while True:
            try:
                command = input().split()
            except EOFError:
                return
            if not command:
                continue
            if command[0] == "update":
                if len(command) != 3:
                    Logger.e("CommandThread", "Usage: update <field> <value>")
                    continue
                key = command[1]
                value = command[2]
                try:
                    self.test_imu_frame.update_frame_data(key, value)
                    self.test_imu_frame.encode_frame_to_bytes()
                except (KeyError, ValueError) as error:
                    Logger.e("CommandThread", str(error))

if __name__ == "__main__":
    test_frame = TestIMUFrame()
    command_thread = CommandThread(test_frame)
    command_thread.start()
    while True:
        time.sleep(0.05)
        test_frame.serial_send_bytes()
    