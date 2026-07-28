import time
import spidev
import Jetson.GPIO as GPIO

BUS, DEV = 1, 0          # ← 如果没反应，把这里改成 1, 0 再跑一次
DC, RST = 29, 31

GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)
GPIO.setup(DC, GPIO.OUT)
GPIO.setup(RST, GPIO.OUT)

spi = spidev.SpiDev()
spi.open(BUS, DEV)
spi.max_speed_hz = 4_000_000
spi.mode = 0

def cmd(c):
    GPIO.output(DC, 0)
    spi.writebytes([c])

def dat(*d):
    GPIO.output(DC, 1)
    spi.writebytes(list(d))

# 硬复位
GPIO.output(RST, 1); time.sleep(0.05)
GPIO.output(RST, 0); time.sleep(0.05)
GPIO.output(RST, 1); time.sleep(0.15)

# ---- ST7796 初始化序列 ----
cmd(0x01); time.sleep(0.12)          # SWRESET
cmd(0x11); time.sleep(0.12)          # SLPOUT
cmd(0xF0); dat(0xC3)                  # 打开命令集
cmd(0xF0); dat(0x96)
cmd(0x36); dat(0x48)                  # MADCTL (方向/BGR)
cmd(0x3A); dat(0x55)                  # 16bit 565
cmd(0xB4); dat(0x01)
cmd(0xB6); dat(0x80, 0x02, 0x3B)
cmd(0xC0); dat(0x80, 0x45)
cmd(0xC1); dat(0x13)
cmd(0xC2); dat(0xA7)
cmd(0xC5); dat(0x0A)
cmd(0xE8); dat(0x40, 0x8A, 0x00, 0x00, 0x29, 0x19, 0xA5, 0x33)
cmd(0xE0); dat(0xD0,0x08,0x0F,0x06,0x06,0x33,0x30,0x33,0x47,0x17,0x13,0x13,0x2B,0x31)
cmd(0xE1); dat(0xD0,0x0A,0x11,0x0B,0x09,0x07,0x2F,0x33,0x47,0x38,0x15,0x16,0x2C,0x32)
cmd(0xF0); dat(0x3C)
cmd(0xF0); dat(0x69)
time.sleep(0.12)
cmd(0x21)                             # 反显(部分屏需要，可去掉试)
cmd(0x29)                             # DISPON

# ---- 整屏铺红 ----
W, H = 320, 480
cmd(0x2A); dat(0x00, 0x00, (W-1) >> 8, (W-1) & 0xFF)   # 列 0..319
cmd(0x2B); dat(0x00, 0x00, (H-1) >> 8, (H-1) & 0xFF)   # 行 0..479
cmd(0x2C)

GPIO.output(DC, 1)
row = bytes([0xF8, 0x00]) * W          # 红 565
frame = row * H
CHUNK = 4096
for i in range(0, len(frame), CHUNK):
    spi.writebytes2(frame[i:i+CHUNK])

print("done, holding 10s")
time.sleep(10)
spi.close()
GPIO.cleanup()