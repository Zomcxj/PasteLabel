"""
自定义标题栏模块 - 支持深色/浅色主题，可拖拽
"""
import os
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QPixmap, QPainter

from .theme import ThemeManager

try:
    from PyQt5.QtSvg import QSvgRenderer
    _has_svg = True
except ImportError:
    _has_svg = False


def _load_svg_icon(svg_data, size=16, color="#999"):
    if not _has_svg:
        return QPixmap(size, size)
    svg_data = svg_data.replace('currentColor', color)
    renderer = QSvgRenderer(bytearray(svg_data.encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap


SVG_MINIMIZE = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><line x1="5" y1="12" x2="19" y2="12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>'
SVG_MAXIMIZE = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><rect x="5" y="5" width="14" height="14" rx="1" stroke="currentColor" stroke-width="2" fill="none"/></svg>'
SVG_RESTORE = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><rect x="3" y="7" width="12" height="12" rx="1" stroke="currentColor" stroke-width="2" fill="none"/><polyline points="7,3 17,3 17,13" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>'
SVG_CLOSE = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>'


class TitleBar(QWidget):
    """自定义标题栏"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_pos = None
        self._pre_max_geometry = None
        self._is_maximized = False
        self.setFixedHeight(36)
        self.setObjectName("titleBar")
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 0, 0)
        layout.setSpacing(0)

        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ico_image", "icoo.png")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ico_image", "icoo.png")

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(20, 20)
        if os.path.exists(icon_path):
            self.icon_label.setPixmap(QIcon(icon_path).pixmap(16, 16))
        layout.addWidget(self.icon_label)

        self.title_label = QLabel("PasteLabel")
        self.title_label.setObjectName("titleLabel")
        layout.addWidget(self.title_label)

        layout.addStretch()

        self._color = ThemeManager.get_theme()['text_secondary']

        self.btn_min = QPushButton()
        self.btn_min.setObjectName("tbBtn")
        self.btn_min.setFixedSize(46, 36)
        self.btn_min.setIcon(QIcon(_load_svg_icon(SVG_MINIMIZE, 14, self._color)))
        self.btn_min.setToolTip("最小化")
        self.btn_min.clicked.connect(self._on_minimize)
        layout.addWidget(self.btn_min)

        self.btn_max = QPushButton()
        self.btn_max.setObjectName("tbBtn")
        self.btn_max.setFixedSize(46, 36)
        self.btn_max.setIcon(QIcon(_load_svg_icon(SVG_MAXIMIZE, 14, self._color)))
        self.btn_max.setToolTip("最大化")
        self.btn_max.clicked.connect(self._on_maximize)
        layout.addWidget(self.btn_max)

        self.btn_close = QPushButton()
        self.btn_close.setObjectName("tbCloseBtn")
        self.btn_close.setFixedSize(46, 36)
        self.btn_close.setIcon(QIcon(_load_svg_icon(SVG_CLOSE, 14, self._color)))
        self.btn_close.setToolTip("关闭")
        self.btn_close.clicked.connect(self._on_close)
        layout.addWidget(self.btn_close)

    def _on_minimize(self):
        self.window().showMinimized()

    def _on_maximize(self):
        if self._is_maximized:
            self._restore()
        else:
            self._maximize()

    def _maximize(self):
        self._pre_max_geometry = self.window().geometry()
        self._is_maximized = True
        self.btn_max.setIcon(QIcon(_load_svg_icon(SVG_RESTORE, 14, self._color)))
        self.btn_max.setToolTip("还原")
        self.window().showMaximized()

    def _restore(self):
        self._is_maximized = False
        self.btn_max.setIcon(QIcon(_load_svg_icon(SVG_MAXIMIZE, 14, self._color)))
        self.btn_max.setToolTip("最大化")
        self.window().showNormal()
        if self._pre_max_geometry is not None:
            self.window().setGeometry(self._pre_max_geometry)

    def _on_close(self):
        self.window().close()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.window().pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos:
            if self._is_maximized:
                ratio = event.globalPos().x() / self.window().width()
                self.window().showNormal()
                new_x = event.globalPos().x() - int(self.window().width() * ratio)
                self.window().move(new_x, event.globalPos().y() - 18)
                self._drag_pos = event.globalPos() - self.window().pos()
                self._is_maximized = False
                self.btn_max.setIcon(QIcon(_load_svg_icon(SVG_MAXIMIZE, 14, self._color)))
                self.btn_max.setToolTip("最大化")
            else:
                self.window().move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._on_maximize()
            event.accept()

    def update_theme(self):
        t = ThemeManager.get_theme()
        c = t['text_secondary']
        self.btn_min.setIcon(QIcon(_load_svg_icon(SVG_MINIMIZE, 14, c)))
        if self._is_maximized:
            self.btn_max.setIcon(QIcon(_load_svg_icon(SVG_RESTORE, 14, c)))
        else:
            self.btn_max.setIcon(QIcon(_load_svg_icon(SVG_MAXIMIZE, 14, c)))
        self.btn_close.setIcon(QIcon(_load_svg_icon(SVG_CLOSE, 14, c)))
