"""
UndoManager 单元测试 - 纯数据结构操作，不需要 PyQt5
"""
import importlib.util
import os
import sys
import types

def _load_module(name, path):
    saved = {k: sys.modules.get(k) for k in ['PasteY', 'PasteY.engine', 'PasteY.core.config']}
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    config_mod = types.ModuleType('PasteY.core.config')
    config_mod.UNDO_CONFIG = {'max_history': 50}
    sys.modules['PasteY.core.config'] = config_mod
    pkg = types.ModuleType('PasteY')
    sys.modules['PasteY'] = pkg
    engine_pkg = types.ModuleType('PasteY.engine')
    sys.modules['PasteY.engine'] = engine_pkg
    spec.loader.exec_module(mod)
    for k, v in saved.items():
        if v is None:
            sys.modules.pop(k, None)
        else:
            sys.modules[k] = v
    return mod

_undo_path = os.path.join(os.path.dirname(__file__), '..', 'engine', 'undo_manager.py')
_mod = _load_module('PasteY.engine.undo_manager', os.path.abspath(_undo_path))
UndoManager = _mod.UndoManager


class TestUndoManagerBasic:
    """基本功能测试"""

    def test_initial_state(self):
        um = UndoManager()
        assert not um.can_undo()
        assert not um.can_redo()

    def test_save_state_enables_undo(self):
        um = UndoManager()
        um.save_state([], [])
        assert um.can_undo()
        assert not um.can_redo()

    def test_undo_returns_previous_state(self):
        um = UndoManager()
        um.save_state(['item1'], [{'label': 'a'}])
        items, boxes = um.undo([], [])
        assert items == ['item1']
        assert boxes == [{'label': 'a'}]

    def test_redo_after_undo(self):
        um = UndoManager()
        um.save_state(['item1'], [])
        items, boxes = um.undo([], [])
        assert not um.can_undo()
        assert um.can_redo()
        items2, boxes2 = um.redo(items, boxes)
        assert items2 == []
        assert boxes2 == []

    def test_undo_empty_returns_unchanged(self):
        um = UndoManager()
        items, boxes = um.undo(['a'], [{'b': 1}])
        assert items == ['a']
        assert boxes == [{'b': 1}]

    def test_redo_empty_returns_unchanged(self):
        um = UndoManager()
        items, boxes = um.redo(['a'], [{'b': 1}])
        assert items == ['a']
        assert boxes == [{'b': 1}]

    def test_clear(self):
        um = UndoManager()
        um.save_state(['a'], [])
        um.save_state(['b'], [])
        um.clear()
        assert not um.can_undo()
        assert not um.can_redo()

    def test_save_state_clears_redo(self):
        um = UndoManager()
        um.save_state(['a'], [])
        um.undo([], [])
        assert um.can_redo()
        um.save_state(['b'], [])
        assert not um.can_redo()


class TestUndoManagerHistory:
    """历史记录边界测试"""

    def test_max_history_limit(self):
        um = UndoManager()
        for i in range(60):
            um.save_state([i], [])
        count = 0
        while um.can_undo():
            um.undo([], [])
            count += 1
        assert count == 50

    def test_multiple_undo_redo(self):
        um = UndoManager()
        um.save_state(['a'], [])
        um.save_state(['b'], [])
        um.save_state(['c'], [])
        # undo 栈: [a, b, c], 当前画布状态假定为 ['d']
        items, _ = um.undo(['d'], [])
        assert items == ['c']
        items, _ = um.undo(items, [])
        assert items == ['b']
        items, _ = um.redo(items, [])
        assert items == ['c']
        items, _ = um.redo(items, [])
        assert items == ['d']

    def test_detection_boxes_are_deep_copied(self):
        um = UndoManager()
        original = [{'label': 'cat', 'x': 0}]
        um.save_state([], original)
        original[0]['label'] = 'dog'
        _, boxes = um.undo([], [])
        assert boxes[0]['label'] == 'cat'
