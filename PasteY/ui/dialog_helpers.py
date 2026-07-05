"""对话框辅助函数：统一标题栏主题和按钮文字。"""
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QDialog, QInputDialog, QMessageBox

from . import i18n
from .dwm import set_titlebar_dark
from .theme import ThemeManager


def sync_titlebar(widget):
    is_dark = ThemeManager.get_mode().value == "dark"
    QTimer.singleShot(30, lambda: set_titlebar_dark(int(widget.winId()), is_dark))


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


def get_text(parent, title, label, text=""):
    dialog = ThemedInputDialog(parent)
    dialog.setWindowTitle(i18n.t(title))
    dialog.setLabelText(i18n.t(label))
    dialog.setTextValue(text)
    dialog.setOkButtonText(i18n.t("确定"))
    dialog.setCancelButtonText(i18n.t("取消"))
    return dialog.textValue(), dialog.exec_() == QDialog.Accepted


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
