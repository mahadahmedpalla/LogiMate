"""
AI Logisim Controller — Desktop Application.
Launches as a native desktop window (no terminal spam, no manual server start).
"""

import os
import sys
import time
import socket
import threading
import traceback
import multiprocessing
import requests
import uvicorn


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


def find_free_port(start_port: int = 8000) -> int:
    """Finds an available local port."""
    for port in range(start_port, start_port + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start_port


def run_server(port: int):
    """Runs the FastAPI server with explicit config avoiding dynamic import issues."""
    try:
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
    except Exception as e:
        base_dir = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
        log_path = os.path.join(base_dir, "server_startup_error.log")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())


def wait_for_server(port: int, timeout: float = 12.0) -> bool:
    """Waits until the local server responds."""
    start = time.time()
    url = f"http://127.0.0.1:{port}/api/status"
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=0.5)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.15)
    return False


def main():
    port = find_free_port(8000)
    app_url = f"http://127.0.0.1:{port}"

    # Start FastAPI server in background thread
    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()

    # Wait for server ready
    ready = wait_for_server(port)

    # Try launching as a native desktop window via pywebview
    try:
        import webview
        # Create native desktop window
        window = webview.create_window(
            title="LogiMate — AI Logisim Controller",
            url=app_url,
            width=1280,
            height=850,
            min_size=(960, 640),
            background_color="#080c14",
        )
        # Starts native GUI loop (blocks until window is closed)
        webview.start()
    except Exception as e:
        # Fallback to default browser if native webview has issue
        import webbrowser
        print(f"Opening in browser ({e})...")
        webbrowser.open(app_url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
