"""
AI Logisim Controller — Desktop Application.
Launches as a native desktop window (no terminal spam, no manual server start).

Startup stability design:
  1. Single-instance lock  -> double-clicking LogiMate again never spawns a second
                              server/engine; it just brings the existing window forward.
  2. Instant loading window -> a native window with a loading screen appears immediately,
                              while the AI engine (FastAPI + AI SDKs) warms up in background.
  3. Fast port selection    -> bind-based check (instant) instead of connect probing,
                              which costs ~2s per closed port on Windows.
"""

import os
import sys
import json
import time
import socket
import threading
import traceback
import multiprocessing
import urllib.request


APP_TITLE = "LogiMate — AI Logisim Controller"
MUTEX_NAME = "Local\\LogiMate_AI_Logisim_Controller_SingleInstance"
SERVER_START_TIMEOUT = 180.0  # Slow lab PCs + first-run antivirus scans can take a while

# Keep a reference so the mutex handle lives for the whole process lifetime
_instance_mutex = None


# In Windows GUI mode (--windowed), sys.stdout and sys.stderr are None. Provide dummy sinks to prevent uvicorn logging crashes.
class NullWriter:
    def write(self, s):
        pass
    def flush(self):
        pass
    def isatty(self):
        return False

if sys.stdout is None:
    sys.stdout = NullWriter()
if sys.stderr is None:
    sys.stderr = NullWriter()


def get_base_dir() -> str:
    return os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# Single-instance guard
# ---------------------------------------------------------------------------

def acquire_single_instance() -> bool:
    """
    Returns True if this is the only running LogiMate instance.
    Uses a Win32 named mutex, which Windows releases automatically if the
    process exits or crashes, so a stale lock can never block future launches.
    """
    global _instance_mutex
    if os.name != "nt":
        return True
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        _instance_mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
        ERROR_ALREADY_EXISTS = 183
        if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            return False
    except Exception:
        pass  # If the guard itself fails, never block the user from launching
    return True


