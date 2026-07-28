import time
import Jetson.GPIO as GPIO
from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.lcd.device import ili9486  # 使用 ili9486

GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)

serial = spi(
    bus=0,
    device=0,
    gpio_DC=29,
    gpio_RST=31,
    gpio=GPIO,
    speed_hz=10_000_000
)

# 初始化设备（ili9486 默认物理分辨率即为 320x480）
device = ili9486(
    serial_interface=serial,
    width=480,
    height=320,
    rotate=1,
    bgr=True,
    gpio=GPIO,
    gpio_LIGHT=18
)

with canvas(device) as draw:
    draw.rectangle(device.bounding_box, outline="red", fill="black")
    draw.text((20, 30), "Hello ST7796 (via ili9486)", fill="white")

time.sleep(5)