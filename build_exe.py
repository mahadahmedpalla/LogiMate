"""
Build script to compile AI Logisim Controller into a standalone Windows desktop executable (.exe).
Run: python build_exe.py
"""

import os
import sys
import subprocess


def build():
    print("Preparing standalone native desktop executable for AI Logisim Controller...")

    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",  # Suppresses terminal/console window completely
        "--name", "AI_Logisim_Controller",
        "--icon=app_icon.ico",
        "--add-data", "ui;ui",
        "--hidden-import", "pywebview",
        "--hidden-import", "clr_loader",
        "--hidden-import", "pythonnet",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.lifespan",
        "--hidden-import", "uvicorn.lifespan.on",
        "run.py"
    ]

    print("Executing command:", " ".join(cmd))
    subprocess.check_call(cmd)
    print("\n" + "=" * 65)
    print("  SUCCESS: Standalone Desktop App Built!")
    print("  Location: dist/AI_Logisim_Controller/AI_Logisim_Controller.exe")
    print("  Double-clicking the .exe opens a native desktop window directly.")
    print("  No terminal, no command prompt, no browser tabs!")
    print("=" * 65)


if __name__ == "__main__":
    build()
