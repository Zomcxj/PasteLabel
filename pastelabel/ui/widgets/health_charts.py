"""数据集健康自绘图表：QPainter 条形图 / 直方图，无第三方依赖。"""
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QColor, QPen

from ..theme import ThemeManager


class HealthBarChart(QWidget):
    """横向条形图（类别分布）或纵向直方图（尺寸/长宽比/IoU）。"""

    def __init__(self, parent=None, height=120):
        super().__init__(parent)
        self._mode = 'empty'
        self._items = []
        self._edges = []
        self._counts = []
        self._horizontal = True
        self._highlight = False
        self._placeholder = ''
        self.setMinimumHeight(height)

    def set_data(self, items, horizontal=True, highlight_extremes=False):
        self._mode = 'bars'
        self._items = list(items or [])
        self._horizontal = horizontal
        self._highlight = highlight_extremes
        self.update()

    def set_histogram(self, edges, counts):
        self._mode = 'hist'
        self._edges = list(edges or [])
        self._counts = list(counts or [])
        self.update()

    def set_placeholder(self, text):
        self._mode = 'empty'
        self._placeholder = str(text or '')
        self.update()

    def paintEvent(self, event):
        t = ThemeManager.get_theme()
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            w = self.width()
            h = self.height()
            if self._mode == 'empty':
                painter.setPen(QPen(QColor(t['text_secondary'])))
                painter.drawText(0, 0, w, h, Qt.AlignCenter, self._placeholder)
                return
            if self._mode == 'bars':
                self._paint_bars(painter, w, h, t)
            else:
                self._paint_hist(painter, w, h, t)
        finally:
            painter.end()

    def _paint_bars(self, painter, w, h, t):
        if not self._items:
            return
        values = [float(i.get('value', 0) or 0) for i in self._items]
        peak = max(values) or 1.0
        accent = QColor(t['accent'])
        border = QColor(t['border_color'])
        if self._horizontal:
            row_h = max(8, h // max(1, len(self._items)))
            for idx, item in enumerate(self._items):
                y = idx * row_h
                bar_w = int((float(item.get('value', 0) or 0) / peak) * (w - 60))
                color = accent
                if self._highlight and idx in (0, len(self._items) - 1):
                    color = QColor(t['accent_hover'])
                painter.setPen(QPen(border))
                painter.setBrush(color)
                painter.drawRect(50, y + 2, bar_w, row_h - 4)
                painter.setPen(QPen(QColor(t['text_primary'])))
                painter.drawText(0, y, 48, row_h, Qt.AlignVCenter | Qt.AlignRight,
                                 str(item.get('label', '')))
        else:
            col_w = max(4, w // max(1, len(self._items)))
            for idx, item in enumerate(self._items):
                x = idx * col_w
                bar_h = int((float(item.get('value', 0) or 0) / peak) * (h - 20))
                painter.setPen(QPen(border))
                painter.setBrush(accent)
                painter.drawRect(x + 2, h - bar_h, col_w - 4, bar_h)

    def _paint_hist(self, painter, w, h, t):
        if not self._counts:
            return
        peak = max(self._counts) or 1
        accent = QColor(t['accent'])
        border = QColor(t['border_color'])
        n = len(self._counts)
        col_w = max(2, w // max(1, n))
        for idx, count in enumerate(self._counts):
            x = idx * col_w
            bar_h = int((count / peak) * (h - 20))
            painter.setPen(QPen(border))
            painter.setBrush(accent)
            painter.drawRect(x + 1, h - bar_h, col_w - 2, bar_h)
