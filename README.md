## basic-uart

实现基本的 UART 串口收发与简单附加功能.

本科生科创项目子任务.

![task_detail_1](https://raw.githubusercontent.com/lecrion/basic-uart/main/Images/task_detail_1.jpg)

![task_detail_2](https://raw.githubusercontent.com/lecrion/basic-uart/main/Images/task_detail_2.jpg)

### 参考工具

1. UARTAssist 串口调试助手, 绿色软件, 来源 [野人家园](www.cmsoft.cn/software.html), 包含收发日志显示( 可选 ASCII/HEX ), 串口波特率, 数据位, 停止位, 校验位, 流控制等参数的配置, 接收保存到文件, 自动循环发送信号等功能. 属于较为底层的软件

![uart_assist_show](https://raw.githubusercontent.com/lecrion/basic-uart/main/Images/uart_assist_show.jpg)

1. Vofa+ 高自由度上位机, 这个软件支持的通信协议不仅限于串口, 还能够通过 UDP/TCP 接收数据. 它有一个很值得借鉴的功能就是插件驱动, 通过插件可以实现在屏幕上绘制曲线, 图表等一系列可视化组件. 同时也支持 raw 数据的显示, 以及串口全部参数的配置.

![vofa_show](https://raw.githubusercontent.com/lecrion/basic-uart/main/Images/vofa_show.jpg)

### 技术设想

1. 整体使用 Python 按模块开发, 包括: 
    - 利用 pyserial 模块, 将底层 (操作系统层) 串口数据收发功能封装为核心库, 暴露有关 API 供后续使用
    - 使用 PyQt 搭建 GUI 界面, 同时基于与核心交互的数据, 使用 PyQtGraph 绘制曲线或图像

1. 核心库可能的细节:
    - 可以同时打开很多串口, 并且分别触发不同的代码行为
    - 在内核封装简单附加功能: 临时改变串口的波特率, 校验位, bytesize 等参数; 接收时内置过滤器; 循环发送等
    - 可以作为单独的程序调用, 或者通过 import 作为子模块调用. 两种方式下, 分别通过 stdin/stdout, 函数调用和传参, 进行数据的出入.
    - 模拟串口接收中断: 目前想到的是利用 Python 的装饰器特性, 将外部模块的函数注册并绑定在核心的接收工作循环中.
    - 日志功能, 将每个串口的输入/输出都保存到各自的日志中
    
### 查找资料

最常见的应该是 UART 串口, 但是在雷达这种需要高频大量传输数据的情形下, 可能需要更高级的串口: 比如我查询网络得到的 RS-232 串口, 其除了基本的 TXD, RXD, GND 线以外, 还提供了 RTS/CTS, DSR/DTR 等硬件流控专用信号线.

**流控制**

串口硬件通过控制某条信号线上的电位, 可以将自身状态告知给对方设备(例如因缓冲区满而无法接收数据), 也可以通过某条信号线上的电位得知对方设备能否接收数据, 从而决定是否发送数据. 硬件流控不用通过上层代码实现, 而是由操作系统驱动程序与串口硬件共同保证实现.

1. RTS/CTS 硬件流控

1. DSR/DTR 硬件流控

1. Xon/Xoff 软件流控

### 项目介绍

1. `serial_test.py`

最开始 vibe coding 实现的 demo 小项目, 实现最基本的查看串口属性, 根据命令行传参决定串口参数( 波特率, 校验位等 ), 打开关闭串口等功能.

1. `serial_io_core.py`

99% 手写实现的一个串口读写内核. 

为什么要在 `pyserial` 模块已经封装很完善的情况下再额外封装一个内核呢? 

我的想法是这样的, 项目书中要求实现实时显示带时间戳的接收数据, 这就要求一个非阻塞的接收模块( 不能阻塞直到接收到指定长度的字节串, 因为这样就不能实时显示数据了 ). 而如果采用在主线程中直接使用非阻塞的 `serial.Serial.read_all()` 方法高频轮询读取的话, 又会造成大量的 CPU 开销, 且不容许主线程调用其他的阻塞函数. 日后如果添加数据分析模块和图形渲染模块的话, 也不太能接受这种性能的浪费.

所以我将读取串口数据的部分专门解耦出来, 封装到一个独立的线程 `SerialIOCore.SerialRecvThread` 中. 

串口接收线程的逻辑是: 在读到数据前持续阻塞, 读到 1 字节数据后才将缓冲区内的所有数据都读出来, 并写到日志文件 / 主进程 stdout / 子进程 stdout 中, 再进入下一个循环. 这样的优点是保证了实时性, 同时不会造成大量 CPU 开销, 我们也能在主线程中异步进行阻塞性操作, 非常的优雅.

另外, 我还想到了一种很优雅的设计, 并且实现到了代码中. 这就是通过 Python 特有的装饰器( `@decorator` ) 语法实现的事件驱动型编程. 

通过装饰器, 在定义函数时将函数名注册到接收线程维护的注册列表中, 接收线程每进行一次事件循环, 都会在特定的时机触发相应的外部函数. 具体用法可以见下面的 "代码文档" 章节.

1. `serial_recv_display.py` `serial_recv_display_utf8.py`

接收线程如果将串口收发数据都打印在主进程的控制台, 将会非常杂乱. 所以我在接收线程中新建了一个子进程, 将串口收发数据通过管道传递到子进程, 并打印在子进程的新窗口. 这样的话, 主进程控制台的命令信息或调试信息就和子进程的串口收发信息分开来了. 

`serial_recv_display.py` `serial_recv_display_utf8.py` 这两个文件就是子进程实际执行的内容: 功能都是将 stdin 读取到的字节流原封不动地打印到自己所属的控制台窗口上. 开发时发现, 第一份代码无法正确将包含中文等特殊字符的 UTF-8 字节串打印出来, 所以我 vibe coding 出了第二份代码, 也就是能够将管道中单字节传输的字节串重组为正确 UTF-8 编码再打印到屏幕上的版本. 简单来说就是第一版不能显示串口收发的中文字符, 而第二版可以.

1. `core_test.py`

用于检验将 `serial_io_core.py` 作为模块导入后能否正常工作.

1. `interface_test.py`

学习用的 demo, 测试 PyQt 模块的功能.

### API Docs

**`serial_io_core.py`**

1. `serial_io_core.list_serial_ports()`

    - 参数: 无
    - 返回值: 无
    - 简介: 调用该函数, 在命令行打印所有可用的串口号及其信息.

1. `serial_io_core.SerialIOCore`

    - 简介: 串口读写总内核, 可以实现多个串口同时输入输出.
    - 属性: 无
    - 方法:

        1. `add_serial_io(self, serial_args: dict)`

            - 参数: `serial_args: dict` 打开串口时使用的参数字典, 格式形如 `{"port": "COM3", "baudrate": 115200}`
            - 返回值: 打开的串口 `serial_io_core.SerialIOCore.SerialIO` 实例
            - 简介: 向内核添加一个串口 I/O 实例

        1. `get_serial_io(self, port: str)`

            - 参数: `port: str` 串口端口号, 形如 `"COM3"`
            - 返回值: 端口号对应的串口 `serial_io_core.SerialIOCore.SerialIO` 实例. 若端口对应实例不存在, 返回 `None`.
            - 简介: 在内核中查找端口号对应的串口 I/O 实例

        1. `remove_serial_io(self, port: str)`

            - 参数: `port: str` 串口端口号, 形如 `"COM3"`
            - 返回值: 无
            - 简介: 从内核中删除端口号对应的串口 I//O 实例.
    - 子类:

        1. `serial_io_core.SerialIOCore.SerialRecvThread`

            - 初始化:
                ```python
                serial_io_core.SerialIOCore.SerialRecvThread(
                    serial_object: serial.Serial,
                    new_console_output = True,
                    file_output = True, 
                    normal_output = False
                )
                ```