
import struct

from imu_frame_parser import (
    read_u8,
    read_u16,
    read_u32,
    read_s8,
    read_s16,
    read_s32,
    read_f32,
)


def parse_imu_frame(frame):
    """按照 IMU 字段表解析一帧 119 字节数据。"""

    if len(frame) != 119:
        raise ValueError(
            f"帧长度错误：预期 119 字节，实际 {len(frame)} 字节"
        )

    if frame[0:2] != b"\xEB\x90":
        raise ValueError("帧头错误，应为 EB 90")

    
    data = {
        "frame_header": frame[:2].hex(" ").upper(),
        "frame_length": read_u8(frame, 2),
        "frame_id": read_u8(frame, 3),
        "frame_counter": read_u32(frame, 4),

        "imu_status": format(read_u8(frame, 8), "08b"),

        "pitch": round(read_f32(frame, 9), 2),
        "roll": round(read_f32(frame, 13), 2),
        "yaw": round(read_f32(frame, 17), 2),
        "yaw_gps": round(read_f32(frame, 21), 2),

        "pitch_rate": round(read_f32(frame, 25), 2),
        "roll_rate": round(read_f32(frame, 29), 2),
        "yaw_rate": round(read_f32(frame, 33), 2),

        "lon": read_s32(frame, 37) * 0.0000001,
        "lat": read_s32(frame, 41) * 0.0000001,
        "alt_baro": read_s32(frame, 45) * 0.01,
        "alt_gps": read_s32(frame, 49) * 0.01,
        "alt": read_s32(frame, 53) * 0.01,

        "velocity_n": round(read_f32(frame, 57), 2),
        "velocity_e": round(read_f32(frame, 61), 2),
        "velocity_d": round(read_f32(frame, 65), 2),
        "velocity_air": round(read_f32(frame, 69), 2),

        "accel_n": round(read_f32(frame, 73), 2),
        "accel_e": round(read_f32(frame, 77), 2),
        "accel_d": round(read_f32(frame, 81), 2),

        "satellite_num": read_u8(frame, 85),
        "hdop": round(read_u16(frame, 86) * 0.01, 2),
        "vdop": round(read_u16(frame, 88) * 0.01, 2),
        "gps_status": read_u8(frame, 90),
        "gps_hh": read_u8(frame, 91),
        "gps_mm": read_u8(frame, 92),
        "gps_ss": read_u8(frame, 93),

        "temperature": read_s8(frame, 94),
        "HDT": round(read_s16(frame, 95) * 0.1, 2),
        "HDG_Dev": round(read_s16(frame, 97) * 0.1, 2),

        "redundancy": format(read_u8(frame, 99), "08b"),

        "GPSO_DT": read_u8(frame, 100) * 100,
        "GPS1DT": read_u8(frame, 101) * 100,

        "GPS_vn": round(read_f32(frame, 102), 2),
        "GPS_ve": round(read_f32(frame, 106), 2),
        "GPS_vd": round(read_f32(frame, 110), 2),

        "gps_ms": read_u16(frame, 114),
        "gps_day": read_u8(frame, 116),
        "gps_week": read_u16(frame, 117),
    }

    return data



def print_imu_data(data):
    for name, value in data.items():
        print(f"{name:16s}: {value}")


if __name__ == "__main__":
    print("请在测试文件中导入 parse_imu_frame，")
    print("将 IMUFrameParser 提取出的完整帧传入解析函数。")
