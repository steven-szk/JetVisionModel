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

    def send_info(self, data: str) -> bool:
        """Write payload with header 'S' directly to ESP32."""
        try:
            msg = i2c_msg.write(self.address, b'S' + data.encode('utf-8'))
            self.bus.i2c_rdwr(msg)
            return True
        except OSError as e:
            print(f"[I2C Error] Bus {self.bus_id}, Addr 0x{self.address:02X}: {e}")
            return False

    def send_result(self, regions) -> bool:
        """Send a per-defect count summary to the ESP with the 'RES' header.

        'regions' is the list returned by infermodel.infer(). The full contours are
        far too big for the 128-byte I2C buffer, so we send counts per defect type,
        e.g. 'crack:2 delam:5 scratch:0 coating:1'. On the wire this is
        b'S' + b'RES' + summary: 'S' is the header the ESP firmware gates on, and
        'RES' tags it as a result (route it to the RESULTS panel on the ESP side)."""
        counts = {}
        for r in regions:
            feat = r.get("feature")
            if feat == "edge":          # edge is the electrode boundary, not a defect
                continue
            counts[feat] = counts.get(feat, 0) + 1
        summary = " ".join(f"{feat}:{counts.get(feat, 0)}"
                           for feat in ("crack", "delam", "scratch", "coating"))
        return self.send_info(f"RES {summary}")

    def init(self, ip_str: str = None) -> bool: #at init, send ip
        if ip_str is None:
            import getIP
            ip_str = getIP.get_ip()
        return self.send_info(f"IP{ip_str}")

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
                controller.send_info(text)
                print("sent:", text)
            except OSError as e:
                print(f"fail to send esp")
            counter += 1
            time.sleep(1)
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        controller.close()
