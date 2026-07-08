from pastelabel.ui.theme import ThemeManager


def test_dialog_button_style_matches_settings_radius():
    style = ThemeManager.get_dialog_button_style()
    assert "border-radius: 10px" in style
    assert "font-size: 12px" in style
