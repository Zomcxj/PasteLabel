"""
设置对话框 - 快捷键自定义
"""
import json
import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QScrollArea, QWidget, QSpinBox, QStackedWidget,
    QComboBox, QDoubleSpinBox
)
from PyQt5.QtCore import Qt, QEvent

from ..core.config import SHORTCUT_CONFIG
from .theme import ThemeManager
from .dwm import set_titlebar_dark
from .dialog_helpers import center_on_parent
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
        self.setMinimumWidth(507)
        self.setMinimumHeight(500)
        self.setObjectName("settingsDialog")

        self.shortcut_inputs = {}
        self._init_ui()
        self._load_shortcuts()
        self._load_options()
        self.installEventFilter(self)
        if self._editor and hasattr(self._editor, '_shortcuts'):
            for sc in self._editor._shortcuts:
                sc.setEnabled(False)

    def showEvent(self, event):
        """窗口显示后设置标题栏颜色"""
        super().showEvent(event)
        center_on_parent(self)
        self._sync_titlebar()

    def closeEvent(self, event):
        """关闭时恢复主窗口快捷键"""
        super().closeEvent(event)
        if self._editor and hasattr(self._editor, '_shortcuts'):
            for sc in self._editor._shortcuts:
                sc.setEnabled(True)

    def hideEvent(self, event):
        """隐藏时也恢复快捷键"""
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
        layout.setContentsMargins(10, 10, 10, 10)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(10)

        nav_layout = QVBoxLayout()
        nav_layout.setSpacing(8)

        self.shortcut_page_btn = QPushButton(tr("快捷键设置"))
        self.shortcut_page_btn.setCheckable(True)
        self.shortcut_page_btn.setChecked(True)
        self.shortcut_page_btn.setFixedWidth(108)
        self.shortcut_page_btn.setMinimumHeight(38)
        self.shortcut_page_btn.setStyleSheet(ThemeManager.get_dialog_button_style())
        self.shortcut_page_btn.clicked.connect(lambda: self._switch_page(0))
        nav_layout.addWidget(self.shortcut_page_btn)

        self.options_page_btn = QPushButton(tr("参数设置"))
        self.options_page_btn.setCheckable(True)
        self.options_page_btn.setFixedWidth(108)
        self.options_page_btn.setMinimumHeight(38)
        self.options_page_btn.setStyleSheet(ThemeManager.get_dialog_button_style())
        self.options_page_btn.clicked.connect(lambda: self._switch_page(1))
        nav_layout.addWidget(self.options_page_btn)
        nav_layout.addStretch()

        self.stack = QStackedWidget()

        group = QGroupBox(tr("快捷键设置"))
        group_layout = QVBoxLayout(group)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        shortcut_names = {
            'undo': tr("撤销"),
            'redo': tr("重做"),
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
            'remove_image': tr("移除图片"),
            'restore_image': tr("恢复到工作路径"),
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
            reset_btn.setStyleSheet(ThemeManager.get_dialog_button_style())
            reset_btn.clicked.connect(lambda _, k=key, f=input_field: self._reset_shortcut(k, f))
            row.addWidget(reset_btn)

            scroll_layout.addLayout(row)

        scroll.setWidget(scroll_content)
        group_layout.addWidget(scroll)
        self.stack.addWidget(group)

        opt_group = QGroupBox(tr("参数设置"))
        opt_layout = QVBoxLayout(opt_group)
        opt_layout.setContentsMargins(19, 14, 9, 9)

        prefix_row = QHBoxLayout()
        prefix_label = QLabel(tr("添加文件名前缀") + ":")
        prefix_row.addWidget(prefix_label, 2)

        self.prefix_input = QLineEdit()
        self.prefix_input.setObjectName("shortcutInput")
        self.prefix_input.setMinimumWidth(150)
        prefix_row.addWidget(self.prefix_input)
        prefix_row.addStretch()
        opt_layout.addLayout(prefix_row)

        from ..core.config import GRID_CONFIG, DETECTION_BOX_CONFIG, MAGNIFIER_CONFIG
        grid_width_row = QHBoxLayout()
        grid_width_label = QLabel(tr("网格线粗细") + ":")
        grid_width_row.addWidget(grid_width_label, 2)
        self.grid_width_spin = QSpinBox()
        self.grid_width_spin.setRange(1, 10)
        self.grid_width_spin.setValue(GRID_CONFIG.get('line_width', 1))
        self.grid_width_spin.setMinimumWidth(150)
        grid_width_row.addWidget(self.grid_width_spin)
        grid_width_row.addStretch()
        opt_layout.addLayout(grid_width_row)

        grid_alpha_row = QHBoxLayout()
        grid_alpha_label = QLabel(tr("网格线灰度") + ":")
        grid_alpha_row.addWidget(grid_alpha_label, 2)
        self.grid_alpha_spin = QSpinBox()
        self.grid_alpha_spin.setRange(0, 255)
        self.grid_alpha_spin.setValue(GRID_CONFIG.get('alpha', 120))
        self.grid_alpha_spin.setMinimumWidth(150)
        grid_alpha_row.addWidget(self.grid_alpha_spin)
        grid_alpha_row.addStretch()
        opt_layout.addLayout(grid_alpha_row)

        from ..core.config import STATUSBAR_CONFIG
        max_labels_row = QHBoxLayout()
        max_labels_label = QLabel(tr("状态栏类别数") + ":")
        max_labels_row.addWidget(max_labels_label, 2)
        self.max_labels_spin = QSpinBox()
        self.max_labels_spin.setRange(1, 20)
        self.max_labels_spin.setValue(getattr(self._editor, '_max_labels', STATUSBAR_CONFIG.get('max_labels', 3)))
        self.max_labels_spin.setMinimumWidth(150)
        max_labels_row.addWidget(self.max_labels_spin)
        max_labels_row.addStretch()
        opt_layout.addLayout(max_labels_row)

        handle_size_row = QHBoxLayout()
        handle_size_label = QLabel(tr("缩放句柄大小") + ":")
        handle_size_row.addWidget(handle_size_label, 2)
        self.handle_size_spin = QSpinBox()
        self.handle_size_spin.setRange(3, 15)
        self.handle_size_spin.setValue(DETECTION_BOX_CONFIG.get('resize_handle_size', 8))
        self.handle_size_spin.setMinimumWidth(150)
        handle_size_row.addWidget(self.handle_size_spin)
        handle_size_row.addStretch()
        opt_layout.addLayout(handle_size_row)

        label_font_size_row = QHBoxLayout()
        label_font_size_label = QLabel(tr("类别名字号") + ":")
        label_font_size_row.addWidget(label_font_size_label, 2)
        self.label_font_size_spin = QSpinBox()
        self.label_font_size_spin.setRange(5, 15)
        self.label_font_size_spin.setValue(DETECTION_BOX_CONFIG.get('label_font_size', 9))
        self.label_font_size_spin.setMinimumWidth(150)
        label_font_size_row.addWidget(self.label_font_size_spin)
        label_font_size_row.addStretch()
        opt_layout.addLayout(label_font_size_row)

        label_position_row = QHBoxLayout()
        label_position_label = QLabel(tr("类别名位置") + ":")
        label_position_row.addWidget(label_position_label, 2)
        self.label_position_combo = QComboBox()
        self.label_position_combo.setMinimumWidth(150)
        self.label_position_combo.addItem(tr("框外侧"), "outside")
        self.label_position_combo.addItem(tr("框内侧"), "inside")
        label_position = DETECTION_BOX_CONFIG.get('label_position', 'outside')
        index = self.label_position_combo.findData(label_position)
        self.label_position_combo.setCurrentIndex(index if index >= 0 else 0)
        label_position_row.addWidget(self.label_position_combo)
        label_position_row.addStretch()
        opt_layout.addLayout(label_position_row)

        magnifier_zoom_row = QHBoxLayout()
        magnifier_zoom_label = QLabel(tr("放大倍率") + ":")
        magnifier_zoom_row.addWidget(magnifier_zoom_label, 2)
        self.magnifier_zoom_spin = QDoubleSpinBox()
        self.magnifier_zoom_spin.setObjectName("paramSpin")
        self.magnifier_zoom_spin.setRange(0.8, 3.0)
        self.magnifier_zoom_spin.setSingleStep(0.1)
        self.magnifier_zoom_spin.setDecimals(1)
        self.magnifier_zoom_spin.setMinimumWidth(150)
        self.magnifier_zoom_spin.setValue(max(0.8, min(3.0, float(MAGNIFIER_CONFIG.get('zoom', 2.0)))))
        magnifier_zoom_row.addWidget(self.magnifier_zoom_spin)
        magnifier_zoom_row.addStretch()
        opt_layout.addLayout(magnifier_zoom_row)

        opt_layout.addStretch()
        self.stack.addWidget(opt_group)

        content_layout.addLayout(nav_layout, 0)
        content_layout.addWidget(self.stack, 1)

        layout.addLayout(content_layout, 1)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton(tr("保存"))
        save_btn.setObjectName("successBtn")
        save_btn.setStyleSheet(ThemeManager.get_dialog_button_style())
        save_btn.clicked.connect(self._save_shortcuts)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton(tr("取消"))
        cancel_btn.setStyleSheet(ThemeManager.get_dialog_button_style())
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def _switch_page(self, index):
        """切换左侧按钮对应的右侧设置页。"""
        self.stack.setCurrentIndex(index)
        self.shortcut_page_btn.setChecked(index == 0)
        self.options_page_btn.setChecked(index == 1)

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
        from ..core.config import GRID_CONFIG, DETECTION_BOX_CONFIG, MAGNIFIER_CONFIG
        self.grid_width_spin.setValue(GRID_CONFIG.get('line_width', 1))
        self.grid_alpha_spin.setValue(GRID_CONFIG.get('alpha', 120))
        self.handle_size_spin.setValue(max(3, min(15, DETECTION_BOX_CONFIG.get('resize_handle_size', 8))))
        self.label_font_size_spin.setValue(max(5, min(15, DETECTION_BOX_CONFIG.get('label_font_size', 9))))
        label_position = DETECTION_BOX_CONFIG.get('label_position', 'outside')
        index = self.label_position_combo.findData(label_position)
        self.label_position_combo.setCurrentIndex(index if index >= 0 else 0)
        self.magnifier_zoom_spin.setValue(max(0.8, min(3.0, float(MAGNIFIER_CONFIG.get('zoom', 2.0)))))

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

        from ..core.config import GRID_CONFIG, DETECTION_BOX_CONFIG, PASTE_ITEM_CONFIG, MAGNIFIER_CONFIG
        GRID_CONFIG['line_width'] = self.grid_width_spin.value()
        GRID_CONFIG['alpha'] = self.grid_alpha_spin.value()
        handle_size = max(3, min(15, self.handle_size_spin.value()))
        DETECTION_BOX_CONFIG['resize_handle_size'] = handle_size
        PASTE_ITEM_CONFIG['handle_size'] = handle_size
        label_font_size = max(5, min(15, self.label_font_size_spin.value()))
        label_position = self.label_position_combo.currentData() or 'outside'
        if label_position not in ('outside', 'inside'):
            label_position = 'outside'
        DETECTION_BOX_CONFIG['label_font_size'] = label_font_size
        DETECTION_BOX_CONFIG['label_position'] = label_position
        magnifier_zoom = max(0.8, min(3.0, float(self.magnifier_zoom_spin.value())))
        MAGNIFIER_CONFIG['zoom'] = magnifier_zoom

        from ..core import config_manager as cm
        max_labels = self.max_labels_spin.value()
        cm.save_all(
            shortcuts=shortcuts,
            max_labels=max_labels,
            grid_line_width=GRID_CONFIG['line_width'],
            grid_alpha=GRID_CONFIG['alpha'],
            resize_handle_size=handle_size,
            label_font_size=label_font_size,
            label_position=label_position,
            magnifier_zoom=magnifier_zoom,
        )
        if self._editor:
            self._editor._max_labels = max_labels
            if hasattr(self._editor, 'canvas'):
                self._editor.canvas.update()
        self.accept()


def load_shortcuts():
    """加载快捷键配置"""
    return config_manager.load_shortcuts()
