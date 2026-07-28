import time
import Jetson.GPIO as GPIO
from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.lcd.device import ili9341
from luma.core.util import noop

# 1. 显式设定 Jetson 为 BOARD 编号模式（物理引脚 29, 31）
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)

# 2. 配置 SPI 接口
# 设置 gpio_LIGHT=noop() 可防止 luma 内部尝试重新 setmode(BCM)
serial = spi(
    bus=0,
    device=0,
    gpio_DC=29,
    gpio_RST=31,
    gpio=GPIO,
    speed_hz=10_000_000
)

# 3. 初始化设备
# 配合 gpio_LIGHT=noop() 屏蔽 luma 底层的自动 setmode 逻辑
device = ili9341(
    serial_interface=serial,
    width=480,
    height=320,
    rotate=1,
    bgr=True,
    gpio=GPIO,
    gpio_LIGHT=noop()
)

# 4. 绘图测试
with canvas(device) as draw:
    draw.rectangle(device.bounding_box, outline="red", fill="black")
    draw.rectangle((10, 10, 470, 70), fill="blue")
    draw.text((20, 30), "Hello Jetson Orin Nano!", fill="white")
    draw.text((20, 100), "Driven by luma.lcd + Jetson.GPIO", fill="green")

print("Render successful! Holding for 5 seconds...")
time.sleep(5)