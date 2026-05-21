"""
对话框模块 - 定义各种对话框
"""
import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, 
    QLineEdit, QPushButton, QInputDialog, QMessageBox
)
from PyQt5.QtCore import Qt


class LabelSelectionDialog(QDialog):
    """标签选择对话框"""
    
    def __init__(self, parent=None, labels=None):
        super().__init__(parent)
        self.setWindowTitle("选择标签")
        self.setMinimumWidth(400)
        
        if labels is None:
            labels = []
        
        layout = QVBoxLayout()
        
        # 现有标签列表
        layout.addWidget(QLabel("现有标签："))
        self.label_list = QListWidget()
        for label in labels:
            # 提取纯标签名称，去除"(count)"部分
            pure_label = self._extract_pure_label(label)
            self.label_list.addItem(pure_label)
        layout.addWidget(self.label_list)
        
        # 新标签输入框
        layout.addWidget(QLabel("或输入新标签："))
        self.new_label_input = QLineEdit()
        layout.addWidget(self.new_label_input)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.ok_btn = QPushButton("确定")
        self.ok_btn.setStyleSheet(self._get_button_style())
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setStyleSheet(self._get_button_style())
        
        button_layout.addStretch()
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # 连接信号
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        
        # 按下回车键等同于点击确定按钮
        self.new_label_input.returnPressed.connect(self.accept)
        
        # 双击标签列表项等同于点击确定按钮
        self.label_list.itemDoubleClicked.connect(self.accept)
    
    @staticmethod
    def _extract_pure_label(label_text):
        """从标签文本中提取纯标签名称"""
        if " (" in label_text:
            return label_text.split(" (")[0]
        return label_text
    
    @staticmethod
    def _get_button_style():
        """获取按钮样式"""
        return """
            QPushButton {
                background-color: #BBDEFB;
                border: 1px solid #1976D2;
                border-radius: 8px;
                padding: 4px 8px;
                font-size: 12px;
                color: #0D47A1;
            }
            QPushButton:hover {
                background-color: #90CAF9;
            }
            QPushButton:pressed {
                background-color: #64B5F6;
            }
        """
    
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
        """
        创建进度条对话框
        :param parent: 父窗口
        :param title: 标题
        :param label_text: 标签文本
        :param maximum: 最大值
        :return: QProgressDialog
        """
        from PyQt5.QtWidgets import QProgressDialog
        
        progress_dialog = QProgressDialog(label_text, "取消", 0, maximum, parent)
        progress_dialog.setWindowTitle(title)
        progress_dialog.setMinimumWidth(400)
        progress_dialog.setModal(True)
        progress_dialog.setStyleSheet(ProgressDialogFactory._get_style())
        
        # 居中显示
        ProgressDialogFactory._center_dialog(progress_dialog)
        
        return progress_dialog
    
    @staticmethod
    def _get_style():
        """获取进度条样式"""
        return """
            QProgressDialog {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 12px;
            }
            QProgressBar {
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                background-color: #F5F5F5;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-radius: 6px;
            }
            QPushButton {
                background-color: #E3F2FD;
                border: 1px solid #2196F3;
                border-radius: 8px;
                padding: 4px 12px;
                font-size: 12px;
                color: #1976D2;
            }
            QPushButton:hover {
                background-color: #BBDEFB;
            }
        """
    
    @staticmethod
    def _center_dialog(dialog):
        """将对话框居中显示"""
        from PyQt5.QtWidgets import QApplication
        
        screen_geometry = QApplication.desktop().screenGeometry()
        dialog_geometry = dialog.geometry()
        x = (screen_geometry.width() - dialog_geometry.width()) // 2
        y = (screen_geometry.height() - dialog_geometry.height()) // 2
        dialog.move(x, y)


class SaveTipDialog:
    """保存提示对话框"""
    
    @staticmethod
    def show_save_tip(parent, file_path, success=True):
        """
        显示保存提示
        :param parent: 父窗口
        :param file_path: 保存路径
        :param success: 是否成功
        """
        from PyQt5.QtWidgets import QLabel
        from PyQt5.QtCore import QTimer
        try:
            from .utils import PathUtils
        except ImportError:
            from utils import PathUtils
        
        formatted_file_path = PathUtils.to_display_path(file_path)
        
        if success and os.path.exists(file_path):
            tip_text = f"已保存！\n保存路径：{formatted_file_path}"
            label_style = """
                QLabel {
                    color: black;
                    background: rgba(200, 200, 200, 0.9);
                    font-size: 16px;
                    font-weight: bold;
                    padding: 10px 10px;
                    border-radius: 10px;
                    border: none;
                    text-align: center;
                }
            """
            show_time = 1000
        else:
            tip_text = f"未保存成功！\n目标路径：{formatted_file_path}"
            label_style = """
                QLabel {
                    color: white;
                    background: rgba(255, 0, 0, 0.9);
                    font-size: 16px;
                    font-weight: bold;
                    padding: 10px 10px;
                    border-radius: 10px;
                    border: none;
                    text-align: center;
                }
            """
            show_time = 3000
        
        # 创建提示标签
        save_label = QLabel(tip_text, parent)
        save_label.setStyleSheet(label_style)
        save_label.setWordWrap(True)
        save_label.adjustSize()
        
        # 计算位置（显示在画布中心）
        canvas_rect = parent.canvas.rect()
        img_width = parent.current_background.width()
        img_height = parent.current_background.height()
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
        
        # 定时关闭
        QTimer.singleShot(show_time, save_label.deleteLater)
