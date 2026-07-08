"""
Theme module - manages dark/light theme switching
"""
from enum import Enum


class ThemeMode(Enum):
    LIGHT = "light"
    DARK = "dark"


LIGHT_THEME = {
    "name": "light",
    "window_bg": "#F5F5F5",
    "widget_bg": "#FFFFFF",
    "panel_bg": "#FAFAFA",
            "canvas_bg": "#FFFFFF",
    "border_color": "#E0E0E0",
    "border_hover": "#BBDEFB",
    "text_primary": "#212121",
    "text_secondary": "#757575",
    "text_disabled": "#BDBDBD",
    "accent": "#2196F3",
    "accent_hover": "#1976D2",
    "accent_light": "#E3F2FD",
    "success": "#4CAF50",
    "success_light": "#E8F5E9",
    "warning": "#FF9800",
    "warning_light": "#FFF3E0",
    "danger": "#F44336",
    "danger_light": "#FFEBEE",
    "list_hover": "#F5F5F5",
    "list_selected_bg": "#E3F2FD",
    "list_selected_text": "#1976D2",
    "list_border": "#F0F0F0",
    "toolbar_bg": "#FFFFFF",
    "statusbar_bg": "#FAFAFA",
    "scrollbar_bg": "#F0F0F0",
    "scrollbar_handle": "#BDBDBD",
    "scrollbar_handle_hover": "#9E9E9E",
    "groupbox_bg": "#FFFFFF",
    "groupbox_border": "#E0E0E0",
    "tooltip_bg": "#616161",
    "tooltip_text": "#FFFFFF",
    "surface_secondary": "#F0F0F0",
}

DARK_THEME = {
    "name": "dark",
    "window_bg": "#1E1E1E",
    "widget_bg": "#2D2D2D",
    "panel_bg": "#252525",
    "canvas_bg": "#2D2D2D",
    "border_color": "#3E3E3E",
    "border_hover": "#505050",
    "text_primary": "#E0E0E0",
    "text_secondary": "#9E9E9E",
    "text_disabled": "#616161",
    "accent": "#42A5F5",
    "accent_hover": "#1E88E5",
    "accent_light": "#1A2332",
    "success": "#66BB6A",
    "success_light": "#1A2E1A",
    "warning": "#FFA726",
    "warning_light": "#2E2218",
    "danger": "#EF5350",
    "danger_light": "#2E1A1A",
    "list_hover": "#333333",
    "list_selected_bg": "#1A2332",
    "list_selected_text": "#42A5F5",
    "list_border": "#3E3E3E",
    "toolbar_bg": "#252525",
    "statusbar_bg": "#1E1E1E",
    "scrollbar_bg": "#2D2D2D",
    "scrollbar_handle": "#555555",
    "scrollbar_handle_hover": "#777777",
    "groupbox_bg": "#2D2D2D",
    "groupbox_border": "#3E3E3E",
    "tooltip_bg": "#424242",
    "tooltip_text": "#E0E0E0",
    "surface_secondary": "#383838",
}


