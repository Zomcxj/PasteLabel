"""画布渲染回归测试。"""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_magnifier_only_appears_for_selected_box_or_draw_mode():
    source = (ROOT / "PasteY" / "canvas" / "canvas_renderer.py").read_text(encoding="utf-8")

    assert "if self.selected_box is None and not self.is_drawing_box:" in source
    assert "if getattr(self._editor, 'edit_mode', 'paste') != 'annotate':" in source
