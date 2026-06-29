# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:\\VsPro\\PasteLabel/PasteY/main.py'],
    pathex=['D:\\VsPro\\PasteLabel'],
    binaries=[('D:\\software\\miniforge3\\envs\\llm\\Library\\bin\\ffi.dll', '.')],
    datas=[('D:\\VsPro\\PasteLabel/ico_image', 'ico_image')],
    hiddenimports=['PasteY', 'PasteY.ui', 'PasteY.ui.main_window', 'PasteY.ui.ui_builder', 'PasteY.ui.settings_dialog', 'PasteY.ui.theme', 'PasteY.ui.dwm', 'PasteY.ui.dialogs', 'PasteY.ui.widgets', 'PasteY.ui.i18n', 'PasteY.ui.styles', 'PasteY.engine', 'PasteY.engine.save_manager', 'PasteY.engine.undo_manager', 'PasteY.engine.label_manager', 'PasteY.engine.image_loader', 'PasteY.engine.paste_engine', 'PasteY.engine.event_handler', 'PasteY.canvas', 'PasteY.canvas.canvas', 'PasteY.canvas.canvas_renderer', 'PasteY.canvas.canvas_interaction', 'PasteY.canvas.canvas_drawing', 'PasteY.canvas.canvas_menu', 'PasteY.core', 'PasteY.core.config', 'PasteY.core.config_manager', 'PasteY.core.utils', 'PasteY.core.models', 'PasteY.core.editor_protocol', 'PasteY.core.exception_hook'],
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
