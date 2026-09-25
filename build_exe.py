"""
Build script to compile AI Logisim Controller into a standalone Windows desktop executable (.exe).
Run: python build_exe.py
"""

import os
import sys
import shutil
import subprocess


def build():
    print("Preparing standalone native desktop executable for LogiMate AI Controller...")

    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",  # Suppresses terminal/console window completely
        "--name", "AI_Logisim_Controller",
        "--icon=app_icon.ico",
        "--add-data", "ui;ui",
        "--collect-all", "google.genai",
        "--collect-all", "webview",
        "--collect-all", "uvicorn",
        "--collect-all", "fastapi",
        "--collect-all", "starlette",
        "--collect-all", "pydantic",
        "--hidden-import", "webview",
        "--hidden-import", "clr_loader",
        "--hidden-import", "pythonnet",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops.asyncio",
        "--hidden-import", "uvicorn.protocols.http.h11_impl",
        "--hidden-import", "uvicorn.lifespan.off",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "h11",
        "--hidden-import", "anyio",
        "run.py"
    ]

    print("Executing command:", " ".join(cmd))
    subprocess.check_call(cmd)

    # Post-build: Ensure ui assets and icon are directly in dist root as well
    dist_dir = os.path.join("dist", "AI_Logisim_Controller")
    ui_dest = os.path.join(dist_dir, "ui")
    if not os.path.exists(ui_dest):
        shutil.copytree("ui", ui_dest)
        print("Copied ui to dist/AI_Logisim_Controller/ui")

    icon_dest = os.path.join(dist_dir, "app_icon.ico")
    shutil.copy2("app_icon.ico", icon_dest)

    print("\n" + "=" * 65)
    print("  SUCCESS: Standalone Desktop App Built!")
    print("  Location: dist/AI_Logisim_Controller/AI_Logisim_Controller.exe")
    print("  Double-clicking the .exe opens a native desktop window directly.")
    print("  No terminal, no command prompt, no browser tabs!")
    print("=" * 65)


if __name__ == "__main__":
    build()
