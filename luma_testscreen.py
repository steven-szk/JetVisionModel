import time
import Jetson.GPIO as GPIO
from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.lcd.device import ili9486   # 若上面查到有 st7796 就改成 st7796

GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)

serial = spi(
    bus=1, device=0,
    gpio_DC=29, gpio_RST=31,
    gpio=GPIO,
    speed_hz=16_000_000,
)

device = ili9486(
    serial_interface=serial,
    width=320, height=480,
    rotate=1, bgr=True,
    gpio=GPIO,
    gpio_LIGHT=18,        # 合法引脚，不要再用 noop()
)

with canvas(device) as draw:
    draw.rectangle(device.bounding_box, outline="red", fill="black")
    draw.text((20, 30), "Hello Jetson Orin Nano!", fill="white")

print("Render successful! Holding for 5 seconds...")
time.sleep(5)