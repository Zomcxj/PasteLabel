"""
Canvas 绘制逻辑 - 检测框的创建、拖动、缩放
"""
from PyQt5.QtWidgets import QInputDialog
from PyQt5.QtCore import Qt, QRectF, QSizeF

from ..core.config import DETECTION_BOX_CONFIG


class CanvasDrawingMixin:
    """检测框绘制、拖动、缩放"""

    def _can_edit_canvas(self):
        return not getattr(self._editor, '_is_delete_view', False)

    def _handle_drawing_press(self, mouse_pos):
        if not self._can_edit_canvas():
            return True
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
            self.selected_boxes = []
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

        label_items = self._label_choices_for_draw()

        selected_label = LabelSelectionDialog.select_label(
            self, label_items, anchor_rect=self.temp_draw_box, show_group=True,
        )
        if isinstance(selected_label, tuple):
            selected_label, group_id = selected_label
        else:
            group_id = None

        if selected_label:
            self._create_detection_box(x, y, width, height, selected_label,
                                       group_id=group_id)

        self._reset_drawing_state()

    def _canvas_to_image_point(self, mouse_pos, background_rect=None):
        background_rect = background_rect or self.get_background_rect()
        if background_rect is None:
            return None
        constrained = self._constrain_to_background(mouse_pos, background_rect)
        x = (constrained.x() - background_rect.left()) / self.background_scale
        y = (constrained.y() - background_rect.top()) / self.background_scale
        return [float(x), float(y)]

    def _handle_polygon_press(self, mouse_pos):
        if not self._can_edit_canvas():
            return True
        if (not self._editor.background_images or
            self._editor.current_background_index < 0):
            return True
        background_rect = self.get_background_rect()
        if not background_rect or not background_rect.contains(mouse_pos):
            return True
        point = self._canvas_to_image_point(mouse_pos, background_rect)
        if point is None:
            return True
        if self._polygon_at_max_points():
            self._show_max_polygon_points_hint()
            return True
        self.temp_polygon_points.append(point)
        self.selected_box = None
        self.selected_boxes = []
        self._editor.selected_item = None
        self.update_status_label()
        self.update()
        return True

    def _polygon_at_max_points(self):
        limit = DETECTION_BOX_CONFIG.get("max_polygon_points", 32)
        return len(self.temp_polygon_points) >= limit

    def _show_max_polygon_points_hint(self):
        from ..ui.i18n import t as tr
        status = getattr(self._editor, "status_label", None)
        if status is not None:
            status.setText(tr("已达最大点数"))

    def _sync_polygon_bbox(self, box):
        points = box.get("points") or []
        if not points:
            return
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        box["x"], box["y"] = min(xs), min(ys)
        box["width"] = max(xs) - box["x"]
        box["height"] = max(ys) - box["y"]

    def _delete_polygon_vertex(self, box_index, vertex_index):
        if not self._can_edit_canvas():
            return False
        boxes = self._editor.detection_boxes
        if not (0 <= box_index < len(boxes)):
            return False
        box = boxes[box_index]
        points = box.get("points") or []
        if len(points) <= 3 or not (0 <= vertex_index < len(points)):
            return False
        if hasattr(self._editor, "save_undo_state"):
            self._editor.save_undo_state()
        del points[vertex_index]
        box["points"] = points
        self._sync_polygon_bbox(box)
        if getattr(self, "hover_resize_handle", None) == f"v{vertex_index}":
            self.hover_resize_handle = None
        self._sync_detection_box_to_dict(box_index)
        self._save_current_detection_boxes()
        self.update()
        return True

    def _insert_polygon_vertex(self, box_index, vertex_index, point):
        boxes = self._editor.detection_boxes
        if not (0 <= box_index < len(boxes)):
            return False
        box = boxes[box_index]
        points = box.get("points") or []
        if box.get("shape_type") != "polygon" or not points:
            return False
        if not (0 <= vertex_index <= len(points)):
            return False
        limit = DETECTION_BOX_CONFIG.get("max_polygon_points", 32)
        if len(points) >= limit:
            self._show_max_polygon_points_hint()
            return False
        if hasattr(self._editor, "save_undo_state"):
            self._editor.save_undo_state()
        points.insert(vertex_index, [float(point[0]), float(point[1])])
        self._sync_polygon_bbox(box)
        self._sync_detection_box_to_dict(box_index)
        self._save_current_detection_boxes()
        self.update()
        return True

    def _scale_polygon(self, box, factor):
        """绕外接框中心等比缩放多边形所有顶点，并同步外接框。"""
        points = box.get("points") or []
        if not points:
            return
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        cx = (min(xs) + max(xs)) / 2
        cy = (min(ys) + max(ys)) / 2
        bg = getattr(self._editor, "current_background", None)
        new_points = []
        for p in points:
            px = cx + (p[0] - cx) * factor
            py = cy + (p[1] - cy) * factor
            if bg is not None:
                px = max(0, min(px, bg.width()))
                py = max(0, min(py, bg.height()))
            new_points.append([px, py])
        box["points"] = new_points
        self._sync_polygon_bbox(box)

    def _create_point_at(self, img_point, label, group_id=None):
        px = float(img_point[0])
        py = float(img_point[1])
        self._create_detection_box(
            px, py, 1, 1, label,
            shape_type="point", points=[[px, py]], group_id=group_id,
        )

    def _handle_point_press(self, mouse_pos):
        from ..ui.dialogs import LabelSelectionDialog
        if not self._can_edit_canvas():
            return True
        if (not self._editor.background_images or
            self._editor.current_background_index < 0):
            return True
        background_rect = self.get_background_rect()
        if not background_rect or not background_rect.contains(mouse_pos):
            return True
        point = self._canvas_to_image_point(mouse_pos, background_rect)
        if point is None:
            return True
        self._editor.save_undo_state()
        result = LabelSelectionDialog.select_label(
            self, self._label_choices_for_draw(), show_group=True,
        )
        if isinstance(result, tuple):
            label, group_id = result
        else:
            label, group_id = result, None
        if label:
            self._create_point_at(point, label, group_id)
        self.update_status_label()
        self.update()
        return True

    def _can_close_polygon(self):
        return len(self.temp_polygon_points) >= 3

    def _polygon_pop_last_point(self):
        if self.temp_polygon_points:
            self.temp_polygon_points.pop()
        if not self.temp_polygon_points:
            self._reset_drawing_state()
        else:
            self.update()

    def _finish_polygon(self, label=None, pop_duplicate=False, group_id=None):
        if pop_duplicate and len(self.temp_polygon_points) > 3:
            self.temp_polygon_points.pop()
        if not self._can_close_polygon() or not label:
            self._reset_drawing_state()
            return
        points = [list(p) for p in self.temp_polygon_points]
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        x, y = min(xs), min(ys)
        self._create_detection_box(
            x, y, max(xs) - x, max(ys) - y, label,
            shape_type="polygon", points=points, group_id=group_id,
        )
        self._reset_drawing_state()

    def _prompt_finish_polygon(self, pop_duplicate=False):
        from ..ui.dialogs import LabelSelectionDialog
        if pop_duplicate and len(self.temp_polygon_points) > 3:
            self.temp_polygon_points.pop()
        if not self._can_close_polygon():
            return
        self._editor.save_undo_state()
        label_items = self._label_choices_for_draw()
        result = LabelSelectionDialog.select_label(
            self, label_items, show_group=True,
        )
        if isinstance(result, tuple):
            selected_label, group_id = result
        else:
            selected_label, group_id = result, None
        self._finish_polygon(label=selected_label, pop_duplicate=False,
                             group_id=group_id)

    def _label_choices_for_draw(self):
        """Labels offered after drawing a box (dataset-wide, not only current list)."""
        if hasattr(self, '_collect_dataset_labels'):
            labels = self._collect_dataset_labels()
            if labels:
                return list(labels)
        label_items = []
        label_list = getattr(self._editor, 'label_list', None)
        if label_list is not None:
            for i in range(label_list.count()):
                item = label_list.item(i)
                if item is not None:
                    label_items.append(item.text())
        return label_items

    def _constrain_to_background(self, pos, background_rect):
        constrained = pos
        constrained.setX(int(max(background_rect.left(), min(constrained.x(), background_rect.right()))))
        constrained.setY(int(max(background_rect.top(), min(constrained.y(), background_rect.bottom()))))
        return constrained

    def _create_detection_box(self, x, y, width, height, label, shape_type="rectangle",
                              points=None, group_id=None, visible=None):
        if not self._can_edit_canvas():
            return
        x = max(0, x)
        y = max(0, y)
        width = max(1, width)
        height = max(1, height)

        new_box = {
            "x": x, "y": y, "width": width, "height": height, "label": label,
            "shape_type": shape_type, "group_id": group_id,
        }
        if points is not None:
            new_box["points"] = points
        if visible is not None:
            new_box["visible"] = visible
        self._editor.detection_boxes.append(new_box)

        if self._editor.current_background_index >= 0:
            self._sync_all_detection_boxes_to_dict()

        pure = (label or "").strip()
        if pure:
            gl = getattr(self._editor, 'global_labels', None)
            if isinstance(gl, set):
                gl.add(pure)
            bg = getattr(self._editor, 'background_dataset_labels', None)
            if isinstance(bg, set):
                bg.add(pure)
            lm = getattr(self._editor, 'label_manager', None)
            if lm is not None and hasattr(lm, '_seed_stats_cache_from_disk_and_memory'):
                lm._seed_stats_cache_from_disk_and_memory()
            elif pure and hasattr(self._editor, 'get_label_color'):
                self._editor.get_label_color(pure)

        self._editor.update_label_list()
        self._save_current_detection_boxes()

    def _reset_drawing_state(self):
        self.draw_start_pos = None
        self.temp_draw_box = None
        self.temp_polygon_points = []
        self.is_drawing_box = False
        self.is_drawing_polygon = False
        self.is_drawing_point = False
        self.is_drawing_obb = False
        self.current_draw_mode = None
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
        if hasattr(self._editor, '_sync_pasted_boxes_to_cache'):
            self._editor._sync_pasted_boxes_to_cache()

    def _sync_all_detection_boxes_to_dict(self):
        idx = self._editor.current_background_index
        if idx >= 0:
            self._editor.detection_boxes_dict[idx] = self._editor.detection_boxes.copy()

    def _drag_box(self):
        if not self._can_edit_canvas():
            return
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

            applied_dx = nx - box["x"]
            applied_dy = ny - box["y"]
            box["x"] = nx
            box["y"] = ny
            if box.get("points"):
                box["points"] = [[p[0] + applied_dx, p[1] + applied_dy] for p in box["points"]]
            self.box_drag_start = self.mouse_pos

            self._sync_detection_box_to_dict(self.selected_box)
            self._needs_save = True
            if box.get("shape_type") == "point":
                # 关键点移动后位置/状态可能变化，刷新列表警告标记
                self._editor.update_label_list()
            self.update()

    def _resize_box(self):
        if not self._can_edit_canvas():
            return
        delta = self.mouse_pos - self.box_resize_start
        bg_rect = self.get_background_rect()

        if bg_rect:
            dx = delta.x() / self.background_scale
            dy = delta.y() / self.background_scale
            box = self._editor.detection_boxes[self.selected_box]
            handle = self.resize_handle or ""
            if isinstance(handle, str) and handle.startswith("v") and box.get("points"):
                idx = int(handle[1:])
                if 0 <= idx < len(box["points"]):
                    px = box["points"][idx][0] + dx
                    py = box["points"][idx][1] + dy
                    if self._editor.current_background:
                        bw = self._editor.current_background.width()
                        bh = self._editor.current_background.height()
                        px = max(0, min(px, bw))
                        py = max(0, min(py, bh))
                    box["points"][idx] = [px, py]
                    xs = [p[0] for p in box["points"]]
                    ys = [p[1] for p in box["points"]]
                    box["x"], box["y"] = min(xs), min(ys)
                    box["width"] = max(xs) - box["x"]
                    box["height"] = max(ys) - box["y"]
                    self.box_resize_start = self.mouse_pos
                    self._sync_detection_box_to_dict(self.selected_box)
                    self._needs_save = True
                    self.update()
                return

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
        if not self._can_edit_canvas():
            return False
        handle_name = self._box_handle_at_pos(mouse_pos, box_index, x, y, width, height)
        if handle_name:
            self.selected_box = box_index
            self.selected_boxes = [box_index]
            self.box_resize_start = mouse_pos
            self.is_resizing_box = True
            self.resize_handle = handle_name
            self.hover_resize_target = 'box'
            self.hover_resize_handle = handle_name
            self._editor.selected_item = None
            self.selected_item_size = None
            self.update_status_label()
            self.update()
            return True

        return False

    def _box_handle_at_pos(self, mouse_pos, box_index, x=None, y=None, width=None, height=None):
        """返回鼠标所在的检测框圆形缩放手柄名称，不修改编辑状态。"""
        if box_index is None or not (0 <= box_index < len(self._editor.detection_boxes)):
            return None

        box = self._editor.detection_boxes[box_index]
        background_rect = self.get_background_rect()
        if background_rect is None:
            return None
        if box.get("shape_type") == "point":
            return None
        handle_size = DETECTION_BOX_CONFIG['resize_handle_size']
        if box.get("shape_type") == "polygon" and box.get("points"):
            mx, my = mouse_pos.x(), mouse_pos.y()
            half = handle_size / 2
            for i, p in enumerate(box["points"]):
                hx = p[0] * self.background_scale + background_rect.left()
                hy = p[1] * self.background_scale + background_rect.top()
                if hx - half <= mx <= hx + half and hy - half <= my <= hy + half:
                    return f"v{i}"
            return None

        if x is None or y is None or width is None or height is None:
            x = box["x"] * self.background_scale + background_rect.left()
            y = box["y"] * self.background_scale + background_rect.top()
            width = box["width"] * self.background_scale
            height = box["height"] * self.background_scale

        handle_size = DETECTION_BOX_CONFIG['resize_handle_size']

        handles = {
            "br": (x + width, y + height),
            "tl": (x, y),
            "tr": (x + width, y),
            "bl": (x, y + height),
        }

        for handle_name, (hx, hy) in handles.items():
            handle_rect = QRectF(
                hx - handle_size / 2,
                hy - handle_size / 2,
                handle_size,
                handle_size,
            )
            if handle_rect.contains(mouse_pos):
                return handle_name

        return None
