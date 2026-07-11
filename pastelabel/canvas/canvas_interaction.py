"""
Canvas 交互混入 - 鼠标/键盘事件入口、拖拽、缩放
"""
import os
from PyQt5.QtCore import Qt, QRectF, QUrl, QMimeData
from PyQt5.QtGui import QDrag

from ..core.config import BACKGROUND_SCALE_CONFIG, PASTE_ITEM_CONFIG, NUDGE_CONFIG, DETECTION_BOX_WHEEL_CONFIG
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
        self._drag_out_pending = False
        self.update()
        super().leaveEvent(event)

    def _do_canvas_drag_out(self):
        """延迟执行 Canvas 拖出复制"""
        if not getattr(self._editor, '_canvas_image_copy_enabled', False):
            self._drag_out_pending = False
            return
        from PyQt5.QtGui import QCursor
        global_pos = QCursor.pos()
        main_win = self._editor
        if not main_win.geometry().contains(main_win.mapFromGlobal(global_pos)):
            file_path = self._editor.background_images[self._editor.current_background_index]
            if os.path.isfile(file_path):
                drag = QDrag(self)
                mime = QMimeData()
                mime.setUrls([QUrl.fromLocalFile(file_path)])
                drag.setMimeData(mime)
                drag.exec_(Qt.CopyAction)

    def mousePressEvent(self, event):
        self.setFocus()
        mouse_pos = event.pos()

        if self.is_drawing_box and event.button() == Qt.LeftButton:
            self._drag_out_pending = False
            if self._handle_drawing_press(mouse_pos):
                return

        if event.button() == Qt.RightButton:
            self._drag_out_pending = False
            if self._handle_right_click(mouse_pos):
                return
        elif event.button() != Qt.LeftButton:
            self._drag_out_pending = False
            return

        self._drag_out_pending = (
            getattr(self._editor, '_canvas_image_copy_enabled', False)
            and not self.is_drawing_box
            and not self.is_dragging_background
            and not self.is_dragging_box
            and not self.is_dragging_item
            and not self.is_manual_scale
            and self.background_scale <= 1.0
            and self.find_item_at_position(mouse_pos) is None
        )
        self._handle_left_click(mouse_pos)
        if self.is_dragging_box or self.is_resizing_box:
            self._drag_out_pending = False

    def _handle_left_click(self, mouse_pos):
        is_annotate = getattr(self._editor, 'edit_mode', 'paste') == 'annotate'

        if is_annotate:
            if self._editor.show_labels_checkbox.isChecked() and self._editor.current_background:
                if self._handle_detection_box_click(mouse_pos):
                    return
            item_at_pos = self.find_item_at_position(mouse_pos)
            if item_at_pos is not None:
                self._handle_item_click(item_at_pos, mouse_pos)
                return
        else:
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
        self.hover_resize_target = None
        self.hover_resize_handle = None
        self.selected_box = None
        self.selected_boxes = []
        _, rect, _ = self._editor.canvas_items[item_index]

        if self._editor.selected_item != item_index:
            self._editor.selected_item = item_index
            self.selected_item_size = (rect.width(), rect.height())
            self.update()

        if self._check_resize_handle(mouse_pos, rect):
            self.setCursor(Qt.ClosedHandCursor)
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
            self.setCursor(Qt.ClosedHandCursor)

    def _check_resize_handle(self, mouse_pos, rect):
        handle_name = self._item_handle_at_pos(mouse_pos, rect)
        if handle_name:
            self.resize_handle = handle_name
            self.resize_start = mouse_pos
            self.hover_resize_target = 'item'
            self.hover_resize_handle = handle_name
            return True

        return False

    def _item_handle_at_pos(self, mouse_pos, rect):
        """返回鼠标所在的贴图圆形缩放手柄名称，不修改编辑状态。"""
        if not self._editor.current_background:
            return None

        background_rect = self.get_background_rect()
        if background_rect is None:
            return None
        item_x = (rect.x() * self.background_scale) + background_rect.left()
        item_y = (rect.y() * self.background_scale) + background_rect.top()
        item_width = rect.width() * self.background_scale
        item_height = rect.height() * self.background_scale
        item_rect = QRectF(item_x, item_y, item_width, item_height)

        handle_size = PASTE_ITEM_CONFIG['handle_size']
        br_handle = item_rect.bottomRight()

        handle_rect = QRectF(
            br_handle.x() - handle_size / 2,
            br_handle.y() - handle_size / 2,
            handle_size,
            handle_size,
        )
        if handle_rect.contains(mouse_pos):
            return 'br'

        return None

    def _handle_detection_box_click(self, mouse_pos):
        background_rect = self.get_background_rect()
        if not background_rect:
            return False

        ctrl_pressed = bool(self._current_modifiers() & Qt.ControlModifier)

        for i, box in enumerate(self._editor.detection_boxes):
            box_x = box["x"] * self.background_scale + background_rect.left()
            box_y = box["y"] * self.background_scale + background_rect.top()
            box_width = box["width"] * self.background_scale
            box_height = box["height"] * self.background_scale

            if self._check_box_handle(mouse_pos, box_x, box_y, box_width, box_height, i):
                return True

            box_rect = QRectF(box_x, box_y, box_width, box_height)
            if box_rect.contains(mouse_pos):
                self.hover_resize_target = None
                self.hover_resize_handle = None
                self._editor.selected_item = None
                self.selected_item_size = None

                if ctrl_pressed:
                    self._toggle_box_selection(i)
                    self.update_status_label()
                    self.update()
                    return True

                self._editor.save_undo_state()
                self.selected_boxes = [i]
                self.selected_box = i
                self.box_drag_start = mouse_pos
                self.is_dragging_box = True
                self.setCursor(Qt.ClosedHandCursor)
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
        self.selected_boxes = []
        self.hover_resize_target = None
        self.hover_resize_handle = None
        self.setCursor(Qt.ArrowCursor)
        self.update_status_label()
        self.update()

    def _toggle_box_selection(self, box_index):
        if box_index in self.selected_boxes:
            self.selected_boxes = [idx for idx in self.selected_boxes if idx != box_index]
        else:
            self.selected_boxes = [
                idx for idx in self.selected_boxes
                if 0 <= idx < len(self._editor.detection_boxes)
            ]
            self.selected_boxes.append(box_index)

        self.selected_box = self.selected_boxes[-1] if self.selected_boxes else None
        self.is_dragging_box = False
        self.is_resizing_box = False
        self.resize_handle = None

    def _current_modifiers(self):
        app = getattr(self._editor, 'app', None)
        if app is not None and hasattr(app, 'keyboardModifiers'):
            return app.keyboardModifiers()

        from PyQt5.QtWidgets import QApplication
        return QApplication.keyboardModifiers()

    def _do_canvas_drag_out(self):
        """检测鼠标是否离开窗口，触发拖出复制"""
        if not getattr(self._editor, '_canvas_image_copy_enabled', False):
            self._drag_out_pending = False
            return
        from PyQt5.QtGui import QCursor
        global_pos = QCursor.pos()
        main_win = self._editor
        if not main_win.geometry().contains(main_win.mapFromGlobal(global_pos)):
            idx = self._editor.current_background_index
            if idx >= 0 and idx < len(self._editor.background_images):
                file_path = self._editor.background_images[idx]
                if os.path.isfile(file_path):
                    self._editor._canvas_drag_active = True
                    drag = QDrag(self)
                    mime = QMimeData()
                    mime.setUrls([QUrl.fromLocalFile(file_path)])
                    drag.setMimeData(mime)
                    self._drag_out_pending = False
                    drag.exec_(Qt.CopyAction)
                    self._editor._canvas_drag_active = False

    def mouseMoveEvent(self, event):
        self.mouse_pos = event.pos()
        self.update_status_label()

        if self._drag_out_pending:
            from PyQt5.QtGui import QCursor
            global_pos = QCursor.pos()
            main_win = self._editor
            if not main_win.geometry().contains(main_win.mapFromGlobal(global_pos)):
                self._do_canvas_drag_out()
                return

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
            self.setCursor(Qt.ClosedHandCursor)
            delta = self.mouse_pos - self.drag_start
            self.background_offset += delta
            self.drag_start = self.mouse_pos
            self.update()
            return

        if self.is_dragging_box and self.selected_box is not None:
            self.setCursor(Qt.ClosedHandCursor)
            self._drag_box()
            return

        if self.is_resizing_box and self.selected_box is not None:
            self.setCursor(Qt.ClosedHandCursor)
            self._resize_box()
            return

        if self.is_dragging_item and self._editor.selected_item is not None:
            self.setCursor(Qt.ClosedHandCursor)
            self._drag_item()
            return

        if self.resize_handle and self._editor.selected_item is not None:
            self.setCursor(Qt.ClosedHandCursor)
            self._scale_item()
            return

        self._check_hover()
        self.update()

    def _check_hover(self):
        """更新悬停状态。

        保持原有进入编辑状态方式：贴图点击进入；标注框鼠标移上去进入。
        同时只在当前编辑对象的缩放手柄上显示高亮提示。
        """
        old_target = self.hover_resize_target
        old_handle = self.hover_resize_handle
        self.hover_resize_target = None
        self.hover_resize_handle = None

        if self._editor.current_background is None or self._editor.current_background_index < 0:
            if (old_target, old_handle) != (self.hover_resize_target, self.hover_resize_handle):
                self.update()
            return

        bg_rect = self.get_background_rect()
        if bg_rect is None:
            if (old_target, old_handle) != (self.hover_resize_target, self.hover_resize_handle):
                self.update()
            return

        is_annotate = getattr(self._editor, 'edit_mode', 'paste') == 'annotate'
        if (is_annotate and self._editor.show_labels_checkbox.isChecked() and
                self._select_hovered_detection_box(bg_rect)):
            pass
        elif not is_annotate and (item_index := self.find_item_at_position(self.mouse_pos)) is not None:
            _, rect, _ = self._editor.canvas_items[item_index]
            self._editor.selected_item = item_index
            self.selected_item_size = (rect.width(), rect.height())
            self.selected_box = None
            self.selected_boxes = []
            self.setCursor(Qt.OpenHandCursor)
        elif (self._editor.selected_item is not None and
            0 <= self._editor.selected_item < len(self._editor.canvas_items)):
            _, rect, _ = self._editor.canvas_items[self._editor.selected_item]
            handle = self._item_handle_at_pos(self.mouse_pos, rect)
            if handle:
                self.hover_resize_target = 'item'
                self.hover_resize_handle = handle
                self.setCursor(Qt.PointingHandCursor)
            elif self._item_rect_contains(rect, self.mouse_pos):
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
        elif (self.selected_box is not None and
              0 <= self.selected_box < len(self._editor.detection_boxes)):
            handle = self._box_handle_at_pos(self.mouse_pos, self.selected_box)
            if handle:
                self.hover_resize_target = 'box'
                self.hover_resize_handle = handle
                self.setCursor(Qt.PointingHandCursor)
            elif self._box_rect_contains(self.selected_box, self.mouse_pos):
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

        if (old_target, old_handle) != (self.hover_resize_target, self.hover_resize_handle):
            self.update()

    def _select_hovered_detection_box(self, background_rect):
        """鼠标移入检测框即进入该框编辑状态。"""
        try:
            modifiers = self._current_modifiers()
        except AttributeError:
            modifiers = 0
        ctrl_pressed = bool(modifiers & Qt.ControlModifier)

        for i, box in enumerate(self._editor.detection_boxes):
            box_rect = QRectF(
                box["x"] * self.background_scale + background_rect.left(),
                box["y"] * self.background_scale + background_rect.top(),
                box["width"] * self.background_scale,
                box["height"] * self.background_scale,
            )

            if box_rect.contains(self.mouse_pos):
                handle = self._box_handle_at_pos(
                    self.mouse_pos, i,
                    box_rect.x(), box_rect.y(), box_rect.width(), box_rect.height()
                )
                selection_changed = self.selected_box != i
                if ctrl_pressed:
                    valid_indexes = [
                        idx for idx in self.selected_boxes
                        if 0 <= idx < len(self._editor.detection_boxes)
                    ]
                    if i not in valid_indexes:
                        valid_indexes.append(i)
                        selection_changed = True
                    self.selected_boxes = valid_indexes
                    self.selected_box = i
                else:
                    if self.selected_boxes != [i]:
                        selection_changed = True
                    self.selected_box = i
                    self.selected_boxes = [i]

                if selection_changed:
                    self._editor.selected_item = None
                    self.selected_item_size = None
                    self.update_status_label()

                if handle:
                    self.hover_resize_target = 'box'
                    self.hover_resize_handle = handle
                    self.setCursor(Qt.PointingHandCursor)
                else:
                    self.setCursor(Qt.OpenHandCursor)
                return True

        if self.selected_box is None or not (0 <= self.selected_box < len(self._editor.detection_boxes)):
            return False

        handle = self._box_handle_at_pos(self.mouse_pos, self.selected_box)
        if handle:
            self.hover_resize_target = 'box'
            self.hover_resize_handle = handle
            self.setCursor(Qt.PointingHandCursor)
            return True

        return False

    def _item_rect_contains(self, rect, mouse_pos):
        background_rect = self.get_background_rect()
        if background_rect is None:
            return False

        item_rect = QRectF(
            rect.x() * self.background_scale + background_rect.left(),
            rect.y() * self.background_scale + background_rect.top(),
            rect.width() * self.background_scale,
            rect.height() * self.background_scale,
        )
        return item_rect.contains(mouse_pos)

    def _box_rect_contains(self, box_index, mouse_pos):
        if box_index is None or not (0 <= box_index < len(self._editor.detection_boxes)):
            return False

        background_rect = self.get_background_rect()
        if background_rect is None:
            return False

        box = self._editor.detection_boxes[box_index]
        box_rect = QRectF(
            box["x"] * self.background_scale + background_rect.left(),
            box["y"] * self.background_scale + background_rect.top(),
            box["width"] * self.background_scale,
            box["height"] * self.background_scale,
        )
        return box_rect.contains(mouse_pos)

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
        self._drag_out_pending = False
        if self.is_dragging_box or self.is_resizing_box:
            if hasattr(self, '_needs_save') and self._needs_save:
                self._save_current_detection_boxes()
                self._needs_save = False

        self.is_dragging_item = False
        self.is_dragging_background = False
        self.is_dragging_box = False
        self.is_resizing_box = False
        self.resize_handle = None
        self._check_hover()
        self.update()

    def wheelEvent(self, event):
        if not self._editor.current_background:
            return

        if event.modifiers() & Qt.ControlModifier:
            self._scale_background(event)
        elif self._editor.selected_item is not None:
            self._scale_selected_item(event)
        elif self.selected_box is not None:
            if self._is_mouse_inside_selected_box():
                self._scale_selected_box(event)
            else:
                self._adjust_selected_box_edge(event)

        self.update()

    def _is_mouse_inside_selected_box(self):
        return self._box_rect_contains(self.selected_box, self.mouse_pos)

    def _get_mouse_pos_in_image_coords(self):
        background_rect = self.get_background_rect()
        if background_rect is None or not self.background_scale:
            return None
        return (
            (self.mouse_pos.x() - background_rect.left()) / self.background_scale,
            (self.mouse_pos.y() - background_rect.top()) / self.background_scale,
        )

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
        step = max(0.01, min(0.30, float(DETECTION_BOX_WHEEL_CONFIG.get('paste_item_scale_step', 0.15))))
        scale_factor = 1.0 + step if delta > 0 else max(0.1, 1.0 - step)

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
        step = max(0.01, min(0.30, float(DETECTION_BOX_WHEEL_CONFIG.get('detection_box_scale_step', 0.05))))
        scale_factor = 1.0 + step if delta > 0 else max(0.1, 1.0 - step)

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

    def _adjust_selected_box_edge(self, event):
        if (self.selected_box is None or
            self.selected_box >= len(self._editor.detection_boxes)):
            return

        box = self._editor.detection_boxes[self.selected_box]
        bg = self._editor.current_background
        min_width = 10
        min_height = 10
        edge_step = max(1, min(50, int(DETECTION_BOX_WHEEL_CONFIG.get('edge_step', 5))))
        step = edge_step if event.angleDelta().y() > 0 else -edge_step

        left = box["x"]
        top = box["y"]
        right = left + box["width"]
        bottom = top + box["height"]
        mouse_pos = self._get_mouse_pos_in_image_coords()
        if mouse_pos is None:
            return
        mouse_x, mouse_y = mouse_pos

        if mouse_x < left and top <= mouse_y <= bottom:
            nearest_edge = 'left'
        elif mouse_x > right and top <= mouse_y <= bottom:
            nearest_edge = 'right'
        elif mouse_y < top and left <= mouse_x <= right:
            nearest_edge = 'top'
        elif mouse_y > bottom and left <= mouse_x <= right:
            nearest_edge = 'bottom'
        else:
            distances = {
                'left': abs(mouse_x - left),
                'right': abs(mouse_x - right),
                'top': abs(mouse_y - top),
                'bottom': abs(mouse_y - bottom),
            }
            nearest_edge = min(distances, key=distances.get)

        if nearest_edge == 'left':
            new_left = max(0, min(left - step, right - min_width))
            box["x"] = new_left
            box["width"] = right - new_left
        elif nearest_edge == 'right':
            new_right = min(bg.width(), max(right + step, left + min_width))
            box["width"] = new_right - left
        elif nearest_edge == 'top':
            new_top = max(0, min(top - step, bottom - min_height))
            box["y"] = new_top
            box["height"] = bottom - new_top
        else:
            new_bottom = min(bg.height(), max(bottom + step, top + min_height))
            box["height"] = new_bottom - top

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

    def _nudge_selected(self, dx, dy):
        if self.selected_box is not None and 0 <= self.selected_box < len(self._editor.detection_boxes):
            box = self._editor.detection_boxes[self.selected_box]
            step = NUDGE_CONFIG['step']
            bg = self._editor.current_background
            bw = bg.width() if bg else 0
            bh = bg.height() if bg else 0
            nx = max(0, min(box["x"] + dx * step, bw - box["width"]))
            ny = max(0, min(box["y"] + dy * step, bh - box["height"]))
            box["x"] = nx
            box["y"] = ny
            self._sync_detection_box_to_dict(self.selected_box)
            self.update()
        elif self._editor.selected_item is not None and 0 <= self._editor.selected_item < len(self._editor.canvas_items):
            p, rect, label = self._editor.canvas_items[self._editor.selected_item]
            step = NUDGE_CONFIG['step']
            bg = self._editor.current_background
            bw = bg.width() if bg else 0
            bh = bg.height() if bg else 0
            nx = max(0, min(rect.x() + dx * step, bw - rect.width()))
            ny = max(0, min(rect.y() + dy * step, bh - rect.height()))
            nr = QRectF(nx, ny, rect.width(), rect.height())
            self._editor.canvas_items[self._editor.selected_item] = (p, nr, label)
            self.update()

    def keyPressEvent(self, event):
        super().keyPressEvent(event)

    def resizeEvent(self, event):
        self.update()
        super().resizeEvent(event)
