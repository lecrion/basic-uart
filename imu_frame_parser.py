
"""
imu_frame_parser.py

功能：
1. 接收串口传来的原始 bytes；
2. 缓存不完整的数据；
3. 根据 EB 90 查找 IMU 帧头；
4. 每次提取完整的 119 字节数据帧；
5. 提供小端序字段读取工具。

注意：
- 当前协议帧长固定为 119 字节。
- 任务书示例中的第 3 字节帧长是 0，与固定 119 字节存在矛盾。
  因此本版本不依赖第 3 字节判断帧长，而是按固定长度提取。
- 任务书说明帧末尾有校验和，但尚未确认校验和算法，
  所以本版本只做帧头和帧长度检查，不声称完成了校验和验证。
"""

import struct


FRAME_HEADER = b"\xEB\x90"
FRAME_LENGTH = 119


class IMUFrameParser:

    def __init__(self):
        # 保存上次未能组成完整帧的数据
        self.buffer = bytearray()

        # 统计信息，便于后续测试
        self.frames_ok = 0
        self.bytes_discarded = 0

    def feed(self, data: bytes) -> list[bytes]:
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("feed() 需要原始 bytes 数据，不能传入十六进制字符串")

        if not data:
            return []

        self.buffer.extend(data)
        frames = []

        while True:
            # 查找帧头 EB 90
            header_pos = self.buffer.find(FRAME_HEADER)

            if header_pos < 0:
                keep_last_eb = (
                    len(self.buffer) > 0
                    and self.buffer[-1] == FRAME_HEADER[0]
                )

                if keep_last_eb:
                    discarded = len(self.buffer) - 1
                    if discarded > 0:
                        del self.buffer[:discarded]
                        self.bytes_discarded += discarded
                else:
                    self.bytes_discarded += len(self.buffer)
                    self.buffer.clear()

                break

            # 丢弃帧头之前的干扰数据
            if header_pos > 0:
                del self.buffer[:header_pos]
                self.bytes_discarded += header_pos

            # 如果数据还不足 119 字节，留在缓存中等下一次接收
            if len(self.buffer) < FRAME_LENGTH:
                break

            # 按固定长度提取一帧
            candidate = bytes(self.buffer[:FRAME_LENGTH])

            if not candidate.startswith(FRAME_HEADER):
                del self.buffer[0]
                self.bytes_discarded += 1
                continue

            # 提取成功，从缓存中删除这 119 字节
            del self.buffer[:FRAME_LENGTH]

            frames.append(candidate)
            self.frames_ok += 1

        return frames

    def reset(self):
        self.buffer.clear()
        self.frames_ok = 0
        self.bytes_discarded = 0


def read_u8(frame: bytes, offset: int) -> int:
    return struct.unpack_from("<B", frame, offset)[0]


def read_u16(frame: bytes, offset: int) -> int:
    return struct.unpack_from("<H", frame, offset)[0]


def read_u32(frame: bytes, offset: int) -> int:
    return struct.unpack_from("<I", frame, offset)[0]


def read_s8(frame: bytes, offset: int) -> int:
    return struct.unpack_from("<b", frame, offset)[0]


def read_s16(frame: bytes, offset: int) -> int:
    return struct.unpack_from("<h", frame, offset)[0]


def read_s32(frame: bytes, offset: int) -> int:
    return struct.unpack_from("<i", frame, offset)[0]


def read_f32(frame: bytes, offset: int) -> float:
    return struct.unpack_from("<f", frame, offset)[0]

def frame_to_hex(frame: bytes) -> str:
    return " ".join(f"{byte:02X}" for byte in frame)
