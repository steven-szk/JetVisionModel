#!/usr/bin/env python3
"""
Jetson -> ESP32 I2C 发送 (Jetson 作 I2C 主机)

接线:
    Jetson 物理 3 脚 (SDA) -> ESP SDA
    Jetson 物理 5 脚 (SCL) -> ESP SCL
    Jetson GND (物理 6)    -> ESP GND   (必须共地)

Orin Nano 上 物理 3/5 脚 = /dev/i2c-7。
若 i2cdetect -l 显示的编号不同, 改下面的 I2C_BUS。

用法:
    .venv/bin/pip install smbus2
    .venv/bin/python i2c_send.py
"""
import time
from smbus2 import SMBus, i2c_msg

I2C_BUS = 7          # 物理 3/5 脚对应的总线号 (Orin Nano = 7)
ESP_ADDR = 0x08      # ESP32 从机地址, 必须和 ESP 端代码一致


def send_bytes(bus, addr, data: bytes):
    """把任意字节原样写给从机 (i2c_rdwr 不需要寄存器地址, 最通用)。"""
    msg = i2c_msg.write(addr, data)
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


if __name__ == "__main__":
    main()
