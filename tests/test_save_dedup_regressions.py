"""保存前同类框去重回归测试。"""
from pastelabel.engine.save_manager import SaveManager


class Rect:
    def __init__(self, x, y, width, height):
        self._x = x
        self._y = y
        self._width = width
        self._height = height

    def x(self): return self._x
    def y(self): return self._y
    def width(self): return self._width
    def height(self): return self._height


def test_deduplicate_rectangles_keeps_first_item_when_later_item_iou_is_at_least_98_percent():
    items = [
        (None, Rect(10, 10, 100, 100), 'first'),
        (None, Rect(11, 10, 100, 100), 'later'),
    ]

    kept = SaveManager._deduplicate_rectangles(items, lambda item: item[1])

    assert kept == [items[0]]


def test_deduplicate_rectangles_ignores_label_when_comparing_same_type_rectangles():
    boxes = [
        {'label': 'first', 'x': 10, 'y': 10, 'width': 100, 'height': 100},
        {'label': 'later', 'x': 11, 'y': 10, 'width': 100, 'height': 100},
    ]

    kept = SaveManager._deduplicate_rectangles(
        boxes, lambda box: Rect(box['x'], box['y'], box['width'], box['height'])
    )

    assert kept == [boxes[0]]


def test_deduplicate_rectangles_keeps_rectangles_below_98_percent_iou():
    boxes = [
        {'label': 'first', 'x': 10, 'y': 10, 'width': 100, 'height': 100},
        {'label': 'later', 'x': 20, 'y': 10, 'width': 100, 'height': 100},
    ]

    kept = SaveManager._deduplicate_rectangles(
        boxes, lambda box: Rect(box['x'], box['y'], box['width'], box['height'])
    )

    assert kept == boxes
