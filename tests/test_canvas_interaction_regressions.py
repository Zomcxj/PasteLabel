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


class Background:
    def __init__(self, w=100, h=100):
        self._w = w
        self._h = h

    def width(self): return self._w
    def height(self): return self._h


class WheelDelta:
    def __init__(self, y):
        self._y = y

    def y(self): return self._y


class WheelEvent:
    def __init__(self, delta_y, modifiers=0):
        self._delta = WheelDelta(delta_y)
        self._modifiers = modifiers

    def angleDelta(self): return self._delta
    def modifiers(self): return self._modifiers


class Editor:
    def __init__(self, mode):
        self.edit_mode = mode
        self.current_background = Background()
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
        self.synced_indexes = []

    def setCursor(self, *a):
        pass

    def update_status_label(self):
        pass

    def get_background_rect(self):
        return Rect(0, 0, 100, 100)

    def update(self):
        self.updated += 1

    def _sync_detection_box_to_dict(self, index):
        self.synced_indexes.append(index)

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


def test_scale_selected_box_uses_configured_scale_step(monkeypatch):
    monkeypatch.setattr(canvas_interaction, "QRectF", Rect)
    monkeypatch.setitem(canvas_interaction.DETECTION_BOX_WHEEL_CONFIG, 'scale_step', 0.1)
    canvas = Canvas("annotate")
    canvas.selected_box = 0

    canvas._scale_selected_box(WheelEvent(120))

    box = canvas._editor.detection_boxes[0]
    assert round(box['x'], 2) == 0.0
    assert round(box['y'], 2) == 0.0
    assert round(box['width'], 2) == 11.0
    assert round(box['height'], 2) == 11.0
    assert canvas.synced_indexes == [0]


def test_adjust_selected_box_edge_moves_only_nearest_edge(monkeypatch):
    monkeypatch.setattr(canvas_interaction, "QRectF", Rect)
    monkeypatch.setitem(canvas_interaction.DETECTION_BOX_WHEEL_CONFIG, 'edge_step', 5)
    canvas = Canvas("annotate")
    canvas.selected_box = 0
    canvas._editor.detection_boxes[0].update({"x": 20, "y": 10, "width": 10, "height": 10})
    canvas.mouse_pos = Point(17, 15)

    canvas._adjust_selected_box_edge(WheelEvent(120))

    box = canvas._editor.detection_boxes[0]
    assert box['x'] == 15
    assert box['y'] == 10
    assert box['width'] == 15
    assert box['height'] == 10
    assert canvas.synced_indexes == [0]


def test_wheel_event_uses_edge_adjustment_when_mouse_is_outside_selected_box(monkeypatch):
    monkeypatch.setattr(canvas_interaction, "QRectF", Rect)
    monkeypatch.setitem(canvas_interaction.DETECTION_BOX_WHEEL_CONFIG, 'edge_step', 4)
    canvas = Canvas("annotate")
    canvas.selected_box = 0
    canvas._editor.detection_boxes[0].update({"x": 20, "y": 10, "width": 20, "height": 10})
    canvas.mouse_pos = Point(41, 15)

    canvas.wheelEvent(WheelEvent(-120))

    box = canvas._editor.detection_boxes[0]
    assert box['x'] == 20
    assert box['y'] == 10
    assert box['width'] == 16
    assert box['height'] == 10


def test_wheel_event_uses_image_coords_for_right_edge_adjustment_when_scaled(monkeypatch):
    monkeypatch.setattr(canvas_interaction, "QRectF", Rect)
    monkeypatch.setitem(canvas_interaction.DETECTION_BOX_WHEEL_CONFIG, 'edge_step', 4)
    canvas = Canvas("annotate")
    canvas.selected_box = 0
    canvas.background_scale = 0.5
    canvas._editor.detection_boxes[0].update({"x": 20, "y": 10, "width": 20, "height": 10})
    canvas.mouse_pos = Point(21, 8)

    canvas.wheelEvent(WheelEvent(-120))

    box = canvas._editor.detection_boxes[0]
    assert box['x'] == 20
    assert box['y'] == 10
    assert box['width'] == 16
    assert box['height'] == 10
