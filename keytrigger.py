"""
keytrigger.py -- wait for an Enter keypress on a keyboard physically attached to
the Jetson, instead of the terminal that launched the program (e.g. an SSH session).

It reads the raw input device via evdev, so it works even when main.py is started
over SSH -- the trigger comes from the Jetson's own USB keyboard.

Setup on the Jetson:
    pip install evdev
    sudo usermod -aG input $USER      # read access to /dev/input; then log out/in
                                      # (or just run the program with sudo)

Usage:
    from keytrigger import wait_for_enter
    wait_for_enter()                  # blocks until Enter on the Jetson keyboard
                                      # (falls back to stdin input() if unavailable)

Standalone test:
    python3 keytrigger.py             # shows the keyboard it found, then waits
"""

try:
    from evdev import InputDevice, ecodes, list_devices #type: ignore
    _HAVE_EVDEV = True
    # accept both the main Enter and the numpad Enter
    _ENTER_KEYS = (ecodes.KEY_ENTER, ecodes.KEY_KPENTER)
except ImportError:
    _HAVE_EVDEV = False
    _ENTER_KEYS = ()


def find_keyboard():
    """Return the first /dev/input device that looks like a keyboard (reports the
    main Enter key), or None if evdev is missing / no keyboard / no permission."""
    if not _HAVE_EVDEV:
        return None
    for path in list_devices():
        try:
            dev = InputDevice(path)
        except (PermissionError, OSError):
            continue                      # can't open this one, skip it
        if ecodes.KEY_ENTER in dev.capabilities().get(ecodes.EV_KEY, []):
            return dev
    return None


_keyboard = None  # cached device, discovered on first use


def wait_for_enter(prompt="Press Enter on the Jetson keyboard..."):
    """Block until Enter is pressed on the Jetson's own keyboard.

    Falls back to the launching terminal's stdin input() if no physical keyboard
    can be read (evdev not installed, no device, or no permission)."""
    global _keyboard
    if _keyboard is None:
        _keyboard = find_keyboard()

    if _keyboard is None:                 # nothing to read -> use the terminal
        input(prompt + " [stdin fallback] ")
        return

    print(prompt)
    for event in _keyboard.read_loop():
        if event.type == ecodes.EV_KEY and event.value == 1 and event.code in _ENTER_KEYS:
            return                        # value 1 = key down


if __name__ == "__main__":
    kbd = find_keyboard()
    if kbd is None:
        if not _HAVE_EVDEV:
            print("evdev not installed  ->  pip install evdev")
        else:
            print("No readable keyboard found (join the 'input' group or use sudo).")
        print("wait_for_enter() will fall back to stdin.")
    else:
        print(f"Using keyboard: {kbd.path}  ({kbd.name})")
    wait_for_enter()
    print("Enter received!")
