"""
Logisim 2.7.1 Windows Automation Driver.
Handles window discovery, foreground focusing, shortcut commands,
and pixel-exact canvas coordinate clicking for pin poking.
Includes comprehensive Logisim and Java discovery, bundled Logisim fallback,
and zero-keystroke direct circuit loading.
"""

import os
import sys
import glob
import time
import base64
import shutil
import subprocess
from io import BytesIO
from typing import Dict, Optional, Tuple, List
import pygetwindow as gw
import pyautogui
from PIL import Image

try:
    import win32gui
    import win32con
    import win32process
    import ctypes
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


# Default calibrated offsets for Logisim 2.7.1 on Windows:
# Window top-left to canvas (0, 0)
DEFAULT_CANVAS_OFFSET_X = 200  # Left tool explorer width ~195-205px
DEFAULT_CANVAS_OFFSET_Y = 70   # Titlebar + Menu + Icon Toolbar ~65-75px

# Poke tool icon offset in the top toolbar
DEFAULT_POKE_TOOL_X = 22
DEFAULT_POKE_TOOL_Y = 58


def find_java() -> Optional[str]:
    """
    Finds javaw or java executable on the system.
    Searches PATH, JAVA_HOME, and standard 64-bit/32-bit Java installation directories.
    """
    for name in ["javaw", "java"]:
        p = shutil.which(name)
        if p:
            return p

    if os.environ.get("JAVA_HOME"):
        for name in ["javaw.exe", "java.exe"]:
            p = os.path.join(os.environ["JAVA_HOME"], "bin", name)
            if os.path.exists(p):
                return p

    search_patterns = [
        r"C:\Program Files\Common Files\Oracle\Java\javapath\javaw.exe",
        r"C:\Program Files\Java\*\bin\javaw.exe",
        r"C:\Program Files (x86)\Java\*\bin\javaw.exe",
        r"C:\Program Files\Eclipse Adoptium\*\bin\javaw.exe",
        r"C:\Program Files\Amazon Corretto\*\bin\javaw.exe",
        r"C:\Program Files\Zulu\*\bin\javaw.exe",
        r"C:\Program Files\Microsoft\*\bin\javaw.exe",
    ]
    for pat in search_patterns:
        matches = glob.glob(pat)
        if matches:
            return matches[0]

    return None


def find_logisim_exe(custom_path: Optional[str] = None) -> Optional[str]:
    """
    Discovers Logisim 2.7.1 executable or jar across all standard and bundled locations:
    1. Explicit custom user path
    2. Bundled logisim folder in application root / distribution
    3. User Downloads, Desktop, Documents (case-insensitive search for *logisim*.exe or *logisim*.jar)
    4. Program Files
    5. PATH
    6. Fallback legacy paths
    """
    if custom_path and os.path.exists(custom_path):
        return os.path.abspath(custom_path)

    base_dirs: List[str] = []

    # 1. Check frozen app directory (PyInstaller dist / installed folder)
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        meipass = getattr(sys, "_MEIPASS", "")
        base_dirs.extend([
            os.path.join(exe_dir, "logisim"),
            exe_dir,
            meipass,
            os.path.join(meipass, "logisim"),
        ])

    # 2. Check source development directory
    mod_dir = os.path.dirname(os.path.abspath(__file__))
    app_root = os.path.abspath(os.path.join(mod_dir, ".."))
    parent_dir = os.path.abspath(os.path.join(app_root, ".."))
    base_dirs.extend([
        os.path.join(app_root, "logisim"),
        app_root,
        os.path.join(parent_dir, "logisim"),
        parent_dir,
    ])

    standard_logisim_names = [
        "logisim-win-2.7.1.exe",
        "logisim-win-2.7.1 (1).exe",
        "logisim-win-2.7.1 (2).exe",
        "logisim.exe",
        "logisim.jar",
        "logisim-generic-2.7.1.jar",
    ]

    for bd in base_dirs:
        if not bd or not os.path.exists(bd):
            continue
        for fname in standard_logisim_names:
            p = os.path.join(bd, fname)
            if os.path.exists(p):
                return os.path.abspath(p)

    # 3. Check user standard directories (Downloads, Desktop, Documents)
    user_dirs = [
        os.path.expanduser(r"~\Downloads"),
        os.path.expanduser(r"~\Desktop"),
        os.path.expanduser(r"~\Documents"),
        r"C:\Program Files\Logisim",
        r"C:\Program Files (x86)\Logisim",
    ]
    for ud in user_dirs:
        if not os.path.exists(ud):
            continue
        for ext in ["*.exe", "*.jar"]:
            for match in glob.glob(os.path.join(ud, f"*logisim*{ext}")):
                # Avoid matching AI_Logisim_Controller itself
                if "ai_logisim_controller" in os.path.basename(match).lower():
                    continue
                if os.path.exists(match):
                    return os.path.abspath(match)

    # 4. Check system PATH
    for cmd in ["logisim", "logisim.exe"]:
        p = shutil.which(cmd)
        if p and "ai_logisim_controller" not in p.lower():
            return os.path.abspath(p)

    # 5. Legacy developer fallbacks
    fallbacks = [
        r"f:\original final downloads\logisim-win-2.7.1 (1).exe",
        r"f:\original final downloads\logisim-win-2.7.1.exe",
    ]
    for fb in fallbacks:
        if os.path.exists(fb):
            return os.path.abspath(fb)

    return None


