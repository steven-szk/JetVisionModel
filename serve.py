"""Live view: grab frames from the USB camera (~10fps) and stream them to a web page.
Run: python3 serve.py  (Ctrl+C to stop). No need to run capture.py separately."""
import http.server
import socket
import threading
import time

import capture  # opens the camera on import

PORT = 8000
INTERVAL = 0.1  # seconds between frames (~10 fps)

PAGE = b"""<!doctype html>
<title>Jetson live</title>
<body style="margin:0;background:#111;display:flex;justify-content:center;align-items:center;height:100vh">
<img src="/stream" style="max-width:100%;max-height:100vh">
</body>"""

grab_lock = threading.Lock()  # one camera, so serialize frame grabs across viewers


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(PAGE)))
            self.end_headers()
            self.wfile.write(PAGE)
        elif self.path.startswith("/stream"):
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()
            try:
                while True:
                    with grab_lock:
                        jpg = capture.cap_jpg(annotate=True)
                    if jpg is None:
                        continue
                    self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(jpg)}\r\n\r\n".encode())
                    self.wfile.write(jpg)
                    self.wfile.write(b"\r\n")
                    time.sleep(INTERVAL)
            except (BrokenPipeError, ConnectionResetError):
                pass  # viewer closed the tab
        else:
            super().do_GET()

    def log_message(self, *args):
        pass  # quiet: don't log every frame


# find LAN IP
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))  # no packet sent, just picks the outgoing interface
    ip = s.getsockname()[0]
    s.close()
except OSError:
    ip = "localhost"

server = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
print(f"Live view at  http://{ip}:{PORT}   (local: http://localhost:{PORT})")
print("Ctrl+C to stop")
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    capture.close_camera()
    server.shutdown()
