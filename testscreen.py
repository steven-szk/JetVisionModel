#!/usr/bin/env python3
"""Simple ST7796 (3.5" 320x480 SPI) test screen for Jetson Nano (Super).

Self-contained driver using spidev + Jetson.GPIO so it does NOT depend on
RPi.GPIO / luma (which don't drive the control pins on Jetson).

Wiring (defaults below use BOARD physical pin numbers on the 40-pin header):
    LCD    Jetson 40-pin
    ----   -------------
    VCC    Pin 1  (3.3V)   or Pin 2 (5V) if the board has its own regulator
    GND    Pin 6  (GND)
    SCK    Pin 23 (SPI0_SCK)   -> header "SPI 0" = spidev0.0
    MOSI   Pin 19 (SPI0_MOSI)
    CS     Pin 24 (SPI0_CS0)   -> handled by spidev (bus 0, device 0)
    DC     Pin 29 (GPIO, PQ.05)   <-- NOT 22; 22 defaults to SPI3 on Orin Nano
    RST    Pin 31 (GPIO, PQ.06)   <-- NOT 18; 18 defaults to SPI3 on Orin Nano
    BL     Pin 17 (3.3V) always-on  (GPIO can't source enough backlight current)

Enable SPI first:  sudo /opt/nvidia/jetson-io/jetson-io.py  -> Configure -> spi1 (bus0)
Run:               sudo python3 testscreen.py
"""

import time

import Jetson.GPIO as GPIO  # type: ignore  # noqa: PLR0402
import spidev  # type: ignore
from PIL import Image, ImageDraw, ImageFont  # type: ignore

# ---- Pin configuration (BOARD numbering) ----
# NOTE: On the Orin Nano dev kit, header pins 16/18/22 default to SPI3 (SFIO),
# NOT GPIO, so they can't be driven as GPIO without a pinmux change.
# Pins 29/31/32/33 default to plain GPIO -- use those for DC/RST.
PIN_DC = 29          # PQ.05 (soc_gpio32)
PIN_RST = 31         # PQ.06 (soc_gpio33)
PIN_BL = None        # backlight wired straight to 3.3V (GPIO can't source enough current)

SPI_BUS = 0          # /dev/spidev0.0
SPI_DEV = 0
SPI_HZ = 24_000_000  # drop to 24_000_000 if you see glitches

WIDTH = 480          # landscape
HEIGHT = 320


