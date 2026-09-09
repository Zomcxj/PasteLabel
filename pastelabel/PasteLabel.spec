# -*- mode: python ; coding: utf-8 -*-
import os
import sys

_root = os.getcwd()

_ffi_dll = os.path.join(sys.prefix, 'Library', 'bin', 'ffi.dll')
_binaries = []
if os.path.exists(_ffi_dll):
    _binaries.append((_ffi_dll, '.'))

_icon = [os.path.join(_root, 'ico_image', 'icoo.png')] if sys.platform == 'win32' else []

a = Analysis(
    [os.path.join(_root, 'pastelabel', 'main.py')],
    pathex=[_root],
    binaries=_binaries,
    datas=[(os.path.join(_root, 'ico_image'), 'ico_image')],
    hiddenimports=['pastelabel', 'pastelabel.main', 'pastelabel.sip', 'pastelabel.ui', 'pastelabel.ui.main_window', 'pastelabel.ui.ui_builder', 'pastelabel.ui.icons', 'pastelabel.ui.settings_dialog', 'pastelabel.ui.theme', 'pastelabel.ui.dwm', 'pastelabel.ui.dialogs', 'pastelabel.ui.i18n', 'pastelabel.ui.dialog_helpers', 'pastelabel.ui.memory_dialog', 'pastelabel.ui.segmented_control', 'pastelabel.ui.processing_panel', 'pastelabel.ui.dataset_classifier_dialog', 'pastelabel.ui.mixins', 'pastelabel.ui.mixins.dataset_classifier', 'pastelabel.ui.mixins.background_list', 'pastelabel.ui.mixins.label_cache_slot', 'pastelabel.ui.mixins.memory_record', 'pastelabel.ui.mixins.stats', 'pastelabel.ui.mixins.theme', 'pastelabel.ui.mixins.translation', 'pastelabel.ui.mixins.toolbar', 'pastelabel.ui.mixins.options_popup', 'pastelabel.ui.mixins.cache_menu', 'pastelabel.ui.mixins.lists', 'pastelabel.ui.mixins.panels', 'pastelabel.ui.mixins.processing_panel_builder', 'pastelabel.widgets', 'pastelabel.widgets.canvas_adjustment', 'pastelabel.widgets.spinner', 'pastelabel.widgets.drag_out_list', 'pastelabel.widgets.hover_popup', 'pastelabel.widgets.hover_menu', 'pastelabel.widgets.processing', 'pastelabel.engine', 'pastelabel.engine.save_manager', 'pastelabel.engine.undo_manager', 'pastelabel.engine.label_manager', 'pastelabel.engine.image_loader', 'pastelabel.engine.paste_engine', 'pastelabel.engine.event_handler', 'pastelabel.engine.augmenter', 'pastelabel.engine.augmenter.base', 'pastelabel.engine.augmenter.color', 'pastelabel.engine.augmenter.flipt', 'pastelabel.engine.augmenter.noise', 'pastelabel.engine.augmenter.translate', 'pastelabel.engine.augmenter.rotate', 'pastelabel.engine.augmenter.scale', 'pastelabel.engine.yolo_exporter', 'pastelabel.engine.base_exporter', 'pastelabel.engine.voc_exporter', 'pastelabel.engine.coco_exporter', 'pastelabel.engine.splitter', 'pastelabel.engine.dataset_classifier', 'pastelabel.canvas', 'pastelabel.canvas.canvas', 'pastelabel.canvas.canvas_renderer', 'pastelabel.canvas.canvas_interaction', 'pastelabel.canvas.canvas_drawing', 'pastelabel.canvas.canvas_menu', 'pastelabel.core', 'pastelabel.core.config', 'pastelabel.core.config_manager', 'pastelabel.core.utils', 'pastelabel.core.editor_protocol', 'pastelabel.core.exception_hook', 'pkgutil'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'pandas', 'pytest', 'PySide6', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets', 'PySide6.QtSvg', 'PySide6.QtNetwork'],
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    ([('-O2', None, 'OPTION')] if sys.platform == 'win32' else []),
    name='PasteLabel',
    onefile=(sys.platform != 'win32'),
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
