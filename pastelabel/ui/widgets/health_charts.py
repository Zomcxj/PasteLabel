"""数据集健康自绘图表：QPainter 条形图 / 直方图，无第三方依赖。"""
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QColor, QPen

from ..theme import ThemeManager

_PALETTE = (
    '#2196F3', '#4CAF50', '#FF9800', '#F44336', '#9C27B0',
    '#00BCD4', '#795548', '#607D8B', '#E91E63', '#3F51B5',
)
_LEFT_LABEL_W = 70
_RIGHT_PAD = 8
_AXIS_H = 18
_TOP_PAD = 16


def _bar_label(value, total):
    """条形图右侧文字：数量 + 整数百分比。"""
    pct = int(round(value / total * 100)) if total else 0
    return f"{_fmt_num(value)} ({pct}%)"


def _fmt_num(v):
    """面积等大数格式化：1.2k / 2.5M / 整数。"""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return '0'
    if abs(v) >= 1e6:
        return f"{v / 1e6:.1f}M"
    if abs(v) >= 1e3:
        return f"{v / 1e3:.1f}k"
    return str(int(round(v)))


class HealthBarChart(QWidget):
    """横向条形图（类别分布）或纵向直方图（尺寸/长宽比/IoU）。"""

    def __init__(self, parent=None, height=140):
        super().__init__(parent)
        self._mode = 'empty'
        self._items = []
        self._edges = []
        self._counts = []
        self._horizontal = True
        self._highlight = False
        self._placeholder = ''
        self._xlabel = ''
        self._ylabel = ''
        self.setMinimumHeight(height)

    def set_data(self, items, horizontal=True, highlight_extremes=False):
        self._mode = 'bars'
        self._items = list(items or [])
        self._horizontal = horizontal
        self._highlight = highlight_extremes
        self.update()

    def set_histogram(self, edges, counts, xlabel='', ylabel=''):
        self._mode = 'hist'
        self._edges = list(edges or [])
        self._counts = list(counts or [])
        self._xlabel = str(xlabel or '')
        self._ylabel = str(ylabel or '')
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
        total = sum(values) or 1.0
        border = QColor(t['border_color'])
        text_pen = QPen(QColor(t['text_primary']))
        if self._horizontal:
            row_h = max(8, h // max(1, len(self._items)))
            bar_area_w = max(10, w - _LEFT_LABEL_W - 90)
            for idx, item in enumerate(self._items):
                y = idx * row_h
                value = float(item.get('value', 0) or 0)
                bar_w = int((value / peak) * bar_area_w)
                color = QColor(item.get('color') or _PALETTE[idx % len(_PALETTE)])
                if self._highlight and idx in (0, len(self._items) - 1):
                    pen = QPen(QColor(t['accent_hover']))
                    pen.setWidth(2)
                    painter.setPen(pen)
                else:
                    painter.setPen(QPen(border))
                painter.setBrush(color)
                painter.drawRect(_LEFT_LABEL_W, y + 2, bar_w, row_h - 4)
                painter.setPen(text_pen)
                painter.drawText(0, y, _LEFT_LABEL_W - 4, row_h,
                                 Qt.AlignVCenter | Qt.AlignRight,
                                 str(item.get('label', '')))
                painter.drawText(_LEFT_LABEL_W + bar_w + 4, y,
                                 w - _LEFT_LABEL_W - bar_w - 4, row_h,
                                 Qt.AlignVCenter | Qt.AlignLeft,
                                 _bar_label(value, total))
        else:
            col_w = max(4, w // max(1, len(self._items)))
            for idx, item in enumerate(self._items):
                x = idx * col_w
                value = float(item.get('value', 0) or 0)
                bar_h = int((value / peak) * (h - 20))
                color = QColor(item.get('color') or _PALETTE[idx % len(_PALETTE)])
                painter.setPen(QPen(border))
                painter.setBrush(color)
                painter.drawRect(x + 2, h - bar_h, col_w - 4, bar_h)

    def _paint_hist(self, painter, w, h, t):
        if not self._counts:
            return
        peak = max(self._counts) or 1
        accent = QColor(t['accent'])
        border = QColor(t['border_color'])
        text_pen = QPen(QColor(t['text_primary']))
        plot_h = max(10, h - _AXIS_H - 12 - _TOP_PAD)
        n = len(self._counts)
        col_w = max(2, w // max(1, n))
        for idx, count in enumerate(self._counts):
            x = idx * col_w
            bar_h = int((count / peak) * max(1, plot_h - _TOP_PAD))
            top = plot_h - bar_h
            color = accent.lighter(100 + (idx % 5) * 6)
            painter.setPen(QPen(border))
            painter.setBrush(color)
            painter.drawRect(x + 1, top, col_w - 2, bar_h)
            if count > 0:
                painter.setPen(text_pen)
                painter.drawText(x, top - 14, col_w, 12,
                                 Qt.AlignHCenter | Qt.AlignBottom,
                                 _fmt_num(count))
        edges = self._edges
        if edges:
            painter.setPen(text_pen)
            ticks = [0, len(edges) // 2, len(edges) - 1]
            for i in ticks:
                painter.drawText(i * col_w - 30, plot_h + 2, 60, _AXIS_H - 4,
                                 Qt.AlignHCenter | Qt.AlignTop,
                                 _fmt_num(edges[i]))
        painter.setPen(text_pen)
        if self._ylabel:
            painter.drawText(0, 0, w, 12, Qt.AlignLeft | Qt.AlignTop,
                             f"{self._ylabel}: {_fmt_num(peak)}")
        if self._xlabel:
            painter.drawText(0, plot_h + 2, w, _AXIS_H - 4,
                             Qt.AlignRight | Qt.AlignTop, self._xlabel)
