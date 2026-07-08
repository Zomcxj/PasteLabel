"""模式与导航控件回归测试。"""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_mode_segment_places_annotate_button_before_paste_button():
    source = (ROOT / "pastelabel" / "ui" / "ui_builder.py").read_text(encoding="utf-8")

    annotate_pos = source.index('self.btn_annotate_mode = QPushButton(tr("标注"))')
    paste_pos = source.index('self.btn_paste_mode = QPushButton(tr("贴图"))')
    assert annotate_pos < paste_pos
    assert "AnimatedSegmentedControl(self.mode_seg, self.btn_annotate_mode, self.btn_paste_mode)" in source


def test_mode_segment_defaults_to_annotate_checked():
    source = (ROOT / "pastelabel" / "ui" / "ui_builder.py").read_text(encoding="utf-8")

    assert "self.btn_annotate_mode.setChecked(True)" in source


def test_theme_button_icon_uses_gold_color():
    source = (ROOT / "pastelabel" / "ui" / "ui_builder.py").read_text(encoding="utf-8")

    assert "self.theme_btn.setIcon(QIcon(_load_svg_icon(SUN_SVG, 16, \"#D4AF37\")))" in source


def test_stats_button_uses_stats_copy_in_both_languages():
    ui_source = (ROOT / "pastelabel" / "ui" / "ui_builder.py").read_text(encoding="utf-8")
    i18n_source = (ROOT / "pastelabel" / "ui" / "i18n.py").read_text(encoding="utf-8")

    assert 'self.view_stats_btn = QPushButton(tr("统计"))' in ui_source
    assert '"统计": "统计"' in i18n_source
    assert '"统计": "Stats"' in i18n_source


def test_image_editor_starts_in_annotate_mode():
    source = (ROOT / "pastelabel" / "ui" / "main_window.py").read_text(encoding="utf-8")

    assert "self.edit_mode = 'annotate'" in source


def test_settings_dialog_uses_param_spin_style_for_magnifier_zoom():
    source = (ROOT / "pastelabel" / "ui" / "settings_dialog.py").read_text(encoding="utf-8")

    assert 'self.magnifier_zoom_spin = QDoubleSpinBox()' in source
    assert 'self.magnifier_zoom_spin.setObjectName("paramSpin")' in source


def test_settings_dialog_magnifier_zoom_range_is_point_eight_to_three():
    source = (ROOT / "pastelabel" / "ui" / "settings_dialog.py").read_text(encoding="utf-8")

    assert 'self.magnifier_zoom_spin.setRange(0.8, 3.0)' in source
    assert 'max(0.8, min(3.0,' in source


def test_settings_dialog_magnifier_zoom_supports_wheel_adjustment():
    source = (ROOT / "pastelabel" / "ui" / "settings_dialog.py").read_text(encoding="utf-8")

    assert 'self.magnifier_zoom_spin.setSingleStep(0.1)' in source


def test_theme_styles_qdouble_spinbox_like_other_numeric_inputs():
    source = (ROOT / "pastelabel" / "ui" / "theme.py").read_text(encoding="utf-8")

    assert 'QDoubleSpinBox {' in source
    assert 'QDoubleSpinBox:hover {' in source
    assert 'QDoubleSpinBox:focus {' in source
