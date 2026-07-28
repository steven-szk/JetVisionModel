import time
import Jetson.GPIO as GPIO
from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.lcd.device import ili9488

GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)

serial = spi(
    bus=0, device=0,
    gpio_DC=29, gpio_RST=31,
    gpio=GPIO,
    speed_hz=4_000_000,      # 先降速排除时序问题
)

device = ili9488(
    serial_interface=serial,
    width=480, height=320,
    rotate=1, bgr=True,
    gpio=GPIO,
    gpio_LIGHT=18,
)

with canvas(device) as draw:
    draw.rectangle(device.bounding_box, outline="red", fill="black")  # 整屏铺白，最容易看出变化

print("done, holding 10s...")
time.sleep(10)