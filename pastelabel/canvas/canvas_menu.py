"""
Canvas 右键菜单 - 贴图标签管理
"""
import os
from PyQt5.QtWidgets import QMenu, QAction
from PyQt5.QtCore import QPoint

from ..core.utils import extract_label_name
from ..ui import dialog_helpers
from ..ui.i18n import t as tr


class CanvasMenuMixin:
    """右键菜单逻辑"""

    @staticmethod
    def _remove_index_from_mapping(mapping, removed_index):
        """删除背景图后同步重排按图片索引保存的数据。"""
        return {
            (index - 1 if index > removed_index else index): value
            for index, value in mapping.items()
            if index != removed_index
        }

    def _handle_right_click(self, mouse_pos):
        item_index = self.find_item_at_position(mouse_pos)
        if item_index is not None:
            self._show_paste_context_menu(item_index, mouse_pos)
            return True
        labels_visible = self._editor.show_labels_checkbox.isChecked()
        box_index = self._find_detection_box_at(mouse_pos) if labels_visible else None
        if box_index is not None and not self._editor._is_delete_view:
            self._show_box_label_menu(box_index, mouse_pos)
            return True
        if self._editor.current_background is not None:
            if self._editor._is_delete_view:
                self._show_restore_context_menu(mouse_pos)
            else:
                self._show_background_context_menu(mouse_pos)
            return True
        return False

    def _find_detection_box_at(self, mouse_pos):
        """查找鼠标位置下的检测框"""
        background_rect = self.get_background_rect()
        if not background_rect:
            return None
        for i, box in enumerate(self._editor.detection_boxes):
            box_x = box["x"] * self.background_scale + background_rect.left()
            box_y = box["y"] * self.background_scale + background_rect.top()
            box_w = box["width"] * self.background_scale
            box_h = box["height"] * self.background_scale
            from PyQt5.QtCore import QRectF
            if QRectF(box_x, box_y, box_w, box_h).contains(mouse_pos):
                return i
        return None

    def _show_box_label_menu(self, box_index, mouse_pos):
        """检测框右键修改标签菜单"""
        from ..core.utils import extract_label_name
        menu = QMenu(self)

        current_label = self._editor.detection_boxes[box_index].get("label", "")

        modify_action = QAction(tr("修改标签"), self)
        modify_action.triggered.connect(
            lambda checked, idx=box_index: self._modify_box_label(idx)
        )
        menu.addAction(modify_action)

        remove_action = QAction(tr("移除"), self)
        remove_action.triggered.connect(
            lambda checked: self._editor._delete_selected_box()
        )
        menu.addAction(remove_action)

        menu.addSeparator()

        label_items = []
        for i in range(self._editor.label_list.count()):
            label = self._editor.label_list.item(i).text()
            pure_label = extract_label_name(label)
            label_items.append(pure_label)

        for label in label_items:
            if label == current_label:
                continue
            action = QAction(label, self)
            action.triggered.connect(
                lambda checked, l=label, idx=box_index: self._change_box_label(idx, l)
            )
            menu.addAction(action)

        menu.exec_(QPoint(self.mapToGlobal(mouse_pos)))

    def _modify_box_label(self, box_index):
        """修改检测框标签"""
        if self._editor._is_delete_view:
            return
        current_label = self._editor.detection_boxes[box_index].get("label", "")
        new_label, ok = dialog_helpers.get_text(
            self, "修改标签", "请输入新的标签名称:", text=current_label
        )
        if ok and new_label.strip():
            new_label = new_label.strip()
            old_label = current_label
            for box in self._editor.detection_boxes:
                if box.get("label") == old_label:
                    box["label"] = new_label
            for idx in self._editor.detection_boxes_dict:
                for box in self._editor.detection_boxes_dict[idx]:
                    if box.get("label") == old_label:
                        box["label"] = new_label
            if self._editor.current_background_index >= 0:
                self._editor.detection_boxes_dict[self._editor.current_background_index] = \
                    self._editor.detection_boxes.copy()
            self._editor.update_label_list()
            self.update()

    def _change_box_label(self, box_index, new_label):
        """切换检测框标签"""
        if self._editor._is_delete_view:
            return
        if 0 <= box_index < len(self._editor.detection_boxes):
            self._editor.detection_boxes[box_index]["label"] = new_label
            if self._editor.current_background_index >= 0:
                self._editor.detection_boxes_dict[self._editor.current_background_index] = \
                    self._editor.detection_boxes.copy()
            self._editor.update_label_list()
            self.update()

    def _show_restore_context_menu(self, mouse_pos):
        menu = QMenu(self)

        restore_action = QAction(tr("恢复到工作路径"), self)
        restore_action.triggered.connect(self._restore_current_background)
        menu.addAction(restore_action)

        menu.exec_(QPoint(self.mapToGlobal(mouse_pos)))

    def _restore_current_background(self):
        """从移除路径恢复当前图片到工作路径"""
        import shutil
        if not self._editor.background_images:
            return
        if not hasattr(self._editor, '_delete_files') or not self._editor._delete_files:
            return
        idx = self._editor.background_list.currentRow()
        if idx < 0 or idx >= len(self._editor._delete_files):
            return
        file_path = self._editor._delete_files[idx]
        delete_dir = os.path.dirname(file_path)
        original_dir = os.path.dirname(delete_dir)

        dst = os.path.join(original_dir, os.path.basename(file_path))
        shutil.move(file_path, dst)
        json_path = os.path.splitext(file_path)[0] + '.json'
        if os.path.isfile(json_path):
            shutil.move(json_path, os.path.splitext(dst)[0] + '.json')

        insert_idx = len(self._editor.background_images)
        self._editor.background_images.append(dst)
        self._editor.canvas_items_dict[insert_idx] = []
        self._editor.detection_boxes_dict[insert_idx] = []

        self._editor._show_delete_view()

    def _show_background_context_menu(self, mouse_pos):
        menu = QMenu(self)

        remove_action = QAction(tr("移除图片"), self)
        remove_action.triggered.connect(self._remove_current_background)
        menu.addAction(remove_action)

        menu.exec_(QPoint(self.mapToGlobal(mouse_pos)))

    def _remove_current_background(self):
        """从画布移除当前背景图（移到删除文件夹）"""
        import shutil
        if self._editor._is_delete_view:
            return
        idx = self._editor.current_background_index
        if idx < 0 or idx >= len(self._editor.background_images):
            return
        file_path = self._editor.background_images[idx]

        delete_dir = os.path.join(os.path.dirname(file_path), '_delete_')
        os.makedirs(delete_dir, exist_ok=True)
        shutil.move(file_path, os.path.join(delete_dir, os.path.basename(file_path)))
        json_path = os.path.splitext(file_path)[0] + '.json'
        if os.path.isfile(json_path):
            shutil.move(json_path, os.path.join(delete_dir, os.path.basename(json_path)))

        self._editor.background_images.pop(idx)
        self._editor.canvas_items_dict = self._remove_index_from_mapping(
            self._editor.canvas_items_dict, idx
        )
        self._editor.detection_boxes_dict = self._remove_index_from_mapping(
            self._editor.detection_boxes_dict, idx
        )

        new_idx = min(idx, len(self._editor.background_images) - 1)
        if self._editor.background_images:
            self._editor.current_background_index = new_idx
            from PyQt5.QtGui import QPixmap
            pixmap = QPixmap(self._editor.background_images[new_idx])
            if not pixmap.isNull():
                self._editor.current_background = pixmap
                self._editor.detection_boxes = self._editor.detection_boxes_dict.get(new_idx, []).copy()
                self._editor.canvas_items = self._editor.canvas_items_dict.get(new_idx, [])
                self.reset_view()
                self.update()
        else:
            self._editor.current_background = None
            self._editor.current_background_index = -1
            self.update()

        self._editor.update_file_count()
        self._editor.update_label_list()
        self._editor._show_work_view()

    def _show_paste_context_menu(self, item_index, mouse_pos):
        menu = QMenu(self)

        remove_action = QAction(tr("移除"), self)
        remove_action.triggered.connect(
            lambda checked, idx=item_index: self._remove_paste_item(idx)
        )
        menu.addAction(remove_action)

        menu.addSeparator()

        label_items = []
        for i in range(self._editor.paste_label_list.count()):
            label = self._editor.paste_label_list.item(i).text()
            pure_label = extract_label_name(label)
            label_items.append(pure_label)

        for label in label_items:
            action = QAction(label, self)
            action.triggered.connect(
                lambda checked, l=label, idx=item_index: self.change_item_label(idx, l)
            )
            menu.addAction(action)

        menu.addSeparator()

        new_label_action = QAction(tr("增加标签"), self)
        new_label_action.triggered.connect(
            lambda checked, idx=item_index: self.add_new_label(idx)
        )
        menu.addAction(new_label_action)

        menu.exec_(QPoint(self.mapToGlobal(mouse_pos)))

    def change_item_label(self, item_index, new_label):
        if self._editor._is_delete_view:
            return
        if 0 <= item_index < len(self._editor.canvas_items):
            pixmap, rect, _ = self._editor.canvas_items[item_index]
            self._editor.canvas_items[item_index] = (pixmap, rect, new_label)
            self.update()

    def add_new_label(self, item_index):
        if self._editor._is_delete_view:
            return
        new_label, ok = dialog_helpers.get_text(
            self, "增加标签", "请输入新的标签名称:"
        )
        if ok and new_label.strip():
            new_label = new_label.strip()
            self._editor.paste_label_list.addItem(new_label)

            if 0 <= item_index < len(self._editor.canvas_items):
                pixmap, rect, _ = self._editor.canvas_items[item_index]
                self._editor.canvas_items[item_index] = (pixmap, rect, new_label)
                self.update()

    def _remove_paste_item(self, item_index):
        """移除贴图项"""
        if self._editor._is_delete_view:
            return
        if 0 <= item_index < len(self._editor.canvas_items):
            self._editor.canvas_items.pop(item_index)
            self._editor.selected_item = None
            self.update()
