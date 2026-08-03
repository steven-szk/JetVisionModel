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
    counter = 0
    with SMBus(I2C_BUS) as bus:
        print(f"向 0x{ESP_ADDR:02X} @ i2c-{I2C_BUS} 每秒发一条, Ctrl-C 停")
        while True:
            text = f"hello {counter}"
            try:
                send_bytes(bus, ESP_ADDR, text.encode())
                print("sent:", text)
            except OSError as e:
                # 从机没应答 (地址错/没上电/线没接好) 会到这里
                print(f"发送失败: {e}  (检查地址/接线/共地)")
            counter += 1
            time.sleep(1)

def init():
    """test esp by sending IP of the Jetson to it"""
    import getIP
    ip = getIP.get_ip()
    with SMBus(I2C_BUS) as bus:
        send_bytes(bus, ESP_ADDR, f"IP{ip}".encode()) #send with header IP
        print(f"sent IP {ip} to 0x{ESP_ADDR:02X} @ i2c-{I2C_BUS}")


if __name__ == "__main__":
    init()
    main()
