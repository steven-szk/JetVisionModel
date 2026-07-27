#!/usr/bin/env python3
"""Print how Jetson.GPIO maps BOARD pins 16/18/22 to kernel gpiochip lines."""
from Jetson.GPIO import gpio_pin_data

data = gpio_pin_data.get_data()
# get_data() returns (model, JETSON_INFO, channel_data_by_mode) across versions
channel_data = data[-1]
board = channel_data["BOARD"]

for pin in (16, 18, 22):
    ci = board.get(pin)
    print(f"--- BOARD pin {pin} ---")
    if ci is None:
        print("   (not a usable GPIO on this board)")
        continue
    # ChannelInfo is a namedtuple; dump every field
    for field in ci._fields:
        print(f"   {field} = {getattr(ci, field)}")
