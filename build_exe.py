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
        "--add-data", "logisim;logisim",
        "--collect-all", "google.genai",
        "--collect-all", "webview",
        "--collect-all", "uvicorn",
        "--collect-all", "fastapi",
        "--collect-all", "starlette",
        "--collect-all", "pydantic",
        "--collect-all", "requests",
        "--collect-all", "groq",
        "--hidden-import", "groq",
        "--hidden-import", "requests",
        "--hidden-import", "webview",
        "--hidden-import", "clr_loader",
        "--hidden-import", "pythonnet",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops.asyncio",
        "--hidden-import", "uvicorn.protocols.http.h11_impl",
        "--hidden-import", "uvicorn.lifespan.off",
        "--hidden-import", "uvicorn.lifespan.on",
        "--distpath", "dist_build",
        "--hidden-import", "h11",
        "--hidden-import", "anyio",
        "run.py"
    ]

    print("Executing command:", " ".join(cmd))
    subprocess.check_call(cmd)

    # Post-build: Ensure built binary and assets are placed into dist/AI_Logisim_Controller safely
    staging_dir = os.path.join("dist_build", "AI_Logisim_Controller")
    dist_dir = os.path.join("dist", "AI_Logisim_Controller")
    os.makedirs(dist_dir, exist_ok=True)

    if os.path.exists(staging_dir):
        shutil.copytree(staging_dir, dist_dir, dirs_exist_ok=True)
        print("Copied built binary to dist/AI_Logisim_Controller")
        try:
            shutil.rmtree("dist_build")
        except Exception:
            pass

    ui_dest = os.path.join(dist_dir, "ui")
    shutil.copytree("ui", ui_dest, dirs_exist_ok=True)
    print("Copied updated ui to dist/AI_Logisim_Controller/ui")

    logisim_dest = os.path.join(dist_dir, "logisim")
    if os.path.exists("logisim"):
        shutil.copytree("logisim", logisim_dest, dirs_exist_ok=True)
        print("Copied bundled logisim to dist/AI_Logisim_Controller/logisim")

    icon_dest = os.path.join(dist_dir, "app_icon.ico")
    shutil.copy2("app_icon.ico", icon_dest)

    # Clean any local user credentials or test circuits from distribution bundle
    dist_config = os.path.join(dist_dir, "config.json")
    if os.path.exists(dist_config):
        os.remove(dist_config)
    dist_output = os.path.join(dist_dir, "output")
    if os.path.exists(dist_output):
        shutil.rmtree(dist_output, ignore_errors=True)

    print("\n" + "=" * 65)
    print("  SUCCESS: Standalone Desktop App Built!")
    print("  Location: dist/AI_Logisim_Controller/AI_Logisim_Controller.exe")
    print("  Double-clicking the .exe opens a native desktop window directly.")
    print("  No terminal, no command prompt, no browser tabs!")
    print("=" * 65)


if __name__ == "__main__":
    build()
