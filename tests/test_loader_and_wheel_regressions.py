"""加载流程和滚轮优先级回归测试。"""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_load_background_folder_initializes_first_image_inside_loop():
    source = (ROOT / "pastelabel" / "engine" / "image_loader.py").read_text(encoding="utf-8")

    assert "if load_first and self.current_background is None:" in source
    assert "self.current_background = self._get_cached_pixmap(file_path)" in source


def test_load_background_folder_defers_background_list_updates_until_first_image_ready():
    source = (ROOT / "pastelabel" / "engine" / "image_loader.py").read_text(encoding="utf-8")

    freeze_pos = source.index("self.background_list.setUpdatesEnabled(False)")
    current_background_pos = source.index("self.current_background = self._get_cached_pixmap(file_path)")
    current_row_pos = source.index("self.background_list.setCurrentRow(new_index)")
    restore_pos = source.index("self.background_list.setUpdatesEnabled(True)")

    assert freeze_pos < current_background_pos < current_row_pos < restore_pos


def test_ctrl_wheel_scales_background_before_selected_objects():
    source = (ROOT / "pastelabel" / "canvas" / "canvas_interaction.py").read_text(encoding="utf-8")

    ctrl_pos = source.index("if event.modifiers() & Qt.ControlModifier:")
    item_pos = source.index("if self._editor.selected_item is not None:")
    box_pos = source.index("elif self.selected_box is not None:")
    assert ctrl_pos < item_pos < box_pos
