"""事件处理回归测试。"""
from pastelabel.engine.event_handler import EventHandlerMixin


class FakeEditor(EventHandlerMixin):
    def __init__(self):
        self._is_delete_view = False
        self.background_images = ["0.png", "1.png", "2.png", "3.png"]
        self.current_background_index = 0
        self._nav_step = 2
        self.switched_to = None

    def switch_background_to_index(self, index):
        self.switched_to = index


def test_work_path_navigation_uses_step():
    editor = FakeEditor()

    editor.switch_background(1)

    assert editor.switched_to == 2
