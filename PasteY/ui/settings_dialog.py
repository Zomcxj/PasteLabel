"""
设置对话框 - 快捷键自定义
"""
import json
import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QScrollArea, QWidget, QCheckBox
)
from PyQt5.QtCore import Qt, QTimer, QEvent

from ..core.config import SHORTCUT_CONFIG
from .theme import ThemeManager, ThemeMode
from .dwm import set_titlebar_dark
from ..core import config_manager
from . import i18n


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        from . import i18n
        tr = i18n.t
        self._editor = parent
        self.setWindowTitle(tr("设置"))
        self.setMinimumWidth(400)
        self.setMinimumHeight(500)
        self.setObjectName("settingsDialog")

        self.shortcut_inputs = {}
        self._init_ui()
        self._load_shortcuts()
        self._load_options()
        self.installEventFilter(self)

    def showEvent(self, event):
        """窗口显示后禁用主窗口快捷键，避免冲突"""
        super().showEvent(event)
        QTimer.singleShot(30, self._sync_titlebar)
        if self._editor and hasattr(self._editor, '_shortcuts'):
            for sc in self._editor._shortcuts:
                sc.setEnabled(False)

    def hideEvent(self, event):
        """窗口关闭后恢复主窗口快捷键"""
        super().hideEvent(event)
        if self._editor and hasattr(self._editor, '_shortcuts'):
            for sc in self._editor._shortcuts:
                sc.setEnabled(True)

    def _sync_titlebar(self):
        """同步标题栏颜色"""
        is_dark = ThemeManager.get_mode().value == "dark"
        hwnd = int(self.winId())
        set_titlebar_dark(hwnd, is_dark)

    def _init_ui(self):
        from . import i18n
        tr = i18n.t
        layout = QVBoxLayout(self)

        group = QGroupBox(tr("快捷键设置"))
        group_layout = QVBoxLayout(group)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        shortcut_names = {
            'undo': tr("撤销"),
            'redo': tr("重做"),
            'save': tr("保存"),
            'save_all': tr("全部保存"),
            'toggle_grid': tr("显示网格"),
            'toggle_labels': tr("显示BOX"),
            'toggle_label_names': tr("显示Label"),
            'toggle_auto_save': tr("自动保存"),
            'toggle_paste_names': tr("显示贴图名"),
            'draw_box': tr("绘制检测框"),
            'quit_draw': tr("退出绘制"),
            'next_image': tr("下一张"),
            'prev_image': tr("上一张"),
            'delete_selected': tr("删除选中"),
            'fit_view': tr("适应视图"),
            'zoom_in': tr("放大"),
            'zoom_out': tr("缩小"),
        }

        for key, name in shortcut_names.items():
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{name}:"), 2)

            input_field = QLineEdit()
            input_field.setObjectName("shortcutInput")
            input_field.setText(SHORTCUT_CONFIG.get(key, ''))
            input_field.setReadOnly(True)
            input_field.setMinimumWidth(150)
            input_field.installEventFilter(self)
            input_field.keyPressEvent = lambda event, field=input_field: self._capture_key(event, field)
            self.shortcut_inputs[key] = input_field
            row.addWidget(input_field, 1)

            reset_btn = QPushButton(tr("重置"))
            reset_btn.setObjectName("resetBtn")
            reset_btn.setFixedWidth(70)
            reset_btn.clicked.connect(lambda _, k=key, f=input_field: self._reset_shortcut(k, f))
            row.addWidget(reset_btn)

            scroll_layout.addLayout(row)

        scroll.setWidget(scroll_content)
        group_layout.addWidget(scroll)
        layout.addWidget(group)

        opt_group = QGroupBox(tr("选项设置"))
        opt_layout = QVBoxLayout(opt_group)
        opt_layout.setContentsMargins(9, 14, 9, 9)

        prefix_row = QHBoxLayout()
        prefix_label = QLabel(tr("添加文件名前缀") + ":")
        prefix_row.addWidget(prefix_label, 2)

        self.prefix_input = QLineEdit()
        self.prefix_input.setObjectName("shortcutInput")
        self.prefix_input.setMinimumWidth(220)
        prefix_row.addWidget(self.prefix_input)
        prefix_row.addStretch()
        opt_layout.addLayout(prefix_row)

        layout.addWidget(opt_group)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton(tr("保存"))
        save_btn.setObjectName("successBtn")
        save_btn.clicked.connect(self._save_shortcuts)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton(tr("取消"))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def eventFilter(self, obj, event):
        """拦截快捷键输入框的按键事件（含Ctrl+组合键）"""
        if event.type() == QEvent.KeyPress:
            focused = self.focusWidget()
            if focused is not None:
                for key, field in self.shortcut_inputs.items():
                    if focused is field or obj is field:
                        self._capture_key(event, field)
                        return True
        return super().eventFilter(obj, event)

    def _capture_key(self, event, field):
        """捕获按键"""
        key = event.key()
        modifiers = event.modifiers()

        key_name = ""
        if modifiers & Qt.ControlModifier:
            key_name += "Ctrl+"
        if modifiers & Qt.AltModifier:
            key_name += "Alt+"
        if modifiers & Qt.ShiftModifier:
            key_name += "Shift+"

        key_map = {
            Qt.Key_A: 'A', Qt.Key_B: 'B', Qt.Key_C: 'C', Qt.Key_D: 'D',
            Qt.Key_E: 'E', Qt.Key_F: 'F', Qt.Key_G: 'G', Qt.Key_H: 'H',
            Qt.Key_I: 'I', Qt.Key_J: 'J', Qt.Key_K: 'K', Qt.Key_L: 'L',
            Qt.Key_M: 'M', Qt.Key_N: 'N', Qt.Key_O: 'O', Qt.Key_P: 'P',
            Qt.Key_Q: 'Q', Qt.Key_R: 'R', Qt.Key_S: 'S', Qt.Key_T: 'T',
            Qt.Key_U: 'U', Qt.Key_V: 'V', Qt.Key_W: 'W', Qt.Key_X: 'X',
            Qt.Key_Y: 'Y', Qt.Key_Z: 'Z',
            Qt.Key_0: '0', Qt.Key_1: '1', Qt.Key_2: '2', Qt.Key_3: '3',
            Qt.Key_4: '4', Qt.Key_5: '5', Qt.Key_6: '6', Qt.Key_7: '7',
            Qt.Key_8: '8', Qt.Key_9: '9',
            Qt.Key_Delete: 'Delete', Qt.Key_Space: 'Space',
            Qt.Key_F1: 'F1', Qt.Key_F2: 'F2', Qt.Key_F3: 'F3', Qt.Key_F4: 'F4',
            Qt.Key_F5: 'F5', Qt.Key_F6: 'F6', Qt.Key_F7: 'F7', Qt.Key_F8: 'F8',
            Qt.Key_F9: 'F9', Qt.Key_F10: 'F10', Qt.Key_F11: 'F11', Qt.Key_F12: 'F12',
        }

        if key in key_map:
            key_name += key_map[key]
            field.setText(key_name)

    def _reset_shortcut(self, key, field):
        """重置单个快捷键"""
        field.setText(SHORTCUT_CONFIG.get(key, ''))

    def _load_shortcuts(self):
        """加载保存的快捷键"""
        shortcuts = config_manager.load_shortcuts()
        for key, field in self.shortcut_inputs.items():
            if key in shortcuts:
                field.setText(shortcuts[key])

    def _load_options(self):
        """加载选项状态"""
        if self._editor:
            self.prefix_input.setText(self._editor.prefix_input.text())

    def _save_shortcuts(self):
        """保存快捷键到文件并立即生效"""
        shortcuts = {}
        for key, field in self.shortcut_inputs.items():
            text = field.text().strip()
            if text:
                shortcuts[key] = text

        if self._editor:
            self._editor.prefix_input.setText(self.prefix_input.text())
            self._editor.shortcut_config = shortcuts
            if hasattr(self._editor, 'update_shortcuts'):
                self._editor.update_shortcuts()
            if hasattr(self._editor, '_refresh_menu_shortcuts'):
                self._editor._refresh_menu_shortcuts()

        config_manager.save_shortcuts(shortcuts)
        self.accept()


def load_shortcuts():
    """加载快捷键配置"""
    return config_manager.load_shortcuts()
