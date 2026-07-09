"""标签缓存多选复制的 RED 回归测试。"""
from pathlib import Path

from pastelabel.ui.main_window import ImageEditor
from pastelabel.ui.ui_builder import UIBuilderMixin


def test_canvas_uses_selected_boxes_state_for_multi_selection():
    source = Path("pastelabel/canvas/canvas.py").read_text(encoding="utf-8")

    assert "self.selected_boxes" in source


def test_get_selected_detection_boxes_returns_all_selected_boxes():
    editor = type("Editor", (), {})()
    editor.detection_boxes = [
        {"label": "cat", "x": 1, "y": 2, "width": 3, "height": 4},
        {"label": "dog", "x": 5, "y": 6, "width": 7, "height": 8},
        {"label": "bird", "x": 9, "y": 10, "width": 11, "height": 12},
    ]
    editor.canvas = type("Canvas", (), {"selected_boxes": [0, 2]})()

    selected = ImageEditor._get_selected_detection_boxes(editor)

    assert selected == [
        dict(editor.detection_boxes[0]),
        dict(editor.detection_boxes[2]),
    ]


def test_copy_selected_labels_triggers_hover_sync_when_selection_is_empty():
    detection_box = {"label": "cat", "x": 1, "y": 2, "width": 3, "height": 4}

    class Canvas:
        def __init__(self):
            self.selected_box = None
            self.selected_boxes = []

        def _check_hover(self):
            self.selected_box = 0
            self.selected_boxes = [0]

    class StatusLabel:
        def __init__(self):
            self.text = None

        def setText(self, text):
            self.text = text

    editor = type("Editor", (), {})()
    editor.detection_boxes = [detection_box]
    editor.canvas = Canvas()
    editor.status_label = StatusLabel()
    editor.label_cache_slots = [{"name": "1", "items": [], "locked": False}]
    editor.active_label_cache_slot = 0
    editor.saved = 0
    editor.rebuilt = 0
    editor._save_label_cache_slots = lambda: setattr(editor, "saved", editor.saved + 1)
    editor._rebuild_label_cache_menu = lambda: setattr(editor, "rebuilt", editor.rebuilt + 1)
    editor._get_selected_detection_boxes = lambda: ImageEditor._get_selected_detection_boxes(editor)

    ImageEditor.copy_selected_labels_to_active_cache_slot(editor)

    assert editor.canvas.selected_box == 0
    assert editor.canvas.selected_boxes == [0]
    assert editor.label_cache_slots[0]["items"] == [dict(detection_box)]


def test_copy_selected_labels_falls_back_to_first_unlocked_slot_when_active_slot_locked():
    detection_box = {"label": "cat", "x": 1, "y": 2, "width": 3, "height": 4}

    class Canvas:
        def __init__(self):
            self.selected_box = 0
            self.selected_boxes = [0]

    class StatusLabel:
        def __init__(self):
            self.text = None

        def setText(self, text):
            self.text = text

    editor = type("Editor", (), {})()
    editor.detection_boxes = [detection_box]
    editor.canvas = Canvas()
    editor.status_label = StatusLabel()
    editor.label_cache_slots = [
        {"name": "1", "items": [], "locked": True},
        {"name": "2", "items": [], "locked": False},
        {"name": "3", "items": [], "locked": False},
    ]
    editor.active_label_cache_slot = 0
    editor.saved = 0
    editor.rebuilt = 0
    editor._save_label_cache_slots = lambda: setattr(editor, "saved", editor.saved + 1)
    editor._rebuild_label_cache_menu = lambda: setattr(editor, "rebuilt", editor.rebuilt + 1)
    editor._get_selected_detection_boxes = lambda: ImageEditor._get_selected_detection_boxes(editor)

    ImageEditor.copy_selected_labels_to_active_cache_slot(editor)

    assert editor.active_label_cache_slot == 1
    assert editor.label_cache_slots[0]["items"] == []
    assert editor.label_cache_slots[1]["items"] == [dict(detection_box)]


def test_reset_label_cache_slots_clears_items_and_locked_state():
    editor = type("Editor", (), {})()
    editor.label_cache_slots = [
        {"name": "自定义1", "items": [{"label": "cat"}], "locked": True, "copied_at": "10:00:00", "shortcut": "1"},
        {"name": "自定义2", "items": [{"label": "dog"}], "locked": True, "copied_at": "10:00:01", "shortcut": "2"},
        {"name": "自定义3", "items": [], "locked": False, "copied_at": "", "shortcut": "3"},
    ]
    editor.active_label_cache_slot = 2

    ImageEditor._reset_label_cache_slots(editor)

    assert editor.active_label_cache_slot == 0
    assert [slot["name"] for slot in editor.label_cache_slots] == ["缓存槽1", "缓存槽2", "缓存槽3"]
    assert [slot["items"] for slot in editor.label_cache_slots] == [[], [], []]
    assert [slot["locked"] for slot in editor.label_cache_slots] == [False, False, False]
    assert [slot["copied_at"] for slot in editor.label_cache_slots] == ["", "", ""]


def test_copy_selected_labels_rotates_to_oldest_unlocked_slot_instead_of_sticking_to_first_slot():
    detection_box = {"label": "cat", "x": 1, "y": 2, "width": 3, "height": 4}

    class Canvas:
        def __init__(self):
            self.selected_box = 0
            self.selected_boxes = [0]

    class StatusLabel:
        def __init__(self):
            self.text = None

        def setText(self, text):
            self.text = text

    editor = type("Editor", (), {})()
    editor.detection_boxes = [detection_box]
    editor.canvas = Canvas()
    editor.status_label = StatusLabel()
    editor.label_cache_slots = [
        {"items": [{"label": "old-1"}], "locked": False, "copied_at": "10:00:00", "copy_order": 1, "shortcut": "1"},
        {"items": [{"label": "old-2"}], "locked": False, "copied_at": "10:00:01", "copy_order": 2, "shortcut": "2"},
        {"items": [{"label": "old-3"}], "locked": False, "copied_at": "10:00:02", "copy_order": 3, "shortcut": "3"},
    ]
    editor.active_label_cache_slot = 0
    editor._label_cache_copy_counter = 3
    editor.saved = 0
    editor.rebuilt = 0
    editor._save_label_cache_slots = lambda: setattr(editor, "saved", editor.saved + 1)
    editor._rebuild_label_cache_menu = lambda: setattr(editor, "rebuilt", editor.rebuilt + 1)
    editor._get_selected_detection_boxes = lambda: ImageEditor._get_selected_detection_boxes(editor)

    ImageEditor.copy_selected_labels_to_active_cache_slot(editor)

    assert editor.active_label_cache_slot == 0
    assert editor.label_cache_slots[0]["items"] == [dict(detection_box)]

    ImageEditor.copy_selected_labels_to_active_cache_slot(editor)

    assert editor.active_label_cache_slot == 1
    assert editor.label_cache_slots[1]["items"] == [dict(detection_box)]


def test_cache_slot_row_click_only_switches_active_slot():
    editor = type("Editor", (), {})()
    editor.active = None
    editor.pasted = 0
    editor.cache_menu = None
    editor.set_active_label_cache_slot = lambda idx: setattr(editor, "active", idx)
    editor.paste_label_cache_slot = lambda idx: setattr(editor, "pasted", editor.pasted + 1)

    UIBuilderMixin._handle_cache_slot_row_click(editor, 2)

    assert editor.active == 2
    assert editor.pasted == 0
