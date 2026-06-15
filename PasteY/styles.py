"""
样式模块 - 定义 UI 样式表
使用主题模块统一管理深色/浅色主题
"""
from .theme import ThemeManager


def get_list_style():
    return ThemeManager.get_list_style()


def get_action_button_style(bg_color, text_color):
    return ThemeManager.get_action_button_style(bg_color, text_color)


def get_spinbox_style():
    return ThemeManager.get_spinbox_style()


def get_checkbox_style(checked_color):
    return ThemeManager.get_checkbox_style(checked_color)


def get_input_style():
    return ThemeManager.get_input_style()


def get_draw_button_style():
    return ThemeManager.get_draw_button_style()


def get_icon_button_style():
    return ThemeManager.get_button_style(variant="icon")


def get_prefix_input_focus_style(text_color="black"):
    return ThemeManager.get_prefix_input_focus_style(text_color)


def _lighten_color(color_str):
    return "#F5F5F5"


def _darken_color(color_str):
    return "#CCCCCC"
