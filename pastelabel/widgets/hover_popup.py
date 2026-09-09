from PyQt5.QtWidgets import QWidget, QApplication, QLineEdit


class HoverDismissPopup(QWidget):
    """鼠标移出后自动收起的轻量弹层。"""

    def leaveEvent(self, event):
        super().leaveEvent(event)
        focus_widget = QApplication.focusWidget()
        if isinstance(focus_widget, QLineEdit) and self.isAncestorOf(focus_widget):
            return
        self.hide()
