#!/usr/bin/env python3
"""
Jetson -> ESP32 I2C send info

Pinout:
    Jetson GPIO 3 (SDA) -> ESP SDA
    Jetson GPIO 5 (SCL) -> ESP SCL
    Jetson GND (GPIO 6)    -> ESP GND

"""
import time
from smbus2 import SMBus, i2c_msg # type: ignore

I2C_BUS = 7
ESP_ADDR = 0x08


def send_bytes(bus, addr, data: bytes):
    """write message to esp32 with header 'S'"""
    msg = i2c_msg.write(addr, b'S' + data)
    bus.i2c_rdwr(msg)


def main():
    counter = 1
    with SMBus(I2C_BUS) as bus:
        while True:
            text = f"hello {counter}"
            try:
                send_bytes(bus, ESP_ADDR, text.encode())
                print("sent:", text)
            except OSError as e:
                print(f"fail to send esp")
            counter += 1
            time.sleep(1)

def init():
    """test esp by sending IP of the Jetson to it"""
    import getIP
    ip = getIP.get_ip()
    try:
        with SMBus(I2C_BUS) as bus:
            send_bytes(bus, ESP_ADDR, f"IP{ip}".encode()) #send with header IP
            print(f"sent IP {ip} to 0x{ESP_ADDR:02X} @ i2c-{I2C_BUS}")
    except OSError as e:
        print(f"fail to init esp: {e}")


if __name__ == "__main__":
    init()
    main()
