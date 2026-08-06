"""
keytrigger.py -- wait for an Enter keypress on a keyboard physically attached to
the Jetson, instead of the terminal that launched the program (e.g. an SSH session).

It reads the raw input device via evdev, so it works even when main.py is started
over SSH -- the trigger comes from the Jetson's own USB keyboard.

Why it listens on SEVERAL devices:
    One USB keyboard shows up as MORE THAN ONE /dev/input/event* node -- typically a
    normal keyboard node plus a "Consumer Control" node for media/volume keys. That
    consumer-control node often *advertises* KEY_ENTER in its capabilities but never
    actually sends it; the real Enter comes from the keyboard node. Picking a single
    device by capability therefore lands on the wrong node and Enter looks dead. So we
    open EVERY Enter-capable node and wait on all of them at once.

Setup on the Jetson:
    pip install evdev
    sudo usermod -aG input $USER      # read access to /dev/input; then log out/in
                                      # (or just run the program with sudo)

Usage:
    from keytrigger import wait_for_enter
    wait_for_enter()                  # blocks until Enter on the Jetson keyboard
                                      # (falls back to stdin input() if unavailable)

Standalone test:
    python3 keytrigger.py             # lists the devices it listens on, then waits
    python3 keytrigger.py debug       # prints every key-down (which node, which key)
"""
import select
import sys

try:
    from evdev import InputDevice, ecodes, list_devices  # type: ignore
    _HAVE_EVDEV = True
    # accept both the main Enter and the numpad Enter
    _ENTER_KEYS = (ecodes.KEY_ENTER, ecodes.KEY_KPENTER)
except ImportError:
    _HAVE_EVDEV = False
    _ENTER_KEYS = ()


def find_keyboards():
    """Return ALL readable /dev/input devices that can emit an Enter key.

    A single keyboard can expose several nodes (see the module docstring), so we
    return every candidate rather than guessing which one is 'the' keyboard.
    Empty list if evdev is missing / nothing readable / no permission."""
    if not _HAVE_EVDEV:
        return []
    devs = []
    for path in list_devices():
        try:
            dev = InputDevice(path)
        except (PermissionError, OSError):
            continue                      # can't open this one, skip it
        keys = dev.capabilities().get(ecodes.EV_KEY, [])
        if any(k in keys for k in _ENTER_KEYS):
            devs.append(dev)
    return devs


_keyboards = None  # cached device list, discovered on first use


def wait_for_enter(prompt="Press Enter on the Jetson keyboard..."):
    """Block until Enter is pressed on ANY attached keyboard.

    Falls back to the launching terminal's stdin input() if no physical keyboard
    can be read (evdev not installed, no device, or no permission)."""
    global _keyboards
    if _keyboards is None:
        _keyboards = find_keyboards()

    if not _keyboards:                    # nothing to read -> use the terminal
        input(prompt + " [stdin fallback] ")
        return

    print(prompt)
    fd_to_dev = {dev.fd: dev for dev in _keyboards}
    while True:
        ready, _, _ = select.select(fd_to_dev, [], [])   # block until a node has input
        for fd in ready:
            try:
                for event in fd_to_dev[fd].read():
                    if (event.type == ecodes.EV_KEY and event.value == 1  # 1 = key down
                            and event.code in _ENTER_KEYS):
                        return
            except OSError:
                continue                  # device vanished (unplugged); ignore it


if __name__ == "__main__":
    kbds = find_keyboards()
    if not kbds:
        if not _HAVE_EVDEV:
            print("evdev not installed  ->  pip install evdev")
        else:
            print("No readable keyboard found (join the 'input' group or use sudo).")
        print("wait_for_enter() will fall back to stdin.")
        wait_for_enter()
        print("Enter received!")
        sys.exit(0)

    print("Listening for Enter on:")
    for d in kbds:
        print(f"  {d.path}  ({d.name})")

    if len(sys.argv) > 1 and sys.argv[1] == "debug":
        # Diagnostic mode: show every key-down and which node it came from, so you can
        # confirm the real Enter key and which device delivers it. Ctrl+C to quit.
        print("\nDEBUG: press keys (Ctrl+C to quit)...")
        fd_to_dev = {d.fd: d for d in kbds}
        try:
            while True:
                ready, _, _ = select.select(fd_to_dev, [], [])
                for fd in ready:
                    for e in fd_to_dev[fd].read():
                        if e.type == ecodes.EV_KEY and e.value == 1:
                            name = ecodes.KEY.get(e.code, e.code)
                            enter = "  <-- ENTER" if e.code in _ENTER_KEYS else ""
                            print(f"  {fd_to_dev[fd].name}: code={e.code} {name}{enter}")
        except KeyboardInterrupt:
            print()
    else:
        wait_for_enter()
        print("Enter received!")