class ST7796:
    def __init__(self):
        GPIO.setmode(GPIO.BOARD)
        GPIO.setwarnings(False)
        GPIO.setup(PIN_DC, GPIO.OUT)
        GPIO.setup(PIN_RST, GPIO.OUT)
        if PIN_BL is not None:
            GPIO.setup(PIN_BL, GPIO.OUT)
            GPIO.output(PIN_BL, GPIO.HIGH)  # backlight on

        self.spi = spidev.SpiDev()
        self.spi.open(SPI_BUS, SPI_DEV)
        self.spi.max_speed_hz = SPI_HZ
        self.spi.mode = 0

        self.reset()
        self.init_display()

    # ---- low level ----
    def _cmd(self, c):
        GPIO.output(PIN_DC, GPIO.LOW)
        self.spi.writebytes([c])

    def _data(self, d):
        GPIO.output(PIN_DC, GPIO.HIGH)
        if isinstance(d, int):
            d = [d]
        # spidev caps each transfer at 4096 bytes
        for i in range(0, len(d), 4096):
            self.spi.writebytes(d[i:i + 4096])

    def reset(self):
        GPIO.output(PIN_RST, GPIO.HIGH)
        time.sleep(0.05)
        GPIO.output(PIN_RST, GPIO.LOW)
        time.sleep(0.05)
        GPIO.output(PIN_RST, GPIO.HIGH)
        time.sleep(0.15)

    def init_display(self):
        self._cmd(0x01)          # software reset
        time.sleep(0.12)
        self._cmd(0x11)          # sleep out
        time.sleep(0.12)

        self._cmd(0x3A); self._data(0x55)          # 16-bit/pixel (RGB565)
        self._cmd(0x36); self._data(0x28)          # MADCTL: landscape, BGR

        self._cmd(0xF0); self._data(0xC3)          # unlock manufacturer cmds
        self._cmd(0xF0); self._data(0x96)
        self._cmd(0xB4); self._data(0x01)
        self._cmd(0xB7); self._data(0xC6)
        self._cmd(0xC0); self._data([0x80, 0x45])
        self._cmd(0xC1); self._data(0x13)
        self._cmd(0xC2); self._data(0xA7)
        self._cmd(0xC5); self._data(0x0A)
        self._cmd(0xE8); self._data([0x40, 0x8A, 0x00, 0x00, 0x29, 0x19, 0xA5, 0x33])
        self._cmd(0xE0); self._data([0xD0, 0x08, 0x0F, 0x06, 0x06, 0x33, 0x30,
                                     0x33, 0x47, 0x17, 0x13, 0x13, 0x2B, 0x31])
        self._cmd(0xE1); self._data([0xD0, 0x0A, 0x11, 0x0B, 0x09, 0x07, 0x2F,
                                     0x33, 0x47, 0x38, 0x15, 0x16, 0x2C, 0x32])
        self._cmd(0xF0); self._data(0x3C)          # lock manufacturer cmds
        self._cmd(0xF0); self._data(0x69)

        self._cmd(0x20)          # inversion OFF (this panel shows correct colors without it)
        self._cmd(0x29)          # display on
        time.sleep(0.05)

    def _set_window(self, x0, y0, x1, y1):
        self._cmd(0x2A); self._data([x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF])
        self._cmd(0x2B); self._data([y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF])
        self._cmd(0x2C)

    def display(self, image):
        """Push a PIL RGB image (WIDTH x HEIGHT) to the panel."""
        if image.size != (WIDTH, HEIGHT):
            image = image.resize((WIDTH, HEIGHT))
        self._set_window(0, 0, WIDTH - 1, HEIGHT - 1)

        # Convert to RGB565 big-endian byte stream.
        pix = image.convert("RGB").tobytes()
        buf = bytearray(WIDTH * HEIGHT * 2)
        for i in range(0, len(pix), 3):
            r, g, b = pix[i], pix[i + 1], pix[i + 2]
            v = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            j = (i // 3) * 2
            buf[j] = v >> 8
            buf[j + 1] = v & 0xFF
        self._data(list(buf))

    def cleanup(self):
        try:
            self.spi.close()
        finally:
            GPIO.cleanup()


def build_test_image():
    image = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(image)

    # color bars across the top
    bars = [(255, 0, 0), (0, 255, 0), (0, 0, 255),
            (255, 255, 0), (0, 255, 255), (255, 0, 255), (255, 255, 255)]
    bw = WIDTH // len(bars)
    for i, c in enumerate(bars):
        draw.rectangle((i * bw, 0, (i + 1) * bw, 60), fill=c)

    # border + shapes
    draw.rectangle((5, 5, WIDTH - 6, HEIGHT - 6), outline="red", width=3)
    draw.ellipse((200, 90, 300, 190), fill="yellow")

    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        small = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except OSError:
        font = small = ImageFont.load_default()

    draw.text((20, 90), "Jetson Nano + ST7796", fill="white", font=font)
    draw.text((20, 130), "SPI Display Test OK", fill="lime", font=small)
    draw.text((20, HEIGHT - 40),
              f"{WIDTH}x{HEIGHT}  @ {SPI_HZ // 1_000_000} MHz",
              fill="cyan", font=small)
    return image


def main():
    lcd = ST7796()
    try:
        # quick flash: red -> green -> blue so you can confirm refresh works
        for color in [(255, 0, 0), (0, 255, 0), (0, 0, 255)]:
            lcd.display(Image.new("RGB", (WIDTH, HEIGHT), color))
            time.sleep(0.4)

        lcd.display(build_test_image())
        print("Render complete. Holding for 10 s...")
        time.sleep(10)
    finally:
        lcd.cleanup()


if __name__ == "__main__":
    main()
