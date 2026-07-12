import pytest
from pathlib import Path

from pastelabel.ui.theme import ThemeManager, ThemeMode


@pytest.mark.parametrize("mode", [ThemeMode.LIGHT, ThemeMode.DARK])
def test_named_action_buttons_use_silent_surface_and_blue_hover(mode):
    ThemeManager.set_mode(mode)
    style = ThemeManager.get_stylesheet()
    theme = ThemeManager.get_theme()

    assert f"QPushButton#navBtn {{\n                background-color: transparent;" in style
    assert f"color: {theme['text_secondary']};" in style.split("QPushButton#navBtn {", 1)[1].split("}", 1)[0]
    for name in ("accentBtn", "warningBtn"):
        block = style.split(f"QPushButton#{name} {{", 1)[1].split("}", 1)[0]
        hover_block = style.split(f"QPushButton#{name}:hover {{", 1)[1].split("}", 1)[0]
        assert f"background-color: {theme['widget_bg']};" in block
        assert f"border: 1px solid {theme['border_color']};" in block
        assert f"color: {theme['button_text']};" in block
        assert "border: 1px solid #2950ff;" in hover_block
        assert "background-color" not in hover_block


@pytest.mark.parametrize("mode", [ThemeMode.LIGHT, ThemeMode.DARK])
def test_mode_segment_uses_theme_text_until_selected(mode):
    root = Path(__file__).resolve().parents[1]
    builder = (root / "pastelabel" / "ui" / "ui_builder.py").read_text(encoding="utf-8")
    window = (root / "pastelabel" / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert "background-color: {t['widget_bg']};\n                border: 1px solid {t['border_color']};" in builder
    assert "color: {t['button_text']};" in builder
    assert "color: {t['button_text']};" in window
    assert "QPushButton:hover {{ color:" in builder
    assert "QPushButton:hover {{ color:" in window
    assert "QPushButton:checked {{ color: #FFFFFF;" in builder
    assert "QPushButton:checked {{ color: #FFFFFF;" in window
    assert "background-color: {t['widget_bg']};\n                    border: 1px solid {t['border_color']};" in window


@pytest.mark.parametrize("mode", [ThemeMode.LIGHT, ThemeMode.DARK])
def test_options_buttons_use_blue_pressed_state(mode):
    ThemeManager.set_mode(mode)
    style = ThemeManager.get_stylesheet()

    pressed_block = style.split("QPushButton#optionsBtn:pressed {", 1)[1].split("}", 1)[0]
    assert "background-color: #2950ff;" in pressed_block
    assert "border: 1px solid #2950ff;" in pressed_block
    assert "color: #FFFFFF;" in pressed_block


def test_mode_segment_keeps_blue_indicator_without_blue_inactive_labels():
    root = Path(__file__).resolve().parents[1]
    builder = (root / "pastelabel" / "ui" / "ui_builder.py").read_text(encoding="utf-8")
    window = (root / "pastelabel" / "ui" / "main_window.py").read_text(encoding="utf-8")

    assert "self.mode_seg_ctrl.set_accent(\"#2950ff\")" in builder
    assert "color: {t['button_text']}; border: none;" in builder
    assert "self.mode_seg_ctrl.set_accent(\"#2950ff\")" in window
    assert "color: {t['button_text']}; border: none;" in window


def test_named_controls_use_the_shared_silent_button_styles():
    root = Path(__file__).resolve().parents[1]
    builder = (root / "pastelabel" / "ui" / "ui_builder.py").read_text(encoding="utf-8")

    assert 'self.view_toggle_btn.setObjectName("warningBtn")' in builder
    assert builder.count('setObjectName("accentBtn")') == 2
    assert 'self.toggle_view_btn.setObjectName("warningBtn")' in builder


def test_all_inputs_hover_with_blue_border():
    style = ThemeManager.get_stylesheet()

    assert "QLineEdit:hover {\n                border: 1px solid #2950ff;" in style
    assert "QSpinBox:hover, QDoubleSpinBox:hover {\n                border: 1px solid #2950ff;" in style
    assert "QComboBox:hover {\n                border: 1px solid #2950ff;" in style


def test_label_path_list_selection_is_blue_with_white_text():
    style = ThemeManager.get_stylesheet()

    assert "QListWidget::item:selected {\n                background-color: #2950ff;\n                color: #FFFFFF;" in style
