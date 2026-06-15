"""
Windows DWM API 模块 - 设置标题栏深色/浅色模式
兼容 Win10 1809+ (属性19) 和 Win10 1903+ / Win11 (属性20)
"""
import sys

_dwmapi = None
_user32 = None
_initialized = False
_dwm_available = False


def _init():
    global _dwmapi, _user32, _initialized, _dwm_available
    if _initialized:
        return
    _initialized = True
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        _dwmapi = ctypes.windll.dwmapi
        _user32 = ctypes.windll.user32
        _dwm_available = True
    except Exception:
        _dwm_available = False


def set_titlebar_dark(hwnd, dark):
    """
    设置 Windows 标题栏深色/浅色模式
    :param hwnd: 窗口句柄 (int)
    :param dark: True=深色标题栏, False=浅色标题栏
    """
    _init()
    if not _dwm_available or not hwnd:
        return False
    try:
        import ctypes
        value = ctypes.c_int(1 if dark else 0)
        # Win10 1809: 属性 19 (DWMWA_USE_IMMERSIVE_DARK_MODE)
        _dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(value), ctypes.sizeof(value))
        # Win10 1903+ / Win11: 属性 20
        _dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
        return True
    except Exception:
        return False


def is_available():
    _init()
    return _dwm_available