class LogisimDriver:
    """Controls the local Logisim 2.7.1 desktop application."""

    def __init__(
        self,
        canvas_offset_x: int = DEFAULT_CANVAS_OFFSET_X,
        canvas_offset_y: int = DEFAULT_CANVAS_OFFSET_Y,
        custom_logisim_path: Optional[str] = None,
    ):
        self.canvas_offset_x = canvas_offset_x
        self.canvas_offset_y = canvas_offset_y
        self.custom_logisim_path = custom_logisim_path
        self.poke_tool_offset = (DEFAULT_POKE_TOOL_X, DEFAULT_POKE_TOOL_Y)
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.05

    def find_logisim_exe(self) -> Optional[str]:
        """Discovers Logisim 2.7.1 executable or jar."""
        return find_logisim_exe(self.custom_logisim_path)

    def is_bundled(self) -> bool:
        """Returns True if Logisim was found inside the application's own bundled directory."""
        exe = self.find_logisim_exe()
        if not exe:
            return False
        exe_lower = exe.lower()
        # Check if inside app directory
        app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..")).lower()
        if app_root in exe_lower or "\\logisim\\" in exe_lower:
            return True
        if getattr(sys, "frozen", False):
            inst_dir = os.path.dirname(sys.executable).lower()
            if inst_dir in exe_lower:
                return True
        return False

    def _spawn_logisim(self, exe_path: str, circuit_path: Optional[str] = None) -> bool:
        """Spawns Logisim using Java or direct executable execution."""
        java_cmd = find_java()
        args = []

        if java_cmd:
            args = [java_cmd, "-jar", exe_path, "-nosplash"]
        else:
            args = [exe_path]

        if circuit_path and os.path.exists(circuit_path):
            args.append(os.path.abspath(circuit_path))

        try:
            subprocess.Popen(args)
            time.sleep(0.8)
            self.focus()
            return True
        except Exception:
            # Fallback: if java command failed, try direct execution of .exe
            if java_cmd and exe_path.lower().endswith(".exe"):
                try:
                    direct_args = [exe_path]
                    if circuit_path and os.path.exists(circuit_path):
                        direct_args.append(os.path.abspath(circuit_path))
                    subprocess.Popen(direct_args)
                    time.sleep(0.8)
                    self.focus()
                    return True
                except Exception:
                    pass
        return False

    def launch_logisim(self) -> bool:
        """Launches Logisim 2.7.1 using discovered or bundled executable."""
        # If Logisim is already running, simply focus it without spawning another instance
        if self.find_window():
            self.focus()
            return True

        exe_path = self.find_logisim_exe()
        if not exe_path:
            return False

        return self._spawn_logisim(exe_path)

    def find_window(self) -> Optional[gw.Win32Window]:
        """Finds active Logisim window, strictly excluding the AI Logisim Controller app window."""
        windows = [
            w for w in gw.getAllWindows()
            if "logisim" in w.title.lower() and "ai logisim controller" not in w.title.lower()
        ]
        if not windows:
            return None
        # Sort so non-untitled circuit windows take priority, then largest area
        windows.sort(
            key=lambda w: (
                0 if "untitled" in w.title.lower() else 1,
                w.width * w.height
            ),
            reverse=True
        )
        return windows[0]

    def is_connected(self) -> bool:
        """Returns True if a Logisim window is currently running and detected."""
        return self.find_window() is not None

    def get_window_info(self) -> Dict:
        """Returns window coordinates, size, and status."""
        win = self.find_window()
        if not win:
            return {"connected": False, "title": None, "rect": None}
        return {
            "connected": True,
            "title": win.title,
            "rect": {
                "left": win.left,
                "top": win.top,
                "width": win.width,
                "height": win.height,
            },
            "canvas_offset": {
                "x": self.canvas_offset_x,
                "y": self.canvas_offset_y,
            },
        }

    def focus(self) -> bool:
        """
        Brings the Logisim window to the foreground.
        Uses Win32 thread input attachment to bypass Windows ASFW foreground lock.
        """
        win = self.find_window()
        if not win:
            return False

        if HAS_WIN32:
            try:
                hwnd = win._hWnd
                if win32gui.GetForegroundWindow() == hwnd:
                    return True

                if win32gui.IsIconic(hwnd):
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                else:
                    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

                fore_hwnd = win32gui.GetForegroundWindow()
                fore_thread, _ = win32process.GetWindowThreadProcessId(fore_hwnd)
                app_thread = win32process.GetCurrentThreadId()

                if fore_thread != app_thread:
                    ctypes.windll.user32.AttachThreadInput(fore_thread, app_thread, True)
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
                    ctypes.windll.user32.SetFocus(hwnd)
                    ctypes.windll.user32.AttachThreadInput(fore_thread, app_thread, False)
                else:
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
                    ctypes.windll.user32.SetFocus(hwnd)

                time.sleep(0.15)
                return win32gui.GetForegroundWindow() == hwnd
            except Exception:
                pass

        try:
            win.activate()
            time.sleep(0.15)
            return True
        except Exception:
            return False

    def select_poke_tool(self):
        """Activates the Poke Tool by clicking its standard toolbar icon."""
        win = self.find_window()
        if not win:
            return
        self.focus()
        poke_x = win.left + self.poke_tool_offset[0]
        poke_y = win.top + self.poke_tool_offset[1]
        pyautogui.click(poke_x, poke_y)
        time.sleep(0.05)

    def tick_once(self) -> bool:
        """Sends Ctrl + K to single-step the simulation tick."""
        if not self.focus():
            return False
        pyautogui.hotkey("ctrl", "k")
        return True

    def toggle_ticks(self) -> bool:
        """Sends Ctrl + T to toggle continuous simulation clock ticking."""
        if not self.focus():
            return False
        pyautogui.hotkey("ctrl", "t")
        return True

    def reset_simulation(self) -> bool:
        """Sends Ctrl + R to reset simulation state."""
        if not self.focus():
            return False
        pyautogui.hotkey("ctrl", "r")
        return True

    def poke_canvas_coord(self, canvas_x: int, canvas_y: int) -> bool:
        """
        Clicks a target pin on the canvas using the Poke tool.
        Calculates screen coordinate from window origin + canvas offset.
        """
        win = self.find_window()
        if not win:
            return False

        self.focus()
        self.select_poke_tool()

        target_screen_x = win.left + self.canvas_offset_x + canvas_x
        target_screen_y = win.top + self.canvas_offset_y + canvas_y

        pyautogui.click(target_screen_x, target_screen_y)
        return True

    def open_circuit_direct(self, filepath: str) -> bool:
        """
        Directly launches or updates Logisim with the circuit file.
        Completely eliminates Ctrl+O, file dialogs, and keyboard hijacking.
        """
        abs_path = os.path.abspath(filepath)
        if not os.path.exists(abs_path):
            return False

        # Snapshot existing Logisim windows to close previous empty Untitled windows
        old_windows = [
            w for w in gw.getAllWindows()
            if "logisim" in w.title.lower() and "ai logisim controller" not in w.title.lower()
        ]

        exe_path = self.find_logisim_exe()
        if exe_path:
            spawned = self._spawn_logisim(exe_path, circuit_path=abs_path)
            if spawned:
                time.sleep(0.8)

                # Close previous empty/untitled Logisim windows to prevent window clutter,
                # but preserve any existing user-named projects
                for ow in old_windows:
                    if "untitled" in ow.title.lower():
                        try:
                            if HAS_WIN32:
                                win32gui.PostMessage(ow._hWnd, win32con.WM_CLOSE, 0, 0)
                            else:
                                ow.close()
                        except Exception:
                            pass

                time.sleep(0.3)
                self.focus()
                return True

        # Fallback to shortcut paste only if Logisim is confirmed running and focused
        return self.open_file(abs_path)

    def open_file(self, filepath: str) -> bool:
        """
        Fallback: Opens a .circ file in Logisim using Ctrl+O and clipboard paste.
        STRICTLY VERIFIES that Logisim is the confirmed active foreground window before sending any keystrokes.
        NEVER sends keystrokes if the foreground window is a browser or another app.
        """
        abs_path = os.path.abspath(filepath)
        if not os.path.exists(abs_path):
            return False

        old_win = self.find_window()
        if not old_win:
            return False

        if not self.focus():
            return False

        # SAFETY CHECK: Only proceed if Logisim is truly the foreground window
        if HAS_WIN32:
            fore_hwnd = win32gui.GetForegroundWindow()
            if fore_hwnd != old_win._hWnd:
                # Foreground lock prevented focus; do NOT send Ctrl+O into the user's browser!
                return False

        is_untitled = "untitled" in old_win.title.lower()

        try:
            import pyperclip
            pyperclip.copy(abs_path)
            time.sleep(0.1)
            pyautogui.hotkey("ctrl", "o")
            time.sleep(0.8)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.2)
            pyautogui.press("enter")
            time.sleep(0.7)

            if is_untitled and old_win:
                try:
                    if HAS_WIN32:
                        win32gui.SetForegroundWindow(old_win._hWnd)
                    else:
                        old_win.activate()
                    time.sleep(0.15)
                    pyautogui.hotkey("ctrl", "w")
                    time.sleep(0.15)
                except Exception:
                    pass

            self.focus()
            return True
        except Exception:
            return False

    def capture_screenshot_base64(self) -> Optional[str]:
        """
        Captures the Logisim window image and returns it as a base64 encoded PNG.
        Used for on-demand inspection only.
        """
        win = self.find_window()
        if not win:
            return None

        self.focus()
        try:
            bbox = (win.left, win.top, win.width, win.height)
            if win.width <= 0 or win.height <= 0:
                return None

            img = pyautogui.screenshot(region=bbox)
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            return f"data:image/png;base64,{img_str}"
        except Exception:
            return None