class ThemeManager:
    _instance = None
    _current_theme = LIGHT_THEME
    _mode = ThemeMode.LIGHT

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_theme(cls):
        return cls._current_theme

    @classmethod
    def get_theme_colors(cls):
        return cls._current_theme

    @classmethod
    def get_mode(cls):
        return cls._mode

    @classmethod
    def set_mode(cls, mode):
        cls._mode = mode
        if mode == ThemeMode.DARK:
            cls._current_theme = DARK_THEME
        else:
            cls._current_theme = LIGHT_THEME

    @classmethod
    def toggle(cls):
        if cls._mode == ThemeMode.LIGHT:
            cls.set_mode(ThemeMode.DARK)
        else:
            cls.set_mode(ThemeMode.LIGHT)
        return cls._current_theme

    @classmethod
    def get_stylesheet(cls):
        t = cls._current_theme
        return f"""
            QMainWindow {{
                background-color: {t['window_bg']};
            }}
            QWidget {{
                background-color: {t['widget_bg']};
                color: {t['text_primary']};
                font-family: 'JetBrains Mono', 'Microsoft YaHei', 'Segoe UI', sans-serif;
                font-size: 12px;
            }}
            QSplitter {{
                background-color: {t['widget_bg']};
            }}
            QSplitter::handle {{
                background-color: {t['border_color']};
                width: 2px;
            }}
            QScrollBar:vertical {{
                background: {t['scrollbar_bg']};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {t['scrollbar_handle']};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {t['scrollbar_handle_hover']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background: {t['scrollbar_bg']};
                height: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:horizontal {{
                background: {t['scrollbar_handle']};
                border-radius: 4px;
                min-width: 20px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {t['scrollbar_handle_hover']};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            QStatusBar {{
                background-color: {t['statusbar_bg']};
                color: {t['text_secondary']};
                border-top: 1px solid {t['border_color']};
                font-family: 'JetBrains Mono', 'Microsoft YaHei', 'Segoe UI', sans-serif;
            }}
            QLabel {{
                background-color: transparent;
                color: {t['text_primary']};
            }}
            QLabel#statusLabel {{
                color: {t['text_secondary']};
            }}
            QLabel#shortcutStatusLabel {{
                padding: 2px 8px;
            }}
            QListWidget {{
                border: 1px solid {t['border_color']};
                border-radius: 8px;
                background-color: {t['widget_bg']};
                color: {t['text_primary']};
                outline: none;
                padding: 2px;
                alternate-background-color: {t['widget_bg']};
            }}
            QListWidget:disabled {{
                background-color: {t['scrollbar_bg']};
                color: {t['text_disabled']};
            }}
            QListWidget::item {{
                padding: 4px;
                border-bottom: 1px solid {t['list_border']};
                background-color: {t['widget_bg']};
                color: {t['text_primary']};
            }}
            QListWidget::item:hover {{
                background-color: {t['list_hover']};
            }}
            QListWidget::item:selected {{
                background-color: {t['list_selected_bg']};
                color: {t['list_selected_text']};
            }}
            QLineEdit {{
                border: 1px solid {t['border_color']};
                border-radius: 6px;
                padding: 3px 6px;
                font-size: 12px;
                background-color: {t['widget_bg']};
                color: {t['text_primary']};
                selection-background-color: {t['accent']};
                font-family: 'JetBrains Mono', 'Microsoft YaHei', 'Segoe UI', sans-serif;
            }}
            QLineEdit:hover {{
                border-color: {t['border_hover']};
            }}
            QLineEdit:focus {{
                border-color: {t['accent']};
            }}
            QSpinBox {{
                border: 1px solid {t['border_color']};
                border-radius: 6px;
                padding: 3px 6px;
                font-size: 12px;
                background-color: {t['widget_bg']};
                color: {t['text_primary']};
                font-family: 'JetBrains Mono', 'Microsoft YaHei', 'Segoe UI', sans-serif;
            }}
            QSpinBox:hover {{
                border-color: {t['border_hover']};
            }}
            QSpinBox:focus {{
                border-color: {t['accent']};
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 16px;
                border: none;
                background-color: transparent;
            }}
            QCheckBox {{
                spacing: 6px;
                font-size: 12px;
                color: {t['text_primary']};
                background-color: transparent;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border: 2px solid {t['border_color']};
                border-radius: 4px;
                background-color: {t['widget_bg']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {t['accent']};
                border-color: {t['accent']};
            }}
            QCheckBox::indicator:hover {{
                border-color: {t['accent']};
            }}
            QPushButton {{
                background-color: {t['accent_light']};
                border: none;
                border-radius: 8px;
                padding: 3px 8px;
                color: {t['accent']};
                font-family: 'JetBrains Mono', 'Microsoft YaHei', 'Segoe UI', sans-serif;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {t['accent']};
                color: {t['widget_bg']};
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
            }}
            QPushButton:pressed {{
                background-color: {t['accent_hover']};
                color: {t['widget_bg']};
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
            }}
            QPushButton:disabled {{
                background-color: {t['scrollbar_bg']};
                color: {t['text_disabled']};
            }}
            QGroupBox {{
                border: 1px solid {t['groupbox_border']};
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 12px;
                font-weight: bold;
                color: {t['text_primary']};
                background-color: transparent;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: {t['text_primary']};
            }}
            QToolTip {{
                background-color: {t['tooltip_bg']};
                color: {t['tooltip_text']};
                border: none;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 11px;
            }}
            QFrame {{
                background-color: transparent;
            }}
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollArea#canvasScroll {{
                border: 1px solid {t['border_color']};
                border-radius: 6px;
                background-color: {t['widget_bg']};
            }}
            QComboBox {{
                border: 1px solid {t['border_color']};
                border-radius: 6px;
                padding: 3px 6px;
                background-color: {t['widget_bg']};
                color: {t['text_primary']};
                font-family: 'JetBrains Mono', 'Microsoft YaHei', 'Segoe UI', sans-serif;
            }}
            QComboBox:hover {{
                border-color: {t['border_hover']};
            }}
            QComboBox::drop-down {{
                border: none;
                background-color: transparent;
            }}
            QComboBox QAbstractItemView {{
                background-color: {t['widget_bg']};
                color: {t['text_primary']};
                border: 1px solid {t['border_color']};
                selection-background-color: {t['list_selected_bg']};
                selection-color: {t['list_selected_text']};
            }}

            /* objectName specific styles */
            QPushButton#iconBtn {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 2px;
            }}
            QPushButton#iconBtn:hover {{
                background-color: {t['accent_light']};
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
            }}
            QPushButton#iconBtn:pressed {{
                background-color: {t['accent']};
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
            }}
            QPushButton#navBtn {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                font-size: 10px;
                color: {t['text_secondary']};
            }}
            QPushButton#navBtn:hover {{
                background-color: {t['accent_light']};
                color: {t['accent']};
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
            }}
            QPushButton#navBtn:pressed {{
                background-color: {t['accent']};
                color: {t['widget_bg']};
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
            }}
            QPushButton#bgBtn {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 2px;
            }}
            QPushButton#bgBtn:hover {{
                background-color: #E3F2FD;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
            }}
            QPushButton#bgBtn:pressed {{
                background-color: #BBDEFB;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
            }}
            QPushButton#pasteBtn {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 2px;
            }}
            QPushButton#pasteBtn:hover {{
                background-color: #E8F5E9;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
            }}
            QPushButton#pasteBtn:pressed {{
                background-color: #C8E6C9;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
            }}
            QPushButton#labelBtn {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 2px;
            }}
            QPushButton#labelBtn:hover {{
                background-color: #FFF3E0;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
            }}
            QPushButton#labelBtn:pressed {{
                background-color: #FFE0B2;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
            }}
            QPushButton#themeBtn {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 2px;
                font-size: 16px;
            }}
            QPushButton#themeBtn:hover {{
                background-color: {t['accent_light']};
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
            }}

            /* 设置按钮 */
            QPushButton#settingsBtn {{
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 4px;
                font-size: 16px;
            }}
            QPushButton#settingsBtn:hover {{
                background-color: {t['accent_light']};
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
            }}

            /* 选项按钮 */
            QPushButton#optionsBtn {{
                background-color: {t['accent_light']};
                border: none;
                border-radius: 6px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: bold;
                color: {t['accent']};
            }}
            QPushButton#optionsBtn:hover {{
                background-color: {t['accent']};
                color: {t['widget_bg']};
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
            }}
            QPushButton#optionsBtn::menu-indicator {{
                width: 0px;
                height: 0px;
            }}
            QMenu#optionsMenu {{
                background-color: {t['widget_bg']};
                border: 1px solid {t['border_color']};
                padding: 4px;
            }}
            QMenu#optionsMenu::item {{
                padding: 6px 16px;
            }}
            QMenu#optionsMenu::item:selected {{
                background-color: {t['accent_light']};
                color: {t['accent']};
            }}
            QPushButton#langBtn {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 2px;
                font-size: 11px;
                font-weight: bold;
                color: {t['text_secondary']};
            }}
            QPushButton#langBtn:hover {{
                background-color: {t['accent_light']};
                color: {t['accent']};
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
            }}
            QPushButton#drawBoxBtn {{
                background-color: {t['warning_light']};
                border: none;
                border-radius: 10px;
                padding: 3px 8px;
                font-size: 12px;
                font-weight: 600;
                color: {t['warning']};
            }}
            QPushButton#drawBoxBtn:hover {{
                background-color: {t['warning']};
                color: {t['widget_bg']};
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
            }}
            QPushButton#drawBoxBtn:pressed {{
                background-color: {t['warning']};
                color: {t['widget_bg']};
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
            }}
            QPushButton#accentBtn {{
                background-color: {t['accent_light']};
                border: none;
                border-radius: 10px;
                padding: 3px 8px;
                font-size: 12px;
                font-weight: bold;
                color: {t['accent']};
            }}
            QPushButton#accentBtn:hover {{
                background-color: {t['accent']};
                color: {t['widget_bg']};
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
            }}
            QPushButton#accentBtn:pressed {{
                background-color: {t['accent_hover']};
                color: {t['widget_bg']};
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
            }}
            QPushButton#warningBtn {{
                background-color: {t['warning_light']};
                border: none;
                border-radius: 10px;
                padding: 3px 8px;
                font-size: 12px;
                font-weight: bold;
                color: {t['warning']};
            }}
            QPushButton#warningBtn:hover {{
                background-color: {t['warning']};
                color: {t['widget_bg']};
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
            }}
            QPushButton#warningBtn:pressed {{
                background-color: {t['warning']};
                color: {t['widget_bg']};
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
            }}
            QPushButton#viewToggleBtn {{
                background-color: {t['warning_light']};
                border: none;
                border-radius: 10px;
                padding: 3px 8px;
                font-size: 12px;
                font-weight: bold;
                color: {t['warning']};
            }}
            QPushButton#viewToggleBtn:hover {{
                background-color: {t['warning']};
                color: {t['widget_bg']};
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
            }}
            QPushButton#successBtn {{
                background-color: {t['success_light']};
                border: none;
                border-radius: 10px;
                padding: 3px 8px;
                font-size: 12px;
                font-weight: bold;
                color: {t['success']};
            }}
            QPushButton#successBtn:hover {{
                background-color: {t['success']};
                color: {t['widget_bg']};
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
            }}
            QPushButton#successBtn:pressed {{
                background-color: {t['success']};
                color: {t['widget_bg']};
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
            }}
            QPushButton#dangerBtn {{
                background-color: {t['danger_light']};
                border: none;
                border-radius: 10px;
                padding: 3px 8px;
                font-size: 12px;
                font-weight: bold;
                color: {t['danger']};
            }}
            QPushButton#dangerBtn:hover {{
                background-color: {t['danger']};
                color: {t['widget_bg']};
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
            }}
            QPushButton#dangerBtn:pressed {{
                background-color: {t['danger']};
                color: {t['widget_bg']};
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
            }}
            QFrame#toolbarSep {{
                background-color: transparent;
                border-left: 1px solid {t['border_color']};
                max-width: 1px;
                min-width: 1px;
                margin: 2px 4px;
            }}
            QLabel#fileCountLabel {{
                color: {t['text_secondary']};
                font-size: 11px;
                background-color: transparent;
            }}
            QLineEdit#prefixInput[placeholder="true"] {{
                color: {t['text_disabled']};
            }}
            QLineEdit#prefixInput[placeholder="false"] {{
                color: {t['text_primary']};
            }}
        """

    @classmethod
    def get_list_style(cls):
        t = cls._current_theme
        return f"""
            QListWidget {{
                border: 1px solid {t['border_color']};
                border-radius: 8px;
                background-color: {t['widget_bg']};
                color: {t['text_primary']};
            }}
            QListWidget::item {{
                padding: 4px;
                border-bottom: 1px solid {t['list_border']};
            }}
            QListWidget::item:hover {{
                background-color: {t['list_hover']};
            }}
            QListWidget::item:selected {{
                background-color: {t['list_selected_bg']};
                color: {t['list_selected_text']};
            }}
        """

    @classmethod
    def get_button_style(cls, bg_color=None, text_color=None, variant="default"):
        t = cls._current_theme
        if variant == "icon":
            return f"""
                QPushButton {{
                    background-color: transparent;
                    border: 1px solid transparent;
                    border-radius: 4px;
                    padding: 2px;
                }}
                QPushButton:hover {{
                    background-color: {t['accent_light']};
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
                }}
                QPushButton:pressed {{
                    background-color: {t['accent']};
                    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
                }}
            """
        bg = bg_color or t['accent_light']
        fg = text_color or t['accent']
        return f"""
            QPushButton {{
                background-color: {bg};
                border: none;
                border-radius: 10px;
                padding: 3px 8px;
                font-size: 12px;
                font-weight: bold;
                color: {fg};
            }}
            QPushButton:hover {{
                background-color: {fg};
                color: {t['widget_bg']};
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
            }}
            QPushButton:pressed {{
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
            }}
        """

    @classmethod
    def get_dialog_button_style(cls):
        """小窗按钮复用设置弹窗的普通按钮圆角。"""
        return cls.get_button_style()

    @classmethod
    def get_action_button_style(cls, bg_color, text_color):
        t = cls._current_theme
        return f"""
            QPushButton {{
                background-color: {bg_color};
                border: none;
                border-radius: 10px;
                padding: 3px 8px;
                font-size: 12px;
                font-weight: bold;
                color: {text_color};
            }}
            QPushButton:hover {{
                background-color: {text_color};
                color: {t['widget_bg']};
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
            }}
            QPushButton:pressed {{
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
            }}
        """

    @classmethod
    def get_draw_button_style(cls):
        t = cls._current_theme
        return f"""
            QPushButton {{
                background-color: {t['warning_light']};
                border: none;
                border-radius: 10px;
                padding: 3px 8px;
                font-size: 12px;
                font-weight: 600;
                color: {t['warning']};
            }}
            QPushButton:hover {{
                background-color: {t['warning']};
                color: {t['widget_bg']};
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
            }}
            QPushButton:pressed {{
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
            }}
        """

    @classmethod
    def get_checkbox_style(cls, checked_color=None):
        t = cls._current_theme
        c = checked_color or t['accent']
        return f"""
            QCheckBox {{
                spacing: 6px;
                font-size: 12px;
                color: {t['text_primary']};
                background-color: transparent;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border: 2px solid {t['border_color']};
                border-radius: 4px;
                background-color: {t['widget_bg']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {c};
                border-color: {c};
            }}
        """

    @classmethod
    def get_spinbox_style(cls):
        t = cls._current_theme
        return f"""
            QSpinBox {{
                border: 1px solid {t['border_color']};
                border-radius: 6px;
                padding: 3px 6px;
                font-size: 12px;
                background-color: {t['widget_bg']};
                color: {t['text_primary']};
            }}
        """

    @classmethod
    def get_input_style(cls):
        t = cls._current_theme
        return f"""
            QLineEdit {{
                border: 1px solid {t['border_color']};
                border-radius: 6px;
                padding: 3px 6px;
                font-size: 12px;
                background-color: {t['widget_bg']};
                color: {t['text_primary']};
            }}
        """

    @classmethod
    def get_prefix_input_focus_style(cls, text_color=None):
        t = cls._current_theme
        fg = text_color or t['text_disabled']
        return f"""
            QLineEdit {{
                border: 1px solid {t['border_color']};
                border-radius: 6px;
                padding: 3px 6px;
                font-size: 12px;
                background-color: {t['widget_bg']};
                color: {fg};
            }}
        """
