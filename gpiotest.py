#!/usr/bin/env python3
"""Minimal GPIO output test. Holds pins 16/22/18 HIGH so you can measure them.

Run:  sudo python3 gpiotest.py
Then measure each pin to GND with a multimeter -- each should read ~3.3V.
"""
import Jetson.GPIO as GPIO  # type: ignore

PINS = [29, 31]  # DC (PQ.05), RST (PQ.06) -- real GPIO pins on Orin Nano

GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)
for p in PINS:
    GPIO.setup(p, GPIO.OUT)
    GPIO.output(p, GPIO.LOW)

print(f"Pins {PINS} driven HIGH. Measure each pin to GND now (expect ~3.3V).")
try:
    input("Press ENTER to release the pins and exit...")
finally:
    GPIO.cleanup()
