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


def test_settings_dialog_exposes_separate_wheel_scale_and_edge_step_controls():
    source = (ROOT / "pastelabel" / "ui" / "settings_dialog.py").read_text(encoding="utf-8")
    i18n_source = (ROOT / "pastelabel" / "ui" / "i18n.py").read_text(encoding="utf-8")

    assert '"detection_box_scale_step_spin", "detection_box_scale_step"' in source
    assert '"paste_item_scale_step_spin", "paste_item_scale_step"' in source
    assert 'scale_step_spin.setRange(0.01, 0.30)' in source
    assert 'self.detection_box_wheel_edge_step_spin = QSpinBox()' in source
    assert '"检测框缩放步长", "detection_box_scale_step_spin"' in source
    assert '"贴图缩放步长", "paste_item_scale_step_spin"' in source
    assert 'tr("单侧位移像素")' in source
    assert '"检测框缩放步长": "框缩放步长"' in i18n_source
    assert '"贴图缩放步长": "贴图缩放步长"' in i18n_source
    assert '"单侧位移像素": "单侧位移像素"' in i18n_source


def test_settings_dialog_minimum_width_is_560_pixels():
    source = (ROOT / "pastelabel" / "ui" / "settings_dialog.py").read_text(encoding="utf-8")

    assert 'self.setMinimumWidth(560)' in source


def test_settings_dialog_minimum_height_is_600_pixels():
    source = (ROOT / "pastelabel" / "ui" / "settings_dialog.py").read_text(encoding="utf-8")

    assert 'self.setMinimumHeight(600)' in source


def test_settings_dialog_exposes_crosshair_width_and_color_controls():
    source = (ROOT / "pastelabel" / "ui" / "settings_dialog.py").read_text(encoding="utf-8")

    assert 'self.crosshair_width_spin = QDoubleSpinBox()' in source
    assert 'self.crosshair_color_btn = QPushButton()' in source
    assert 'dialog = ThemedColorDialog(self)' in source
    assert 'tr("十字线粗细")' in source
    assert 'tr("十字线颜色")' in source


def test_settings_dialog_crosshair_width_uses_decimal_range_and_half_step():
    source = (ROOT / "pastelabel" / "ui" / "settings_dialog.py").read_text(encoding="utf-8")

    assert 'self.crosshair_width_spin.setRange(0.5, 3.0)' in source
    assert 'self.crosshair_width_spin.setSingleStep(0.5)' in source
    assert "float(CROSSHAIR_CONFIG.get('width', 1.0))" in source


def test_crosshair_color_button_uses_white_text_on_its_color_background():
    source = (ROOT / "pastelabel" / "ui" / "settings_dialog.py").read_text(encoding="utf-8")

    assert 'color: white;' in source


def test_paste_label_press_highlights_paste_items_and_stats_offer_color_action():
    ui_builder_source = (ROOT / "pastelabel" / "ui" / "ui_builder.py").read_text(encoding="utf-8")
    renderer_source = (ROOT / "pastelabel" / "canvas" / "canvas_renderer.py").read_text(encoding="utf-8")
    main_window_source = (ROOT / "pastelabel" / "ui" / "main_window.py").read_text(encoding="utf-8")

    assert 'self.paste_label_list.itemPressed.connect(self.label_list_item_pressed)' in ui_builder_source
    assert 'self.paste_label_list.itemClicked.connect(self.label_list_item_clicked)' in ui_builder_source
    assert 'is_pressed_label = self._is_pressed_label({"label": label})' in renderer_source
    assert 'self._draw_paste_with_overlay(painter, pixmap, item_rect, label, 155)' in renderer_source
    assert 'self._draw_paste_with_overlay(painter, pixmap, item_rect, label, 60)' in renderer_source
    assert 'ThemedColorDialog' in main_window_source
    assert 'def _set_label_color_button(self, button, color):' in main_window_source
    assert 'self._set_label_color_button(color_button, color.name())' in main_window_source
    assert 'label_item.setBackground' not in main_window_source


def test_stats_color_buttons_show_and_refresh_html_color_values():
    source = (ROOT / "pastelabel" / "ui" / "main_window.py").read_text(encoding="utf-8")

    assert source.count('color_button = QPushButton()') == 2
    assert 'button.setText(color)' in source
    assert 'self._set_label_color_button(color_button, color.name())' in source


