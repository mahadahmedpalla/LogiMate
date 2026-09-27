"""
Logisim 2.7.1 Windows Automation Driver.
Handles window discovery, foreground focusing, shortcut commands,
and pixel-exact canvas coordinate clicking for pin poking.
"""

import os
import time
import base64
from io import BytesIO
from typing import Dict, Optional, Tuple
import pygetwindow as gw
import pyautogui
from PIL import Image

try:
    import win32gui
    import win32con
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


class LogisimDriver:
    """Controls the local Logisim 2.7.1 desktop application."""

    def __init__(
        self,
        canvas_offset_x: int = DEFAULT_CANVAS_OFFSET_X,
        canvas_offset_y: int = DEFAULT_CANVAS_OFFSET_Y,
    ):
        self.canvas_offset_x = canvas_offset_x
        self.canvas_offset_y = canvas_offset_y
        self.poke_tool_offset = (DEFAULT_POKE_TOOL_X, DEFAULT_POKE_TOOL_Y)
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.05

    def launch_logisim(self) -> bool:
        """Launches Logisim 2.7.1 using installed 64-bit Java (bypasses 32-bit Launch4j issue)."""
        # If Logisim is already running, simply focus it without spawning another JVM
        if self.find_window():
            self.focus()
            return True

        possible_paths = [
            r"f:\original final downloads\logisim-win-2.7.1 (1).exe",
            r"f:\original final downloads\logisim-win-2.7.1.exe",
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logisim-win-2.7.1 (1).exe")),
            os.path.expanduser(r"~\Downloads\logisim-win-2.7.1 (1).exe"),
            os.path.expanduser(r"~\Downloads\logisim-win-2.7.1.exe"),
        ]
        for p in possible_paths:
            if os.path.exists(p):
                import subprocess
                try:
                    subprocess.Popen(["javaw", "-jar", p, "-nosplash"])
                    time.sleep(0.5)
                    self.focus()
                    return True
                except Exception:
                    pass
        return False

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
        """Brings the Logisim window to the foreground."""
        win = self.find_window()
        if not win:
            return False

        try:
            if HAS_WIN32:
                hwnd = win._hWnd
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                try:
                    win32gui.SetForegroundWindow(hwnd)
                except Exception:
                    # Workaround for Windows foreground lock: press alt and retry
                    pyautogui.press("alt")
                    time.sleep(0.05)
                    win32gui.SetForegroundWindow(hwnd)
            else:
                win.activate()
            time.sleep(0.2)
            return True
        except Exception:
            try:
                win.activate()
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
        Completely eliminates Ctrl+O, file dialogs, and clipboard pasting.
        """
        abs_path = os.path.abspath(filepath)
        if not os.path.exists(abs_path):
            return False

        # Collect any existing Logisim windows to close after launching the new circuit
        old_windows = [
            w for w in gw.getAllWindows()
            if "logisim" in w.title.lower() and "ai logisim controller" not in w.title.lower()
        ]

        # Locate Logisim executable
        possible_exes = [
            r"f:\original final downloads\logisim-win-2.7.1 (1).exe",
            r"f:\original final downloads\logisim-win-2.7.1.exe",
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logisim-win-2.7.1 (1).exe")),
            os.path.expanduser(r"~\Downloads\logisim-win-2.7.1 (1).exe"),
        ]
        exe_path = next((p for p in possible_exes if os.path.exists(p)), None)

        if exe_path:
            import subprocess
            try:
                # Launch Logisim directly with circuit argument and -nosplash to bypass splash screen deadlock
                subprocess.Popen(["javaw", "-jar", exe_path, "-nosplash", abs_path])
                time.sleep(0.8)

                # Close previous Logisim windows to prevent window and JVM stacking
                for ow in old_windows:
                    try:
                        if HAS_WIN32:
                            win32gui.PostMessage(ow._hWnd, win32con.WM_CLOSE, 0, 0)
                        else:
                            ow.close()
                    except Exception:
                        pass

                time.sleep(0.4)
                self.focus()
                return True
            except Exception:
                pass

        # Fallback to shortcut paste if direct spawn fails
        return self.open_file(abs_path)

    def open_file(self, filepath: str) -> bool:
        """
        Opens a .circ file in Logisim using Ctrl+O and clipboard paste.
        Automatically closes previous empty 'Untitled' windows so only the active circuit remains.
        """
        abs_path = os.path.abspath(filepath)
        if not os.path.exists(abs_path):
            return False

        old_win = self.find_window()
        is_untitled = old_win and "untitled" in old_win.title.lower()

        if not self.focus():
            return False

        try:
            import pyperclip
            pyperclip.copy(abs_path)
            time.sleep(0.1)
            pyautogui.hotkey("ctrl", "o")
            # Allow Java JFileChooser dialog to open and focus the filename text field
            time.sleep(0.8)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.2)
            pyautogui.press("enter")
            time.sleep(0.7)

            # If old window was empty 'Untitled', close it cleanly with Ctrl+W
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

            # Refocus the newly opened circuit window
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
            # Ensure bbox has positive dimensions
            if win.width <= 0 or win.height <= 0:
                return None

            img = pyautogui.screenshot(region=bbox)
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            return f"data:image/png;base64,{img_str}"
        except Exception:
            return None
