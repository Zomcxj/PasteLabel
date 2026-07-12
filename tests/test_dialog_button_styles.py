from pastelabel.ui.theme import ThemeManager


def test_dialog_button_style_matches_settings_radius():
    style = ThemeManager.get_dialog_button_style()
    theme = ThemeManager.get_theme()

    assert "border-radius: 10px" in style
    assert f"font-size: {theme['font_size']}px" in style