def test_settings_dialog_places_handle_and_border_after_label_position():
    source = (ROOT / "pastelabel" / "ui" / "settings_dialog.py").read_text(encoding="utf-8")

    font_size_position = source.index('opt_layout.addLayout(label_font_size_row)')
    label_position = source.index('opt_layout.addLayout(label_position_row)')
    handle_size_position = source.index('opt_layout.addLayout(handle_size_row)')
    border_width_position = source.index('opt_layout.addLayout(box_border_width_row)')
    assert font_size_position < label_position < handle_size_position < border_width_position


def test_label_color_dialog_reuses_non_native_themed_qt_text_translation():
    source = (ROOT / "pastelabel" / "ui" / "dialog_helpers.py").read_text(encoding="utf-8")

    assert 'class ThemedColorDialog(QColorDialog):' in source
    assert 'self.setOption(QColorDialog.DontUseNativeDialog, True)' in source
    assert "'&Basic colors': '基本颜色：'" in source
    assert 'sync_titlebar(self)' in source


def test_crosshair_color_dialog_localizes_its_builtin_labels_and_buttons():
    source = (ROOT / "pastelabel" / "ui" / "dialog_helpers.py").read_text(encoding="utf-8")

    assert 'def showEvent(self, event):' in source
    assert "'&Basic colors': '基本颜色：'" in source
    assert "'&Custom colors': '自定义颜色：'" in source
    assert "'&Pick Screen Color': '拾取屏幕颜色'" in source
    assert "'&Add to Custom Colors': '添加到自定义颜色'" in source
    assert 'widget.setText(i18n.t(translations[text]))' in source


def test_settings_dialog_exposes_crosshair_alpha_control():
    source = (ROOT / "pastelabel" / "ui" / "settings_dialog.py").read_text(encoding="utf-8")

    assert 'self.crosshair_alpha_spin = QSpinBox()' in source
    assert 'self.crosshair_alpha_spin.setRange(0, 255)' in source
    assert 'tr("十字线透明度")' in source


def test_main_window_clamps_crosshair_width_to_decimal_range():
    source = (ROOT / "pastelabel" / "ui" / "main_window.py").read_text(encoding="utf-8")

    assert "CROSSHAIR_CONFIG['width'] = max(0.5, min(3.0, float(settings.get('crosshair_width', CROSSHAIR_CONFIG['width']))))" in source


def test_theme_styles_qdouble_spinbox_like_other_numeric_inputs():
    source = (ROOT / "pastelabel" / "ui" / "theme.py").read_text(encoding="utf-8")

    assert 'QDoubleSpinBox {' in source
    assert 'QDoubleSpinBox:hover {' in source
    assert 'QDoubleSpinBox:focus {' in source


def test_theme_styles_do_not_include_unsupported_box_shadow_property():
    source = (ROOT / "pastelabel" / "ui" / "theme.py").read_text(encoding="utf-8")

    assert 'box-shadow:' not in source


def test_theme_defines_global_translucent_scrollbars_for_both_orientations():
    source = (ROOT / "pastelabel" / "ui" / "theme.py").read_text(encoding="utf-8")

    assert 'QScrollBar:vertical {' in source
    assert 'QScrollBar:horizontal {' in source
    assert source.count('background: transparent;') >= 4
    assert 'width: 10px;' in source
    assert 'height: 10px;' in source
    assert 'border-radius: 5px;' in source
    assert 'rgba(128, 128, 128, 150)' in source
    assert 'rgba(96, 96, 96, 220)' in source
    assert 'QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {' in source
    assert 'QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {' in source
    assert 'height: 0px;' in source
    assert 'width: 0px;' in source
    assert 'QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {' in source
    assert 'QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {' in source


def test_options_button_keeps_qmenu_layout():
    source = (ROOT / "pastelabel" / "ui" / "ui_builder.py").read_text(encoding="utf-8")

    assert 'class HoverKeepMenu(QMenu):' in source
    assert 'self.options_menu = HoverKeepMenu()' in source
    assert 'self.options_btn.setMenu(self.options_menu)' in source
    assert 'if action == self.actions()[0]:' in source
    assert 'action.triggered.emit(False)' in source


def test_cache_popup_keeps_line_edit_open_while_editing():
    source = (ROOT / "pastelabel" / "ui" / "ui_builder.py").read_text(encoding="utf-8")

    assert 'focus_widget = QApplication.focusWidget()' in source
    assert 'isinstance(focus_widget, QLineEdit)' in source


