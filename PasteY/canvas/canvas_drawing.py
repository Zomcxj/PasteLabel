"""
Canvas 绘制逻辑 - 检测框的创建、拖动、缩放
"""
from PyQt5.QtWidgets import QInputDialog
from PyQt5.QtCore import Qt, QRectF, QSizeF


class CanvasDrawingMixin:
    """检测框绘制、拖动、缩放"""

    def _handle_drawing_press(self, mouse_pos):
        if (not self._editor.background_images or
            self._editor.current_background_index < 0):
            return True

        background_rect = self.get_background_rect()
        if not background_rect or not background_rect.contains(mouse_pos):
            return True

        if self.draw_start_pos is None:
            self.draw_start_pos = mouse_pos
            self.temp_draw_box = QRectF(mouse_pos, QSizeF())
            self.selected_box = None
            self._editor.selected_item = None
            self.update_status_label()
            self.update()
        else:
            self._complete_drawing(mouse_pos)

        return True

    def _complete_drawing(self, mouse_pos):
        from ..ui.dialogs import LabelSelectionDialog

        background_rect = self.get_background_rect()
        if background_rect is None:
            return

        self._editor.save_undo_state()
        constrained_pos = self._constrain_to_background(mouse_pos, background_rect)

        x1 = min(self.draw_start_pos.x(), constrained_pos.x())
        y1 = min(self.draw_start_pos.y(), constrained_pos.y())
        x2 = max(self.draw_start_pos.x(), constrained_pos.x())
        y2 = max(self.draw_start_pos.y(), constrained_pos.y())

        self.temp_draw_box = QRectF(x1, y1, x2 - x1, y2 - y1)

        x = (self.temp_draw_box.left() - background_rect.left()) / self.background_scale
        y = (self.temp_draw_box.top() - background_rect.top()) / self.background_scale
        width = self.temp_draw_box.width() / self.background_scale
        height = self.temp_draw_box.height() / self.background_scale

        self.update_status_label()

        if (x <= 0 and y <= 0) or width <= 3 or height <= 3:
            self._reset_drawing_state()
            return

        label_items = []
        for i in range(self._editor.label_list.count()):
            label_items.append(self._editor.label_list.item(i).text())

        selected_label = LabelSelectionDialog.select_label(
            self, label_items, anchor_rect=self.temp_draw_box
        )

        if selected_label:
            self._create_detection_box(x, y, width, height, selected_label)

        self._reset_drawing_state()

    def _constrain_to_background(self, pos, background_rect):
        constrained = pos
        constrained.setX(max(background_rect.left(), min(constrained.x(), background_rect.right())))
        constrained.setY(max(background_rect.top(), min(constrained.y(), background_rect.bottom())))
        return constrained

    def _create_detection_box(self, x, y, width, height, label):
        x = max(0, x)
        y = max(0, y)
        width = max(1, width)
        height = max(1, height)

        new_box = {"x": x, "y": y, "width": width, "height": height, "label": label}
        self._editor.detection_boxes.append(new_box)

        if self._editor.current_background_index >= 0:
            self._sync_all_detection_boxes_to_dict()

        self._editor.update_label_list()
        self._save_current_detection_boxes()

    def _reset_drawing_state(self):
        self.draw_start_pos = None
        self.temp_draw_box = None
        self.is_drawing_box = False
        self.setCursor(Qt.ArrowCursor)

        if hasattr(self._editor, 'draw_box_btn'):
            sc = self._editor._get_shortcut('draw_box')
            self._editor.draw_box_btn.setText(f"绘制 BOX({sc})")

        self.update()

    def _save_current_detection_boxes(self):
        if self._editor.current_background and self._editor.current_background_index >= 0:
            import os
            background_path = self._editor.background_images[self._editor.current_background_index]
            background_name = os.path.basename(background_path)
            self._editor.save_json(background_path, background_name, "", canvas_items=[])

    def _sync_detection_box_to_dict(self, box_index):
        idx = self._editor.current_background_index
        if idx in self._editor.detection_boxes_dict:
            self._editor.detection_boxes_dict[idx][box_index] = \
                self._editor.detection_boxes[box_index].copy()

    def _sync_all_detection_boxes_to_dict(self):
        idx = self._editor.current_background_index
        if idx >= 0:
            self._editor.detection_boxes_dict[idx] = self._editor.detection_boxes.copy()

    def _drag_box(self):
        delta = self.mouse_pos - self.box_drag_start
        bg_rect = self.get_background_rect()

        if bg_rect:
            dx = delta.x() / self.background_scale
            dy = delta.y() / self.background_scale
            box = self._editor.detection_boxes[self.selected_box]

            nx = box["x"] + dx
            ny = box["y"] + dy

            if self._editor.current_background:
                bw = self._editor.current_background.width()
                bh = self._editor.current_background.height()
                nx = max(0, min(nx, bw - box["width"]))
                ny = max(0, min(ny, bh - box["height"]))

            box["x"] = nx
            box["y"] = ny
            self.box_drag_start = self.mouse_pos

            self._sync_detection_box_to_dict(self.selected_box)
            self._needs_save = True
            self.update()

    def _resize_box(self):
        delta = self.mouse_pos - self.box_resize_start
        bg_rect = self.get_background_rect()

        if bg_rect:
            dx = delta.x() / self.background_scale
            dy = delta.y() / self.background_scale
            box = self._editor.detection_boxes[self.selected_box]
            x, y, w, h = box["x"], box["y"], box["width"], box["height"]

            nx, ny, nw, nh = x, y, w, h

            if self.resize_handle == "br":
                nw = max(10, w + dx)
                nh = max(10, h + dy)
            elif self.resize_handle == "tl":
                nx = max(0, min(x + dx, x + w - 10))
                ny = max(0, min(y + dy, y + h - 10))
                nw = w + x - nx
                nh = h + y - ny
            elif self.resize_handle == "tr":
                nw = max(10, w + dx)
                ny = max(0, min(y + dy, y + h - 10))
                nh = h + y - ny
            elif self.resize_handle == "bl":
                nx = max(0, min(x + dx, x + w - 10))
                nw = w + x - nx
                nh = max(10, h + dy)

            box["x"], box["y"], box["width"], box["height"] = nx, ny, nw, nh
            self.box_resize_start = self.mouse_pos

            self._sync_detection_box_to_dict(self.selected_box)
            self._needs_save = True
            self.update()

    def _check_box_handle(self, mouse_pos, x, y, width, height, box_index):
        handle_size = 8

        handles = {
            "br": (x + width, y + height),
            "tl": (x, y),
            "tr": (x + width, y),
            "bl": (x, y + height),
        }

        for handle_name, (hx, hy) in handles.items():
            handle_rect = QRectF(
                hx - handle_size if 'r' in handle_name else hx,
                hy - handle_size if 'b' in handle_name else hy,
                handle_size, handle_size
            )

            if handle_rect.contains(mouse_pos):
                self.selected_box = box_index
                self.box_resize_start = mouse_pos
                self.is_resizing_box = True
                self.resize_handle = handle_name
                self._editor.selected_item = None
                self.selected_item_size = None
                self.update_status_label()
                self.update()
                return True

        return False
