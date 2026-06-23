"""
Windows 标题栏颜色设置辅助脚本
通过独立进程调用，绕过 PyInstaller 的 ctypes 限制
"""
import sys
import ctypes
from ctypes import wintypes

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36


def set_titlebar_color(hwnd, color=None, dark=True):
    dwm = ctypes.windll.dwmapi

    value = ctypes.c_int(1 if dark else 0)
    dwm.DwmSetWindowAttribute(
        wintypes.HWND(hwnd),
        ctypes.c_int(DWMWA_USE_IMMERSIVE_DARK_MODE),
        ctypes.byref(value),
        ctypes.sizeof(value),
    )

    if color is not None:
        r, g, b = color
        colorref = ctypes.c_int((b << 16) | (g << 8) | r)
        dwm.DwmSetWindowAttribute(
            wintypes.HWND(hwnd),
            ctypes.c_int(DWMWA_CAPTION_COLOR),
            ctypes.byref(colorref),
            ctypes.sizeof(colorref),
        )


if __name__ == "__main__":
    hwnd = int(sys.argv[1])
    dark = sys.argv[2] == "1"
    color_str = sys.argv[3] if len(sys.argv) > 3 else None

    color = None
    if color_str:
        parts = color_str.split(",")
        color = (int(parts[0]), int(parts[1]), int(parts[2]))

    set_titlebar_color(hwnd, color=color, dark=dark)
