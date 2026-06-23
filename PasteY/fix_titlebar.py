"""设置标题栏颜色 - 独立脚本，通过 llm 环境的 Python 运行"""
import sys

try:
    import ctypes
    from ctypes import wintypes
    
    hwnd = int(sys.argv[1])
    dark = int(sys.argv[2])
    
    dwm = ctypes.windll.dwmapi
    value = ctypes.c_int(1 if dark else 0)
    dwm.DwmSetWindowAttribute(
        wintypes.HWND(hwnd), 20, ctypes.byref(value), ctypes.sizeof(value)
    )
    dwm.DwmSetWindowAttribute(
        wintypes.HWND(hwnd), 19, ctypes.byref(value), ctypes.sizeof(value)
    )
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
