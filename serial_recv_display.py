import sys
import os

if len(sys.argv) > 1:
    os.system(f"title {sys.argv[1]}")

while True:
    recv_buf = sys.stdin.buffer.read(1)
    if not recv_buf:
        sys.stdout.buffer.write(b"stdin buffer read error\n")
        sys.stdout.buffer.flush()
        break
    sys.stdout.buffer.write(b"|")
    sys.stdout.buffer.write(recv_buf)
    sys.stdout.buffer.flush()