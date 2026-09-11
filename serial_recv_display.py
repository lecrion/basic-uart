import sys

while True:
    recv_buf = sys.stdin.buffer.read(1)
    if not recv_buf:
        break
    sys.stdout.buffer.write(recv_buf)
    sys.stdout.buffer.flush()