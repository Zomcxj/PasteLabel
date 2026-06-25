"""
对话框模块 - 定义各种对话框
"""
import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QLineEdit, QPushButton
)
from PyQt5.QtCore import Qt

from ..core.utils import extract_label_name
from .theme import ThemeManager


class LabelSelectionDialog(QDialog):
    """标签选择对话框"""

    def __init__(self, parent=None, labels=None):
        super().__init__(parent)
        self.setWindowTitle("选择标签")
        self.setMinimumWidth(400)

        if labels is None:
            labels = []

        layout = QVBoxLayout()

        layout.addWidget(QLabel("现有标签："))
        self.label_list = QListWidget()
        for label in labels:
            pure_label = self._extract_pure_label(label)
            self.label_list.addItem(pure_label)
        self.label_list.setStyleSheet(ThemeManager.get_list_style())
        layout.addWidget(self.label_list)

        layout.addWidget(QLabel("或输入新标签："))
        self.new_label_input = QLineEdit()
        self.new_label_input.setStyleSheet(ThemeManager.get_input_style())
        layout.addWidget(self.new_label_input)

        button_layout = QHBoxLayout()
        self.ok_btn = QPushButton("确定")
        self.ok_btn.setObjectName("successBtn")
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setStyleSheet(ThemeManager.get_button_style())

        button_layout.addStretch()
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

        self.new_label_input.returnPressed.connect(self.accept)
        self.label_list.itemDoubleClicked.connect(self.accept)
    
    @staticmethod
    def _extract_pure_label(label_text):
        """从标签文本中提取纯标签名称"""
        return extract_label_name(label_text)
    
    def get_selected_label(self):
        """获取选中的标签"""
        # 优先返回列表中选中的标签
        selected_items = self.label_list.selectedItems()
        if selected_items:
            return selected_items[0].text()
        # 如果没有选中，返回输入框中的文本
        return self.new_label_input.text().strip()
    
    @staticmethod
    def select_label(parent, labels):
        """静态方法：显示标签选择对话框并返回选中的标签"""
        dialog = LabelSelectionDialog(parent, labels)
        if dialog.exec_():
            return dialog.get_selected_label()
        return None


class ProgressDialogFactory:
    """进度条对话框工厂类"""

    @staticmethod
    def create_progress_dialog(parent, title, label_text, maximum):
        from PyQt5.QtWidgets import QProgressDialog
        t = ThemeManager.get_theme()

        progress_dialog = QProgressDialog(label_text, "取消", 0, maximum, parent)
        progress_dialog.setWindowTitle(title)
        progress_dialog.setMinimumWidth(400)
        progress_dialog.setModal(True)
        progress_dialog.setStyleSheet(f"""
            QProgressDialog {{
                background-color: {t['widget_bg']};
                border: 1px solid {t['border_color']};
                border-radius: 12px;
            }}
            QProgressBar {{
                border: 1px solid {t['border_color']};
                border-radius: 8px;
                background-color: {t['scrollbar_bg']};
                text-align: center;
                color: {t['text_primary']};
            }}
            QProgressBar::chunk {{
                background-color: {t['accent']};
                border-radius: 6px;
            }}
            QPushButton {{
                background-color: {t['accent_light']};
                border: 1px solid {t['accent']};
                border-radius: 8px;
                padding: 4px 12px;
                font-size: 12px;
                color: {t['accent']};
            }}
            QPushButton:hover {{
                background-color: {t['accent']};
                color: {t['widget_bg']};
            }}
        """)

        ProgressDialogFactory._center_dialog(progress_dialog)
        return progress_dialog
    
    @staticmethod
    def _center_dialog(dialog):
        from PyQt5.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
        else:
            screen_geometry = QApplication.desktop().screenGeometry()
        dialog_geometry = dialog.geometry()
        x = (screen_geometry.width() - dialog_geometry.width()) // 2
        y = (screen_geometry.height() - dialog_geometry.height()) // 2
        dialog.move(x, y)


class SaveTipDialog:
    """保存提示对话框"""

    @staticmethod
    def show_save_tip(parent, file_path, success=True):
        from PyQt5.QtWidgets import QLabel
        from PyQt5.QtCore import QTimer
        from ..core.utils import PathUtils

        t = ThemeManager.get_theme()
        formatted_file_path = PathUtils.to_display_path(file_path)

        if success and os.path.exists(file_path):
            tip_text = f"已保存！路径：{formatted_file_path}"
            label_style = f"""
                QLabel {{
                    color: {t['text_primary']};
                    background: {t['widget_bg']};
                    border: 1px solid {t['success']};
                    font-size: 14px;
                    font-weight: bold;
                    padding: 12px 16px;
                    border-radius: 10px;
                }}
            """
            show_time = 1000
        else:
            tip_text = f"未保存成功！\n目标路径：{formatted_file_path}"
            label_style = f"""
                QLabel {{
                    color: {t['widget_bg']};
                    background: {t['danger']};
                    font-size: 14px;
                    font-weight: bold;
                    padding: 12px 16px;
                    border-radius: 10px;
                }}
            """
            show_time = 3000

        save_label = QLabel(tip_text, parent)
        save_label.setStyleSheet(label_style)
        save_label.setWordWrap(True)
        save_label.adjustSize()

        canvas_rect = parent.canvas.rect()
        if parent.current_background:
            img_width = parent.current_background.width()
            img_height = parent.current_background.height()
        else:
            img_width = canvas_rect.width()
            img_height = canvas_rect.height()
        img_x = (canvas_rect.width() - img_width) // 2
        img_y = (canvas_rect.height() - img_height) // 2
        img_center_x = img_x + img_width // 2
        img_center_y = img_y + img_height // 2
        label_x = img_center_x - save_label.width() // 2
        label_y = img_center_y - save_label.height() // 2

        save_label.move(label_x, label_y)
        save_label.setAttribute(Qt.WA_TranslucentBackground, False)
        save_label.raise_()
        save_label.show()

        QTimer.singleShot(show_time, save_label.deleteLater)
