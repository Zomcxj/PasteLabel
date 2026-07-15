# -*- mode: python ; coding: utf-8 -*-
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_ffi_dll = os.path.join(_root, '..', 'Library', 'bin', 'ffi.dll')
_binaries = []
if os.path.exists(_ffi_dll):
    _binaries.append((_ffi_dll, '.'))

_icon = [os.path.join(_root, 'ico_image', 'icoo.png')] if sys.platform == 'win32' else []

a = Analysis(
    [os.path.join(_root, 'pastelabel', 'main.py')],
    pathex=[_root],
    binaries=_binaries,
    datas=[(os.path.join(_root, 'ico_image'), 'ico_image')],
    hiddenimports=['pastelabel', 'pastelabel.ui', 'pastelabel.ui.main_window', 'pastelabel.ui.ui_builder', 'pastelabel.ui.settings_dialog', 'pastelabel.ui.theme', 'pastelabel.ui.dwm', 'pastelabel.ui.dialogs', 'pastelabel.ui.i18n', 'pastelabel.engine', 'pastelabel.engine.save_manager', 'pastelabel.engine.undo_manager', 'pastelabel.engine.label_manager', 'pastelabel.engine.image_loader', 'pastelabel.engine.paste_engine', 'pastelabel.engine.event_handler', 'pastelabel.canvas', 'pastelabel.canvas.canvas', 'pastelabel.canvas.canvas_renderer', 'pastelabel.canvas.canvas_interaction', 'pastelabel.canvas.canvas_drawing', 'pastelabel.canvas.canvas_menu', 'pastelabel.core', 'pastelabel.core.config', 'pastelabel.core.config_manager', 'pastelabel.core.utils', 'pastelabel.core.editor_protocol', 'pastelabel.core.exception_hook'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'pandas', 'numpy', 'pytest'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [('-O2', None, 'OPTION')],
    name='PasteLabel',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_icon,
)
