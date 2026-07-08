"""对话框回归测试。"""
from pastelabel.ui import i18n
from pastelabel.ui.dialog_helpers import center_on_parent
from pastelabel.ui.dialogs import ProgressDialogFactory


def test_progress_dialog_cancel_button_uses_current_language():
    i18n.set_lang("en")

    dialog = ProgressDialogFactory.create_progress_dialog(None, "保存进度", "正在保存所有图片...", 1)

    assert dialog.args[1] == "Cancel"


class Geometry:
    def __init__(self, x, y, w, h):
        self._x, self._y, self._w, self._h = x, y, w, h

    def x(self): return self._x
    def y(self): return self._y
    def width(self): return self._w
    def height(self): return self._h


class Widget:
    def __init__(self, geometry, parent=None):
        self._geometry = geometry
        self._parent = parent
        self.moved_to = None

    def geometry(self): return self._geometry
    def parent(self): return self._parent
    def move(self, x, y): self.moved_to = (x, y)


def test_center_on_parent_uses_parent_window_geometry():
    parent = Widget(Geometry(100, 200, 800, 600))
    dialog = Widget(Geometry(0, 0, 200, 100), parent)

    center_on_parent(dialog)

    assert dialog.moved_to == (400, 450)
