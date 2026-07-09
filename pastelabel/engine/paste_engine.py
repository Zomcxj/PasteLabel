"""
贴图引擎混入 - 负责贴图的添加、删除、随机/批量放置
"""
import os
import random
from PyQt5.QtWidgets import QProgressDialog, QApplication
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QRectF

from ..core.config import RANDOM_POSITION_CONFIG, PASTE_ITEM_CONFIG
from ..core.utils import extract_label_name, calculate_iou
from ..ui.i18n import t as tr


OVERLAP_OFFSET_STEP = 3


class PasteEngineMixin:
    """贴图引擎混入类 - 管理贴图的添加、删除、随机和批量放置"""

    def _offset_overlapping_paste_group(self, pasted_group):
        existing_boxes = {
            (box['x'], box['y'], box['width'], box['height'])
            for box in getattr(self, 'detection_boxes', [])
        }
        if not existing_boxes:
            return pasted_group

        adjusted_group = []
        for rect, label in pasted_group:
            adjusted_group.append((QRectF(rect.x(), rect.y(), rect.width(), rect.height()), label))
        while True:
            group_boxes = [
                (rect.x(), rect.y(), rect.width(), rect.height())
                for rect, label in adjusted_group
            ]
            if not any(box in existing_boxes for box in group_boxes):
                return adjusted_group
            adjusted_group = [
                (
                    QRectF(
                        rect.x() + OVERLAP_OFFSET_STEP,
                        rect.y() + OVERLAP_OFFSET_STEP,
                        rect.width(),
                        rect.height(),
                    ),
                    label,
                )
                for rect, label in adjusted_group
            ]

    def add_small_to_canvas(self, item):
        """添加贴图到画布"""
        if self._busy:
            return
        self.save_undo_state()
        index = item.data(Qt.UserRole)
        pixmap = self.small_images[index][1]

        if self.current_background is None:
            return

        base_scale_factor = PASTE_ITEM_CONFIG['base_scale_factor'] * self.canvas.background_scale
        scale_factor = max(0.1, min(base_scale_factor, 2.0))

        width = pixmap.width() * scale_factor
        height = pixmap.height() * scale_factor

        if width <= 0 or height <= 0:
            return

        min_edge = self.min_size_spin.value()
        aspect_ratio = width / height
        if width < height:
            width = min_edge
            height = width / aspect_ratio
        else:
            height = min_edge
            width = height * aspect_ratio

        bg_width = self.current_background.width()
        bg_height = self.current_background.height()
        x = max(0, (bg_width - width) / 2)
        y = max(0, (bg_height - height) / 2)

        rect = QRectF(x, y, width, height)
        paste_label = self._get_paste_label(index)

        self.canvas_items.append((pixmap, rect, paste_label))
        self.canvas.update()

    def _get_paste_label(self, index):
        """获取贴图标签"""
        paste_label = "paste"

        if hasattr(self, 'auto_label_checkbox') and self.auto_label_checkbox.isChecked():
            image_path = self.small_images[index][0]
            image_name = os.path.basename(image_path)
            label_part = image_name.split('_')[0]
            label_part = os.path.splitext(label_part)[0]

            if label_part:
                paste_label = label_part

                label_exists = False
                for i in range(self.paste_label_list.count()):
                    existing_label = self.paste_label_list.item(i).text()
                    pure_label = extract_label_name(existing_label)
                    if pure_label == paste_label:
                        label_exists = True
                        break

                if not label_exists:
                    self.paste_label_list.addItem(paste_label)

        elif hasattr(self, 'paste_label_list'):
            if self.paste_label_list.count() == 0:
                self.paste_label_list.addItem("paste")
            else:
                selected_items = self.paste_label_list.selectedItems()
                if selected_items:
                    paste_label = selected_items[0].text()
                else:
                    paste_label = self.paste_label_list.item(0).text()

        return paste_label

    def clear_canvas(self):
        """清空画布"""
        if self._busy:
            return
        self.save_undo_state()
        self.canvas_items.clear()
        if self.current_background_index >= 0:
            self.canvas_items_dict[self.current_background_index] = self.canvas_items.copy()
        self.selected_item = None
        self.canvas.update()

    def random_paste_images(self, background=None, detection_boxes=None):
        """随机贴图 - 中心点避让算法"""
        if not self.small_images or not self.current_background:
            return

        self.save_undo_state()
        self._validate_size_range()

        current_background = background if background else self.current_background
        current_detection_boxes = detection_boxes if detection_boxes else self.detection_boxes

        self.canvas_items.clear()

        det_boxes = []
        for box in current_detection_boxes:
            det_boxes.append((box['x'], box['y'], box['x'] + box['width'], box['y'] + box['height']))

        bg_w = current_background.width()
        bg_h = current_background.height()

        ml = RANDOM_POSITION_CONFIG['margin_left']
        mt = RANDOM_POSITION_CONFIG['margin_top']
        mr = RANDOM_POSITION_CONFIG['margin_right']

        num_paste = self.paste_count_spin.value()
        selected_indices = random.choices(range(len(self.small_images)), k=num_paste)

        pasted_boxes = []

        for idx in selected_indices:
            file_path, pixmap = self.small_images[idx]

            if pixmap.width() <= 0 or pixmap.height() <= 0:
                continue

            aspect_ratio = pixmap.width() / pixmap.height()
            min_size = self.min_size_spin.value()
            max_size = self.max_size_spin.value()
            target_size = random.randint(min_size, max_size)

            if pixmap.width() > pixmap.height():
                new_width = target_size
                new_height = new_width / aspect_ratio
            else:
                new_height = target_size
                new_width = new_height * aspect_ratio

            if min(new_width, new_height) < min_size:
                if new_width < new_height:
                    new_width = min_size
                    new_height = new_width / aspect_ratio
                else:
                    new_height = min_size
                    new_width = new_height * aspect_ratio

            valid_position = False
            x, y = ml, mt

            place_w = bg_w - new_width - mr
            place_h = bg_h - new_height

            if place_w <= ml or place_h <= mt:
                continue

            for _ in range(RANDOM_POSITION_CONFIG['max_retries']):
                cx = random.uniform(ml + new_width / 2, place_w + new_width / 2)
                cy = random.uniform(mt + new_height / 2, place_h + new_height / 2)

                tx = cx - new_width / 2
                ty = cy - new_height / 2

                point_in_det = False
                for db in det_boxes:
                    if db[0] <= cx <= db[2] and db[1] <= cy <= db[3]:
                        point_in_det = True
                        break

                if point_in_det:
                    continue

                new_box = (tx, ty, tx + new_width, ty + new_height)

                overlaps_pasted = False
                for pb in pasted_boxes:
                    if calculate_iou(new_box, pb) > RANDOM_POSITION_CONFIG['overlap_iou_pasted']:
                        overlaps_pasted = True
                        break

                if overlaps_pasted:
                    continue

                x, y = tx, ty
                valid_position = True
                break

            if valid_position:
                rect = QRectF(x, y, new_width, new_height)
                paste_label = self._get_paste_label(idx)
                self.canvas_items.append((pixmap, rect, paste_label))
                pasted_boxes.append((x, y, x + new_width, y + new_height))

        if not background:
            self.canvas.update()

        if self.current_background_index >= 0:
            self.canvas_items_dict[self.current_background_index] = self.canvas_items.copy()

    def batch_paste_images(self):
        """从当前图片开始依次处理所有图片，应用随机贴图，然后返回当前图片"""
        if self._busy:
            return

        if not self.small_images:
            return

        if not self.background_images:
            return

        self._busy = True

        total_count = len(self.background_images)
        start_index = self.current_background_index if self.current_background_index >= 0 else 0
        process_count = total_count - start_index

        from ..ui.dialogs import ProgressDialogFactory
        progress_dialog = ProgressDialogFactory.create_progress_dialog(
            self, tr("一键贴图进度"), tr("正在一键贴图..."), process_count
        )
        progress_dialog.show()

        original_index = self.current_background_index
        original_background = self.current_background
        original_detection_boxes = self.detection_boxes.copy()
        original_canvas_items = self.canvas_items.copy()

        processed_count = 0

        for i in range(start_index, total_count):
            if progress_dialog.wasCanceled():
                break

            file_path = self.background_images[i]
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                if i in self.detection_boxes_dict and len(self.detection_boxes_dict[i]) > 0:
                    temp_detection_boxes = self.detection_boxes_dict[i].copy()
                else:
                    temp_detection_boxes = self.load_detection_boxes(file_path)
                    self.detection_boxes_dict[i] = temp_detection_boxes.copy()

                self.current_background_index = i
                self.canvas_items = self.canvas_items_dict.get(i, []).copy()

                self.random_paste_images(background=pixmap, detection_boxes=temp_detection_boxes)

                self.canvas_items_dict[i] = self.canvas_items.copy()

                processed_count += 1

                progress_dialog.setValue(processed_count)
                progress_dialog.setLabelText(f"{tr('正在处理第')} {i+1} {tr('张图片，共')} {total_count} {tr('张')}")

                QApplication.processEvents()

        progress_dialog.setValue(process_count)

        if original_index >= 0:
            self.current_background_index = original_index
            self.current_background = original_background
            self.detection_boxes = original_detection_boxes
            self.canvas_items = self.canvas_items_dict.get(original_index, []).copy()
            self.canvas.update()

        self._busy = False
