"""分段按钮动画控件（PyQt5版本，参考ScanVerse）"""

from PyQt5.QtWidgets import QFrame, QWidget, QPushButton
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect


class AnimatedSegmentedControl(QFrame):
    """带滑动指示器的分段按钮控件"""

    def __init__(self, container, *buttons):
        super().__init__(container.parent())
        self._container = container
        self._buttons = list(buttons)
        self._accent = "#2196F3"

        self._indicator = QWidget(container)
        self._indicator.lower()
        self._indicator.setStyleSheet(
            f"background: {self._accent}; border-radius: 5px;")

        self._anim = QPropertyAnimation(self._indicator, b"geometry")
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        for btn in self._buttons:
            btn.clicked.connect(lambda: self.update_position(animated=True))

    def set_accent(self, color):
        self._accent = color
        self._indicator.setStyleSheet(
            f"background: {color}; border-radius: 5px;")

    def update_position(self, animated=True):
        checked = None
        for i, btn in enumerate(self._buttons):
            if btn.isChecked():
                checked = btn
                break
        if checked is None:
            if not self._buttons:
                return
            checked = self._buttons[0]

        h = checked.height() or self._container.height() or 24
        w = checked.width() or 80

        # 按钮在容器contentsRect内定位，指示器作为子控件用widget坐标
        # 需要加上contentsRect的偏移（border造成）
        cr = self._container.contentsRect()
        x_offset = cr.x()
        y_offset = cr.y()

        x = x_offset
        for btn in self._buttons:
            if btn is checked:
                break
            x += btn.width()

        container_h = self._container.height()
        content_h = container_h - y_offset * 2
        y = y_offset + max(0, (content_h - h) // 2)
        target = QRect(x, y, w, h)
        cur = self._indicator.geometry()

        if animated and cur.isValid() and cur != target:
            self._anim.stop()
            self._anim.setStartValue(cur)
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self._indicator.setGeometry(target)
