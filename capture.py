#!/usr/bin/env python3
"""Take a photo from the USB camera: python3 capture.py [output.jpg]"""
import sys
import cv2

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))  # set before resolution
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

if not cap.isOpened():
    sys.exit("Camera not found, check: v4l2-ctl --list-devices")

for _ in range(3):  # let auto-exposure settle
    cap.read()

ok, frame = cap.read()
cap.release()
if not ok:
    sys.exit("Failed to capture frame")

out = sys.argv[1] if len(sys.argv) > 1 else "capture.jpg"
cv2.imwrite(out, frame)
print(f"Saved {out} {frame.shape}")
