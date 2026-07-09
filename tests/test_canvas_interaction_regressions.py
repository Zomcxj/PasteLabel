"""画布悬停状态回归测试。"""
from PyQt5.QtCore import Qt

from pastelabel.canvas import canvas_interaction
from pastelabel.canvas.canvas_interaction import CanvasInteractionMixin


class Point:
    def __init__(self, x, y):
        self._x = x
        self._y = y

    def x(self): return self._x
    def y(self): return self._y


class Rect:
    def __init__(self, x=0, y=0, w=10, h=10):
        self._x = x
        self._y = y
        self._w = w
        self._h = h

    def x(self): return self._x
    def y(self): return self._y
    def width(self): return self._w
    def height(self): return self._h
    def left(self): return self._x
    def top(self): return self._y
    def contains(self, point):
        return self._x <= point.x() <= self._x + self._w and self._y <= point.y() <= self._y + self._h


class Editor:
    def __init__(self, mode):
        self.edit_mode = mode
        self.current_background = object()
        self.current_background_index = 0
        self.canvas_items = [(None, Rect(0, 0, 10, 10), "paste")]
        self.detection_boxes = [{"label": "cat", "x": 0, "y": 0, "width": 10, "height": 10}]
        self.selected_item = None
        self.pressed_label = None
        self.show_labels_checkbox = type("Check", (), {"isChecked": lambda self: True})()


class Canvas(CanvasInteractionMixin):
    def __init__(self, mode):
        self._editor = Editor(mode)
        self.background_scale = 1
        self.mouse_pos = Point(5, 5)
        self.selected_box = None
        self.selected_boxes = []
        self.selected_item_size = None
        self.updated = 0
        self.hover_resize_target = None
        self.hover_resize_handle = None

    def setCursor(self, *a):
        pass

    def update_status_label(self):
        pass

    def get_background_rect(self):
        return Rect(0, 0, 100, 100)

    def update(self):
        self.updated += 1

    def _current_modifiers(self):
        return Qt.NoModifier


def test_paste_hover_detects_box_handle(monkeypatch):
    monkeypatch.setattr(canvas_interaction, "QRectF", Rect)
    canvas = Canvas("paste")
    canvas.selected_box = 0
    canvas._editor.pressed_label = "cat"

    canvas._check_hover()

    # paste mode 下 hover 到选中框手柄，不修改编辑状态
    assert canvas.hover_resize_target == 'box'


def test_annotate_hover_clears_paste_item_edit_state(monkeypatch):
    monkeypatch.setattr(canvas_interaction, "QRectF", Rect)
    canvas = Canvas("annotate")
    canvas._editor.selected_item = 0
    canvas.selected_item_size = (10, 10)

    canvas._check_hover()

    # annotate mode 下 hover 到检测框，自动切换到框编辑
    assert canvas.selected_box == 0
    assert canvas._editor.selected_item is None
    assert canvas.selected_item_size is None


def test_paste_hover_selects_detection_box_without_click(monkeypatch):
    monkeypatch.setattr(canvas_interaction, "QRectF", Rect)
    canvas = Canvas("paste")

    canvas._check_hover()

    assert canvas.selected_box == 0
    assert canvas.selected_boxes == [0]


def test_ctrl_hover_adds_detection_box_to_selected_boxes_without_click(monkeypatch):
    monkeypatch.setattr(canvas_interaction, "QRectF", Rect)
    canvas = Canvas("annotate")
    canvas.selected_box = 0
    canvas.selected_boxes = [0]
    canvas.mouse_pos = Point(25, 5)
    canvas._editor.detection_boxes.append({"label": "dog", "x": 20, "y": 0, "width": 10, "height": 10})
    canvas._current_modifiers = lambda: Qt.ControlModifier

    canvas._check_hover()

    assert canvas.selected_box == 1
    assert canvas.selected_boxes == [0, 1]
