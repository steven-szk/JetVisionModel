"""
controlpanel.py -- a small web control panel served on the Jetson's own IP:1234.

It shows, all auto-refreshing in the browser:
  * Raw image      -- live view from the USB camera (aim here, then capture)
  * Processed image-- the annotated result of the last capture (defect outlines)
  * Results        -- edge area, per-defect %, PASS/FAIL, per-region details
  * Debug panel    -- timestamped log + image quality (brightness / sharpness)
  * Capture button -- does EXACTLY what pressing Enter does (capture -> infer -> ESP)

The camera + models are the same ones main.py already loaded, so they are handed
in via start(); nothing heavy is imported here. A lock serialises captures, so the
physical Enter key and the web button can never fire a capture at the same time.

Wiring (kept out of main.py):
    import controlpanel
    controlpanel.start(cap_frame=cap_frame, infer=infer, espcontrol=espcontrol)
    ...
    controlpanel.capture_and_process()   # called by BOTH Enter and the web button
"""
import http.server
import json
import os
import signal
import socket
import threading
import time

import cv2          # type: ignore
import numpy as np  # type: ignore

PORT = 1234
RAW_INTERVAL = 0.1          # seconds between raw-stream frames (~10 fps)
FAIL_PCT = 10.0            # total defect % at/above which a part FAILs (mirrors sendESP)

# per-feature draw colour in BGR (mirrors infermodel.COLORS)
COLORS = {
    "edge":    (111, 71, 239),
    "coating": (160, 214, 6),
    "delam":   (178, 138, 17),
    "scratch": (102, 209, 255),
    "crack":   (53, 107, 255),
}

# --- injected by start() (owned by main.py) ---
_cap_frame = None
_infer = None
_espcontrol = None
_server = None      # the running HTTP server, so stop() can shut it down

# --- shared state, read by the web handlers, written by capture_and_process ---
_state_lock = threading.Lock()    # guards the _state dict below
_cam_lock = threading.Lock()      # one camera -> serialise every frame grab
_process_lock = threading.Lock()  # one capture cycle at a time (Enter vs button)

_state = {
    "raw_jpg": None,     # latest raw frame, JPEG bytes (live stream fallback)
    "proc_jpg": None,    # latest annotated frame, JPEG bytes
    "results": None,     # summary dict for the results panel
    "log": [],           # debug log lines
    "seq": 0,            # capture counter -> tells the browser to reload processed.jpg
    "busy": False,       # a capture is currently running
}


def log(msg):
    """Append a timestamped line to the debug panel (and stdout)."""
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    with _state_lock:
        _state["log"].append(line)
        del _state["log"][:-200]     # keep only the last 200 lines
    print(msg)


def _get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))   # no packet sent, just picks the outgoing interface
        ip = s.getsockname()[0]
        s.close()
    except OSError:
        ip = "localhost"
    return ip


def _encode(frame):
    """BGR frame -> JPEG bytes (or None)."""
    ok, buf = cv2.imencode(".jpg", frame)
    return buf.tobytes() if ok else None


