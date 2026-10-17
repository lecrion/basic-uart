import datetime
import time
import rich.console

serial_logger_console = rich.console.Console()

class Logger:
    @staticmethod
    def d(tag, msg):
        serial_logger_console.print(f"[{datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]}] [bold blue][DEBUG][/bold blue] [{tag}] {msg}")
    
    @staticmethod
    def i(tag, msg):
        serial_logger_console.print(f"[{datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]}] [bold green][INFO][/bold green] [{tag}] {msg}")

    @staticmethod
    def w(tag, msg):
        serial_logger_console.print(f"[{datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]}] [bold yellow][WARNING][/bold yellow] [{tag}] {msg}")
    
    @staticmethod
    def e(tag, msg):
        serial_logger_console.print(f"[{datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]}] [bold red][ERROR][/bold red] [{tag}] {msg}")


if __name__ == "__main__":
    Logger.d("114", "514")
    Logger.i("1919", "810")
    Logger.e("test", "test")