# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['PasteY\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('ico_image', 'ico_image'), ('D:\\software\\miniforge3\\envs\\llm\\Library\\bin\\ffi.dll', '.')],
    hiddenimports=['PasteY.ui.settings_dialog', 'PasteY.engine.save_manager', 'PasteY.engine.undo_manager', 'PasteY.canvas.canvas_drawing', 'PasteY.canvas.canvas_menu', 'PasteY.core.config_manager'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'pandas', 'numpy', 'pytest'],
    noarchive=False,
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
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['ico_image\\icoo.png'],
)
