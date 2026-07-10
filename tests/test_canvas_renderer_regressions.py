"""画布渲染回归测试。"""
from pathlib import Path

from PyQt5.QtCore import QRectF

from pastelabel.engine.paste_engine import PasteEngineMixin


ROOT = Path(__file__).resolve().parents[1]


def test_magnifier_only_appears_for_selected_box_or_draw_mode():
    source = (ROOT / "pastelabel" / "canvas" / "canvas_renderer.py").read_text(encoding="utf-8")

    assert "if self.selected_box is None and not self.is_drawing_box:" in source
    assert "if getattr(self._editor, 'edit_mode', 'paste') != 'annotate':" in source


def test_crosshair_is_drawn_only_in_annotate_mode_while_mouse_is_inside_canvas():
    source = (ROOT / "pastelabel" / "canvas" / "canvas_renderer.py").read_text(encoding="utf-8")

    assert "if (getattr(self._editor, 'edit_mode', 'paste') == 'annotate' and" in source
    assert "self.mouse_inside and self._editor.current_background is not None and" in source
    assert "background_rect is not None):" in source
    assert "def _draw_crosshair(self, painter):" in source
    assert "CROSSHAIR_CONFIG" in source
    assert "CROSSHAIR_CONFIG.get('alpha', 160)" in source


def test_paste_engine_offsets_fully_overlapping_group_by_three_pixels():
    source = (ROOT / "pastelabel" / "engine" / "paste_engine.py").read_text(encoding="utf-8")

    assert "OVERLAP_OFFSET_STEP = 3" in source
    assert "def _offset_overlapping_paste_group(" in source
    assert "for rect, label in pasted_group:" in source


def test_offset_overlapping_paste_group_keeps_boxes_inside_background_bounds():
    class FakeBackground:
        def width(self):
            return 10

        def height(self):
            return 10

    class Editor(PasteEngineMixin):
        def __init__(self):
            self.current_background = FakeBackground()
            self.detection_boxes = [{"x": 7, "y": 7, "width": 3, "height": 3, "label": "cat"}]

    editor = Editor()

    adjusted = editor._offset_overlapping_paste_group([(QRectF(7, 7, 3, 3), "cat")])

    rect, label = adjusted[0]
    assert rect.x() >= 0
    assert rect.y() >= 0
    assert rect.x() + rect.width() <= editor.current_background.width()
    assert rect.y() + rect.height() <= editor.current_background.height()
