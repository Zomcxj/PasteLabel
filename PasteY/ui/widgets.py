"""
自定义控件模块 - Canvas 等控件
"""
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QPushButton, QFrame
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, pyqtSignal


class OptionsPopup(QWidget):
    """圆角选项弹出菜单"""
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setObjectName("optionsPopup")
        self._bg_color = QColor(255, 255, 255)
        self._border_color = QColor(200, 200, 200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)

        self._items = []
        self._draw_box_btn = None

    def set_colors(self, bg, border):
        self._bg_color = bg
        self._border_color = border
        self.update()

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QPen
        try:
            from PyQt5.QtGui import QPainterPath
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            path = QPainterPath()
            path.addRoundedRect(1, 1, self.width() - 2, self.height() - 2, 10, 10)
            painter.setPen(QPen(self._border_color, 1))
            painter.setBrush(self._bg_color)
            painter.drawPath(path)
            painter.end()
        except ImportError:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(self._border_color, 1))
            painter.setBrush(self._bg_color)
            painter.drawRoundedRect(1, 1, self.width() - 2, self.height() - 2, 10, 10)
            painter.end()

    def add_draw_box_action(self, text, shortcut, callback):
        row = QHBoxLayout()
        row.setContentsMargins(4, 0, 4, 0)

        btn = QPushButton(text)
        btn.setObjectName("popupDrawBoxBtn")
        btn.clicked.connect(lambda: self._on_draw_box(callback))
        row.addWidget(btn, 1)

        if shortcut:
            key_lbl = QLabel(shortcut)
            key_lbl.setObjectName("popupShortcut")
            key_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(key_lbl)

        self.layout().addLayout(row)
        self._draw_box_btn = btn

    def add_separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setObjectName("popupSeparator")
        line.setFixedHeight(1)
        self.layout().addWidget(line)

    def add_check_item(self, text, shortcut, checkbox):
        row = QHBoxLayout()
        row.setContentsMargins(4, 0, 4, 0)

        cb = QCheckBox()
        cb.setChecked(checkbox.isChecked())
        cb.stateChanged.connect(lambda state, c=checkbox: c.setChecked(state == Qt.Checked))
        checkbox.stateChanged.connect(lambda state, c=cb: c.setChecked(state == Qt.Checked))
        row.addWidget(cb)

        lbl = QLabel(text)
        row.addWidget(lbl, 1)

        if shortcut:
            key_lbl = QLabel(shortcut)
            key_lbl.setObjectName("popupShortcut")
            key_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(key_lbl)

        self._items.append((cb, checkbox))
        self.layout().addLayout(row)

    def _on_draw_box(self, callback):
        callback()
        self.close()

    def update_texts(self, texts):
        if len(texts) >= 1 and self._draw_box_btn:
            self._draw_box_btn.setText(texts[0])
        for i, (cb, _) in enumerate(self._items):
            if i + 1 < len(texts):
                row_layout = cb.parent().layout() if cb.parent() else None
                if row_layout:
                    for j in range(row_layout.count()):
                        item = row_layout.itemAt(j)
                        if item and item.widget() and isinstance(item.widget(), QLabel):
                            w = item.widget()
                            if not w.objectName():
                                w.setText(texts[i + 1])
                                break


from ..canvas import Canvas  # noqa: F401
