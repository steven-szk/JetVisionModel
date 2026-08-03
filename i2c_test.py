#!/usr/bin/env python3
"""
I2C 发送测试: Jetson -> ESP32 (i2c-7, 地址 0x08), ESP 只接收。

Jetson 端能验证的是"每次写入有没有被 ACK"(没报错=ESP 收到了)。
数据内容对不对, 到 ESP 串口监视器(115200)里看 "got: ..."。

用法:
    .venv/bin/pip install smbus2
    .venv/bin/python i2c_test.py
"""
import time
from smbus2 import SMBus, i2c_msg

I2C_BUS = 7
ESP_ADDR = 0x08


def probe(bus, addr):
    """探测从机是否应答 (ACK)。"""
    try:
        bus.write_quick(addr)
        return True
    except OSError:
        return False


def send(bus, addr, data: bytes):
    bus.i2c_rdwr(i2c_msg.write(addr, data))


def main():
    passed = failed = 0
    with SMBus(I2C_BUS) as bus:
        print(f"===== I2C 发送测试  bus=i2c-{I2C_BUS}  addr=0x{ESP_ADDR:02X} =====\n")

        # [1] 存在性检测
        if probe(bus, ESP_ADDR):
            print("[1] 存在性检测: ACK ✅\n")
            passed += 1
        else:
            print("[1] 存在性检测: 无应答 ❌ (检查接线/共地/ESP 是否在跑)")
            return

        # [2] 发送各种类型的数据, 逐条确认被 ACK
        print("[2] 发送测试 (去 ESP 串口看 got: 内容)")
        cases = [
            b"hello",                       # 字符串
            b"1234567890",                  # 长一点
            bytes([0x01, 0x02, 0x03]),      # 原始字节
            bytes([0xAA, 0x55, 0xFF, 0x00]),
            "温度25".encode("utf-8"),       # 中文/UTF-8
        ]
        for payload in cases:
            try:
                send(bus, ESP_ADDR, payload)
                print(f"    发出 {payload}  ✅ ACK")
                passed += 1
            except OSError as e:
                print(f"    发出 {payload}  ❌ {e}")
                failed += 1
            time.sleep(0.3)

        # [3] 连续压力测试: 快速发 50 条
        print("\n[3] 连续发送 50 条 (压力测试)")
        for i in range(50):
            try:
                send(bus, ESP_ADDR, f"n={i}".encode())
                passed += 1
            except OSError as e:
                print(f"    第 {i} 条失败: {e}")
                failed += 1
            time.sleep(0.02)
        print(f"    完成, 失败 {failed} 条")

    print(f"\n===== 结果: {passed} 通过, {failed} 失败 =====")
    if failed == 0:
        print("Jetson -> ESP 发送链路正常 🎉  (内容请在 ESP 串口核对)")


if __name__ == "__main__":
    main()
