"""Take a photo from the USB camera: python3 capture.py [output.jpg]"""
import cv2  # type: ignore

# Camera config
WIDTH, HEIGHT = 1920, 1080       # capture resolution
EXPOSURE_US = 1300000              # shutter speed in microsections, None = auto
'''VERY IMPORTANT, in UK, 50Hz mains, so use multiples of 10ms'''
GAIN = 1                      # exposure conpensation
COLOUR_GAINS = (1.2, 1.5)
AUTO = False

# Set up camera upon import
cap = cv2.VideoCapture(0)

if not AUTO:
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # manual mode
    cap.set(cv2.CAP_PROP_EXPOSURE, EXPOSURE_US / 1e6)  # seconds
    cap.set(cv2.CAP_PROP_GAIN, GAIN)
    #cap.set(cv2.CAP_PROP_AUTO_WB, 0) 
    #cap.set(cv2.CAP_PROP_WHITE_BALANCE_BLUE_U, COLOUR_GAINS[1])
    #cap.set(cv2.CAP_PROP_WHITE_BALANCE_RED_V, COLOUR_GAINS[0])

cap.set(cv2.CAP_PROP_AUTO_WB, 1)

cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))  # set before resolution
cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)

#reduce buffer so no lag in server
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

if not cap.isOpened():
    print("Camera not found, check: v4l2-ctl --list-devices")
    #return with Error
    raise RuntimeError("Camera not found, check: v4l2-ctl --list-devices")

for _ in range(3):  # let auto-exposure settle
    cap.read()
    
def cap_frame():
    ok, frame = cap.read()
    if not ok:
        print("Failed to capture frame")
    return frame

def get_properties(frame):
    """Extract basic image properties from a BGR frame. Returns a dict."""
    h, w = frame.shape[:2]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return {
        "res": f"{w}x{h}",
        "brightness": f"{gray.mean():.0f}",                          # mean 0-255, check exposure
        "sharpness": f"{cv2.Laplacian(gray, cv2.CV_64F).var():.0f}",  # higher = better focus
    }

def get_camera_settings():
    """Read the camera's exposure / gain / white-balance from the driver.
    NOTE: on a USB/UVC adapter these are in the driver's OWN units (exposure is usually
    100us steps, not seconds; WB in Kelvin), and some read -1 if the adapter doesn't
    expose them. `v4l2-ctl -d /dev/video0 --all` is the authoritative source."""
    g = cap.get
    return {
        "exp": g(cv2.CAP_PROP_EXPOSURE),
        "gain": g(cv2.CAP_PROP_GAIN),
        "auto_exp": g(cv2.CAP_PROP_AUTO_EXPOSURE),
        "wb": g(cv2.CAP_PROP_WB_TEMPERATURE),
        "auto_wb": g(cv2.CAP_PROP_AUTO_WB),
        "fps": g(cv2.CAP_PROP_FPS),
    }

def draw_properties(frame):
    """Overlay image properties + camera settings in the top-right corner (modifies frame)."""
    font, scale, thick = cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1
    props = {**get_properties(frame), **get_camera_settings()}
    y = 26
    for k, v in props.items():
        v = f"{v:g}" if isinstance(v, float) else v   # tidy floats: 156.0 -> 156, keep 0.25
        text = f"{k}: {v}"
        (tw, th), _ = cv2.getTextSize(text, font, scale, thick)
        x = frame.shape[1] - tw - 12  # hug the right edge, 12px margin
        cv2.putText(frame, text, (x, y), font, scale, (0, 0, 0), 3, cv2.LINE_AA)      # black outline
        cv2.putText(frame, text, (x, y), font, scale, (0, 255, 0), thick, cv2.LINE_AA)  # green text
        y += th + 12

def cap_jpg(annotate=False):
    """Grab a frame and return it JPEG-encoded (bytes). If annotate, overlay properties top-right."""
    frame = cap_frame()
    if frame is None:
        return None
    if annotate:
        draw_properties(frame)
    _, buf = cv2.imencode(".jpg", frame)  # BGR frame -> JPEG
    return buf.tobytes()

def close_camera():
    cap.release()

if __name__ == "__main__":
    frame = cap_frame()
    cv2.imwrite("capture.jpg", frame)
    print(f"Saved capture.jpg {frame.shape}")
    close_camera()


