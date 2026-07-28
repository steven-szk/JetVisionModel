from luma.core.interface.serial import spi # type: ignore
from luma.lcd.device import st7796 # type: ignore
from PIL import Image, ImageDraw, ImageFont
import Jetson.GPIO as GPIO # type: ignore
import time

# ---- 引脚配置 (BOARD 编号) ----
# DC = Pin 29, RST = Pin 31
# 注意：luma 内部支持直接使用 GPIO 编号
serial = spi(
    bus=0, 
    device=0, 
    cs_high=False,
    gpio_DC=29, 
    gpio_RST=31,
    gpio=GPIO,                 # 明确指定使用 Jetson.GPIO
    speed_hz=10_000_000        # 10MHz 稳定频率
)

# ---- 初始化 ST7796 显示屏设备 ----
# 3.5 寸屏幕分辨率为 480x320，rotate=1 代表横屏
device = st7796(
    serial_interface=serial, 
    width=480, 
    height=320, 
    rotate=1, 
    bgr=True
)

# ---- 绘图与显示 ----
# luma 提供了非常优雅的 Canvas 上下文，画完自动刷新到屏幕
with canvas(device) as draw:
    draw.rectangle(device.bounding_box, outline="white", fill="black")
    draw.rectangle((10, 10, 470, 70), fill="blue")
    draw.text((20, 30), "Hello Jetson Orin Nano!", fill="white")
    draw.text((20, 100), "Driven by luma.lcd", fill="green")

print("Render successful!")
time.sleep(5)