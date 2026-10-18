
from imu_frame_parser import IMUFrameParser
from imu_parser import parse_imu_frame, print_imu_data


TASK_HEX = """
EB 90 00 61 00 62 00 63 00 64 00 65 00 66
00 67 00 68 00 69 00 6A 00 6B 00 6C 00 6D 00 6E 00 6F 00 70 00 71 00 72 00 73 00
74 00 75 00 76 00 77 00 78 00 79 00 7A 00 61 00 62 00 63 00 64 00 65 00 66 00 67
00 68 00 69 00 6A 00 6B 00 6C 00 6D 00 6E 00 6F 00 70 00 71 00 72 00 73 00 74 00
75 00 76 00 77 00 78 00 79 00 7A 00 61 00 62 00 63 00 64 00 65 00 66 00
"""

FRAME_LENGTH = 119


def make_test_frame():
    """将十六进制测试数据转换为一帧字节数据。"""
    frame = bytes.fromhex(TASK_HEX)

    if len(frame) != FRAME_LENGTH:
        raise ValueError(
            f"测试数据长度错误：实际 {len(frame)} 字节，"
            f"预期 {FRAME_LENGTH} 字节"
        )

    if frame[:2] != bytes.fromhex("EB 90"):
        raise ValueError("测试数据帧头不是 EB 90")

    return frame


def test_multiple_frames(frame, frame_count=2):
    """一次输入多帧，检查拆帧器能否提取全部帧。"""
    print("\n" + "=" * 60)
    print(f"测试一：一次输入 {frame_count} 帧")
    print("=" * 60)

    # 将同一帧模拟数据重复多次，构造连续字节流
    raw_data = frame * frame_count

    parser = IMUFrameParser()
    frames = parser.feed(raw_data)

    print(f"输入总字节数：{len(raw_data)}")
    print(f"预期帧数：{frame_count}")
    print(f"实际提取帧数：{len(frames)}")
    print(f"剩余缓存字节数：{len(parser.buffer)}")

    assert len(frames) == frame_count, (
        f"帧数不匹配：预期 {frame_count}，实际 {len(frames)}"
    )

    assert all(item == frame for item in frames), "提取出的帧内容不一致"
    assert len(parser.buffer) == 0, "处理完成后不应有剩余缓存"

    print("多帧连续输入测试通过！")

    return frames


def test_fragmented_multiple_frames(frame, frame_count=5):
    """把多帧连续数据拆成多个数据块，模拟分批接收。"""
    print("\n" + "=" * 60)
    print(f"测试二：分段输入 {frame_count} 帧")
    print("=" * 60)

    raw_data = frame * frame_count
    parser = IMUFrameParser()

    # 故意使用不规则的分段长度
    chunk_sizes = [13, 50, 7, 119, 31, 200]
    frames = []
    position = 0
    chunk_index = 0

    while position < len(raw_data):
        size = chunk_sizes[chunk_index % len(chunk_sizes)]
        chunk = raw_data[position:position + size]

        new_frames = parser.feed(chunk)
        frames.extend(new_frames)

        print(
            f"第 {chunk_index + 1} 段："
            f"输入 {len(chunk)} 字节，"
            f"本段提取 {len(new_frames)} 帧，"
            f"累计提取 {len(frames)} 帧"
        )

        position += len(chunk)
        chunk_index += 1

    print(f"\n预期帧数：{frame_count}")
    print(f"实际提取帧数：{len(frames)}")
    print(f"剩余缓存字节数：{len(parser.buffer)}")

    assert len(frames) == frame_count, (
        f"分段输入后帧数不匹配：预期 {frame_count}，"
        f"实际 {len(frames)}"
    )

    assert all(item == frame for item in frames), "分段后提取的帧内容不一致"
    assert len(parser.buffer) == 0, "所有数据输入完毕后缓存应为空"

    print("多帧分段输入测试通过！")

    return frames


def test_garbage_before_frame(frame):
    """测试一：正常帧前面存在乱码"""
    print("\n========== 异常测试 1：帧前有乱码 ==========")

    parser = IMUFrameParser()

    # 模拟接收到的乱码
    garbage = bytes.fromhex("11 22 33")

    # 乱码后面接一帧正常数据
    frames = parser.feed(garbage + frame)

    assert len(frames) == 1, (
        f"预期提取 1 帧，实际提取 {len(frames)} 帧"
    )
    assert frames[0] == frame, "提取的数据帧与正常帧不一致"

    print("通过：成功跳过帧前的乱码，提取出正常数据帧")


def test_incomplete_frame(frame):
    """测试二：只接收到半帧数据"""
    print("\n========== 异常测试 2：数据帧不完整 ==========")

    parser = IMUFrameParser()

    # 只输入前 60 字节，完整帧应该是 119 字节
    partial_data = frame[:60]
    frames = parser.feed(partial_data)

    assert len(frames) == 0, (
        f"预期不提取完整帧，实际提取 {len(frames)} 帧"
    )

    print("通过：只收到 60 字节时，没有误判为完整帧")
    print("说明：剩余数据到达后，解析器才能继续尝试提取")


def test_wrong_header_before_frame(frame):
    """测试三：错误帧头后面跟着正常帧"""
    print("\n========== 异常测试 3：错误帧头后跟正常帧 ==========")

    parser = IMUFrameParser()

    # EB 91 不是规定的 EB 90 帧头
    wrong_data = bytes.fromhex("EB 91 22 33")

    frames = parser.feed(wrong_data + frame)

    if len(frames) == 1 and frames[0] == frame:
        print("通过：成功跳过错误数据，重新找到正常帧")
    else:
        print(f"未通过：实际提取 {len(frames)} 帧")
        print("说明：当前解析器可能还需要加强错误帧头后的重新同步处理")


def test_exception_data(frame):
    """统一运行异常数据测试"""
    print("\n\n################################")
    print("# 开始测试异常数据处理")
    print("################################")

    test_garbage_before_frame(frame)
    test_incomplete_frame(frame)
    test_wrong_header_before_frame(frame)

    print("\n========== 异常数据测试结束 ==========")

def main():
    # 1. 准备一帧模拟数据
    frame = make_test_frame()
    print(f"单帧数据长度：{len(frame)} 字节")
    print(f"帧头：{frame[:2].hex(' ').upper()}")

    # 2. 测试连续输入两帧
    frames_2 = test_multiple_frames(frame, frame_count=2)

    # 3. 测试连续输入五帧，但拆成多个数据块
    frames_5 = test_fragmented_multiple_frames(frame, frame_count=5)

    # 4. 展示其中一帧的字段解析结果
    print("\n" + "=" * 60)
    print("测试三：解析其中一帧的 IMU 字段")
    print("=" * 60)

    imu_data = parse_imu_frame(frames_5[0])
    print_imu_data(imu_data)

    print("\n" + "=" * 60)
    print("所有多帧模拟测试通过！")
    print("=" * 60)
    
      # 5. 新增：异常数据测试
    test_exception_data(frame)



if __name__ == "__main__":
    main()
