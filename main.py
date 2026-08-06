"""
Press Enter -> capture a frame -> run inference -> send a defect-count summary to
the ESP32 over I2C (with the 'RES' header). Ctrl+C to quit.

A web control panel is also served on the Jetson's IP at port 1234 (raw + processed
image, results, debug log, and a Capture button that does the same as Enter). Both
the Enter key and that button call controlpanel.capture_and_process().

Run from the repo root:  python main.py
"""

import sendESP
from keytrigger import wait_for_enter

# --- ESP32 link (I2C) ---
espcontrol = None
try:
    espcontrol = sendESP.sendESP()
    espcontrol.init()                        # push the Jetson IP to the ESP display
    espcontrol.send_info("Initialise...")
    import controlpanel
    espcontrol.send_info("Control panel initialized...")
except Exception as e:
    print(f"Error init ESP/Control panel (continuing without it): {e}")
    espcontrol.send_info("ERROR in ESP/CONTROL PANEL")


# --- camera (opens the USB camera on import) ---
try:
    from capture import cap_frame, close_camera
    espcontrol.send_info("Camera Loaded")
except Exception as e:
    espcontrol.send_info("ERROR loading camera") 
    print(f"Error loading camera: {e}")
    exit(1)

# --- models (loads all 5 ONNX sessions on import) ---
try:
    from infermodel import infer
    espcontrol.send_info("Models Loaded")
except Exception as e:
    espcontrol.send_info("ERROR loading MODELS")
    print(f"Error loading models: {e}")
    exit(1)

# --- main loop: Enter (or the web Capture button) -> capture -> infer -> send RES ---
def main():
    # Start the web control panel (port 1234). It drives the same camera/models/ESP,
    # and its Capture button calls the very same capture_and_process() as Enter does.
    controlpanel.start(cap_frame=cap_frame, infer=infer, espcontrol=espcontrol)

    espcontrol.send_info("Ready - press Enter to capture")
    try:
        while True:
            # use the Jetson's own keyboard (the web button is the other trigger)
            wait_for_enter("Press Enter to capture a frame and run inference (Ctrl+C to quit)...")
            controlpanel.capture_and_process()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting")
    finally:
        close_camera()
        espcontrol.close()
        controlpanel.stop()
        print("shutdown gracefully")


if __name__ == "__main__":
    main()