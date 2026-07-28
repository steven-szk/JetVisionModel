#!/usr/bin/env python3
"""
DC/RST GPIO 稳态测试 —— 一次测一根脚, 高/低电平各保持 5 秒, 方便万用表稳稳地量。

正常: 读到干净的 3.3V 和 0V。
异常: 读到 1.6V 之类的中间值 或 乱跳 = 该脚在浮空(没真正驱动) 或 接触不良。

用法: sudo .venv/bin/python gpio_test.py
如需换脚测: 改下面的 PINS 即可, 例如 {15: "DC", 18: "RST"}
"""
import time
import Jetson.GPIO as GPIO

PINS = {32: "DC", 33: "RST"}
HOLD = 5   # 每个电平保持秒数

GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)

try:
    for pin, name in PINS.items():
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
        print("=" * 55)
        print(f"现在测 物理 {pin} 脚 ({name}) —— 万用表量 {pin} 脚 对 GND")
        print("=" * 55)
        for level, label, volt in [(GPIO.HIGH, "HIGH", "3.3V"),
                                   (GPIO.LOW,  "LOW ", "0V")]:
            GPIO.output(pin, level)
            print(f"  {name} 置 {label} -> 应读 {volt}, 保持 {HOLD} 秒 ...")
            time.sleep(HOLD)
        print()
    print("测完。干净 3.3V/0V = GPIO 正常; 读到 1.6V 或乱跳 = 该脚有问题。")
finally:
    GPIO.cleanup()
    print("done.")
