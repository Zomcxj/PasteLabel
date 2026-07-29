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


class _FakeBg:
    def width(self):
        return 100

    def height(self):
        return 80


def test_save_current_json_annotate_skips_never_annotated(tmp_path):
    img = tmp_path / "a.jpg"
    img.write_bytes(b"x")

    class Editor:
        _is_delete_view = False
        edit_mode = "annotate"
        detection_boxes = []
        canvas_items = []
        current_background_index = 0
        background_images = [str(img)]
        current_background = _FakeBg()
        saved = []

        def __init__(self):
            pass

    editor = Editor()
    mgr = SaveManager(editor)
    mgr.save_json = lambda *a, **k: editor.saved.append((a, k))
    mgr.save_current_json()
    assert editor.saved == []


def test_save_current_json_annotate_saves_when_has_boxes(tmp_path):
    img = tmp_path / "b.jpg"
    img.write_bytes(b"x")

    class Editor:
        _is_delete_view = False
        edit_mode = "annotate"
        detection_boxes = [{"label": "Car", "x": 0, "y": 0, "width": 1, "height": 1}]
        canvas_items = []
        current_background_index = 0
        background_images = [str(img)]
        current_background = _FakeBg()
        saved = []

    editor = Editor()
    mgr = SaveManager(editor)
    mgr.save_json = lambda *a, **k: editor.saved.append((a, k))
    mgr.save_current_json()
    assert len(editor.saved) == 1
    assert editor.saved[0][0][0] == str(img)


def test_save_current_json_annotate_saves_empty_when_json_exists(tmp_path):
    img = tmp_path / "c.jpg"
    img.write_bytes(b"x")
    (tmp_path / "c.json").write_text('{"shapes":[]}', encoding="utf-8")

    class Editor:
        _is_delete_view = False
        edit_mode = "annotate"
        detection_boxes = []
        canvas_items = []
        current_background_index = 0
        background_images = [str(img)]
        current_background = _FakeBg()
        saved = []

    editor = Editor()
    mgr = SaveManager(editor)
    mgr.save_json = lambda *a, **k: editor.saved.append((a, k))
    mgr.save_current_json()
    assert len(editor.saved) == 1
