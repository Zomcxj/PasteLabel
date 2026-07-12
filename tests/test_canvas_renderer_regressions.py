"""画布渲染回归测试。"""
import os
from pathlib import Path
import subprocess
import sys

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


def test_boxes_use_label_color_fills_with_expected_alpha_states():
    script = '''
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QColor, QImage, QPainter, QPixmap
from PyQt5.QtWidgets import QApplication
from pastelabel.canvas.canvas_renderer import CanvasRendererMixin

class Check:
    def isChecked(self): return False

class Editor:
    show_paste_names_checkbox = Check()
    show_label_names_checkbox = Check()
    def get_label_color(self, label): return "#e53935"

class Renderer(CanvasRendererMixin):
    def __init__(self):
        self._editor = Editor()
        self.hover_resize_target = None
        self.hover_resize_handle = None

def pixel_after(draw):
    image = QImage(60, 60, QImage.Format_ARGB32)
    image.fill(Qt.white)
    painter = QPainter(image)
    draw(painter)
    painter.end()
    return image.pixelColor(30, 30)

def expected(alpha):
    color = QColor("#e53935")
    return QColor(
        round((color.red() * alpha + 255 * (255 - alpha)) / 255),
        round((color.green() * alpha + 255 * (255 - alpha)) / 255),
        round((color.blue() * alpha + 255 * (255 - alpha)) / 255),
    )

renderer = Renderer()
app = QApplication.instance() or QApplication([])
pixmap = QPixmap(40, 40)
pixmap.fill(Qt.white)
for draw in (
    lambda painter: renderer._draw_single_detection_box(painter, 10, 10, 40, 40, "cat", False, False),
    lambda painter: renderer._draw_single_paste_item(painter, pixmap, QRectF(10, 10, 40, 40), "cat", False, False),
):
    actual = pixel_after(draw)
    assert actual == expected(50), (actual.getRgb(), expected(50).getRgb())

for draw in (
    lambda painter: renderer._draw_single_detection_box(painter, 10, 10, 40, 40, "cat", True, False),
    lambda painter: renderer._draw_single_detection_box(painter, 10, 10, 40, 40, "cat", False, True),
    lambda painter: renderer._draw_single_paste_item(painter, pixmap, QRectF(10, 10, 40, 40), "cat", True, False),
    lambda painter: renderer._draw_single_paste_item(painter, pixmap, QRectF(10, 10, 40, 40), "cat", False, True),
):
    actual = pixel_after(draw)
    assert actual == expected(80), (actual.getRgb(), expected(80).getRgb())
'''
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=os.environ | {"QT_QPA_PLATFORM": "offscreen", "PYTHONPATH": str(ROOT)},
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
