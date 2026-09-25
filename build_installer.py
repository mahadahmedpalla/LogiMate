"""
Build script to compile LogiMate into a single-file Windows Installer (LogiMate-Setup-v1.0.0.exe).
Run: python build_installer.py
"""

import os
import sys
import subprocess


def find_iscc() -> str:
    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"),
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    raise FileNotFoundError("ISCC.exe (Inno Setup Compiler) not found. Please install Inno Setup 6.")


def build_installer():
    iscc = find_iscc()
    print("Found Inno Setup Compiler:", iscc)

    # Ensure dist/AI_Logisim_Controller exists
    dist_dir = os.path.join("dist", "AI_Logisim_Controller")
    if not os.path.exists(dist_dir):
        print("dist/AI_Logisim_Controller not found! Building application first...")
        import build_exe
        build_exe.build()

    iss_file = "installer.iss"
    print(f"Compiling Windows Installer using {iss_file}...")
    subprocess.check_call([iscc, iss_file])

    output_exe = os.path.abspath(os.path.join("dist_installer", "LogiMate-Setup-v1.0.0.exe"))
    print("\n" + "=" * 65)
    print("  SUCCESS: Single-File Setup Installer Created!")
    print(f"  Location: {output_exe}")
    print("  Size:", f"{os.path.getsize(output_exe) / (1024 * 1024):.1f} MB")
    print("  This single file is what you upload to your website or GitHub!")
    print("=" * 65)


if __name__ == "__main__":
    build_installer()
