"""
SaveManager 静态方法单元测试 - 纯函数，不需要 PyQt5
"""
import importlib.util
import os
import sys
import types

def _load_module(name, path):
    saved_keys = ['PasteY', 'PasteY.engine', 'PasteY.core', 'PasteY.core.config',
                  'PasteY.core.utils', 'PasteY.ui', 'PasteY.ui.i18n']
    saved = {k: sys.modules.get(k) for k in saved_keys}
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    # use existing PyQt5 mocks from conftest.py, only add missing ones
    qt_widgets = sys.modules.get('PyQt5.QtWidgets')
    if qt_widgets and not hasattr(qt_widgets, 'QProgressDialog'):
        class _MockProgressDialog:
            def __init__(self, *a, **kw): pass
            def wasCanceled(self): return False
            def setValue(self, *a): pass
            def setLabelText(self, *a): pass
        qt_widgets.QProgressDialog = _MockProgressDialog
    if qt_widgets and not hasattr(qt_widgets, 'QMessageBox'):
        class _MockMessageBox:
            @staticmethod
            def critical(*a, **kw): return 0
            @staticmethod
            def warning(*a, **kw): return 0
            @staticmethod
            def information(*a, **kw): return 0
            @staticmethod
            def question(*a, **kw): return 0
        qt_widgets.QMessageBox = _MockMessageBox
    if qt_widgets and not hasattr(qt_widgets, 'QFileDialog'):
        qt_widgets.QFileDialog = type('QFileDialog', (), {
            'getSaveFileName': staticmethod(lambda *a, **kw: ('', '')),
        })
    for m in ['PasteY', 'PasteY.engine', 'PasteY.core', 'PasteY.ui']:
        if m not in sys.modules:
            sys.modules[m] = types.ModuleType(m)
    config_mod = types.ModuleType('PasteY.core.config')
    config_mod.AUTO_SAVE_CONFIG = {'enabled': False}
    config_mod.DEFAULT_PREFIX = 'paste'
    config_mod.OUTPUT_DIR_SUFFIX = '_paste_output'
    config_mod.LABELME_VERSION = '5.0.1'
    sys.modules['PasteY.core.config'] = config_mod
    utils_mod = types.ModuleType('PasteY.core.utils')
    utils_mod.extract_label_name = lambda x: x.split(' (')[0] if ' (' in x else x
    utils_mod.PathUtils = type('PathUtils', (), {})
    sys.modules['PasteY.core.utils'] = utils_mod
    i18n_mod = types.ModuleType('PasteY.ui.i18n')
    i18n_mod.t = lambda x: x
    sys.modules['PasteY.ui.i18n'] = i18n_mod
    spec.loader.exec_module(mod)
    for k in saved_keys:
        if saved[k] is None:
            sys.modules.pop(k, None)
        else:
            sys.modules[k] = saved[k]
    return mod

_sm_path = os.path.join(os.path.dirname(__file__), '..', 'engine', 'save_manager.py')
_mod = _load_module('PasteY.engine.save_manager', os.path.abspath(_sm_path))
_build_labelme_shape = _mod.SaveManager._build_labelme_shape


class TestBuildLabelmeShape:
    """_build_labelme_shape 静态方法测试"""

    def test_basic_shape(self):
        result = _build_labelme_shape('cat', 10, 20, 100, 50)
        assert result['label'] == 'cat'
        assert result['shape_type'] == 'rectangle'
        assert result['group_id'] is None
        assert result['description'] == ''
        assert result['flags'] == {}

    def test_points_correct(self):
        result = _build_labelme_shape('dog', 0, 0, 10, 10)
        points = result['points']
        assert points == [[0, 0], [10, 0], [10, 10], [0, 10]]

    def test_negative_coordinates(self):
        result = _build_labelme_shape('x', -5, -10, 20, 30)
        points = result['points']
        assert points[0] == [-5, -10]
        assert points[2] == [15, 20]

    def test_zero_size(self):
        result = _build_labelme_shape('empty', 0, 0, 0, 0)
        assert result['points'] == [[0, 0], [0, 0], [0, 0], [0, 0]]

    def test_float_coordinates(self):
        result = _build_labelme_shape('f', 1.5, 2.5, 3.0, 4.0)
        assert result['points'][0] == [1.5, 2.5]
        assert result['points'][2] == [4.5, 6.5]
