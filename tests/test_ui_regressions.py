"""Regression tests for recently reported UI failures."""
import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_canvas_imports_qpixmap_for_brightness_contrast_updates():
    source = (ROOT / "pastelabel" / "canvas" / "canvas.py").read_text(encoding="utf-8")

    assert "from PyQt5.QtGui import QPixmap" in source


def test_brightness_contrast_uses_vectorized_pixel_processing():
    source = (ROOT / "pastelabel" / "canvas" / "canvas.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    method = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "apply_brightness_contrast"
    )

    assert not any(isinstance(node, (ast.For, ast.While)) for node in ast.walk(method))
    assert "np.frombuffer" in source
    assert "np.clip" in source


def test_message_box_relocalizes_detail_button_after_click():
    source = (ROOT / "pastelabel" / "ui" / "dialog_helpers.py").read_text(encoding="utf-8")

    assert "btn.clicked" in source
    assert "QTimer.singleShot(0, self._fix_detail_buttons)" in source


def test_memory_action_dispatches_memory_records_dialog(monkeypatch):
    from pastelabel.ui import memory_dialog
    from pastelabel.ui.mixins.options_popup import OptionsPopupMixin

    calls = {}

    class FakeMemoryRecordsDialog:
        def __init__(self, parent):
            calls["parent"] = parent

        def exec_(self):
            calls["executed"] = True

    monkeypatch.setattr(memory_dialog, "MemoryRecordsDialog", FakeMemoryRecordsDialog)

    owner = object()
    OptionsPopupMixin._show_memory_records(owner)

    assert calls == {"parent": owner, "executed": True}
