"""Take a photo from the USB camera: python3 capture.py [output.jpg]"""
import cv2 #type: ignore

# Camera config
WIDTH, HEIGHT = 1920, 1080       # capture resolution
EXPOSURE_US = 15000              # shutter speed in microsections, None = auto
'''VERY IMPORTANT, in UK, 50Hz mains, so use multiples of 10ms'''
GAIN = 5                      # exposure conpensation
# Fixed white-balance gains (red, blue). With AWB off these lock the colour
COLOUR_GAINS = (1.156, 1.649)
AUTO = True

# Set up camera
cap = cv2.VideoCapture(0)

if not AUTO:
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # manual mode
    cap.set(cv2.CAP_PROP_EXPOSURE, EXPOSURE_US / 1e6)  # seconds
    cap.set(cv2.CAP_PROP_GAIN, GAIN)
    cap.set(cv2.CAP_PROP_AUTO_WB, 0)
    cap.set(cv2.CAP_PROP_WHITE_BALANCE_BLUE_U, COLOUR_GAINS[1])
    cap.set(cv2.CAP_PROP_WHITE_BALANCE_RED_V, COLOUR_GAINS[0])

cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))  # set before resolution
cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)

if not cap.isOpened():
    print("Camera not found, check: v4l2-ctl --list-devices")

for _ in range(3):  # let auto-exposure settle
    cap.read()
    
def cap_jpg():
    ok, frame = cap.read()
    if not ok:
        print("Failed to capture frame")
    return frame

def close_camera():
    cap.release()

if __name__ == "__main__":
    frame = cap_jpg()
    cv2.imwrite("capture.jpg", frame)
    print(f"Saved capture.jpg {frame.shape}")
    close_camera()


