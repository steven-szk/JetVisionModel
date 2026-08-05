"""
Press Enter -> capture a frame -> run inference -> send a defect-count summary to
the ESP32 over I2C (with the 'RES' header). Ctrl+C to quit.

Run from the repo root:  python main.py
"""
import time

import sendESP

# --- ESP32 link (I2C) ---
espcontrol = None
try:
    espcontrol = sendESP.sendESP()
    espcontrol.init()                        # push the Jetson IP to the ESP display
    espcontrol.send_info("Initialise...")
except Exception as e:
    print(f"Error init ESP (continuing without it): {e}")


# --- camera (opens the USB camera on import) ---
try:
    from capture import cap_frame, close_camera
    espcontrol.send_info("Camera Loaded")
except Exception as e:
    print(f"Error loading camera: {e}")
    cap_frame = close_camera = None

# --- models (loads all 5 ONNX sessions on import) ---
try:
    from infermodel import infer
    espcontrol.send_info("Models Loaded")
except Exception as e:
    print(f"Error loading models: {e}")
    infer = None

# --- main loop: Enter -> capture -> infer -> send RES to ESP ---
def main():
    if cap_frame and infer:
        espcontrol.send_info("Ready - press Enter to capture")
        try:
            while True:
                input("\nPress Enter to capture + infer (Ctrl+C to quit)...")
                frame = cap_frame()
                espcontrol.send_info("Frame Captured - running inference...")
                if frame is None:
                    espcontrol.send_info("Capture failed")
                    continue
                regions = infer(frame)
                print(f"{len(regions)} region(s) detected")
                if espcontrol:
                    espcontrol.send_result(regions)     # -> ESP with 'RES' header
                    espcontrol.send_info("analysis Complete")
                    time.sleep(1)
                                        
        except (KeyboardInterrupt, EOFError):
            print("\nExiting")
        finally:
            if close_camera:
                close_camera()
            if espcontrol:
                espcontrol.close()
    else:
        print("Camera or models failed to load -- cannot start (see errors above).")


if __name__ == "__main__":
    main()