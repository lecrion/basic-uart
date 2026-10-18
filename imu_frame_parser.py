
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
