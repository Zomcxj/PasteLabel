"""
Canvas 绘制混入 - 负责所有绘制逻辑（背景、贴图、检测框、临时框、网格）
"""
from PyQt5.QtGui import QPainter, QPixmap, QColor, QPen, QFontMetrics
from PyQt5.QtCore import Qt, QPointF, QRectF

from ..core.config import DETECTION_BOX_CONFIG, PASTE_ITEM_CONFIG, GRID_CONFIG
from ..ui.theme import ThemeManager


class CanvasRendererMixin:
    """Canvas 绘制混入类 - paintEvent 及所有 _draw_* 方法"""

    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        t = ThemeManager.get_theme()
        bg_color = t['canvas_bg']
        r = int(bg_color[1:3], 16)
        g = int(bg_color[3:5], 16)
        b = int(bg_color[5:7], 16)
        painter.fillRect(self.rect(), QColor(r, g, b))

        background_rect = self.get_background_rect()

        if self.parent.current_background is not None and background_rect:
            self._draw_background(painter, background_rect)

        if background_rect:
            self._draw_grid(painter, background_rect)

        if background_rect:
            self._draw_paste_items(painter, background_rect)

        if (self.parent.show_labels_checkbox.isChecked() and
            background_rect and self.parent.detection_boxes):
            self._draw_detection_boxes(painter, background_rect)

        if self.is_drawing_box:
            self._draw_temp_box(painter)

    def _draw_background(self, painter, background_rect):
        """绘制背景图"""
        painter.drawPixmap(
            int(background_rect.left()),
            int(background_rect.top()),
            int(background_rect.width()),
            int(background_rect.height()),
            self.parent.current_background
        )

    def _draw_grid(self, painter, background_rect):
        """绘制网格参考线"""
        if not self.parent.show_grid_checkbox.isChecked():
            return

        t = ThemeManager.get_theme()
        mode = ThemeManager.get_mode().value
        color_map = {'light': GRID_CONFIG['color_light'],
                     'dark': GRID_CONFIG['color_dark'],
                     'ink': GRID_CONFIG['color_ink']}
        grid_color = color_map.get(mode, GRID_CONFIG['color_light'])

        r = int(grid_color[1:3], 16)
        g = int(grid_color[3:5], 16)
        b = int(grid_color[5:7], 16)

        pen = QPen(QColor(r, g, b, 120))
        pen.setWidth(1)
        pen.setStyle(Qt.DotLine)
        painter.setPen(pen)

        spacing = GRID_CONFIG['spacing']
        scaled_spacing = spacing * self.background_scale

        if scaled_spacing < 5:
            return

        x = background_rect.left()
        while x <= background_rect.right():
            painter.drawLine(int(x), int(background_rect.top()),
                           int(x), int(background_rect.bottom()))
            x += scaled_spacing

        y = background_rect.top()
        while y <= background_rect.bottom():
            painter.drawLine(int(background_rect.left()), int(y),
                           int(background_rect.right()), int(y))
            y += scaled_spacing

    def _draw_paste_items(self, painter, background_rect):
        """绘制所有贴图"""
        for i, (pixmap, rect, label) in enumerate(self.parent.canvas_items):
            item_x = (rect.x() * self.background_scale) + background_rect.left()
            item_y = (rect.y() * self.background_scale) + background_rect.top()
            item_width = rect.width() * self.background_scale
            item_height = rect.height() * self.background_scale

            item_rect = QRectF(item_x, item_y, item_width, item_height)
            is_selected = (i == self.parent.selected_item)

            self._check_mouse_hover(item_rect, i)

            self._draw_single_paste_item(
                painter, pixmap, item_rect, label, is_selected, i
            )

    def _check_mouse_hover(self, item_rect, item_index):
        """检查鼠标是否悬停在贴图上，如果是则自动选中"""
        mouse_pos = self.mouse_pos
        if item_rect.contains(mouse_pos):
            if self.parent.selected_item != item_index:
                self.parent.selected_item = item_index
                _, rect, _ = self.parent.canvas_items[item_index]
                self.selected_item_size = (rect.width(), rect.height())
            return True
        return False

    def _draw_single_paste_item(self, painter, pixmap, item_rect, label, is_selected, item_index=0):
        """绘制单个贴图"""
        item_x = item_rect.left()
        item_y = item_rect.top()
        item_width = item_rect.width()
        item_height = item_rect.height()

        if is_selected:
            self._draw_selected_paste(painter, pixmap, item_rect, label)
        else:
            painter.drawPixmap(
                int(item_x), int(item_y),
                int(item_width), int(item_height),
                pixmap
            )

        from ..core.config import LABEL_COLORS
        label_color_index = (hash(label) + item_index) % len(LABEL_COLORS)
        label_color_hex = LABEL_COLORS[label_color_index]
        lr = int(label_color_hex[1:3], 16)
        lg = int(label_color_hex[3:5], 16)
        lb = int(label_color_hex[5:7], 16)

        border_color = QColor(lr, lg, lb)
        pen_width = 3 if is_selected else 2
        pen = QPen(border_color, pen_width)
        painter.setPen(pen)
        painter.drawRect(int(item_x), int(item_y), int(item_width), int(item_height))

        if is_selected:
            self._draw_resize_handle(painter, item_rect, border_color)

        self._draw_paste_label(painter, item_x, item_y, label, is_selected, item_index)

    def _draw_selected_paste(self, painter, pixmap, item_rect, label):
        """绘制选中的贴图（带透明蒙版）"""
        temp_pixmap = QPixmap(int(item_rect.width()), int(item_rect.height()))
        temp_pixmap.fill(Qt.transparent)
        temp_painter = QPainter(temp_pixmap)

        temp_painter.drawPixmap(
            0, 0, int(item_rect.width()), int(item_rect.height()), pixmap
        )

        overlay_color = QColor(135, 206, 250, 80)
        temp_painter.fillRect(
            0, 0, int(item_rect.width()), int(item_rect.height()), overlay_color
        )
        temp_painter.end()

        painter.drawPixmap(
            int(item_rect.left()), int(item_rect.top()),
            temp_pixmap
        )

    def _draw_resize_handle(self, painter, item_rect, color):
        """绘制右下角缩放手柄"""
        handle_size = PASTE_ITEM_CONFIG['handle_size']
        br_handle = item_rect.bottomRight()
        painter.fillRect(
            int(br_handle.x() - handle_size),
            int(br_handle.y() - handle_size),
            handle_size, handle_size,
            color
        )

    @staticmethod
    def _draw_label_above_rect(painter, x, y, label, bg_color):
        """在矩形上方绘制标签（背景 + 文字）"""
        font = painter.font()
        metrics = QFontMetrics(font)
        text_width = metrics.width(label)
        text_height = metrics.height()

        painter.fillRect(int(x), int(y) - text_height, text_width, text_height, bg_color)
        painter.setPen(QColor(0, 0, 0))
        painter.setFont(font)
        painter.drawText(int(x), int(y) - 2, label)

    def _draw_paste_label(self, painter, x, y, label, is_selected, item_index=0):
        """绘制贴图标签"""
        if not self.parent.show_paste_names_checkbox.isChecked():
            return
        from ..core.config import LABEL_COLORS
        label_color_index = (hash(label) + item_index) % len(LABEL_COLORS)
        label_color_hex = LABEL_COLORS[label_color_index]
        lr = int(label_color_hex[1:3], 16)
        lg = int(label_color_hex[3:5], 16)
        lb = int(label_color_hex[5:7], 16)
        bg_color = QColor(lr, lg, lb)
        self._draw_label_above_rect(painter, x, y, label, bg_color)

    def _draw_detection_boxes(self, painter, background_rect):
        """绘制所有检测框"""
        for i, box in enumerate(self.parent.detection_boxes):
            if box["width"] <= 0 or box["height"] <= 0:
                continue

            box_x = box["x"] * self.background_scale + background_rect.left()
            box_y = box["y"] * self.background_scale + background_rect.top()
            box_width = box["width"] * self.background_scale
            box_height = box["height"] * self.background_scale

            is_selected = (i == self.selected_box)
            is_pressed_label = self._is_pressed_label(box)

            self._draw_single_detection_box(
                painter, box_x, box_y, box_width, box_height,
                box.get("label", ""), is_selected, is_pressed_label
            )

    def _is_pressed_label(self, box):
        """检查检测框是否是当前按下的标签"""
        if not hasattr(self.parent, 'pressed_label') or self.parent.pressed_label is None:
            return False
        return box.get('label') == self.parent.pressed_label

    def _draw_single_detection_box(self, painter, x, y, width, height, label,
                                    is_selected, is_pressed_label):
        """绘制单个检测框"""
        from ..core.config import LABEL_COLORS
        label_color_index = hash(label) % len(LABEL_COLORS)
        label_color_hex = LABEL_COLORS[label_color_index]
        lr = int(label_color_hex[1:3], 16)
        lg = int(label_color_hex[3:5], 16)
        lb = int(label_color_hex[5:7], 16)

        if is_selected:
            fill_color = QColor(lr, lg, lb, 50)
            border_color = QColor(lr, lg, lb)
            pen_width = 3
        elif is_pressed_label:
            fill_color = QColor(lr, lg, lb, 50)
            border_color = QColor(lr, lg, lb)
            pen_width = 2
        else:
            fill_color = None
            border_color = QColor(lr, lg, lb)
            pen_width = 2

        if fill_color:
            painter.fillRect(int(x), int(y), int(width), int(height), fill_color)

        pen = QPen(border_color, pen_width)
        painter.setPen(pen)
        painter.drawRect(int(x), int(y), int(width), int(height))

        if label and getattr(self.parent, 'show_label_names_checkbox', None) and self.parent.show_label_names_checkbox.isChecked():
            self._draw_box_label(painter, x, y, label, border_color)

        if is_selected:
            self._draw_box_handles(painter, x, y, width, height, border_color)

    def _draw_box_label(self, painter, x, y, label, bg_color):
        """绘制检测框标签"""
        self._draw_label_above_rect(painter, x, y, label, bg_color)

    def _draw_box_handles(self, painter, x, y, width, height, color):
        """绘制检测框的四个调整手柄"""
        handle_size = DETECTION_BOX_CONFIG['resize_handle_size']

        painter.fillRect(int(x), int(y), handle_size, handle_size, color)
        painter.fillRect(int(x + width - handle_size), int(y), handle_size, handle_size, color)
        painter.fillRect(int(x), int(y + height - handle_size), handle_size, handle_size, color)
        painter.fillRect(int(x + width - handle_size), int(y + height - handle_size),
                         handle_size, handle_size, color)

    def _draw_temp_box(self, painter):
        """绘制临时检测框（正在绘制中）"""
        if self.temp_draw_box is not None and self.draw_start_pos is not None:
            pen = QPen(QColor(0, 255, 0), 2, Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(self.temp_draw_box)

        if self.mouse_pos is not None:
            cross_pen = QPen(QColor(0, 255, 128), 1, Qt.DashLine)
            painter.setPen(cross_pen)

            painter.drawLine(
                QPointF(0, self.mouse_pos.y()),
                QPointF(self.width(), self.mouse_pos.y())
            )
            painter.drawLine(
                QPointF(self.mouse_pos.x(), 0),
                QPointF(self.mouse_pos.x(), self.height())
            )
