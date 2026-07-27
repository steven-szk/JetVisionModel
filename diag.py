#!/usr/bin/env python3
"""One-shot diagnostic for the ST7796 setup on Orin Nano. Run: sudo python3 diag.py"""
import glob
import subprocess

print("=" * 50)

# 1. SPI device nodes present?
nodes = sorted(glob.glob("/dev/spidev*"))
print(f"[1] /dev/spidev* nodes: {nodes if nodes else 'NONE  <-- SPI not enabled!'}")

# 2. Can we open the SPI bus?
try:
    import spidev
    spi = spidev.SpiDev()
    spi.open(0, 0)
    spi.max_speed_hz = 8_000_000
    spi.mode = 0
    spi.xfer2([0x00])
    print("[2] spidev0.0 open + xfer: OK")
    spi.close()
except Exception as e:  # noqa: BLE001
    print(f"[2] spidev0.0 FAILED: {e}")

# 3. libgpiod: find our DC/RST lines
for name in ("PQ.05", "PQ.06"):
    try:
        out = subprocess.run(["gpiofind", name], capture_output=True,
                             text=True, timeout=5).stdout.strip()
        print(f"[3] gpiofind {name}: {out if out else 'NOT FOUND'}")
    except Exception as e:  # noqa: BLE001
        print(f"[3] gpiofind {name} error: {e}")

# 4. python gpiod available?
try:
    import gpiod
    ver = getattr(gpiod, "__version__", "?")
    print(f"[4] python gpiod: OK (version {ver})")
except Exception as e:  # noqa: BLE001
    print(f"[4] python gpiod: NOT available ({e})")

# 5. Jetson.GPIO board detection
try:
    import Jetson.GPIO as GPIO
    print(f"[5] Jetson.GPIO model: {GPIO.model}")
except Exception as e:  # noqa: BLE001
    print(f"[5] Jetson.GPIO: {e}")

print("=" * 50)
print("Now testing GPIO drive via gpioset (hold HIGH).")
print("Measure Pin 29 (PQ.05) and Pin 31 (PQ.06) to GND while this waits.")
try:
    import gpiod  # noqa: F811
    # try to drive with libgpiod v1 API
    chip = gpiod.Chip("gpiochip0")
    print("    (using python gpiod -- press Ctrl+C when done measuring)")
    # locate lines by name
    lines = {}
    for name in ("PQ.05", "PQ.06"):
        try:
            l = chip.find_line(name)
        except Exception:  # noqa: BLE001
            l = None
        lines[name] = l
    print(f"    found lines: {[(k, (v.offset() if v else None)) for k,v in lines.items()]}")
    input("    Press ENTER to exit...")
except Exception as e:  # noqa: BLE001
    print(f"    python gpiod path unavailable ({e}); use command line instead:")
    print("    sudo gpioset $(gpiofind PQ.05)=1   # then measure Pin 29")
