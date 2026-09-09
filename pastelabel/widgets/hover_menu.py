from PyQt5.QtWidgets import QMenu


class HoverKeepMenu(QMenu):
    """点击菜单项不关闭，鼠标移开后关闭。"""

    def mouseReleaseEvent(self, event):
        action = self.actionAt(event.pos())
        if action and action.isEnabled():
            if action == self.actions()[0]:
                action.triggered.emit(False)
                event.accept()
                return
            action.trigger()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.hide()
