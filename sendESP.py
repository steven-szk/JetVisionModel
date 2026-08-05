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

    def send_result(self, regions):
        """Send an area summary to the ESP with the 'RES' header.

        'regions' is the list returned by infermodel.infer(). Sends the electrode
        (edge) contour area, then each defect type as a percentage of that area, e.g.
            'EDGEarea:152340 crack:2.34% delam:0.12% scratch:0.00% coating:1.05%'
        On the wire this is b'S' + b'RES' + summary ('S' is the header the ESP firmware
        gates on, 'RES' tags it as a result). Area is in pixels of the captured frame;
        percentages are defect_area / electrode_area. If no edge is found the area is
        0 and every percentage is 0."""
        edge_area = sum(r.get("area", 0.0) for r in regions if r.get("feature") == "edge")
        defect_area = {}
        for r in regions:
            feat = r.get("feature")
            if feat == "edge":          # edge is the electrode boundary, not a defect
                continue
            defect_area[feat] = defect_area.get(feat, 0.0) + r.get("area", 0.0)

        def pct(feat):
            return 100.0 * defect_area.get(feat, 0.0) / edge_area if edge_area else 0.0

        summary = f"EDGEarea:{edge_area:.0f}px " + " ".join(
            f"{feat}:{pct(feat):.2f}%" for feat in ("crack", "delam", "scratch", "coating"))
        
        tot_defect_percent = sum(defect_area.values()) / edge_area * 100 if edge_area else 0
        result_state = "PASS" if tot_defect_percent > 10.0 else "FAIL"
        
        self.send_info(f"RES{summary}")
        time.sleep(0.1)
        self.send_info("STATE" + result_state)

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
