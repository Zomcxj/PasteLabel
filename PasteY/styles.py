"""
样式模块 - 定义 UI 样式表
将样式从主窗口类中分离，便于统一管理和修改
"""


def get_list_style():
    """获取列表样式"""
    return """
        QListWidget {
            border: 1px solid #E0E0E0;
            border-radius: 8px;
            background-color: white;
        }
        QListWidget::item {
            padding: 4px;
            border-bottom: 1px solid #F0F0F0;
        }
        QListWidget::item:hover {
            background-color: #F5F5F5;
        }
        QListWidget::item:selected {
            background-color: #E3F2FD;
            color: #1976D2;
        }
    """


def get_action_button_style(bg_color, text_color):
    """获取操作按钮样式"""
    return f"""
        QPushButton {{
            background-color: {bg_color};
            border: 1px solid {text_color};
            border-radius: 12px;
            padding: 6px 12px;
            font-size: 12px;
            font-weight: 500;
            color: {text_color};
        }}
        QPushButton:hover {{
            background-color: {_lighten_color(bg_color)};
        }}
        QPushButton:pressed {{
            background-color: {_darken_color(bg_color)};
        }}
    """


def get_spinbox_style():
    """获取数字输入框样式"""
    return """
        QSpinBox {
            border: 1px solid #E0E0E0;
            border-radius: 8px;
            padding: 4px 8px;
            font-size: 12px;
            background-color: white;
        }
        QSpinBox:hover {
            border-color: #BBDEFB;
        }
    """


def get_checkbox_style(checked_color):
    """获取复选框样式"""
    return f"""
        QCheckBox {{
            spacing: 8px;
            font-size: 12px;
        }}
        QCheckBox::indicator {{
            width: 12px;
            height: 12px;
            border: 2px solid #BDBDBD;
            border-radius: 4px;
            background-color: white;
        }}
        QCheckBox::indicator:checked {{
            background-color: {checked_color};
            border-color: {checked_color};
        }}
    """


def get_input_style():
    """获取输入框样式"""
    return """
        QLineEdit {
            border: 1px solid #E0E0E0;
            border-radius: 8px;
            padding: 4px 8px;
            font-size: 12px;
            background-color: white;
        }
        QLineEdit:hover {
            border-color: #BBDEFB;
        }
    """


def get_draw_button_style():
    """获取绘制按钮样式"""
    return """
        QPushButton {
            background-color: #FFF3E0;
            border: 1px solid #FFCC80;
            border-radius: 12px;
            padding: 6px 12px;
            font-size: 12px;
            font-weight: 500;
            color: #E65100;
        }
        QPushButton:hover {
            background-color: #FFE0B2;
        }
        QPushButton:pressed {
            background-color: #FFCC80;
        }
    """


def _lighten_color(color_str):
    """加亮颜色（简化实现）"""
    return "#F5F5F5"


def _darken_color(color_str):
    """变暗颜色（简化实现）"""
    return "#CCCCCC"
