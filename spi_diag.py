#!/usr/bin/env python3
"""
ST7796 白屏诊断脚本 —— 一次跑完两个测试，定位到底是哪根信号没通。

用法:
    .venv/bin/pip install spidev        # 只需装一次
    sudo .venv/bin/python spi_diag.py

测试 A (SPI 回环): 用一根跳线把【物理 19 脚(MOSI) 短接到 物理 21 脚(MISO)】,
                  屏幕可以不用拔。跑完看哪个 bus 显示 ✅通。
测试 B (GPIO 翻转): 用万用表量【物理 29 / 31 脚 对 GND】的电压,
                  应每秒在 0V <-> 3.3V 之间跳。
"""

import time
import Jetson.GPIO as GPIO

DC_PIN = 29
RST_PIN = 31


# ---------------------------------------------------------------------------
# 测试 A: SPI 回环 (loopback)
# ---------------------------------------------------------------------------
def test_spi_loopback():
    print("=" * 60)
    print("测试 A: SPI 回环")
    print("请确认已用跳线把【物理 19 脚】短接到【物理 21 脚】")
    print("=" * 60)

    try:
        import spidev
    except ImportError:
        print("❌ 没装 spidev, 先运行:  .venv/bin/pip install spidev")
        return

    sent = [0xAA, 0x55, 0xF0, 0x0F]
    found = []
    for bus in (0, 1):
        try:
            s = spidev.SpiDev()
            s.open(bus, 0)
            s.max_speed_hz = 1_000_000
            s.mode = 0
            got = s.xfer2(list(sent))
            s.close()
            ok = (got == sent)
            print(f"  bus {bus}.0 : sent={sent} got={got}  "
                  f"{'✅通 <== 用这个 bus' if ok else '❌不通'}")
            if ok:
                found.append(bus)
        except Exception as e:
            print(f"  bus {bus}.0 : 打不开 ({e})")

    print("-" * 60)
    if found:
        print(f"结论: bus {found} 的 MOSI/SCK 通路正常, 后面驱动就用 bus={found[0]}")
    else:
        print("结论: 两个 bus 都不通 == 物理 19 脚没有 SPI 信号")
        print("      -> jetson-io 里的 SPI1 没真正生效, 十有八九是【改完没重启】")
    print()


# ---------------------------------------------------------------------------
# 测试 B: DC / RST 的 GPIO 翻转
# ---------------------------------------------------------------------------
def test_gpio_toggle(seconds=20):
    print("=" * 60)
    print("测试 B: GPIO 翻转 (DC=29, RST=31)")
    print(f"用万用表量【物理 {DC_PIN} / {RST_PIN} 脚 对 GND】, 应每秒 0V <-> 3.3V 跳")
    print(f"持续 {seconds} 秒...")
    print("=" * 60)

    GPIO.setup(DC_PIN, GPIO.OUT)
    GPIO.setup(RST_PIN, GPIO.OUT)

    for i in range(seconds):
        level = i % 2                      # 0,1,0,1...
        GPIO.output(DC_PIN, level)
        GPIO.output(RST_PIN, level)
        print(f"  [{i+1:2d}/{seconds}]  29 -> {'3.3V' if level else '0V  '}   "
              f"31 -> {'3.3V' if level else '0V'}")
        time.sleep(1)

    print("-" * 60)
    print("如果电压【不跳】(一直 0V 或一直 3.3V) -> 这个 GPIO 没真正放出来")
    print()


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    GPIO.setmode(GPIO.BOARD)
    GPIO.setwarnings(False)
    try:
        test_spi_loopback()
        input("测试 A 完成。拿好万用表, 按【回车】开始测试 B ...")
        test_gpio_toggle(20)
    finally:
        GPIO.cleanup()
        print("done. GPIO 已清理。")
