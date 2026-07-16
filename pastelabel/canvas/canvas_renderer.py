"""
Canvas 绘制混入 - 负责所有绘制逻辑（背景、贴图、检测框、临时框、网格）
"""
from PyQt5.QtGui import QPainter, QPixmap, QColor, QPen, QFontMetrics
from PyQt5.QtCore import Qt, QPointF, QRectF

from ..core.config import DETECTION_BOX_CONFIG, PASTE_ITEM_CONFIG, GRID_CONFIG, MAGNIFIER_CONFIG, CROSSHAIR_CONFIG
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

        if self._editor.current_background is not None and background_rect:
            self._draw_background(painter, background_rect)

        if background_rect:
            self._draw_grid(painter, background_rect)

        if background_rect:
            self._draw_paste_items(painter, background_rect)

        if (self._editor.show_labels_checkbox.isChecked() and
            background_rect and self._editor.detection_boxes):
            self._draw_detection_boxes(painter, background_rect)

        if self.is_drawing_box:
            self._draw_temp_box(painter)

        if (getattr(self._editor, 'edit_mode', 'paste') == 'annotate' and
                self.mouse_inside and self._editor.current_background is not None and
                background_rect is not None):
            self._draw_crosshair(painter)

        if background_rect:
            self._draw_magnifier(painter, background_rect)

    def _draw_background(self, painter, background_rect):
        """绘制背景图"""
        painter.drawPixmap(
            int(background_rect.left()),
            int(background_rect.top()),
            int(background_rect.width()),
            int(background_rect.height()),
            self._editor.current_background
        )

    def _draw_grid(self, painter, background_rect):
        """绘制网格参考线"""
        if not self._editor.show_grid_checkbox.isChecked():
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

        pen = QPen(QColor(r, g, b, GRID_CONFIG.get('alpha', 120)))
        pen.setWidth(GRID_CONFIG.get('line_width', 1))
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
        for i, (pixmap, rect, label) in enumerate(self._editor.canvas_items):
            item_x = (rect.x() * self.background_scale) + background_rect.left()
            item_y = (rect.y() * self.background_scale) + background_rect.top()
            item_width = rect.width() * self.background_scale
            item_height = rect.height() * self.background_scale

            item_rect = QRectF(item_x, item_y, item_width, item_height)
            is_selected = (i == self._editor.selected_item)

            is_pressed_label = self._is_pressed_label({"label": label})
            self._draw_single_paste_item(
                painter, pixmap, item_rect, label, is_selected, is_pressed_label, i
            )

    def _get_box_border_pen(self, border_color, is_selected):
        from ..core.config import BOX_BORDER_CONFIG
        w = max(1, min(4, float(BOX_BORDER_CONFIG['width'])))
        pen_width = w * 1.5 if is_selected else w
        pen_width = max(1, min(4, pen_width))
        return QPen(border_color, pen_width)

    def _draw_single_paste_item(self, painter, pixmap, item_rect, label, is_selected, is_pressed_label, item_index=0):
        """绘制单个贴图"""
        item_x = item_rect.left()
        item_y = item_rect.top()
        item_width = item_rect.width()
        item_height = item_rect.height()

        label_color_hex = self._editor.get_label_color(label)
        lr = int(label_color_hex[1:3], 16)
        lg = int(label_color_hex[3:5], 16)
        lb = int(label_color_hex[5:7], 16)

        if is_selected or is_pressed_label:
            border_color = QColor(255, 255, 255)
        else:
            border_color = QColor(lr, lg, lb)
        pen = self._get_box_border_pen(border_color, is_selected or is_pressed_label)
        painter.setPen(pen)
        rx, ry = int(item_x), int(item_y)
        rw = int(item_x + item_width) - rx
        rh = int(item_y + item_height) - ry
        painter.drawRect(rx, ry, rw, rh)

        if is_selected or is_pressed_label:
            self._draw_paste_with_overlay(painter, pixmap, item_rect, label, 155)
        else:
            self._draw_paste_with_overlay(painter, pixmap, item_rect, label, 60)

        if is_selected:
            is_handle_hovered = (
                self.hover_resize_target == 'item' and
                self.hover_resize_handle == 'br'
            )
            self._draw_resize_handle(painter, item_rect, QColor(255, 255, 255), QColor(lr, lg, lb), is_handle_hovered)

        self._draw_paste_label(painter, item_x, item_y, label, is_selected, item_index)

    def _draw_paste_with_overlay(self, painter, pixmap, item_rect, label, fill_alpha):
        """绘制带标签色透明覆盖层的贴图。"""
        temp_pixmap = QPixmap(int(item_rect.width()), int(item_rect.height()))
        temp_pixmap.fill(Qt.transparent)
        temp_painter = QPainter(temp_pixmap)

        temp_painter.drawPixmap(
            0, 0, int(item_rect.width()), int(item_rect.height()), pixmap
        )

        color = QColor(self._editor.get_label_color(label))
        overlay_color = QColor(color.red(), color.green(), color.blue(), fill_alpha)
        temp_painter.fillRect(
            0, 0, int(item_rect.width()), int(item_rect.height()), overlay_color
        )
        temp_painter.end()

        painter.drawPixmap(
            int(item_rect.left()), int(item_rect.top()),
            temp_pixmap
        )

    def _draw_resize_handle(self, painter, item_rect, stroke_color, fill_color, is_hovered=False):
        """绘制右下角缩放手柄；悬停时显示白色正方形命中范围。"""
        size = PASTE_ITEM_CONFIG['handle_size']
        radius = size / 2
        br_handle = item_rect.bottomRight()

        painter.save()
        if is_hovered:
            painter.setPen(QPen(stroke_color, 2))
            painter.setBrush(QColor(255, 255, 255))
            painter.drawRect(QRectF(br_handle.x() - radius, br_handle.y() - radius, size, size))
        else:
            # 1. 白色底层——减去贴图区域，只留贴图外部分
            from PyQt5.QtGui import QPainterPath
            circle = QPainterPath()
            circle.addEllipse(br_handle, radius * 1.3, radius * 1.3)
            item = QPainterPath()
            item.addRect(item_rect)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 255, 255))
            painter.drawPath(circle.subtracted(item))
            # 2. 常态句柄覆盖（标签色）
            painter.setPen(QPen(fill_color, 1))
            painter.setBrush(fill_color)
            painter.drawEllipse(br_handle, radius, radius)
        painter.restore()

    @staticmethod
    def _draw_label_above_rect(painter, x, y, label, bg_color, font_size=None, position='outside'):
        """在矩形上方或内侧绘制标签（背景 + 文字）"""
        painter.save()
        font = painter.font()
        if font_size is not None:
            font.setPointSize(font_size)
        painter.setFont(font)
        metrics = QFontMetrics(font)
        text_width = metrics.horizontalAdvance(label)
        text_height = metrics.height()
        padding_x = 2

        label_y = int(y) if position == 'inside' else int(y) - text_height
        label_rect = QRectF(int(x), label_y, text_width + padding_x * 2, text_height)
        painter.fillRect(label_rect, bg_color)
        painter.setPen(QColor(0, 0, 0))
        text_rect = label_rect.adjusted(padding_x, 0, -padding_x, 0)
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, label)
        painter.restore()

    def _draw_paste_label(self, painter, x, y, label, is_selected, item_index=0):
        """绘制贴图标签"""
        if not self._editor.show_paste_names_checkbox.isChecked():
            return
        label_color_hex = self._editor.get_label_color(label)
        lr = int(label_color_hex[1:3], 16)
        lg = int(label_color_hex[3:5], 16)
        lb = int(label_color_hex[5:7], 16)
        bg_color = QColor(lr, lg, lb)
        self._draw_label_above_rect(painter, x, y, label, bg_color)

    def _draw_detection_boxes(self, painter, background_rect):
        """绘制所有检测框"""
        for i, box in enumerate(self._editor.detection_boxes):
            if box["width"] <= 0 or box["height"] <= 0:
                continue

            box_x = box["x"] * self.background_scale + background_rect.left()
            box_y = box["y"] * self.background_scale + background_rect.top()
            box_width = box["width"] * self.background_scale
            box_height = box["height"] * self.background_scale

            is_selected = (i == self.selected_box or i in getattr(self, 'selected_boxes', []))
            is_pressed_label = self._is_pressed_label(box)

            self._draw_single_detection_box(
                painter, box_x, box_y, box_width, box_height,
                box.get("label", ""), is_selected, is_pressed_label
            )

    def _is_pressed_label(self, box):
        """检查检测框是否是当前按下的标签"""
        if not hasattr(self._editor, 'pressed_label') or self._editor.pressed_label is None:
            return False
        return box.get('label') == self._editor.pressed_label

    def _draw_single_detection_box(self, painter, x, y, width, height, label,
                                    is_selected, is_pressed_label):
        """绘制单个检测框"""
        label_color_hex = self._editor.get_label_color(label)
        lr = int(label_color_hex[1:3], 16)
        lg = int(label_color_hex[3:5], 16)
        lb = int(label_color_hex[5:7], 16)

        fill_alpha = 155 if is_selected or is_pressed_label else 60
        fill_color = QColor(lr, lg, lb, fill_alpha)
        if is_selected or is_pressed_label:
            border_color = QColor(255, 255, 255)
        else:
            border_color = QColor(lr, lg, lb)
        pen = self._get_box_border_pen(border_color, is_selected or is_pressed_label)
        painter.setPen(pen)
        rx, ry = int(x), int(y)
        rw = int(x + width) - rx
        rh = int(y + height) - ry
        painter.drawRect(rx, ry, rw, rh)
        painter.fillRect(rx, ry, rw, rh, fill_color)

        if label and getattr(self._editor, 'show_label_names_checkbox', None) and self._editor.show_label_names_checkbox.isChecked():
            label_bg = QColor(lr, lg, lb)
            self._draw_box_label(painter, x, y, label, label_bg)

        if is_selected:
            handle_stroke = QColor(255, 255, 255)
            handle_fill = QColor(lr, lg, lb)
            self._draw_box_handles(painter, x, y, width, height, handle_stroke, handle_fill)

    def _draw_box_label(self, painter, x, y, label, bg_color):
        """绘制检测框标签"""
        font_size = max(5, min(15, DETECTION_BOX_CONFIG.get('label_font_size', 9)))
        position = DETECTION_BOX_CONFIG.get('label_position', 'outside')
        if position not in ('outside', 'inside'):
            position = 'outside'
        self._draw_label_above_rect(painter, x, y, label, bg_color, font_size, position)

    def _draw_box_handles(self, painter, x, y, width, height, stroke_color, fill_color):
        """绘制检测框四个角的调整手柄；悬停时显示白色正方形命中范围。"""
        size = DETECTION_BOX_CONFIG['resize_handle_size']
        radius = size / 2
        corners = (
            ('tl', QPointF(x, y)),
            ('tr', QPointF(x + width, y)),
            ('bl', QPointF(x, y + height)),
            ('br', QPointF(x + width, y + height)),
        )

        painter.save()
        for handle_name, corner in corners:
            is_hovered = (
                self.hover_resize_target == 'box' and
                self.hover_resize_handle == handle_name
            )
            if is_hovered:
                painter.setPen(QPen(stroke_color, 2))
                painter.setBrush(QColor(255, 255, 255))
                painter.drawRect(QRectF(corner.x() - radius, corner.y() - radius, size, size))
            else:
                # 1. 白色底层——减去框区域，只留框外部分
                from PyQt5.QtGui import QPainterPath
                circle = QPainterPath()
                circle.addEllipse(corner, radius * 1.3, radius * 1.3)
                box = QPainterPath()
                box.addRect(QRectF(x, y, width, height))
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(255, 255, 255))
                painter.drawPath(circle.subtracted(box))
                # 2. 常态句柄覆盖（标签色）
                painter.setPen(QPen(fill_color, 1))
                painter.setBrush(fill_color)
                painter.drawEllipse(corner, radius, radius)
        painter.restore()

    def _draw_temp_box(self, painter):
        """绘制临时检测框（正在绘制中）"""
        if self.temp_draw_box is not None and self.draw_start_pos is not None:
            crosshair = CROSSHAIR_CONFIG.get('color', '#00FF80')
            pen = QPen(QColor(crosshair), 2, Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(self.temp_draw_box)


    def _draw_crosshair(self, painter):
        """绘制标注模式的鼠标十字虚线。"""
        color = QColor(CROSSHAIR_CONFIG.get('color', '#00FF80'))
        color.setAlpha(CROSSHAIR_CONFIG.get('alpha', 160))
        cross_pen = QPen(color, CROSSHAIR_CONFIG.get('width', 1), Qt.DashLine)
        painter.setPen(cross_pen)
        painter.drawLine(QPointF(0, self.mouse_pos.y()), QPointF(self.width(), self.mouse_pos.y()))
        painter.drawLine(QPointF(self.mouse_pos.x(), 0), QPointF(self.mouse_pos.x(), self.height()))

    def _draw_magnifier(self, painter, background_rect):
        if not getattr(self._editor, '_magnifier_enabled', False):
            return
        if getattr(self._editor, 'edit_mode', 'paste') != 'annotate':
            return
        always = MAGNIFIER_CONFIG.get('always_on', False)
        if not always and self.selected_box is None and not self.is_drawing_box:
            return
        if not self.mouse_inside or self.mouse_pos is None:
            return
        pixmap = self._editor.current_background
        if pixmap is None or pixmap.isNull() or not background_rect.contains(self.mouse_pos):
            return

        size = int(MAGNIFIER_CONFIG.get('size', 160))
        zoom = float(MAGNIFIER_CONFIG.get('zoom', 2.0))
        if size <= 0 or zoom <= 0:
            return

        src_size = max(1, int(size / zoom))
        orig_x = int((self.mouse_pos.x() - background_rect.left()) / self.background_scale)
        orig_y = int((self.mouse_pos.y() - background_rect.top()) / self.background_scale)
        src_x = max(0, min(pixmap.width() - src_size, orig_x - src_size // 2))
        src_y = max(0, min(pixmap.height() - src_size, orig_y - src_size // 2))

        margin = 18
        dst_x = self.mouse_pos.x() + margin
        dst_y = self.mouse_pos.y() + margin
        if dst_x + size > self.width():
            dst_x = self.mouse_pos.x() - margin - size
        if dst_y + size > self.height():
            dst_y = self.mouse_pos.y() - margin - size
        dst_x = max(0, min(self.width() - size, int(dst_x)))
        dst_y = max(0, min(self.height() - size, int(dst_y)))
        dst = QRectF(dst_x, dst_y, size, size)

        painter.save()
        painter.fillRect(dst, QColor(255, 255, 255, 210))
        painter.drawPixmap(dst, pixmap, QRectF(src_x, src_y, src_size, src_size))
        m_scale = size / src_size
        painter.setClipRect(dst)
        from ..core.config import BOX_BORDER_CONFIG
        m_bw = max(1, min(4, float(BOX_BORDER_CONFIG['width']))) * m_scale
        m_bw = max(0.5, m_bw)

        def _draw_single_box(bx, by, bw, bh, label):
            if bw <= 0 or bh <= 0:
                return
            if bx + bw < src_x or bx > src_x + src_size or by + bh < src_y or by > src_y + src_size:
                return
            lh = self._editor.get_label_color(label)
            mc = QColor(int(lh[1:3], 16), int(lh[3:5], 16), int(lh[5:7], 16))
            mx = dst.left() + (bx - src_x) * m_scale
            my = dst.top() + (by - src_y) * m_scale
            mw = bw * m_scale
            mh = bh * m_scale
            painter.setPen(QPen(mc, m_bw))
            painter.drawRect(QRectF(mx, my, mw, mh))

        for box in getattr(self._editor, 'detection_boxes', []):
            _draw_single_box(box["x"], box["y"], box["width"], box["height"], box.get("label", ""))
        # 编辑态中的框（拖拽/缩放中途）
        if (getattr(self, 'is_dragging_box', False) or getattr(self, 'is_resizing_box', False)):
            sb = getattr(self, 'selected_box', None)
            if sb is not None:
                _draw_single_box(sb["x"], sb["y"], sb["width"], sb["height"], sb.get("label", ""))
        for pix, item_rect, label in getattr(self._editor, 'canvas_items', []):
            ir = item_rect
            _draw_single_box(ir.x(), ir.y(), ir.width(), ir.height(), label)
        painter.setClipping(False)
        painter.setPen(QPen(QColor(60, 60, 60, 180), 1))
        painter.drawRect(dst)
        cross_color = QColor(CROSSHAIR_CONFIG.get('color', '#00FF80'))
        cross_color.setAlpha(CROSSHAIR_CONFIG.get('alpha', 160))
        painter.setPen(QPen(cross_color, 1, Qt.DashLine))
        center_x = dst.left() + size / 2
        center_y = dst.top() + size / 2
        painter.drawLine(QPointF(center_x, dst.top()), QPointF(center_x, dst.bottom()))
        painter.drawLine(QPointF(dst.left(), center_y), QPointF(dst.right(), center_y))
        painter.restore()
