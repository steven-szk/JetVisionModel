from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.lcd.device import ili9341  # 导入 ili9341 驱动类
import Jetson.GPIO as GPIO
from PIL import Image, ImageDraw, ImageFont
import time

# ---- 引脚配置 (BOARD 物理编号) ----
# DC = Pin 29, RST = Pin 31
GPIO.setmode(GPIO.BOARD)

serial = spi(
    bus=0, 
    device=0, 
    cs_high=False,
    gpio_DC=29, 
    gpio_RST=31,
    gpio=GPIO,                 # 指定使用 Jetson.GPIO
    speed_hz=10_000_000        # 10MHz 稳定频率
)

# ---- 初始化显示屏设备 ----
# ST7796 使用 ili9341 驱动类，分辨率设为 480x320，rotate=1 轴旋转
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