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

    def _collect_dataset_labels(self):
        """All labels known for the current background dataset (for box context menu)."""
        labels = set()
        bg = getattr(self._editor, 'background_dataset_labels', None) or set()
        if isinstance(bg, (set, list, tuple)):
            labels.update(x for x in bg if isinstance(x, str) and x.strip())
        gl = getattr(self._editor, 'global_labels', None) or set()
        if isinstance(gl, (set, list, tuple)):
            labels.update(x for x in gl if isinstance(x, str) and x.strip())
        for boxes in (getattr(self._editor, 'detection_boxes_dict', {}) or {}).values():
            for box in boxes or []:
                lab = box.get('label') if isinstance(box, dict) else None
                if isinstance(lab, str) and lab.strip():
                    labels.add(lab)
        for box in getattr(self._editor, 'detection_boxes', []) or []:
            lab = box.get('label') if isinstance(box, dict) else None
            if isinstance(lab, str) and lab.strip():
                labels.add(lab)
        label_list = getattr(self._editor, 'label_list', None)
        if label_list is not None:
            for i in range(label_list.count()):
                item = label_list.item(i)
                if item is None:
                    continue
                pure = extract_label_name(item.text())
                if pure:
                    labels.add(pure)
        return sorted(labels, key=lambda x: x.casefold())

    def _show_box_label_menu(self, box_index, mouse_pos):
        """检测框右键修改标签菜单"""
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

        for label in self._collect_dataset_labels():
            if label == current_label:
                continue
            action = QAction(label, self)
            action.triggered.connect(
                lambda checked, l=label, idx=box_index: self._change_box_label(idx, l)
            )
            menu.addAction(action)

        menu.exec_(QPoint(self.mapToGlobal(mouse_pos)))

    def _modify_box_label(self, box_index):
        """修改检测框标签（按标签名全局改名：颜色 + 统计缓存一并更新）。"""
        if self._editor._is_delete_view:
            return
        if not (0 <= box_index < len(self._editor.detection_boxes)):
            return
        current_label = self._editor.detection_boxes[box_index].get("label", "")
        anchor = None
        try:
            from PyQt5.QtGui import QCursor
            anchor = QCursor.pos()
        except Exception:
            anchor = None
        labels = self._collect_dataset_labels()
        if current_label and current_label not in labels:
            labels = [current_label] + list(labels)
        from ..ui.dialogs import LabelSelectionDialog
        new_label = LabelSelectionDialog.select_label(
            self, labels, title="修改标签", initial_text=current_label,
            anchor_pos=anchor,
        )
        if not new_label or not str(new_label).strip():
            return
        new_label = str(new_label).strip()
        if new_label == current_label:
            return
        lm = getattr(self._editor, 'label_manager', None)
        if lm is not None and hasattr(lm, 'rename_detection_label'):
            lm.rename_detection_label(current_label, new_label, rewrite_disk=True)
        else:
            for box in self._editor.detection_boxes:
                if box.get("label") == current_label:
                    box["label"] = new_label
            for idx in self._editor.detection_boxes_dict:
                for box in self._editor.detection_boxes_dict[idx]:
                    if box.get("label") == current_label:
                        box["label"] = new_label
            if self._editor.current_background_index >= 0:
                self._editor.detection_boxes_dict[self._editor.current_background_index] = \
                    list(self._editor.detection_boxes)
        self._editor.update_label_list()
        self.update()

    def _change_box_label(self, box_index, new_label):
        """切换单个检测框标签到数据集中已有标签。"""
        if self._editor._is_delete_view:
            return
        if not (0 <= box_index < len(self._editor.detection_boxes)):
            return
        old_label = self._editor.detection_boxes[box_index].get("label", "")
        new_label = (new_label or "").strip()
        if not new_label or new_label == old_label:
            return
        lm = getattr(self._editor, 'label_manager', None)
        target_exists = True
        if lm is not None and hasattr(lm, '_label_already_exists'):
            target_exists = lm._label_already_exists(new_label)
        self._editor.detection_boxes[box_index]["label"] = new_label
        if self._editor.current_background_index >= 0:
            self._editor.detection_boxes_dict[self._editor.current_background_index] = \
                list(self._editor.detection_boxes)
        gl = getattr(self._editor, 'global_labels', None)
        if isinstance(gl, set):
            gl.add(new_label)
        still_used = any(
            box.get("label") == old_label
            for boxes in (getattr(self._editor, 'detection_boxes_dict', {}) or {}).values()
            for box in (boxes or [])
        ) or any(
            box.get("label") == old_label
            for box in (getattr(self._editor, 'detection_boxes', []) or [])
        )
        if isinstance(gl, set) and not still_used and old_label in gl:
            gl.discard(old_label)
        if lm is not None:
            if hasattr(lm, '_apply_rename_color'):
                lm._apply_rename_color(
                    old_label, new_label, target_exists, move_if_unused=not still_used,
                )
            if hasattr(lm, '_sync_cached_stats_label_rename'):
                lm._sync_cached_stats_label_rename(old_label, new_label, delta=1)
            if hasattr(lm, '_save_detection_json_for_index'):
                lm._save_detection_json_for_index(self._editor.current_background_index)
        elif hasattr(self._editor, 'get_label_color'):
            self._editor.get_label_color(new_label)
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

        delete_labels_action = QAction(tr("删除标签文件"), self)
        delete_labels_action.triggered.connect(self._delete_current_label_file)
        menu.addAction(delete_labels_action)

        remove_action = QAction(tr("移除图片"), self)
        remove_action.triggered.connect(self._remove_current_background)
        menu.addAction(remove_action)

        menu.exec_(QPoint(self.mapToGlobal(mouse_pos)))

    def _delete_current_label_file(self):
        """Delete the current image's sidecar LabelMe JSON and clear in-memory boxes."""
        if self._editor._is_delete_view:
            return
        idx = self._editor.current_background_index
        if idx < 0 or idx >= len(self._editor.background_images):
            return
        file_path = self._editor.background_images[idx]
        json_path = os.path.splitext(file_path)[0] + ".json"
        has_boxes = bool(self._editor.detection_boxes)
        has_json = os.path.isfile(json_path)
        if not has_boxes and not has_json:
            return

        reply = dialog_helpers.question(
            self._editor,
            tr("确认删除"),
            f"{tr('确定要删除当前图片的标签文件吗？')}",
            dialog_helpers.QMessageBox.Yes | dialog_helpers.QMessageBox.No,
            dialog_helpers.QMessageBox.No,
        )
        if reply != dialog_helpers.QMessageBox.Yes:
            return

        self._editor.detection_boxes = []
        self._editor.detection_boxes_dict[idx] = []
        self.selected_box = None
        self.selected_boxes = []
        if has_json:
            try:
                os.remove(json_path)
            except OSError:
                from ..core.exception_hook import _write_log
                _write_log(f"删除标签文件失败: {json_path}")

        refresh = getattr(self._editor, "_refresh_background_item_status", None)
        if callable(refresh):
            refresh(idx, file_path)
        self._editor.update_label_list()
        self.update()

        # 删除后自动跳转到下一张
        if self._editor.background_images:
            new_idx = min(idx, len(self._editor.background_images) - 1)
            self._editor.switch_background_to_index(new_idx)
            row = self._editor._find_bg_list_row_for_index(new_idx)
            if row is not None:
                self._editor.background_list.setCurrentRow(row)

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
