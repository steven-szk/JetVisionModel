import time
import Jetson.GPIO as GPIO
from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.lcd.device import ili9486

GPIO.setmode(GPIO.BOARD)
time.sleep(0.1)
GPIO.setup(29, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(31, GPIO.OUT, initial=GPIO.LOW)
time.sleep(0.1)
GPIO.setwarnings(False)

serial = spi(
    bus=0,
    device=0,
    gpio_DC=29,
    gpio_RST=31,
    gpio=GPIO,
    speed_hz=16_000_000
)

# 关键：width 和 height 填原生物理尺寸 320x480
# rotate=1 代表顺时针旋转 90 度，自动变为 480x320 横屏
device = ili9486(
    serial_interface=serial,
    width=320,
    height=480,
    rotate=1,
    bgr=True,
    gpio=GPIO,
    gpio_LIGHT=18
)

# 此时 device.bounding_box 会自动变成 (0, 0, 480, 320)
with canvas(device) as draw:
    draw.rectangle(device.bounding_box, outline="red", fill="black")
    draw.rectangle((10, 10, 470, 70), fill="blue")
    draw.text((20, 30), "Hello ST7796 via ili9486!", fill="white")
    draw.text((20, 100), "Landscape 480x320", fill="green")

print("Render successful!")
time.sleep(5)