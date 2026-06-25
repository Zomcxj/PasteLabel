"""
Canvas 交互混入 - 鼠标/键盘事件入口、拖拽、缩放
"""
from PyQt5.QtCore import Qt, QRectF

from ..core.config import BACKGROUND_SCALE_CONFIG
from .canvas_drawing import CanvasDrawingMixin
from .canvas_menu import CanvasMenuMixin


class CanvasInteractionMixin(CanvasDrawingMixin, CanvasMenuMixin):
    """Canvas 交互混入类 - 事件入口 + 通用操作"""

    def enterEvent(self, event):
        self.mouse_inside = True
        self.update_status_label()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.mouse_inside = False
        self.update_status_label()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self.setFocus()
        mouse_pos = event.pos()

        if self.is_drawing_box and event.button() == Qt.LeftButton:
            if self._handle_drawing_press(mouse_pos):
                return

        if event.button() == Qt.RightButton:
            if self._handle_right_click(mouse_pos):
                return
        elif event.button() != Qt.LeftButton:
            return

        self._handle_left_click(mouse_pos)

    def _handle_left_click(self, mouse_pos):
        item_at_pos = self.find_item_at_position(mouse_pos)
        if item_at_pos is not None:
            self._handle_item_click(item_at_pos, mouse_pos)
            return

        if self._editor.show_labels_checkbox.isChecked() and self._editor.current_background:
            if self._handle_detection_box_click(mouse_pos):
                return

        if self._editor.current_background:
            if self._handle_background_click(mouse_pos):
                return

        self._clear_selection()

    def _handle_item_click(self, item_index, mouse_pos):
        self.selected_box = None
        _, rect, _ = self._editor.canvas_items[item_index]

        if self._editor.selected_item != item_index:
            self._editor.selected_item = item_index
            self.selected_item_size = (rect.width(), rect.height())
            self.update()

        if self._check_resize_handle(mouse_pos, rect):
            return

        background_rect = self.get_background_rect()
        if background_rect:
            item_x = (rect.x() * self.background_scale) + background_rect.left()
            item_y = (rect.y() * self.background_scale) + background_rect.top()
            item_rect = QRectF(item_x, item_y, rect.width() * self.background_scale,
                              rect.height() * self.background_scale)
            self._editor.save_undo_state()
            self.drag_start = mouse_pos - item_rect.topLeft()
            self.is_dragging_item = True

    def _check_resize_handle(self, mouse_pos, rect):
        if not self._editor.current_background:
            return False

        background_rect = self.get_background_rect()
        if background_rect is None:
            return False
        item_x = (rect.x() * self.background_scale) + background_rect.left()
        item_y = (rect.y() * self.background_scale) + background_rect.top()
        item_width = rect.width() * self.background_scale
        item_height = rect.height() * self.background_scale
        item_rect = QRectF(item_x, item_y, item_width, item_height)

        handle_size = 8
        br_handle = item_rect.bottomRight()

        if (abs(mouse_pos.x() - br_handle.x()) <= handle_size and
            abs(mouse_pos.y() - br_handle.y()) <= handle_size):
            self.resize_handle = 'br'
            self.resize_start = mouse_pos
            return True

        return False

    def _handle_detection_box_click(self, mouse_pos):
        background_rect = self.get_background_rect()
        if not background_rect:
            return False

        for i, box in enumerate(self._editor.detection_boxes):
            box_x = box["x"] * self.background_scale + background_rect.left()
            box_y = box["y"] * self.background_scale + background_rect.top()
            box_width = box["width"] * self.background_scale
            box_height = box["height"] * self.background_scale

            if self._check_box_handle(mouse_pos, box_x, box_y, box_width, box_height, i):
                return True

            box_rect = QRectF(box_x, box_y, box_width, box_height)
            if box_rect.contains(mouse_pos):
                self._editor.save_undo_state()
                self.selected_box = i
                self.box_drag_start = mouse_pos
                self.is_dragging_box = True
                self._editor.selected_item = None
                self.selected_item_size = None
                self.update_status_label()
                self.update()
                return True

        return False

    def _handle_background_click(self, mouse_pos):
        background_rect = self.get_background_rect()
        if not background_rect.contains(mouse_pos):
            return False

        scaled_width = self._editor.current_background.width() * self.background_scale
        scaled_height = self._editor.current_background.height() * self.background_scale

        if scaled_width > self.width() or scaled_height > self.height():
            self._clear_selection()
            self.drag_start = mouse_pos
            self.is_dragging_background = True
            return True

        self._clear_selection()
        self.update_status_label()
        self.update()
        return True

    def _clear_selection(self):
        self._editor.selected_item = None
        self.selected_item_size = None
        self.selected_box = None
        self.update_status_label()
        self.update()

    def mouseMoveEvent(self, event):
        self.mouse_pos = event.pos()
        self.update_status_label()

        if self.is_drawing_box:
            if self.draw_start_pos:
                bg_rect = self.get_background_rect()
                if bg_rect:
                    c = self._constrain_to_background(self.mouse_pos, bg_rect)
                    x1 = min(self.draw_start_pos.x(), c.x())
                    y1 = min(self.draw_start_pos.y(), c.y())
                    x2 = max(self.draw_start_pos.x(), c.x())
                    y2 = max(self.draw_start_pos.y(), c.y())
                    self.temp_draw_box = QRectF(x1, y1, x2 - x1, y2 - y1)
                else:
                    x1 = min(self.draw_start_pos.x(), self.mouse_pos.x())
                    y1 = min(self.draw_start_pos.y(), self.mouse_pos.y())
                    x2 = max(self.draw_start_pos.x(), self.mouse_pos.x())
                    y2 = max(self.draw_start_pos.y(), self.mouse_pos.y())
                    self.temp_draw_box = QRectF(x1, y1, x2 - x1, y2 - y1)
            self.update()
            return

        if self.is_dragging_background:
            delta = self.mouse_pos - self.drag_start
            self.background_offset += delta
            self.drag_start = self.mouse_pos
            self.update()
            return

        if self.is_dragging_box and self.selected_box is not None:
            self._drag_box()
            return

        if self.is_resizing_box and self.selected_box is not None:
            self._resize_box()
            return

        if self.is_dragging_item and self._editor.selected_item is not None:
            self._drag_item()
            return

        if self.resize_handle and self._editor.selected_item is not None:
            self._scale_item()
            return

        self._check_hover()
        self.update()

    def _check_hover(self):
        """检查鼠标悬停在贴图上时自动选中"""
        if self._editor.current_background is None or self._editor.current_background_index < 0:
            return

        bg_rect = self.get_background_rect()
        if bg_rect is None:
            return

        for i, (pixmap, rect, label) in enumerate(self._editor.canvas_items):
            ix = (rect.x() * self.background_scale) + bg_rect.left()
            iy = (rect.y() * self.background_scale) + bg_rect.top()
            iw = rect.width() * self.background_scale
            ih = rect.height() * self.background_scale
            item_rect = QRectF(ix, iy, iw, ih)

            if item_rect.contains(self.mouse_pos):
                if self._editor.selected_item != i:
                    self._editor.selected_item = i
                    self.selected_item_size = (rect.width(), rect.height())
                return

    def _drag_item(self):
        bg_rect = self.get_background_rect()
        if bg_rect:
            p, rect, label = self._editor.canvas_items[self._editor.selected_item]
            np = self.mouse_pos - self.drag_start
            nx = (np.x() - bg_rect.left()) / self.background_scale
            ny = (np.y() - bg_rect.top()) / self.background_scale

            nx = max(0, nx)
            ny = max(0, ny)

            if self._editor.current_background:
                bw = self._editor.current_background.width()
                bh = self._editor.current_background.height()
                nx = min(nx, bw - rect.width())
                ny = min(ny, bh - rect.height())

            nr = QRectF(nx, ny, rect.width(), rect.height())
            self._editor.canvas_items[self._editor.selected_item] = (p, nr, label)
            self.update()

    def _scale_item(self):
        if self._editor.current_background:
            p, rect, label = self._editor.canvas_items[self._editor.selected_item]
            nr = QRectF(rect)

            bg_rect = self.get_background_rect()
            if bg_rect is None:
                return
            ix = (rect.x() * self.background_scale) + bg_rect.left()
            iy = (rect.y() * self.background_scale) + bg_rect.top()
            iw = rect.width() * self.background_scale
            ih = rect.height() * self.background_scale

            if self.resize_handle == 'br':
                nw = self.mouse_pos.x() - ix
                nh = self.mouse_pos.y() - iy

                wr = max(0.01, nw / iw)
                hr = max(0.01, nh / ih)
                sr = min(wr, hr)

                new_w = rect.width() * sr
                new_h = rect.height() * sr

                min_edge = 10
                if new_w < new_h:
                    if new_w < min_edge:
                        new_w = min_edge
                        new_h = min_edge * (rect.height() / rect.width())
                else:
                    if new_h < min_edge:
                        new_h = min_edge
                        new_w = min_edge * (rect.width() / rect.height())

                if self._editor.current_background:
                    bw = self._editor.current_background.width()
                    bh = self._editor.current_background.height()
                    new_w = min(new_w, bw - rect.x())
                    new_h = min(new_h, bh - rect.y())

                nr.setWidth(new_w)
                nr.setHeight(new_h)

                self.selected_item_size = (new_w, new_h)

            self._editor.canvas_items[self._editor.selected_item] = (p, nr, label)
            self.update()

    def mouseReleaseEvent(self, event):
        if self.is_dragging_box or self.is_resizing_box:
            if hasattr(self, '_needs_save') and self._needs_save:
                self._save_current_detection_boxes()
                self._needs_save = False

        self.is_dragging_item = False
        self.is_dragging_background = False
        self.is_dragging_box = False
        self.is_resizing_box = False
        self.resize_handle = None
        self.update()

    def wheelEvent(self, event):
        if not self._editor.current_background:
            return

        if self._editor.selected_item is not None:
            self._scale_selected_item(event)
        elif self.selected_box is not None:
            self._scale_selected_box(event)
        elif event.modifiers() & Qt.ControlModifier:
            self._scale_background(event)

        self.update()

    @staticmethod
    def _clamp_size_with_aspect(new_w, new_h, orig_w, orig_h, min_size=10, max_size=None):
        if max_size is None:
            max_size = min_size * 100
        ratio = orig_h / orig_w if orig_w else 1.0
        if new_w < new_h:
            if new_w < min_size:
                new_w, new_h = min_size, min_size * ratio
            elif new_w > max_size:
                new_w, new_h = max_size, max_size * ratio
        else:
            if new_h < min_size:
                new_h, new_w = min_size, min_size / ratio
            elif new_h > max_size:
                new_h, new_w = max_size, max_size / ratio
        return new_w, new_h

    def _scale_selected_item(self, event):
        if (self._editor.selected_item is None or
            self._editor.selected_item >= len(self._editor.canvas_items)):
            return

        delta = event.angleDelta().y()
        scale_factor = 1.1 if delta > 0 else 0.9

        pixmap, rect, label = self._editor.canvas_items[self._editor.selected_item]

        new_width = rect.width() * scale_factor
        new_height = rect.height() * scale_factor

        bg_short_side = min(self._editor.current_background.width(),
                          self._editor.current_background.height())
        new_width, new_height = self._clamp_size_with_aspect(
            new_width, new_height,
            rect.width(), rect.height(),
            min_size=10, max_size=bg_short_side * 0.9
        )

        center_x = rect.center().x()
        center_y = rect.center().y()

        new_rect = QRectF(
            center_x - new_width / 2,
            center_y - new_height / 2,
            new_width, new_height
        )

        self._editor.canvas_items[self._editor.selected_item] = (pixmap, new_rect, label)
        self.selected_item_size = (new_width, new_height)

    def _scale_selected_box(self, event):
        if (self.selected_box is None or
            self.selected_box >= len(self._editor.detection_boxes)):
            return

        delta = event.angleDelta().y()
        scale_factor = 1.03 if delta > 0 else 0.97

        box = self._editor.detection_boxes[self.selected_box]
        x, y, width, height = box["x"], box["y"], box["width"], box["height"]

        new_width = width * scale_factor
        new_height = height * scale_factor

        bg_size = min(self._editor.current_background.width(),
                     self._editor.current_background.height())
        new_width, new_height = self._clamp_size_with_aspect(
            new_width, new_height,
            width, height,
            min_size=10, max_size=bg_size * 0.9
        )

        center_x = x + width / 2
        center_y = y + height / 2

        new_x = center_x - new_width / 2
        new_y = center_y - new_height / 2

        new_x = max(0, min(new_x, self._editor.current_background.width() - new_width))
        new_y = max(0, min(new_y, self._editor.current_background.height() - new_height))

        box["x"] = new_x
        box["y"] = new_y
        box["width"] = new_width
        box["height"] = new_height

        self._sync_detection_box_to_dict(self.selected_box)

    def _scale_background(self, event):
        delta = event.angleDelta().y()
        scale_factor = 1.1 if delta > 0 else 0.9

        self.background_scale *= scale_factor
        self.background_scale = max(
            BACKGROUND_SCALE_CONFIG['min_scale'],
            min(self.background_scale, BACKGROUND_SCALE_CONFIG['max_scale'])
        )
        self.is_manual_scale = True

    def keyPressEvent(self, event):
        from ..core.config import SHORTCUT_CONFIG

        def _match(action):
            shortcut = SHORTCUT_CONFIG.get(action, '')
            if not shortcut:
                return False
            parts = shortcut.split('+')
            key_str = parts[-1].strip()
            modifiers_str = '+'.join(parts[:-1]).strip() if len(parts) > 1 else ''

            key_map = {
                'Delete': 0x01000007, 'Q': 0x0051, 'F': 0x0046,
            }
            target_key = key_map.get(key_str)
            if target_key is None:
                return False
            if event.key() != target_key:
                return False
            modifiers = event.modifiers()
            expected = Qt.NoModifier
            if 'Ctrl' in modifiers_str:
                expected |= Qt.ControlModifier
            return modifiers == expected

        if _match('delete_selected') or event.key() == Qt.Key_E:
            if (self._editor.selected_item is not None and
                0 <= self._editor.selected_item < len(self._editor.canvas_items)):
                del self._editor.canvas_items[self._editor.selected_item]
                self._editor.selected_item = None
                self.selected_item_size = None
                self.update_status_label()
                self.update()
        elif _match('fit_view'):
            self.reset_view()
            self.update()
        elif _match('quit_draw'):
            if self.is_drawing_box:
                self.is_drawing_box = False
                self.draw_start_pos = None
                self.temp_draw_box = None
                self.setCursor(Qt.ArrowCursor)
                if hasattr(self._editor, 'draw_box_btn'):
                    self._editor.draw_box_btn.setText("绘制 BOX(W)")
                self.update()
        super().keyPressEvent(event)

    def resizeEvent(self, event):
        self.update()
        super().resizeEvent(event)
