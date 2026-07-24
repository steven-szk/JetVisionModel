"""Show capture.jpg on a web page that auto-refreshes. Run: python3 serve.py (Ctrl+C to stop)"""
import http.server
import socketserver
import socket
import time

PORT = 8000
IMG = "capture.jpg"

PAGE = """<!doctype html>
<title>Jetson capture</title>
<meta http-equiv="refresh" content="2">
<body style="margin:0;background:#111;display:flex;justify-content:center;align-items:center;height:100vh">
<img src="{img}?_={t}" style="max-width:100%;max-height:100vh">
</body>"""


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            # cache-busting ?_=timestamp forces the browser to fetch the newest jpg
            html = PAGE.format(img=IMG, t=int(time.time())).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
        else:
            super().do_GET()  # serves capture.jpg (query string is stripped automatically)


# find this machine's LAN IP so you know what to open from another device
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))  # no packet sent, just picks the outgoing interface
    ip = s.getsockname()[0]
    s.close()
except OSError:
    ip = "localhost"

with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
    print(f"Serving at  http://{ip}:{PORT}   (local: http://localhost:{PORT})")
    print("Ctrl+C to stop")
    httpd.serve_forever()
