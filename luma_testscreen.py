import time
import Jetson.GPIO as GPIO
from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.lcd.device import ili9341
from PIL import Image, ImageDraw, ImageFont

# ---- 引脚配置 ----
# 注意：不需手动执行 GPIO.setmode()，直接在 spi 初始化中指定使用 Jetson.GPIO
# gpio_DC=29, gpio_RST=31 (BOARD 物理针脚编号)
serial = spi(
    bus=0,
    device=0,
    gpio_DC=29,
    gpio_RST=31,
    gpio=GPIO,                 # 明确使用 Jetson.GPIO
    speed_hz=10_000_000        # 10MHz 稳定时钟
)

# ---- 初始化显示屏设备 ----
# ST7796 借用 ili9341 驱动，分辨率设为 480x320，rotate=1 轴旋转
device = ili9341(
    serial_interface=serial,
    width=480,
    height=320,
    rotate=1,
    bgr=True
)

# ---- 测试绘图 ----
with canvas(device) as draw:
    draw.rectangle(device.bounding_box, outline="red", fill="black")
    draw.rectangle((10, 10, 470, 70), fill="blue")
    draw.text((20, 30), "Hello Jetson Orin Nano!", fill="white")
    draw.text((20, 100), "Driven by luma.lcd (ili9341 driver)", fill="green")

print("Render successful! Holding for 5 seconds...")
time.sleep(5)