def activate_existing_instance():
    """Brings the already running LogiMate window to the front (restoring it if minimized)."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = 0
        # The first instance may still be creating its window; give it a moment
        for _ in range(20):
            hwnd = user32.FindWindowW(None, APP_TITLE)
            if hwnd:
                break
            time.sleep(0.25)

        if hwnd:
            SW_RESTORE, SW_SHOW = 9, 5
            user32.ShowWindow(hwnd, SW_RESTORE if user32.IsIconic(hwnd) else SW_SHOW)
            user32.SetForegroundWindow(hwnd)
        else:
            user32.MessageBoxW(
                0,
                "LogiMate is already starting up.\n\nPlease wait a few seconds for the window to appear.",
                "LogiMate",
                0x40 | 0x40000,  # MB_ICONINFORMATION | MB_TOPMOST
            )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Local server
# ---------------------------------------------------------------------------

def find_free_port(start_port: int = 8000) -> int:
    """Finds an available local port by trying to bind (instant, unlike connect probing)."""
    for port in range(start_port, start_port + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    # Last resort: let the OS pick any free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run_server(port: int):
    """Runs the FastAPI server with explicit config avoiding dynamic import issues."""
    try:
        import uvicorn
        from server import app
        config = uvicorn.Config(
            app=app,
            host="127.0.0.1",
            port=port,
            log_config=None,
            access_log=False,
            loop="asyncio",
            http="h11",
            lifespan="off",
        )
        server = uvicorn.Server(config)
        server.run()
    except Exception:
        log_path = os.path.join(get_base_dir(), "server_startup_error.log")
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(traceback.format_exc())
        except Exception:
            pass


def wait_for_server(port: int, server_thread: threading.Thread, timeout: float = SERVER_START_TIMEOUT) -> bool:
    """Waits until the local server responds (stops early if the server thread crashed)."""
    start = time.time()
    url = f"http://127.0.0.1:{port}/api/ping"
    while time.time() - start < timeout:
        if not server_thread.is_alive():
            return False
        try:
            with urllib.request.urlopen(url, timeout=1.0) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.2)
    return False


# ---------------------------------------------------------------------------
# Loading screen (shown instantly while the engine warms up)
# ---------------------------------------------------------------------------

SPLASH_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>LogiMate</title>
<style>
  html,body{margin:0;height:100%;background:#080c14;color:#e6edf7;
    font-family:"Segoe UI",Inter,system-ui,sans-serif;overflow:hidden}
  .wrap{height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:22px;
    background:radial-gradient(circle at 50% 40%,rgba(99,102,241,.18),transparent 55%)}
  .logo{font-size:34px;font-weight:700;letter-spacing:-.5px}
  .logo span{background:linear-gradient(90deg,#818cf8,#22d3ee);-webkit-background-clip:text;color:transparent}
  .ring{width:46px;height:46px;border-radius:50%;border:3px solid rgba(129,140,248,.18);
    border-top-color:#818cf8;animation:spin .9s linear infinite}
  @keyframes spin{to{transform:rotate(360deg)}}
  .msg{font-size:14px;color:#94a3b8}
  .hint{font-size:12px;color:#64748b;max-width:420px;text-align:center;line-height:1.5}
  .err{display:none;color:#fca5a5;font-size:13px;max-width:460px;text-align:center;line-height:1.6}
</style></head>
<body><div class="wrap">
  <div class="logo">Logi<span>Mate</span></div>
  <div class="ring" id="ring"></div>
  <div class="msg" id="msg">Starting AI engine…</div>
  <div class="hint" id="hint">The first launch on a new PC can take a little longer while Windows scans the app.
    Please keep this window open — there is no need to open LogiMate again.</div>
  <div class="err" id="err"></div>
</div>
<script>
  var t0 = Date.now();
  var steps = ["Starting AI engine…", "Loading circuit synthesizer…", "Connecting to Logisim driver…", "Almost ready…"];
  setInterval(function(){
    var s = Math.floor((Date.now() - t0) / 1000);
    var i = Math.min(steps.length - 1, Math.floor(s / 4));
    var el = document.getElementById("msg");
    if (el && !window.__failed) el.textContent = steps[i] + (s >= 5 ? "  (" + s + "s)" : "");
  }, 500);
  function showError(text){
    window.__failed = true;
    document.getElementById("ring").style.display = "none";
    document.getElementById("hint").style.display = "none";
    document.getElementById("msg").textContent = "LogiMate could not start";
    var e = document.getElementById("err"); e.textContent = text; e.style.display = "block";
  }
</script></body></html>
"""


def main():
    # 1. Never allow duplicate instances (prevents CPU overload from repeated launches)
    if not acquire_single_instance():
        activate_existing_instance()
        return

    port = find_free_port(8000)
    app_url = f"http://127.0.0.1:{port}"

    # 2. Start loading the server immediately in the background (heavy AI imports happen here)
    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()

    def on_gui_started(window):
        ready = wait_for_server(port, server_thread)
        if ready:
            window.load_url(app_url)
        else:
            log_path = os.path.join(get_base_dir(), "server_startup_error.log")
            message = (
                "The local AI engine did not start. Please close this window and open LogiMate again. "
                f"If it keeps happening, send this file to support: {log_path}"
            )
            try:
                window.evaluate_js(f"showError({json.dumps(message)})")
            except Exception:
                pass

    # 3. Show the native window instantly with a loading screen
    try:
        import webview
        window = webview.create_window(
            title=APP_TITLE,
            html=SPLASH_HTML,
            width=1280,
            height=850,
            min_size=(960, 640),
            background_color="#080c14",
            zoomable=True,
        )
        # Starts native GUI loop (blocks until window is closed); readiness check runs in a separate thread
        webview.start(on_gui_started, window)
    except Exception as e:
        # Fallback to default browser if native webview has issue
        import webbrowser
        print(f"Opening in browser ({e})...")
        wait_for_server(port, server_thread)
        webbrowser.open(app_url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
