#!/usr/bin/env python3
"""
Pinout:
    Jetson GPIO 3 (SDA) -> ESP SDA
    Jetson GPIO 5 (SCL) -> ESP SCL
    Jetson GND (GPIO 6)    -> ESP GND
    
ESP32 I2C Controller Class
"""
import time
from smbus2 import SMBus, i2c_msg # type: ignore


class sendESP:
    def __init__(self, bus_id: int = 7, address: int = 0x08):
        self.bus_id = bus_id
        self.address = address
        self.bus = SMBus(self.bus_id)

    def send_bytes(self, data: bytes) -> bool:
        """Write payload with header 'S' directly to ESP32."""
        try:
            msg = i2c_msg.write(self.address, b'S' + data)
            self.bus.i2c_rdwr(msg)
            return True
        except OSError as e:
            print(f"[I2C Error] Bus {self.bus_id}, Addr 0x{self.address:02X}: {e}")
            return False

    def send_string(self, text: str) -> bool:
        return self.send_bytes(text.encode('utf-8'))

    def init(self, ip_str: str = None) -> bool: #at init, send ip
        if ip_str is None:
            import getIP
            ip_str = getIP.get_ip()
        return self.send_string(f"IP{ip_str}")

    def close(self):
        self.bus.close()

if __name__ == "__main__":
    controller = sendESP()
    try:
        controller.init()
        counter = 1
        while True:
            text = f"hello {counter}"
            try:
                controller.send_string(text)
                print("sent:", text)
            except OSError as e:
                print(f"fail to send esp")
            counter += 1
            time.sleep(1)
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        controller.close()