def _draw(img, regions):
    """Outline every detected region on a copy-safe BGR image (mirrors infermodel)."""
    for r in regions:
        color = COLORS.get(r["feature"], (0, 255, 0))
        pts = np.array(r["contour"], np.int32).reshape(-1, 1, 2)
        cv2.polylines(img, [pts], True, color, 2)
        cx, cy = r["centroid"]
        cv2.circle(img, (cx, cy), 5, color, -1)
        x, y = r["bbox"][:2]
        cv2.putText(img, f"{r['feature']} {r['confidence']:.2f}", (x, max(y - 10, 0)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    return img


def _image_props(frame):
    """Basic quality numbers for the debug panel."""
    h, w = frame.shape[:2]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return {
        "res": f"{w}x{h}",
        "brightness": round(float(gray.mean()), 1),                      # 0-255, exposure
        "sharpness": round(float(cv2.Laplacian(gray, cv2.CV_64F).var())),  # higher = sharper focus
    }


def _summarize(regions, props):
    """Roll the raw region list up into the numbers shown in the results panel.
    Same edge-area / percentage / PASS-FAIL logic as sendESP.send_result()."""
    edge_area = sum(r["area"] for r in regions if r["feature"] == "edge")
    defect_area = {}
    for r in regions:
        if r["feature"] == "edge":            # edge is the electrode boundary, not a defect
            continue
        defect_area[r["feature"]] = defect_area.get(r["feature"], 0.0) + r["area"]

    def pct(feat):
        return 100.0 * defect_area.get(feat, 0.0) / edge_area if edge_area else 0.0

    total_pct = sum(defect_area.values()) / edge_area * 100 if edge_area else 0.0
    return {
        "count": len(regions),
        "edge_area": round(edge_area),
        "defect_pct": {f: round(pct(f), 2) for f in ("crack", "delam", "scratch", "coating")},
        "total_pct": round(total_pct, 2),
        "state": "PASS" if total_pct < FAIL_PCT else "FAIL",
        "props": props,
        "regions": [
            {
                "feature": r["feature"],
                "area": round(r["area"]),
                "confidence": round(r["confidence"], 2),
                "bbox": r["bbox"],
                "centroid": r["centroid"],
            }
            for r in regions
        ],
    }


def capture_and_process():
    """One full cycle: capture a frame -> run inference -> update the panel -> tell the ESP.

    This is the single source of truth shared by the physical Enter key (main.py) and
    the web Capture button, so they behave identically. Guarded so only one runs at a
    time; never raises (a failure is logged and reported instead)."""
    if _cap_frame is None or _infer is None:
        log("Capture ignored: panel not started with camera/models")
        return None

    if not _process_lock.acquire(blocking=False):
        log("Capture ignored: already processing")
        return None

    with _state_lock:
        _state["busy"] = True
    try:
        with _cam_lock:                       # hold the camera only for the grab itself
            frame = _cap_frame()
        if frame is None:
            log("Capture failed")
            if _espcontrol:
                _espcontrol.send_info("Capture failed")
            return None

        with _state_lock:
            _state["raw_jpg"] = _encode(frame)
        log("Frame captured - running inference")
        if _espcontrol:
            _espcontrol.send_info("Frame Captured - running inference")

        regions = _infer(frame)
        annotated = _draw(frame.copy(), regions)
        summary = _summarize(regions, _image_props(frame))

        with _state_lock:
            _state["proc_jpg"] = _encode(annotated)
            _state["results"] = summary
            _state["seq"] += 1
        log(f"{len(regions)} region(s) detected -> {summary['state']} "
            f"({summary['total_pct']:.2f}% defect area)")

        if _espcontrol:
            _espcontrol.send_result(regions)          # -> ESP with 'RES' header
            _espcontrol.send_info("analysis Complete - Enter to capture")
            time.sleep(0.5)
        return summary
    except Exception as e:                    # a bad frame must not kill the loop/server
        log(f"Error during capture/inference: {e}")
        return None
    finally:
        with _state_lock:
            _state["busy"] = False
        _process_lock.release()


# --------------------------------------------------------------------------- web
_PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Jetson Control Panel</title>
<style>
  :root{--bg:#0f1216;--panel:#181d24;--edge:#2a323d;--txt:#e6edf3;--mut:#8b98a5;--accent:#2f81f7}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--txt);font:14px/1.45 system-ui,Segoe UI,Roboto,sans-serif}
  header{display:flex;align-items:center;gap:16px;padding:12px 18px;border-bottom:1px solid var(--edge)}
  header h1{font-size:16px;margin:0;font-weight:600}
  #state{margin-left:auto;font-weight:700;padding:4px 14px;border-radius:6px;background:#333;letter-spacing:.5px}
  #state.PASS{background:#1a7f37;color:#fff}#state.FAIL{background:#b62324;color:#fff}
  .wrap{display:grid;grid-template-columns:1fr 1fr;gap:14px;padding:14px}
  @media(max-width:820px){.wrap{grid-template-columns:1fr}}
  .card{background:var(--panel);border:1px solid var(--edge);border-radius:10px;overflow:hidden}
  .card h2{font-size:12px;text-transform:uppercase;letter-spacing:.6px;color:var(--mut);
           margin:0;padding:9px 12px;border-bottom:1px solid var(--edge)}
  .card .body{padding:12px}
  img{display:block;width:100%;background:#000;min-height:180px;object-fit:contain}
  button{font:600 15px system-ui;color:#fff;background:var(--accent);border:0;border-radius:8px;
         padding:12px 18px;cursor:pointer;width:100%}
  button:disabled{opacity:.5;cursor:default}
  button.danger{background:#b62324;margin-top:10px}
  table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}
  td,th{text-align:left;padding:3px 8px 3px 0;border-bottom:1px solid var(--edge);white-space:nowrap}
  th{color:var(--mut);font-weight:500}
  .grid{display:grid;grid-template-columns:auto 1fr;gap:2px 14px;margin-bottom:10px}
  .grid b{color:var(--mut);font-weight:500}
  pre{margin:0;padding:12px;background:#0b0e12;color:#b7c2cd;font:12px/1.5 ui-monospace,Consolas,monospace;
      height:220px;overflow:auto;white-space:pre-wrap}
  .hint{color:var(--mut);font-size:12px;margin-top:8px}
</style></head>
<body>
<header>
  <h1>Jetson Vision &mdash; Control Panel</h1>
  <span id="state">&mdash;</span>
</header>
<div class="wrap">
  <div class="card"><h2>Raw image (live)</h2><img id="raw" src="/raw" alt="raw camera"></div>
  <div class="card"><h2>Processed image</h2><img id="proc" alt="capture to see result"></div>

  <div class="card"><h2>Capture</h2><div class="body">
    <button id="btn">Capture &amp; Process</button>
    <div class="hint">Does the same as pressing Enter. You can also press Enter here.</div>
    <button id="shut" class="danger">Shutdown</button>
    <div class="hint">Stops the vision app on the Jetson (same as Ctrl+C).</div>
  </div></div>

  <div class="card"><h2>Results</h2><div class="body" id="results">
    <span class="hint">No capture yet.</span></div></div>

  <div class="card" style="grid-column:1/-1"><h2>Debug</h2><pre id="log"></pre></div>
</div>

<script>
const $ = id => document.getElementById(id);
let lastSeq = -1, stopped = false;

$("btn").onclick = () => fetch("/capture", {method:"POST"});
$("shut").onclick = () => {
  if(!confirm("Shut down the vision app? The control panel will go offline.")) return;
  fetch("/shutdown", {method:"POST"});
  stopped = true;
  $("state").textContent = "OFFLINE"; $("state").className = "";
  $("btn").disabled = $("shut").disabled = true;
  $("btn").textContent = "Shutting down…";
};
document.addEventListener("keydown", e => {
  if (e.key === "Enter" && document.activeElement.tagName !== "BUTTON") {
    e.preventDefault(); $("btn").click();
  }
});

function renderResults(r){
  if(!r){ $("results").innerHTML = '<span class="hint">No capture yet.</span>'; return; }
  const dp = r.defect_pct;
  let rows = r.regions.map(x =>
    `<tr><td>${x.feature}</td><td>${x.area}</td><td>${x.confidence}</td>
         <td>${x.bbox.join(", ")}</td></tr>`).join("");
  if(!rows) rows = '<tr><td colspan="4" class="hint">no regions</td></tr>';
  $("results").innerHTML =
    `<div class="grid">
       <b>Regions</b><span>${r.count}</span>
       <b>Edge area</b><span>${r.edge_area} px</span>
       <b>Total defect</b><span>${r.total_pct}%</span>
       <b>crack / delam</b><span>${dp.crack}% / ${dp.delam}%</span>
       <b>scratch / coating</b><span>${dp.scratch}% / ${dp.coating}%</span>
       <b>Resolution</b><span>${r.props.res}</span>
       <b>Brightness</b><span>${r.props.brightness}</span>
       <b>Sharpness</b><span>${r.props.sharpness}</span>
     </div>
     <table><tr><th>feature</th><th>area</th><th>conf</th><th>bbox [x,y,w,h]</th></tr>${rows}</table>`;
}

async function poll(){
  if(stopped) return;
  try{
    const s = await (await fetch("/state")).json();
    const st = $("state"); st.textContent = s.results ? s.results.state : "—";
    st.className = s.results ? s.results.state : "";
    $("btn").disabled = s.busy;
    $("btn").textContent = s.busy ? "Processing…" : "Capture & Process";
    $("log").textContent = s.log.join("\\n");
    if(s.seq !== lastSeq){
      lastSeq = s.seq;
      renderResults(s.results);
      if(s.seq > 0) $("proc").src = "/processed.jpg?seq=" + s.seq;
    }
  }catch(e){/* server busy, try again next tick */}
}
setInterval(poll, 700); poll();
</script>
</body></html>""".encode("utf-8")


class _Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path.startswith("/capture"):
            # run in the background so the button returns instantly; the page polls /state
            threading.Thread(target=capture_and_process, daemon=True).start()
            self._send(200, "application/json", b'{"ok":true}')
        elif self.path.startswith("/shutdown"):
            # reply first, then exit shortly after so the browser sees the response
            self._send(200, "application/json", b'{"ok":true}')
            threading.Timer(0.3, request_shutdown).start()
        else:
            self.send_error(404)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, "text/html", _PAGE)

        elif self.path == "/state":
            with _state_lock:
                body = json.dumps({
                    "results": _state["results"],
                    "log": _state["log"],
                    "seq": _state["seq"],
                    "busy": _state["busy"],
                }).encode()
            self._send(200, "application/json", body)

        elif self.path.startswith("/processed.jpg"):
            jpg = _state["proc_jpg"]
            if jpg is None:
                self.send_error(404)
            else:
                self._send(200, "image/jpeg", jpg)

        elif self.path.startswith("/raw"):
            self._raw_stream()

        else:
            self.send_error(404)

    def _raw_stream(self):
        """Live MJPEG of the raw camera -- shares the camera lock with capture."""
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            while True:
                with _cam_lock:
                    frame = _cap_frame() if _cap_frame else None
                jpg = _encode(frame) if frame is not None else _state["raw_jpg"]
                if jpg:
                    self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(jpg)}\r\n\r\n".encode())
                    self.wfile.write(jpg)
                    self.wfile.write(b"\r\n")
                time.sleep(RAW_INTERVAL)
        except (BrokenPipeError, ConnectionResetError):
            pass  # viewer closed the tab

    def log_message(self, *args):
        pass  # quiet: don't log every frame/poll


def start(cap_frame, infer, espcontrol=None, port=PORT):
    """Start the control panel on a daemon thread and return the server.

    cap_frame / infer / espcontrol are the objects main.py already created, so the
    panel drives the very same camera, models and ESP link."""
    global _cap_frame, _infer, _espcontrol
    _cap_frame, _infer, _espcontrol = cap_frame, infer, espcontrol

    server = http.server.ThreadingHTTPServer(("0.0.0.0", port), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    global _server
    _server = server
    url = f"http://{_get_ip()}:{port}"
    log(f"Control panel at {url}   (local: http://localhost:{port})")
    if _espcontrol:
        _espcontrol.send_info(f"Panel {url}")
    return server


def stop():
    """Shut the web server down and release its socket. Idempotent; safe to call
    from main.py's cleanup (it runs on a different thread than serve_forever)."""
    global _server
    if _server is None:
        return
    srv, _server = _server, None
    log("Control panel stopping")
    try:
        srv.shutdown()        # break serve_forever (running on the daemon thread)
        srv.server_close()    # release the listening socket
    except Exception as e:
        print(f"Error stopping control panel: {e}")


def request_shutdown():
    """Ask the whole app to exit gracefully -- used by the web Shutdown button.

    Sends SIGINT to our own process so main.py's normal Ctrl+C path runs and does
    its usual cleanup (stop the panel, release the camera, close the ESP link).
    The physical Ctrl+C in the terminal still works exactly the same way."""
    log("Shutdown requested from web panel")
    if _espcontrol:
        try:
            _espcontrol.send_info("Shutting down")
        except Exception:
            pass
    os.kill(os.getpid(), signal.SIGINT)   # -> KeyboardInterrupt in main -> clean exit
