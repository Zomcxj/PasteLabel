"""
Canvas 交互混入 - 负责所有鼠标/键盘事件处理、拖拽、缩放、右键菜单
"""
import os
from PyQt5.QtWidgets import QMenu, QAction, QInputDialog
from PyQt5.QtCore import Qt, QPoint, QRectF, QSizeF

from .config import BACKGROUND_SCALE_CONFIG
from .utils import extract_label_name


class CanvasInteractionMixin:
    """Canvas 交互混入类 - 所有事件处理方法"""

    def enterEvent(self, event):
        """鼠标进入事件"""
        self.mouse_inside = True
        self.update_status_label()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标离开事件"""
        self.mouse_inside = False
        self.update_status_label()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """鼠标按下事件"""
        self._handle_mouse_press(event)

    def _handle_mouse_press(self, event):
        """处理鼠标按下事件的入口"""
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

    def _handle_drawing_press(self, mouse_pos):
        """处理绘制模式下的鼠标按下"""
        if (not self.parent.background_images or
            self.parent.current_background_index < 0):
            return True

        background_rect = self.get_background_rect()
        if not background_rect or not background_rect.contains(mouse_pos):
            return True

        if self.draw_start_pos is None:
            self.draw_start_pos = mouse_pos
            self.temp_draw_box = QRectF(mouse_pos, QSizeF())
            self.selected_box = None
            self.parent.selected_item = None
            self.update_status_label()
            self.update()
        else:
            self._complete_drawing(mouse_pos)

        return True

    def _complete_drawing(self, mouse_pos):
        """完成检测框绘制"""
        from .dialogs import LabelSelectionDialog

        background_rect = self.get_background_rect()
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
        for i in range(self.parent.label_list.count()):
            label_items.append(self.parent.label_list.item(i).text())

        selected_label = LabelSelectionDialog.select_label(self, label_items)

        if selected_label:
            self._create_detection_box(x, y, width, height, selected_label)

        self._reset_drawing_state()

    def _constrain_to_background(self, pos, background_rect):
        """限制位置在背景图范围内"""
        constrained = pos
        constrained.setX(max(background_rect.left(), min(constrained.x(), background_rect.right())))
        constrained.setY(max(background_rect.top(), min(constrained.y(), background_rect.bottom())))
        return constrained

    def _create_detection_box(self, x, y, width, height, label):
        """创建检测框并保存"""
        x = max(0, x)
        y = max(0, y)
        width = max(1, width)
        height = max(1, height)

        new_box = {"x": x, "y": y, "width": width, "height": height, "label": label}
        self.parent.detection_boxes.append(new_box)

        if self.parent.current_background_index >= 0:
            self._sync_all_detection_boxes_to_dict()

        self.parent.update_label_list()
        self._save_current_detection_boxes()

    def _reset_drawing_state(self):
        """重置绘制状态"""
        self.draw_start_pos = None
        self.temp_draw_box = None
        self.is_drawing_box = False
        self.setCursor(Qt.ArrowCursor)

        if hasattr(self.parent, 'draw_box_btn'):
            self.parent.draw_box_btn.setText("绘制 BOX(W)")

        self.update()

    def _handle_right_click(self, mouse_pos):
        """处理右键点击"""
        item_index = self.find_item_at_position(mouse_pos)
        if item_index is not None:
            self._show_paste_context_menu(item_index, mouse_pos)
            return True
        return False

    def _show_paste_context_menu(self, item_index, mouse_pos):
        """显示贴图右键菜单"""
        menu = QMenu(self)

        label_items = []
        for i in range(self.parent.paste_label_list.count()):
            label = self.parent.paste_label_list.item(i).text()
            pure_label = extract_label_name(label)
            label_items.append(pure_label)

        for label in label_items:
            action = QAction(label, self)
            action.triggered.connect(
                lambda checked, l=label, idx=item_index: self.change_item_label(idx, l)
            )
            menu.addAction(action)

        menu.addSeparator()

        new_label_action = QAction("添加新标签", self)
        new_label_action.triggered.connect(
            lambda checked, idx=item_index: self.add_new_label(idx)
        )
        menu.addAction(new_label_action)

        menu.exec_(QPoint(self.mapToGlobal(mouse_pos)))

    def _handle_left_click(self, mouse_pos):
        """处理左键点击"""
        item_at_pos = self.find_item_at_position(mouse_pos)
        if item_at_pos is not None:
            self._handle_item_click(item_at_pos, mouse_pos)
            return

        if self.parent.show_labels_checkbox.isChecked() and self.parent.current_background:
            if self._handle_detection_box_click(mouse_pos):
                return

        if self.parent.current_background:
            if self._handle_background_click(mouse_pos):
                return

        self._clear_selection()

    def _handle_item_click(self, item_index, mouse_pos):
        """处理贴图点击"""
        self.selected_box = None
        _, rect, _ = self.parent.canvas_items[item_index]

        if self.parent.selected_item != item_index:
            self.parent.selected_item = item_index
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
            self.drag_start = mouse_pos - item_rect.topLeft()
            self.is_dragging_item = True

    def _check_resize_handle(self, mouse_pos, rect):
        """检查是否点击了缩放手柄"""
        if not self.parent.current_background:
            return False

        background_rect = self.get_background_rect()
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
        """处理检测框点击"""
        background_rect = self.get_background_rect()
        if not background_rect:
            return False

        for i, box in enumerate(self.parent.detection_boxes):
            box_x = box["x"] * self.background_scale + background_rect.left()
            box_y = box["y"] * self.background_scale + background_rect.top()
            box_width = box["width"] * self.background_scale
            box_height = box["height"] * self.background_scale

            if self._check_box_handle(mouse_pos, box_x, box_y, box_width, box_height, i):
                return True

            box_rect = QRectF(box_x, box_y, box_width, box_height)
            if box_rect.contains(mouse_pos):
                self.selected_box = i
                self.box_drag_start = mouse_pos
                self.is_dragging_box = True
                self.parent.selected_item = None
                self.selected_item_size = None
                self.update_status_label()
                self.update()
                return True

        return False

    def _check_box_handle(self, mouse_pos, x, y, width, height, box_index):
        """检查是否点击了检测框的调整手柄"""
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
                self.parent.selected_item = None
                self.selected_item_size = None
                self.update_status_label()
                self.update()
                return True

        return False

    def _handle_background_click(self, mouse_pos):
        """处理背景图点击"""
        background_rect = self.get_background_rect()
        if not background_rect.contains(mouse_pos):
            return False

        scaled_width = self.parent.current_background.width() * self.background_scale
        scaled_height = self.parent.current_background.height() * self.background_scale

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
        """清除所有选择状态"""
        self.parent.selected_item = None
        self.selected_item_size = None
        self.selected_box = None
        self.update_status_label()
        self.update()

    def change_item_label(self, item_index, new_label):
        """更改贴图标签"""
        if 0 <= item_index < len(self.parent.canvas_items):
            pixmap, rect, _ = self.parent.canvas_items[item_index]
            self.parent.canvas_items[item_index] = (pixmap, rect, new_label)
            self.update()

    def add_new_label(self, item_index):
        """添加新标签到贴图"""
        new_label, ok = QInputDialog.getText(
            self, "添加新标签", "请输入新标签名称："
        )
        if ok and new_label.strip():
            new_label = new_label.strip()
            self.parent.paste_label_list.addItem(new_label)

            if 0 <= item_index < len(self.parent.canvas_items):
                pixmap, rect, _ = self.parent.canvas_items[item_index]
                self.parent.canvas_items[item_index] = (pixmap, rect, new_label)
                self.update()

    def _save_current_detection_boxes(self):
        """保存当前检测框到 JSON 文件"""
        if self.parent.current_background and self.parent.current_background_index >= 0:
            background_path = self.parent.background_images[self.parent.current_background_index]
            background_name = os.path.basename(background_path)
            self.parent.save_json(background_path, background_name, "", canvas_items=[])

    def _sync_detection_box_to_dict(self, box_index):
        """将指定检测框同步到 detection_boxes_dict"""
        idx = self.parent.current_background_index
        if idx in self.parent.detection_boxes_dict:
            self.parent.detection_boxes_dict[idx][box_index] = \
                self.parent.detection_boxes[box_index].copy()

    def _sync_all_detection_boxes_to_dict(self):
        """将当前所有检测框同步到 detection_boxes_dict"""
        idx = self.parent.current_background_index
        if idx >= 0:
            self.parent.detection_boxes_dict[idx] = self.parent.detection_boxes.copy()

    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
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

        if self.is_dragging_item and self.parent.selected_item is not None:
            self._drag_item()
            return

        if self.resize_handle and self.parent.selected_item is not None:
            self._scale_item()
            return

        self.update()

    def _drag_box(self):
        """拖动检测框"""
        delta = self.mouse_pos - self.box_drag_start
        bg_rect = self.get_background_rect()

        if bg_rect:
            dx = delta.x() / self.background_scale
            dy = delta.y() / self.background_scale
            box = self.parent.detection_boxes[self.selected_box]

            nx = box["x"] + dx
            ny = box["y"] + dy

            if self.parent.current_background:
                bw = self.parent.current_background.width()
                bh = self.parent.current_background.height()
                nx = max(0, min(nx, bw - box["width"]))
                ny = max(0, min(ny, bh - box["height"]))

            box["x"] = nx
            box["y"] = ny
            self.box_drag_start = self.mouse_pos

            self._sync_detection_box_to_dict(self.selected_box)

            self._save_current_detection_boxes()
            self.update()

    def _resize_box(self):
        """调整检测框大小"""
        delta = self.mouse_pos - self.box_resize_start
        bg_rect = self.get_background_rect()

        if bg_rect:
            dx = delta.x() / self.background_scale
            dy = delta.y() / self.background_scale
            box = self.parent.detection_boxes[self.selected_box]
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

            self._save_current_detection_boxes()
            self.update()

    def _drag_item(self):
        """拖动贴图"""
        bg_rect = self.get_background_rect()
        if bg_rect:
            p, rect, label = self.parent.canvas_items[self.parent.selected_item]
            np = self.mouse_pos - self.drag_start
            nx = (np.x() - bg_rect.left()) / self.background_scale
            ny = (np.y() - bg_rect.top()) / self.background_scale

            nx = max(0, nx)
            ny = max(0, ny)

            if self.parent.current_background:
                bw = self.parent.current_background.width()
                bh = self.parent.current_background.height()
                nx = min(nx, bw - rect.width())
                ny = min(ny, bh - rect.height())

            nr = QRectF(nx, ny, rect.width(), rect.height())
            self.parent.canvas_items[self.parent.selected_item] = (p, nr, label)
            self.update()

    def _scale_item(self):
        """缩放贴图"""
        if self.parent.current_background:
            p, rect, label = self.parent.canvas_items[self.parent.selected_item]
            nr = QRectF(rect)

            bg_rect = self.get_background_rect()
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

                if self.parent.current_background:
                    bw = self.parent.current_background.width()
                    bh = self.parent.current_background.height()
                    new_w = min(new_w, bw - rect.x())
                    new_h = min(new_h, bh - rect.y())

                nr.setWidth(new_w)
                nr.setHeight(new_h)

            self.parent.canvas_items[self.parent.selected_item] = (p, nr, label)
            self.selected_item_size = (new_w, new_h)
            self.update()

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        self.is_dragging_item = False
        self.is_dragging_background = False
        self.is_dragging_box = False
        self.is_resizing_box = False
        self.resize_handle = None
        self.update()

    def wheelEvent(self, event):
        """滚轮事件"""
        if not self.parent.current_background:
            return

        if self.parent.selected_item is not None:
            self._scale_selected_item(event)
        elif self.selected_box is not None:
            self._scale_selected_box(event)
        elif event.modifiers() & Qt.ControlModifier:
            self._scale_background(event)

        self.update()

    @staticmethod
    def _clamp_size_with_aspect(new_w, new_h, orig_w, orig_h, min_size=10, max_size=None):
        """按短边约束缩放尺寸，保持纵横比。返回 (clamped_w, clamped_h)"""
        if max_size is None:
            max_size = min_size * 100  # 默认上限
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
        """缩放选中的贴图"""
        delta = event.angleDelta().y()
        scale_factor = 1.1 if delta > 0 else 0.9

        pixmap, rect, label = self.parent.canvas_items[self.parent.selected_item]

        new_width = rect.width() * scale_factor
        new_height = rect.height() * scale_factor

        bg_short_side = min(self.parent.current_background.width(),
                          self.parent.current_background.height())
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

        self.parent.canvas_items[self.parent.selected_item] = (pixmap, new_rect, label)
        self.selected_item_size = (new_width, new_height)

    def _scale_selected_box(self, event):
        """缩放选中的检测框"""
        delta = event.angleDelta().y()
        scale_factor = 1.03 if delta > 0 else 0.97

        box = self.parent.detection_boxes[self.selected_box]
        x, y, width, height = box["x"], box["y"], box["width"], box["height"]

        new_width = width * scale_factor
        new_height = height * scale_factor

        bg_size = min(self.parent.current_background.width(),
                     self.parent.current_background.height())
        new_width, new_height = self._clamp_size_with_aspect(
            new_width, new_height,
            width, height,
            min_size=10, max_size=bg_size * 0.9
        )

        center_x = x + width / 2
        center_y = y + height / 2

        new_x = center_x - new_width / 2
        new_y = center_y - new_height / 2

        new_x = max(0, min(new_x, self.parent.current_background.width() - new_width))
        new_y = max(0, min(new_y, self.parent.current_background.height() - new_height))

        box["x"] = new_x
        box["y"] = new_y
        box["width"] = new_width
        box["height"] = new_height

        self._sync_detection_box_to_dict(self.selected_box)

    def _scale_background(self, event):
        """缩放背景图"""
        delta = event.angleDelta().y()
        scale_factor = 1.1 if delta > 0 else 0.9

        self.background_scale *= scale_factor
        self.background_scale = max(
            BACKGROUND_SCALE_CONFIG['min_scale'],
            min(self.background_scale, BACKGROUND_SCALE_CONFIG['max_scale'])
        )
        self.is_manual_scale = True

    def keyPressEvent(self, event):
        """键盘按下事件"""
        if event.key() == Qt.Key_Delete or event.key() == Qt.Key_E:
            if self.parent.selected_item is not None:
                del self.parent.canvas_items[self.parent.selected_item]
                self.parent.selected_item = None
                self.selected_item_size = None
                self.update_status_label()
                self.update()
        elif event.key() == Qt.Key_F and event.modifiers() & Qt.ControlModifier:
            self.reset_view()
            self.update()
        elif event.key() == Qt.Key_Q:
            if self.is_drawing_box:
                self.is_drawing_box = False
                self.draw_start_pos = None
                self.temp_draw_box = None
                self.setCursor(Qt.ArrowCursor)
                if hasattr(self.parent, 'draw_box_btn'):
                    self.parent.draw_box_btn.setText("绘制 BOX(W)")
                self.update()
        super().keyPressEvent(event)

    def resizeEvent(self, event):
        """窗口大小变化事件"""
        self.update()
        super().resizeEvent(event)
