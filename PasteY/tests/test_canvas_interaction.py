"""
CanvasInteractionMixin 静态方法单元测试 - 纯函数，不需要 PyQt5
"""
import importlib.util
import os
import sys
import types

def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    # mock PyQt5
    for m in ['PyQt5', 'PyQt5.QtWidgets', 'PyQt5.QtGui', 'PyQt5.QtCore']:
        if m not in sys.modules:
            sys.modules[m] = types.ModuleType(m)
    # mock QtWidgets classes needed by sibling mixins
    qt_widgets = sys.modules['PyQt5.QtWidgets']
    qt_widgets.QInputDialog = type('QInputDialog', (), {
        'getInt': staticmethod(lambda *a, **kw: (0, True)),
        'getText': staticmethod(lambda *a, **kw: ('', True)),
        'getItem': staticmethod(lambda *a, **kw: ('', True)),
    })
    qt_widgets.QApplication = type('QApplication', (), {
        'instance': staticmethod(lambda: None),
        'processEvents': staticmethod(lambda: None),
    })
    qt_widgets.QMessageBox = type('QMessageBox', (), {
        'question': staticmethod(lambda *a, **kw: 0),
    })
    # mock parent packages
    for m in ['PasteY', 'PasteY.canvas', 'PasteY.core', 'PasteY.ui']:
        if m not in sys.modules:
            sys.modules[m] = types.ModuleType(m)
    config_mod = types.ModuleType('PasteY.core.config')
    config_mod.BACKGROUND_SCALE_CONFIG = {'default_scale': 1.0}
    config_mod.WINDOW_CONFIG = {'min_width': 1024, 'min_height': 768}
    config_mod.DETECTION_BOX_CONFIG = {'min_width': 3, 'min_height': 3}
    sys.modules['PasteY.core.config'] = config_mod
    # mock sibling mixins
    for sibling in ['canvas_drawing', 'canvas_menu']:
        mod_path = os.path.join(os.path.dirname(__file__), '..', 'canvas', sibling + '.py')
        sib_spec = importlib.util.spec_from_file_location(f'PasteY.canvas.{sibling}', mod_path)
        sib_mod = importlib.util.module_from_spec(sib_spec)
        sys.modules[f'PasteY.canvas.{sibling}'] = sib_mod
        sib_spec.loader.exec_module(sib_mod)
    spec.loader.exec_module(mod)
    return mod

_ci_path = os.path.join(os.path.dirname(__file__), '..', 'canvas', 'canvas_interaction.py')
_mod = _load_module('PasteY.canvas.canvas_interaction', os.path.abspath(_ci_path))
_clamp = _mod.CanvasInteractionMixin._clamp_size_with_aspect


class TestClampSizeWithAspect:
    """_clamp_size_with_aspect 静态方法测试"""

    def test_no_clamp_needed(self):
        w, h = _clamp(100, 50, 200, 100, min_size=10, max_size=500)
        assert w == 100
        assert h == 50

    def test_min_size_clamp_shorter_dim(self):
        # new_w=5 > new_h=2.5 → else 分支，h 被夹到 min_size
        w, h = _clamp(5, 2.5, 200, 100, min_size=10, max_size=500)
        assert abs(w - 20.0) < 1e-6
        assert abs(h - 10.0) < 1e-6

    def test_min_size_clamp_height(self):
        w, h = _clamp(40, 5, 200, 100, min_size=10, max_size=500)
        assert abs(h - 10.0) < 1e-6

    def test_max_size_no_clamp_height_dominates(self):
        # new_w=600 > new_h=300 → else 分支，h=300 < max_size=500，不夹
        w, h = _clamp(600, 300, 200, 100, min_size=10, max_size=500)
        assert w == 600
        assert h == 300

    def test_max_size_clamp_height(self):
        w, h = _clamp(1000, 600, 200, 100, min_size=10, max_size=500)
        assert abs(h - 500.0) < 1e-6

    def test_default_max_size(self):
        # max_size 默认 = 10*100 = 1000，夹短边 h
        w, h = _clamp(5000, 2500, 200, 100, min_size=10)
        assert abs(h - 1000.0) < 1e-6
        assert abs(w - 2000.0) < 1e-6

    def test_square_aspect(self):
        w, h = _clamp(8, 8, 100, 100, min_size=10, max_size=500)
        assert w == 10
        assert h == 10

    def test_zero_orig_width(self):
        w, h = _clamp(50, 50, 0, 100, min_size=10, max_size=500)
        assert w == 50