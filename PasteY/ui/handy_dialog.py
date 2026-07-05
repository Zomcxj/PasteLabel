"""巧手记录弹窗。"""
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QLabel
from PyQt5.QtCore import QTimer

from ..core import config_manager
from . import i18n
from .dialog_helpers import center_on_parent, get_text
from .dwm import set_titlebar_dark
from .theme import ThemeManager


class HandyRecordsDialog(QDialog):
    """管理并加载最近的素材路径组合。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._editor = parent
        self.setWindowTitle(i18n.t("巧手记录"))
        self.setMinimumWidth(560)
        self.setMinimumHeight(360)
        self._records = []

        layout = QVBoxLayout(self)
        self.info_label = QLabel(i18n.t("最多保留10组记录"))
        layout.addWidget(self.info_label)

        self.record_list = QListWidget()
        layout.addWidget(self.record_list)

        buttons = QHBoxLayout()
        self.load_btn = QPushButton(i18n.t("加载"))
        self.note_btn = QPushButton(i18n.t("修改备注"))
        self.delete_btn = QPushButton(i18n.t("删除"))
        self.close_btn = QPushButton(i18n.t("关闭"))
        for btn in (self.load_btn, self.note_btn, self.delete_btn, self.close_btn):
            btn.setFixedHeight(24)
            buttons.addWidget(btn)
        layout.addLayout(buttons)

        self.load_btn.clicked.connect(self._load_selected)
        self.note_btn.clicked.connect(self._edit_note)
        self.delete_btn.clicked.connect(self._delete_selected)
        self.close_btn.clicked.connect(self.accept)
        self._refresh()

    def showEvent(self, event):
        super().showEvent(event)
        center_on_parent(self)
        is_dark = ThemeManager.get_mode().value == "dark"
        QTimer.singleShot(30, lambda: set_titlebar_dark(int(self.winId()), is_dark))

    def _refresh(self):
        self._records = config_manager.load_handy_records()
        self.record_list.clear()
        for record in self._records:
            note = record.get('note') or i18n.t("未备注")
            bg = record.get('background_path') or i18n.t("空")
            paste = record.get('paste_path') or i18n.t("空")
            label = record.get('label_path') or i18n.t("空")
            image_index = int(record.get('background_index', 0) or 0) + 1
            self.record_list.addItem(
                f"{note}\n{i18n.t('当前图片')}: {image_index}\n{i18n.t('背景图')}: {bg}\n{i18n.t('贴图')}: {paste}\n{i18n.t('标签文件')}: {label}"
            )

    def _selected_index(self):
        row = self.record_list.currentRow()
        return row if 0 <= row < len(self._records) else -1

    def _load_selected(self):
        idx = self._selected_index()
        if idx >= 0 and self._editor:
            self._editor.load_handy_record(self._records[idx])
            self.accept()

    def _edit_note(self):
        idx = self._selected_index()
        if idx < 0:
            return
        record = self._records[idx].copy()
        note, ok = get_text(self, "修改备注", "请输入备注:", text=record.get('note', ''))
        if ok:
            record['note'] = note.strip()
            config_manager.upsert_handy_record(record)
            self._refresh()
            self.record_list.setCurrentRow(0)

    def _delete_selected(self):
        idx = self._selected_index()
        if idx >= 0:
            config_manager.delete_handy_record(idx)
            self._refresh()
