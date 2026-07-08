"""画布右键菜单回归测试。"""
from pastelabel.canvas.canvas_menu import CanvasMenuMixin


class FakeCheckbox:
    def __init__(self, checked):
        self.checked = checked

    def isChecked(self):
        return self.checked


class FakeEditor:
    def __init__(self):
        self.show_labels_checkbox = FakeCheckbox(False)
        self._is_delete_view = False
        self.current_background = object()


class FakeCanvas(CanvasMenuMixin):
    def __init__(self):
        self._editor = FakeEditor()
        self.calls = []

    def find_item_at_position(self, mouse_pos):
        return None

    def _find_detection_box_at(self, mouse_pos):
        self.calls.append("box_lookup")
        return 0

    def _show_box_label_menu(self, box_index, mouse_pos):
        self.calls.append("box_menu")

    def _show_background_context_menu(self, mouse_pos):
        self.calls.append("background_menu")


def test_right_click_ignores_boxes_when_labels_hidden():
    canvas = FakeCanvas()

    assert canvas._handle_right_click(object()) is True
    assert canvas.calls == ["background_menu"]
