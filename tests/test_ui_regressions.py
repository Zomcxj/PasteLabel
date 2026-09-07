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