def test_option_menu_special_actions_sync_checked_state_from_runtime_flags():
    source = (ROOT / "pastelabel" / "ui" / "ui_builder.py").read_text(encoding="utf-8")

    assert "self.canvas_copy_action.setChecked(self._canvas_image_copy_enabled)" in source
    assert "self.magnifier_action.setChecked(self._magnifier_enabled)" in source


def test_options_menu_separates_prefix_and_special_toggles_into_third_group():
    source = (ROOT / "pastelabel" / "ui" / "ui_builder.py").read_text(encoding="utf-8")

    assert 'self.options_menu.addSeparator()' in source
    assert '(tr("显示贴图名"), "toggle_paste_names", self.show_paste_names_checkbox)' in source
    assert 'prefix_action = self.options_menu.addAction(tr("添加文件名前缀"))' in source
    assert 'self.options_menu.addSeparator()' in source


def test_cache_slot_name_input_explicitly_enables_input_method():
    source = (ROOT / "pastelabel" / "ui" / "ui_builder.py").read_text(encoding="utf-8")

    assert 'slot_name_input.setAttribute(Qt.WA_InputMethodEnabled, True)' in source


def test_cache_popup_uses_qmenu_via_setmenu():
    source = (ROOT / "pastelabel" / "ui" / "ui_builder.py").read_text(encoding="utf-8")

    cache_popup_block = source.split('def _rebuild_label_cache_menu(self):', 1)[1].split('def _handle_cache_slot_row_click', 1)[0]
    assert 'HoverKeepMenu' in cache_popup_block
    assert 'QWidgetAction' in cache_popup_block
    assert 'setMenu' in cache_popup_block

    create_block = source.split('def _create_options_menu', 1)[1].split('layout.addSpacing', 1)[0]
    assert 'cache_btn.clicked.connect' not in create_block


def test_draw_box_menu_item_does_not_use_manual_left_padding_hacks():
    ui_source = (ROOT / "pastelabel" / "ui" / "ui_builder.py").read_text(encoding="utf-8")
    main_source = (ROOT / "pastelabel" / "ui" / "main_window.py").read_text(encoding="utf-8")

    assert 'self._draw_box_action = self.options_menu.addAction(f"{tr(\'绘制BOX\')}\\t{sc_w}")' in ui_source
    assert 'self._draw_box_action.setCheckable(True)' in ui_source
    assert 'self._draw_box_action.setChecked(False)' in ui_source
    assert 'self._draw_box_action.triggered.connect(self._trigger_draw_box_menu_action)' in ui_source
    assert '"  " + tr("绘制BOX")' not in ui_source
    assert 'f"  {tr(\'绘制BOX\')}\\t{sc}"' not in main_source
    assert 'self._draw_box_action.setText(f"{tr(\'绘制BOX\')}\\t{sc}")' in main_source


def test_draw_box_action_stays_in_same_menu_section_as_display_toggles():
    source = (ROOT / "pastelabel" / "ui" / "ui_builder.py").read_text(encoding="utf-8")

    draw_box_pos = source.index('self._draw_box_action = self.options_menu.addAction(f"{tr(\'绘制BOX\')}\\t{sc_w}")')
    items_pos = source.index('items = [')
    first_separator_after_items = source.index('self.options_menu.addSeparator()', items_pos)
    assert draw_box_pos < items_pos < first_separator_after_items


def test_cache_slot_name_width_is_limited_to_six_cjk_chars():
    source = (ROOT / "pastelabel" / "ui" / "ui_builder.py").read_text(encoding="utf-8")

    assert 'slot_name_input.setFixedWidth(slot_name_input.fontMetrics().horizontalAdvance("测" * 9) + 24)' in source


def test_toolbar_places_options_before_memory_and_cache_has_tooltip():
    source = (ROOT / "pastelabel" / "ui" / "ui_builder.py").read_text(encoding="utf-8")
    i18n_source = (ROOT / "pastelabel" / "ui" / "i18n.py").read_text(encoding="utf-8")

    options_pos = source.index('self.options_btn = QPushButton(tr("选项"))')
    memory_pos = source.index('self.memory_btn = QPushButton(tr("记忆"))')
    assert options_pos < memory_pos
    assert 'self.cache_btn.setToolTip(tr("复制缓存管理"))' in source
    assert '"复制缓存管理": "复制缓存管理"' in i18n_source
    assert '"复制缓存管理": "Copy Cache Manager"' in i18n_source
