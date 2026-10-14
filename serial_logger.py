import datetime
import time

class Logger:
    def d(self, tag, msg):
        print(f"[{datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]}] [DEBUG] [{tag}] {msg}")
    
    def i(self, tag, msg):
        print(f"[{datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]}] [INFO] [{tag}] {msg}")

    def w(self, tag, msg):
        print(f"[{datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]}] [WARNING] [{tag}] {msg}")
    
    def e(self, tag, msg):
        print(f"[{datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]}] [ERROR] [{tag}] {msg}")

Logger = Logger()

if __name__ == "__main__":
    Logger.d("114", "514")
    Logger.i("1919", "810")
    Logger.e("test", "test")