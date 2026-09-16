import sys
import os
import codecs


sys.stdout.reconfigure(encoding = "utf-8", errors = "replace")
decoder = codecs.getincrementaldecoder("utf-8")(errors = "replace")

if len(sys.argv) > 1:
    os.system(f"title {sys.argv[1]}")

while True:
    recv_buf = sys.stdin.buffer.read(1)
    if not recv_buf:
        break
    display_text = decoder.decode(recv_buf, final = False)
    if display_text:
        sys.stdout.write(display_text)
        sys.stdout.flush()

remaining_text = decoder.decode(b"", final = True)
if remaining_text:
    sys.stdout.write(remaining_text)
    sys.stdout.flush()