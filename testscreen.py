import time

from luma.core.interface.serial import spi  # type: ignore
from luma.lcd.device import st7796  # type: ignore
from PIL import Image, ImageDraw, ImageFont  # type: ignore


def main():
    # 1. 初始化 SPI 通信接口
    # bus=0, device=0 对应 Jetson Nano 的 /dev/spidev0.0
    # gpio_DC=22, gpio_RST=18 对应物理引脚 Pin 22 和 Pin 18
    serial = spi(
        port=0, 
        device=0, 
        gpio_DC=22, 
        gpio_RST=18, 
        bus_speed_hz=40000000  # 40MHz SPI 速率
    )

    # 2. 初始化 ST7796 屏幕 (分辨率 480x320)
    device = st7796(serial, width=480, height=320, rotate=0)

    # 3. 使用 Pillow 绘制图像缓冲区
    # 建立 RGB 画布，背景色设为黑色 (0, 0, 0)
    image = Image.new("RGB", (device.width, device.height), (0, 0, 0))
    draw = ImageDraw.Draw(image)

    # 绘制矩形框（红色外框）
    draw.rectangle((10, 10, device.width - 10, device.height - 10), outline="red", width=3)

    # 绘制填充矩形（蓝色）
    draw.rectangle((30, 30, 150, 100), fill="blue")

    # 绘制圆形（黄色）
    draw.ellipse((200, 30, 300, 130), fill="yellow")

    # 写入文字（白色）
    draw.text((30, 150), "Jetson Nano + ST7796", fill="white")
    draw.text((30, 180), "SPI Display Test Success!", fill="green")

    # 4. 刷新图像到屏幕
    device.display(image)

    print("屏幕渲染完成，保持显示 10 秒...")
    time.sleep(10)

if __name__ == "__main__":
    main()