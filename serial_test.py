import argparse

import serial
import serial.tools.list_ports


def list_serial_ports():
    """Print the port metadata reported by the operating system."""
    ports_list = list(serial.tools.list_ports.comports())
    if not ports_list:
        print("No serial ports found.")
        return []

    print("Available serial ports:")
    for port in ports_list:
        print(f"\nDevice: {port.device}")
        print(f"  Name: {port.name}")
        print(f"  Description: {port.description}")
        print(f"  Hardware ID: {port.hwid}")
        print(f"  VID: {port.vid}")
        print(f"  PID: {port.pid}")
        print(f"  Serial number: {port.serial_number}")
        print(f"  Location: {port.location}")
        print(f"  Manufacturer: {port.manufacturer}")
        print(f"  Product: {port.product}")
        print(f"  Interface: {port.interface}")

    return ports_list


def open_and_configure_port(port_name, baudrate):
    """Open one port with the requested communication parameters."""
    serial_port = serial.Serial(
        port=port_name,
        baudrate=baudrate,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=114514,
        write_timeout=1,
        rtscts=False,
        dsrdtr=False,
    )

    print(f"\nOpened: {serial_port.port}")
    print(f"  Baudrate: {serial_port.baudrate}")
    print(f"  Bytesize: {serial_port.bytesize}")
    print(f"  Parity: {serial_port.parity}")
    print(f"  Stopbits: {serial_port.stopbits}")
    print(f"  Read timeout: {serial_port.timeout}")
    print(f"  Write timeout: {serial_port.write_timeout}")
    print(f"  RTS/CTS: {serial_port.rtscts}")
    print(f"  DSR/DTR: {serial_port.dsrdtr}")
    print(f"  Is open: {serial_port.is_open}")

    print("\ntesting serial write")
    serial_port.write(b"serial port IO test\n")
    serial_port.write(bytes.fromhex("12 34 56 78 9A BC DE"))
    serial_port.flush()

    print("testing serial read")
    serial_port.reset_input_buffer()
    data = serial_port.read(size = 10)
    print(f"read {len(data)} bytes: hex: {data.hex()} ASCII: {data.decode(errors='replace')}")

    serial_port.close()
    print(f"Closed: {serial_port.port}")


def main():
    parser = argparse.ArgumentParser(description="List and test serial ports.")
    parser.add_argument(
        "--port",
        help="Port to open, for example COM3."
    )
    parser.add_argument(
        "--baudrate",
        type=int,
        default=115200,
        help="Baudrate used when opening the port (default: 115200).",
    )
    args = parser.parse_args()

    ports_list = list_serial_ports()
    if args.port:
        known_ports = {port.device for port in ports_list}
        if args.port not in known_ports:
            print(f"\nWarning: {args.port} was not found during enumeration.")
        try:
            open_and_configure_port(args.port, args.baudrate)
        except serial.SerialException as error:
            print(f"Could not open {args.port}: {error}")


if __name__ == "__main__":
    main()