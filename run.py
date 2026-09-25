"""
AI Logisim Controller — Desktop Application.
Launches as a native desktop window (no terminal spam, no manual server start).
"""

import sys
import time
import socket
import threading
import uvicorn
import requests


def find_free_port(start_port: int = 8000) -> int:
    """Finds an available local port."""
    for port in range(start_port, start_port + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start_port


def run_server(port: int):
    """Runs the FastAPI server silently in background with no access log spam."""
    from server import app
    # Disable access logs to prevent terminal spam
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
    )


def wait_for_server(port: int, timeout: float = 8.0) -> bool:
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
    wait_for_server(port)

    # Try launching as a native desktop window via pywebview
    try:
        import webview
        # Create native desktop window
        window = webview.create_window(
            title="AI Logisim Controller",
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
    main()
