"""
Windows DWM API 模块 - 设置标题栏深色/浅色模式
兼容 Win10 1809+ (属性19) 和 Win10 1903+ / Win11 (属性20)
优先使用 ctypes，不可用时使用 PowerShell
"""
import sys
import subprocess

_dwmapi = None
_initialized = False
_dwm_available = False


def _init():
    global _dwmapi, _initialized, _dwm_available
    if _initialized:
        return
    _initialized = True
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        _dwmapi = ctypes.windll.dwmapi
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

    if _dwm_available and hwnd:
        try:
            import ctypes
            value = ctypes.c_int(1 if dark else 0)
            _dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(value), ctypes.sizeof(value))
            _dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
            return True
        except Exception:
            pass

    if sys.platform == 'win32' and hwnd:
        try:
            v = 1 if dark else 0
            ps = (
                'Add-Type @"'
                'using System.Runtime.InteropServices;'
                'public class Dwm{'
                '[DllImport("dwmapi.dll")]'
                'public static extern int DwmSetWindowAttribute(System.IntPtr h,int a,ref int v,int s);}'
                '"@;'
                '[Dwm]::DwmSetWindowAttribute([IntPtr]{h},20,[ref]$v,4);'
                '[Dwm]::DwmSetWindowAttribute([IntPtr]{h},19,[ref]$v,4)'
            ).format(v=v, h=hwnd)
            subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", ps],
                creationflags=0x08000000
            )
            return True
        except Exception:
            pass

    return False


def is_available():
    _init()
    return _dwm_available
