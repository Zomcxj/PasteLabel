"""对话框辅助函数：统一标题栏主题和按钮文字。"""
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QDialog, QInputDialog, QMessageBox, QColorDialog, QLabel, QPushButton

from . import i18n
from .dwm import set_titlebar_dark
from .theme import ThemeManager


def sync_titlebar(widget):
    is_dark = ThemeManager.get_mode().value == "dark"
    set_titlebar_dark(int(widget.winId()), is_dark)


def center_on_parent(dialog, parent=None):
    parent = parent or dialog.parent()
    if not parent:
        return
    parent_geometry = parent.geometry()
    dialog_geometry = dialog.geometry()
    x = parent_geometry.x() + (parent_geometry.width() - dialog_geometry.width()) // 2
    y = parent_geometry.y() + (parent_geometry.height() - dialog_geometry.height()) // 2
    dialog.move(x, y)


class ThemedInputDialog(QInputDialog):
    def showEvent(self, event):
        super().showEvent(event)
        center_on_parent(self)
        sync_titlebar(self)


class ThemedMessageBox(QMessageBox):
    def showEvent(self, event):
        super().showEvent(event)
        center_on_parent(self)
        sync_titlebar(self)
        QTimer.singleShot(0, self._fix_detail_buttons)

    def _fix_detail_buttons(self):
        for btn in self.findChildren(QPushButton):
            raw = btn.text().replace('&', '')
            if raw in ("Show Details...", "Show Details", "显示详情"):
                btn.setText(i18n.t("显示详情"))
            elif raw in ("Hide Details...", "Hide Details", "隐藏详情"):
                btn.setText(i18n.t("隐藏详情"))


class ThemedColorDialog(QColorDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setOption(QColorDialog.DontUseNativeDialog, True)

    def showEvent(self, event):
        super().showEvent(event)
        sync_titlebar(self)
        translations = {
            '&Basic colors': '基本颜色：',
            '&Custom colors': '自定义颜色：',
            '&Pick Screen Color': '拾取屏幕颜色',
            '&Add to Custom Colors': '添加到自定义颜色',
            'Hu&e:': '色调：',
            '&Sat:': '饱和度：',
            '&Val:': '亮度：',
            '&Red:': '红：',
            '&Green:': '绿：',
            'Bl&ue:': '蓝：',
            'A&lpha channel:': '透明度：',
            '&HTML:': 'HTML：',
            'OK': '确定',
            'Cancel': '取消',
        }
        for widget in self.findChildren(QLabel) + self.findChildren(QPushButton):
            text = widget.text()
            if text in translations:
                widget.setText(i18n.t(translations[text]))


def get_text(parent, title, label, text=""):
    dialog = ThemedInputDialog(parent)
    dialog.setWindowTitle(i18n.t(title))
    dialog.setLabelText(i18n.t(label))
    dialog.setTextValue(text)
    dialog.setOkButtonText(i18n.t("确定"))
    dialog.setCancelButtonText(i18n.t("取消"))
    accepted = dialog.exec_() == QDialog.Accepted
    return dialog.textValue(), accepted


def question(parent, title, text, buttons=QMessageBox.Yes | QMessageBox.No,
             default_button=QMessageBox.No):
    box = ThemedMessageBox(parent)
    box.setIcon(QMessageBox.Question)
    box.setWindowTitle(i18n.t(title))
    box.setText(text)
    box.setStandardButtons(buttons)
    box.setDefaultButton(default_button)
    translations = {
        QMessageBox.Yes: "是",
        QMessageBox.No: "否",
        QMessageBox.Cancel: "取消",
        QMessageBox.Ok: "确定",
    }
    for button, label in translations.items():
        btn = box.button(button)
        if btn:
            btn.setText(i18n.t(label))
    return box.exec_()


def warning(parent, title, text):
    box = ThemedMessageBox(parent)
    box.setIcon(QMessageBox.Warning)
    box.setWindowTitle(i18n.t(title))
    box.setText(text)
    box.setStandardButtons(QMessageBox.Ok)
    btn = box.button(QMessageBox.Ok)
    if btn:
        btn.setText(i18n.t("确定"))
    return box.exec_()
