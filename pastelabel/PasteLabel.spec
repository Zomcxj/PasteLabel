# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:\\VsPro\\PasteLabel/pastelabel/main.py'],
    pathex=['D:\\VsPro\\PasteLabel'],
    binaries=[('D:\\software\\miniforge3\\envs\\llm\\Library\\bin\\ffi.dll', '.')],
    datas=[('D:\\VsPro\\PasteLabel/ico_image', 'ico_image')],
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
    icon=['D:\\VsPro\\PasteLabel\\ico_image\\icoo.png'],
)
