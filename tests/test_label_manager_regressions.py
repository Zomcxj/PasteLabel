"""标签管理回归测试。"""
from pastelabel.engine.label_manager import LabelManager


class FakeSignal:
    def emit(self):
        pass


class FakeList:
    def __init__(self, selected=None):
        self.items = []
        self.selected = selected or []

    def clear(self):
        self.items.clear()

    def addItem(self, item):
        self.items.append(item)

    def selectedItems(self):
        return self.selected


class FakeItem:
    def __init__(self, text):
        self._text = text

    def text(self):
        return self._text


class FakeEditor:
    def __init__(self):
        self.global_labels = set()
        self.detection_boxes = []
        self.detection_boxes_dict = {}
        self.current_background = object()
        self.current_background_index = 0
        self.label_list = FakeList()
        self.background_images = []
        self.canvas = type("Canvas", (), {"selected_box": None})()
        self.saved = []

    def save_json(self, *args, **kwargs):
        self.saved.append((args, kwargs))


def test_add_label_ignores_qaction_checked_bool():
    editor = FakeEditor()
    manager = LabelManager(editor)
    manager.label_list_changed = FakeSignal()

    manager.add_label(False)

    assert editor.global_labels == set()


def test_update_label_list_ignores_non_string_labels():
    editor = FakeEditor()
    editor.global_labels = {False, "cat"}
    editor.detection_boxes = [{"label": True}, {"label": "dog"}]

    manager = LabelManager(editor)

    manager.update_label_list()

    assert len(editor.label_list.items) == 2


def test_delete_label_does_not_pass_detection_boxes_as_canvas_items(monkeypatch):
    editor = FakeEditor()
    editor.label_list = FakeList([FakeItem("cat (1)")])
    editor.global_labels = {"cat"}
    editor.background_images = ["cat.png"]
    editor.detection_boxes = [
        {"label": "cat", "x": 1, "y": 2, "width": 3, "height": 4},
        {"label": "dog", "x": 5, "y": 6, "width": 7, "height": 8},
    ]
    editor.detection_boxes_dict = {0: list(editor.detection_boxes)}

    from pastelabel.engine import label_manager
    monkeypatch.setattr(
        label_manager.dialog_helpers,
        "question",
        lambda *a, **kw: label_manager.dialog_helpers.QMessageBox.Yes,
    )
    manager = LabelManager(editor)
    manager.label_list_changed = FakeSignal()
    manager.data_changed = FakeSignal()

    manager.delete_label()

    assert editor.saved[0][1]["canvas_items"] == []


def test_delete_label_saves_each_background_with_its_own_index(monkeypatch):
    editor = FakeEditor()
    editor.label_list = FakeList([FakeItem("cat (1)")])
    editor.global_labels = {"cat", "dog"}
    editor.background_images = ["img0.png", "img1.png"]
    editor.current_background_index = 1
    editor.detection_boxes = [
        {"label": "cat", "x": 1, "y": 1, "width": 2, "height": 2},
        {"label": "dog", "x": 2, "y": 2, "width": 3, "height": 3},
    ]
    editor.detection_boxes_dict = {
        0: [{"label": "cat", "x": 0, "y": 0, "width": 1, "height": 1}],
        1: list(editor.detection_boxes),
    }

    from pastelabel.engine import label_manager
    monkeypatch.setattr(
        label_manager.dialog_helpers,
        "question",
        lambda *a, **kw: label_manager.dialog_helpers.QMessageBox.Yes,
    )
    manager = LabelManager(editor)
    manager.label_list_changed = FakeSignal()
    manager.data_changed = FakeSignal()

    manager.delete_label()

    assert editor.detection_boxes == [
        {"label": "dog", "x": 2, "y": 2, "width": 3, "height": 3}
    ]
    assert editor.detection_boxes_dict == {0: [], 1: editor.detection_boxes}
    assert [call[1]["current_index"] for call in editor.saved] == [0, 1]
    assert [call[1]["canvas_items"] for call in editor.saved] == [[], []]
