"""Windows API helper using ctypes for topmost persistence, DPI scaling, and fallback media keys."""

import ctypes
import os
import sys

# Virtual-Key codes for media controls
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3

# SetWindowPos flags
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040

# Window styles
GWL_EXSTYLE = -20
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002

IS_WINDOWS = sys.platform.startswith("win")


def init_dpi_awareness() -> None:
    """Set process DPI awareness for razor-sharp rendering on high-DPI displays."""
    if not IS_WINDOWS:
        return
    try:
        # Per-monitor DPI awareness (Windows 8.1+)
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            # Fallback for Windows Vista/7
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def get_window_handle(tk_widget) -> int:
    """Resolve correct native OS window handle for a Tkinter window."""
    if not IS_WINDOWS:
        return 0
    try:
        tk_widget.update_idletasks()
        win_id = tk_widget.winfo_id()
        parent = ctypes.windll.user32.GetParent(win_id)
        return parent if parent != 0 else win_id
    except Exception:
        return 0


def set_topmost(hwnd: int) -> bool:
    """Ensure the window stays above other topmost windows without stealing focus."""
    if not IS_WINDOWS or hwnd == 0:
        return False
    try:
        flags = SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
        res = ctypes.windll.user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, flags)
        return bool(res)
    except Exception as e:
        print(f"[Win32] set_topmost failed: {e}")
        return False


def set_tool_window_style(hwnd: int) -> None:
    """Set WS_EX_TOOLWINDOW and WS_EX_TOPMOST so it does not clutter Alt-Tab."""
    if not IS_WINDOWS or hwnd == 0:
        return
    try:
        old_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        new_style = old_style | WS_EX_TOOLWINDOW | WS_EX_TOPMOST
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)
    except Exception as e:
        print(f"[Win32] set_tool_window_style failed: {e}")


def send_media_key(vk_code: int) -> bool:
    """
    Simulate a native Windows multimedia key press.
    Used as an automatic fallback when Spotify Web API returns 403 (Free account)
    or no active Spotify Connect device is reported.
    """
    if not IS_WINDOWS:
        return False
    try:
        user32 = ctypes.windll.user32
        # Key down
        user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
        # Key up
        user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
        return True
    except Exception as e:
        print(f"[Win32] send_media_key error: {e}")
        return False

