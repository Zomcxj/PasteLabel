"""
标签管理器模块 - 管理标签的增删改查操作
"""

from typing import TYPE_CHECKING
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QMenu, QAction, QListWidgetItem

from ..core.utils import extract_label_name
from ..ui import dialog_helpers
from ..ui.i18n import t as tr

if TYPE_CHECKING:
    from ..core.editor_protocol import EditorProtocol


class LabelManager(QObject):
    """标签管理器 - 管理全局标签和贴图标签"""

    # 信号：数据变更后通知编辑器刷新 UI
    data_changed = pyqtSignal()
    label_list_changed = pyqtSignal()

    def __init__(self, editor: "EditorProtocol", parent=None):
        """
        :param editor: 实现 EditorProtocol 的编辑器实例
        """
        super().__init__(parent)
        self.editor = editor
    
    # ========== 贴图标签管理 ==========
    
    def show_paste_label_context_menu(self, position):
        """显示贴图标签右键菜单"""
        menu = QMenu()
        selected_items = self.editor.paste_label_list.selectedItems()
        
        if selected_items:
            modify_action = menu.addAction(tr("修改标签"))
            modify_action.triggered.connect(self.modify_paste_label)
            
            delete_action = menu.addAction(tr("删除标签"))
            delete_action.triggered.connect(self.delete_paste_label)
            
            menu.addSeparator()
        
        add_action = menu.addAction(tr("增加标签"))
        add_action.triggered.connect(self.add_paste_label)
        
        menu.exec_(self.editor.paste_label_list.mapToGlobal(position))
    
    def add_paste_label(self):
        """增加贴图标签"""
        label_name, ok = dialog_helpers.get_text(
            self.editor, "增加贴图标签", "请输入新的贴图标签名称:"
        )
        
        if ok and label_name.strip():
            label_name = label_name.strip()
            
            existing_labels = set()
            for i in range(self.editor.paste_label_list.count()):
                existing_labels.add(self.editor.paste_label_list.item(i).text())
            
            if label_name in existing_labels:
                dialog_helpers.warning(self.editor, "警告", tr("标签名称已存在，请输入不同的名称"))
                return
            
            self.editor.paste_label_list.addItem(label_name)
    
    def modify_paste_label(self):
        """修改贴图标签"""
        selected_items = self.editor.paste_label_list.selectedItems()
        if not selected_items:
            return
        
        old_label = selected_items[0].text()
        new_label, ok = dialog_helpers.get_text(
            self.editor, "修改贴图标签", "请输入新的贴图标签名称:", text=old_label
        )
        
        if ok and new_label.strip():
            new_label = new_label.strip()
            
            existing_labels = set()
            for i in range(self.editor.paste_label_list.count()):
                existing_labels.add(self.editor.paste_label_list.item(i).text())
            
            if new_label in existing_labels and new_label != old_label:
                dialog_helpers.warning(self.editor, "警告", tr("标签名称已存在，请输入不同的名称"))
                return
            
            selected_items[0].setText(new_label)
            
            # 更新所有使用该标签的贴图
            for i in range(len(self.editor.canvas_items)):
                pixmap, rect, label = self.editor.canvas_items[i]
                if label == old_label:
                    self.editor.canvas_items[i] = (pixmap, rect, new_label)
            
            for i in range(len(self.editor.background_images)):
                if i in self.editor.canvas_items_dict:
                    updated_items = []
                    for item in self.editor.canvas_items_dict[i]:
                        if item[2] == old_label:
                            updated_items.append((item[0], item[1], new_label))
                        else:
                            updated_items.append(item)
                    self.editor.canvas_items_dict[i] = updated_items
            
            self.data_changed.emit()
    
    def delete_paste_label(self):
        """删除贴图标签"""
        selected_items = self.editor.paste_label_list.selectedItems()
        if not selected_items:
            return
        
        label_to_delete = selected_items[0].text()
        
        reply = dialog_helpers.question(
            self.editor, tr("确认删除"), 
            f"{tr('确定要删除贴图标签')} '{label_to_delete}' {tr('吗？删除后，所有使用该标签的贴图也会被删除。')}",
            dialog_helpers.QMessageBox.Yes | dialog_helpers.QMessageBox.No,
            dialog_helpers.QMessageBox.No
        )
        
        if reply == dialog_helpers.QMessageBox.Yes:
            for item in selected_items:
                self.editor.paste_label_list.takeItem(
                    self.editor.paste_label_list.row(item)
                )
            
            # 删除所有使用该标签的贴图
            new_canvas_items = []
            for pixmap, rect, label in self.editor.canvas_items:
                if label != label_to_delete:
                    new_canvas_items.append((pixmap, rect, label))
            self.editor.canvas_items = new_canvas_items
            self.editor.selected_item = None
            
            for i in range(len(self.editor.background_images)):
                if i in self.editor.canvas_items_dict:
                    new_items = []
                    for item in self.editor.canvas_items_dict[i]:
                        if item[2] != label_to_delete:
                            new_items.append(item)
                    self.editor.canvas_items_dict[i] = new_items
            
            self.data_changed.emit()
    
    # ========== 检测框标签管理 ==========
    
    def show_label_context_menu(self, position):
        """显示标签（检测框标签）右键菜单"""
        menu = QMenu()
        selected_items = self.editor.label_list.selectedItems()
        
        if selected_items:
            modify_action = menu.addAction(tr("修改标签"))
            modify_action.triggered.connect(self.modify_label)
            
            delete_action = menu.addAction(tr("删除标签"))
            delete_action.triggered.connect(self.delete_label)
            
            menu.addSeparator()
        
        add_action = menu.addAction(tr("增加标签"))
        add_action.triggered.connect(self.add_label)
        
        menu.exec_(self.editor.label_list.mapToGlobal(position))
    
    def modify_label(self):
        """修改标签名称。

        - 列表模式（每框一行）：只改选中行对应的那一个检测框
        - 统计模式：按标签名批量改名（当前图 + 全部背景 dict）
        """
        selected_items = self.editor.label_list.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        old_label_text = item.text()
        old_label = extract_label_name(old_label_text)
        mode = getattr(self.editor, '_bg_label_list_mode', 'stats')
        box_index = item.data(0x0100) if hasattr(item, 'data') else None

        anchor = None
        try:
            from PyQt5.QtGui import QCursor
            anchor = QCursor.pos()
        except Exception:
            anchor = None
        labels = self._dataset_labels_for_dialog(prefer_first=old_label)
        from ..ui.dialogs import LabelSelectionDialog
        new_label = LabelSelectionDialog.select_label(
            self.editor, labels, title="修改标签", initial_text=old_label,
            anchor_pos=anchor,
        )
        if not new_label or not str(new_label).strip():
            return
        new_label = str(new_label).strip()
        if new_label == old_label:
            return

        if mode == 'all' and isinstance(box_index, int):
            if not (0 <= box_index < len(self.editor.detection_boxes)):
                return
            # Decide color BEFORE membership of new_label changes.
            target_exists = self._label_already_exists(new_label)
            self.editor.detection_boxes[box_index]["label"] = new_label
            current_index = self.editor.current_background_index
            if current_index >= 0:
                self.editor.detection_boxes_dict[current_index] = \
                    list(self.editor.detection_boxes)
            self.editor.global_labels.add(new_label)
            still_used = any(
                box.get("label") == old_label
                for boxes in self.editor.detection_boxes_dict.values()
                for box in boxes
            )
            if not still_used and old_label in self.editor.global_labels:
                self.editor.global_labels.discard(old_label)
            self._apply_rename_color(old_label, new_label, target_exists, move_if_unused=not still_used)
            self._sync_cached_stats_label_rename(old_label, new_label, delta=1)
            if current_index >= 0:
                self._save_detection_json_for_index(current_index)
            # Keep dataset labels in parity with 标签管理 rename (all-mode)
            bg = getattr(self.editor, 'background_dataset_labels', None) or set()
            if isinstance(bg, set):
                if old_label in bg:
                    bg.discard(old_label)
                bg.add(new_label)
            self.label_list_changed.emit()
            self.data_changed.emit()
            return

        # Stats mode: full rename (memory + color + stats + disk)
        self.rename_detection_label(old_label, new_label, rewrite_disk=True)
    
    def delete_label(self):
        """删除标签。

        - 列表模式（每框一行）：只删选中行对应的那一个检测框
        - 统计模式：按标签名从所有背景删除全部同名框
        """
        selected_items = self.editor.label_list.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        label_text = item.text()
        label_to_delete = extract_label_name(label_text)
        mode = getattr(self.editor, '_bg_label_list_mode', 'stats')
        box_index = item.data(0x0100) if hasattr(item, 'data') else None

        if mode == 'all' and isinstance(box_index, int):
            if not (0 <= box_index < len(self.editor.detection_boxes)):
                return
            reply = dialog_helpers.question(
                self.editor, tr("确认删除"),
                f"{tr('确定要删除此检测框')} '{label_to_delete}' {tr('吗？')}",
                dialog_helpers.QMessageBox.Yes | dialog_helpers.QMessageBox.No,
                dialog_helpers.QMessageBox.No
            )
            if reply != dialog_helpers.QMessageBox.Yes:
                return
            del self.editor.detection_boxes[box_index]
            current_index = self.editor.current_background_index
            if current_index >= 0:
                self.editor.detection_boxes_dict[current_index] = \
                    list(self.editor.detection_boxes)
            self.editor.canvas.selected_box = None
            self.editor.canvas.selected_boxes = []
            # Drop global label only if no remaining box uses it on any image.
            still_used = any(
                box.get("label") == label_to_delete
                for boxes in self.editor.detection_boxes_dict.values()
                for box in boxes
            ) or any(
                box.get("label") == label_to_delete
                for box in self.editor.detection_boxes
            )
            if not still_used and label_to_delete in self.editor.global_labels:
                self.editor.global_labels.discard(label_to_delete)
            if current_index >= 0:
                self._save_detection_json_for_index(current_index)
            self.label_list_changed.emit()
            self.data_changed.emit()
            return

        delete_msg = f"{tr('吗？')}\n{tr('将从所有背景中删除该标签的检测框。')}"
        reply = dialog_helpers.question(
            self.editor, tr("确认删除"),
            f"{tr('确定要删除标签')} '{label_to_delete}' {delete_msg}",
            dialog_helpers.QMessageBox.Yes | dialog_helpers.QMessageBox.No,
            dialog_helpers.QMessageBox.No
        )

        if reply == dialog_helpers.QMessageBox.Yes:
            current_index = self.editor.current_background_index
            if current_index >= 0:
                self.editor.detection_boxes_dict[current_index] = \
                    self.editor.detection_boxes.copy()

            # 从所有背景的检测框中删除，并以当前背景索引重新同步当前列表
            for index, boxes in list(self.editor.detection_boxes_dict.items()):
                self.editor.detection_boxes_dict[index] = [
                    box for box in boxes
                    if box.get("label") != label_to_delete
                ]

            if current_index >= 0:
                self.editor.detection_boxes = \
                    self.editor.detection_boxes_dict.get(current_index, []).copy()
            else:
                self.editor.detection_boxes = []
            self.editor.canvas.selected_box = None
            self.editor.canvas.selected_boxes = []

            # 更新全局标签
            if label_to_delete in self.editor.global_labels:
                self.editor.global_labels.remove(label_to_delete)

            # 保存到所有 JSON 文件：必须传 current_index，否则会把当前图片的标签写到其它图片
            for index in self.editor.detection_boxes_dict:
                self._save_detection_json_for_index(index)

            self.label_list_changed.emit()
            self.data_changed.emit()

    def _save_detection_json_for_index(self, index):
        """按背景索引保存检测框，避免当前图片与其它图片标签串写。"""
        if index < 0 or index >= len(self.editor.background_images):
            return

        import os
        file_path = self.editor.background_images[index]
        background_name = os.path.basename(file_path)
        image_width = None
        image_height = None
        try:
            from PyQt5.QtGui import QImageReader
            image_size = QImageReader(file_path).size()
            if image_size.isValid():
                image_width = image_size.width()
                image_height = image_size.height()
        except (ImportError, AttributeError):
            pass

        self.editor.save_json(
            file_path,
            background_name,
            "",
            canvas_items=[],
            image_width=image_width,
            image_height=image_height,
            current_index=index,
        )
    
    def _dataset_labels_for_dialog(self, prefer_first=None):
        """Dataset labels for LabelSelectionDialog (same sources as canvas)."""
        labels = set()
        bg = getattr(self.editor, 'background_dataset_labels', None) or set()
        if isinstance(bg, (set, list, tuple)):
            labels.update(x for x in bg if isinstance(x, str) and x.strip())
        gl = getattr(self.editor, 'global_labels', None) or set()
        if isinstance(gl, (set, list, tuple)):
            labels.update(x for x in gl if isinstance(x, str) and x.strip())
        for boxes in (getattr(self.editor, 'detection_boxes_dict', {}) or {}).values():
            for box in boxes or []:
                lab = box.get('label') if isinstance(box, dict) else None
                if isinstance(lab, str) and lab.strip():
                    labels.add(lab.strip())
        for box in getattr(self.editor, 'detection_boxes', []) or []:
            lab = box.get('label') if isinstance(box, dict) else None
            if isinstance(lab, str) and lab.strip():
                labels.add(lab.strip())
        cached = getattr(self.editor, '_cached_bg_label_stats', None) or []
        for item in cached:
            if isinstance(item, dict):
                lab = item.get('label')
                if isinstance(lab, str) and lab.strip():
                    labels.add(lab.strip())
        prefer = (prefer_first or '').strip()
        ordered = sorted(labels, key=lambda x: x.casefold())
        if prefer and prefer in ordered:
            ordered = [prefer] + [x for x in ordered if x != prefer]
        elif prefer:
            ordered = [prefer] + ordered
        return ordered

    def add_label(self, label_name=None):
        """添加标签"""
        if label_name is None or isinstance(label_name, bool):
            label_name, ok = dialog_helpers.get_text(
                self.editor, "增加标签", "请输入新的标签名称:"
            )
            if not (ok and label_name.strip()):
                return
            label_name = label_name.strip()
        if not isinstance(label_name, str) or not label_name.strip():
            return
        label_name = label_name.strip()
        
        if label_name not in self.editor.global_labels:
            self.editor.global_labels.add(label_name)
            self.label_list_changed.emit()
    
    def _label_already_exists(self, label):
        """True if label is already used in the current dataset/session."""
        if not label:
            return False
        color_map = getattr(self.editor, 'label_color_map', None)
        if isinstance(color_map, dict) and label in color_map:
            return True
        gl = getattr(self.editor, 'global_labels', None) or set()
        if label in gl:
            return True
        bg = getattr(self.editor, 'background_dataset_labels', None) or set()
        if label in bg:
            return True
        for boxes in (getattr(self.editor, 'detection_boxes_dict', {}) or {}).values():
            for box in boxes or []:
                if isinstance(box, dict) and box.get('label') == label:
                    return True
        for box in getattr(self.editor, 'detection_boxes', []) or []:
            if isinstance(box, dict) and box.get('label') == label:
                return True
        cached = getattr(self.editor, '_cached_bg_label_stats', None) or []
        for item in cached:
            if isinstance(item, dict) and item.get('label') == label:
                return True
        return False

    def _stats_color_for(self, label):
        """Color from bg stats cache for label, if any."""
        if not label:
            return ''
        cached = getattr(self.editor, '_cached_bg_label_stats', None) or []
        for item in cached:
            if isinstance(item, dict) and item.get('label') == label:
                color = str(item.get('color', '') or '').strip()
                if color:
                    return color
        return ''

    def _apply_rename_color(self, old_label, new_label, target_exists, move_if_unused=True):
        """Apply color on rename given whether target already existed *before* rename."""
        color_map = getattr(self.editor, 'label_color_map', None)
        if not isinstance(color_map, dict):
            return
        if target_exists:
            # Keep target's color (map → stats → allocate); never take old color.
            if new_label not in color_map:
                stats_color = self._stats_color_for(new_label)
                if stats_color:
                    color_map[new_label] = stats_color
                elif hasattr(self.editor, 'get_label_color'):
                    color_map[new_label] = self.editor.get_label_color(new_label)
            if move_if_unused and old_label in color_map and old_label != new_label:
                color_map.pop(old_label, None)
        else:
            # Brand-new name: inherit old color.
            if old_label in color_map:
                old_color = color_map[old_label]
                color_map[new_label] = old_color
                if move_if_unused:
                    color_map.pop(old_label, None)
            elif hasattr(self.editor, 'get_label_color'):
                # Bind whatever get_label_color returns to the new name only.
                color = self.editor.get_label_color(old_label) if old_label else ''
                if not color:
                    color = self.editor.get_label_color(new_label)
                color_map[new_label] = color
                if move_if_unused and old_label in color_map:
                    color_map.pop(old_label, None)
        try:
            from ..core import config_manager
            config_manager.save_all(
                label_colors=getattr(self.editor, 'label_colors', None),
                label_color_map=color_map,
            )
        except Exception:
            pass

    def _transfer_label_color(self, old_label, new_label, move_if_unused=True):
        """Color rules on rename (detects target existence at call time)."""
        target_exists = self._label_already_exists(new_label)
        # When called after rename, new_label is always "existing" via global_labels.
        # Prefer explicit pre-check via _apply_rename_color from callers.
        # Fallback: if new_label already had a color, treat as existing.
        color_map = getattr(self.editor, 'label_color_map', None)
        if isinstance(color_map, dict) and new_label in color_map and old_label not in (None, new_label):
            # If new already has color and it wasn't just copied, keep it.
            pass
        self._apply_rename_color(old_label, new_label, target_exists, move_if_unused=move_if_unused)

    def _seed_stats_cache_from_disk_and_memory(self):
        """Build full stats: disk for unloaded images + memory for loaded ones.

        Memory wins for indexes already in detection_boxes_dict so recent
        canvas/list edits are reflected without missing unloaded files.
        """
        import os
        from .image_loader import collect_background_label_counts

        color_map = getattr(self.editor, 'label_color_map', None)
        images = list(getattr(self.editor, 'background_images', None) or [])
        boxes_dict = getattr(self.editor, 'detection_boxes_dict', None) or {}

        # 1) Start from disk scan for the whole dataset.
        counts = collect_background_label_counts(images) if images else {}

        # 2) Override counts for images loaded in memory (source of truth).
        if images and boxes_dict:
            for index, boxes in boxes_dict.items():
                if not isinstance(index, int) or index < 0 or index >= len(images):
                    continue
                # Subtract prior disk contribution for this file, then add memory.
                json_path = f"{os.path.splitext(images[index])[0]}.json"
                try:
                    from .image_loader import _count_labels_in_json
                    disk_part = _count_labels_in_json(json_path) or {}
                except Exception:
                    disk_part = {}
                for lbl, n in disk_part.items():
                    counts[lbl] = max(0, counts.get(lbl, 0) - int(n or 0))
                    if counts.get(lbl, 0) == 0:
                        counts.pop(lbl, None)
                for box in boxes or []:
                    if not isinstance(box, dict):
                        continue
                    label = box.get('label')
                    if not (isinstance(label, str) and label.strip()):
                        continue
                    label = label.strip()
                    counts[label] = counts.get(label, 0) + 1
        elif boxes_dict:
            # No image list: count memory only.
            counts = {}
            for boxes in boxes_dict.values():
                for box in boxes or []:
                    if not isinstance(box, dict):
                        continue
                    label = box.get('label')
                    if not (isinstance(label, str) and label.strip()):
                        continue
                    label = label.strip()
                    counts[label] = counts.get(label, 0) + 1
            for box in getattr(self.editor, 'detection_boxes', []) or []:
                if not isinstance(box, dict):
                    continue
                # Avoid double-count if same objects already in dict values.
                already = any(box is b for bs in boxes_dict.values() for b in (bs or []))
                if already:
                    continue
                label = box.get('label')
                if not (isinstance(label, str) and label.strip()):
                    continue
                label = label.strip()
                counts[label] = counts.get(label, 0) + 1

        def _color_for(label):
            if isinstance(color_map, dict) and color_map.get(label):
                return color_map[label]
            if hasattr(self.editor, 'get_label_color'):
                return self.editor.get_label_color(label)
            return ''

        self.editor._cached_bg_label_stats = [
            {'label': label, 'count': count, 'color': _color_for(label)}
            for label, count in sorted(counts.items(), key=lambda x: (-x[1], x[0]))
            if count > 0
        ]
        path = getattr(self.editor, '_memory_background_path', '') or ''
        if path:
            self.editor._cached_bg_label_stats_path = path

    # Back-compat alias used by older call sites / tests.
    def _seed_stats_cache_from_memory(self):
        self._seed_stats_cache_from_disk_and_memory()

    def _sync_cached_stats_label_rename(self, old_label, new_label, delta=None):
        """Update stats cache after rename.

        delta=None: full rename (all old_label → new_label, merge counts)
        delta=N: only N occurrences moved from old → new (single-box rename)
        """
        color_map = getattr(self.editor, 'label_color_map', None)
        cached = getattr(self.editor, '_cached_bg_label_stats', None)
        if not isinstance(cached, list) or not cached:
            # Full seed (disk+memory). Caller already applied rename to memory/disk.
            self._seed_stats_cache_from_disk_and_memory()
            cached = getattr(self.editor, '_cached_bg_label_stats', None) or []
            for item in cached:
                if not isinstance(item, dict):
                    continue
                label = item.get('label')
                if isinstance(color_map, dict) and color_map.get(label):
                    item['color'] = color_map[label]
            self.editor._cached_bg_label_stats = list(cached)
            return

        def _color_for(label, fallback=''):
            if isinstance(color_map, dict) and color_map.get(label):
                return color_map[label]
            if hasattr(self.editor, 'get_label_color'):
                return self.editor.get_label_color(label)
            return fallback or ''

        if delta is None:
            merged = {}
            target_color = ''
            for item in cached:
                if not isinstance(item, dict):
                    continue
                orig_label = item.get('label')
                label = new_label if orig_label == old_label else orig_label
                if not label:
                    continue
                try:
                    count = max(0, int(item.get('count', 0) or 0))
                except (TypeError, ValueError):
                    count = 0
                color = item.get('color', '') or ''
                # Prefer color that already belonged to the target label.
                if orig_label == new_label and color:
                    target_color = color
                if label in merged:
                    merged[label]['count'] += count
                    if orig_label == new_label and color:
                        merged[label]['color'] = color
                else:
                    merged[label] = {'label': label, 'count': count, 'color': color}
            if new_label in merged:
                preferred = (
                    (color_map.get(new_label) if isinstance(color_map, dict) else None)
                    or target_color
                    or _color_for(new_label, merged[new_label].get('color', ''))
                )
                merged[new_label]['color'] = preferred
            self.editor._cached_bg_label_stats = list(merged.values())
            return

        # Partial move of `delta` counts
        by_label = {}
        for item in cached:
            if not isinstance(item, dict):
                continue
            label = item.get('label')
            if not label:
                continue
            try:
                count = max(0, int(item.get('count', 0) or 0))
            except (TypeError, ValueError):
                count = 0
            by_label[label] = {
                'label': label,
                'count': count,
                'color': item.get('color', '') or '',
            }
        moved = max(0, int(delta or 0))
        if old_label in by_label:
            by_label[old_label]['count'] = max(0, by_label[old_label]['count'] - moved)
            if by_label[old_label]['count'] == 0:
                del by_label[old_label]
        if new_label not in by_label:
            by_label[new_label] = {
                'label': new_label,
                'count': 0,
                'color': _color_for(new_label),
            }
        by_label[new_label]['count'] += moved
        by_label[new_label]['color'] = _color_for(new_label, by_label[new_label].get('color', ''))
        self.editor._cached_bg_label_stats = list(by_label.values())

    def rename_detection_label(self, old_label, new_label, rewrite_disk=True):
        """Rename a detection/background label in memory and optionally all sidecar JSONs."""
        import json
        import os

        old_label = (old_label or "").strip()
        new_label = (new_label or "").strip()
        if not old_label or not new_label or old_label == new_label:
            return False

        # Capture before membership changes.
        target_exists = self._label_already_exists(new_label)

        current_index = getattr(self.editor, 'current_background_index', -1)
        if current_index is not None and current_index >= 0:
            self.editor.detection_boxes_dict[current_index] = list(self.editor.detection_boxes)

        for index in list(self.editor.detection_boxes_dict.keys()):
            for box in self.editor.detection_boxes_dict[index]:
                if box.get("label") == old_label:
                    box["label"] = new_label

        self.editor.detection_boxes = [
            box for box in (
                self.editor.detection_boxes_dict.get(current_index, [])
                if current_index is not None and current_index >= 0
                else self.editor.detection_boxes
            )
        ]
        if current_index is None or current_index < 0:
            for box in self.editor.detection_boxes:
                if box.get("label") == old_label:
                    box["label"] = new_label

        if old_label in self.editor.global_labels:
            self.editor.global_labels.discard(old_label)
            self.editor.global_labels.add(new_label)
        else:
            self.editor.global_labels.add(new_label)

        bg_labels = getattr(self.editor, 'background_dataset_labels', None)
        if isinstance(bg_labels, set):
            if old_label in bg_labels:
                bg_labels.discard(old_label)
            bg_labels.add(new_label)

        self._apply_rename_color(old_label, new_label, target_exists, move_if_unused=True)
        self._sync_cached_stats_label_rename(old_label, new_label)
        # Keep path so stats dialog prefers this live cache.
        path = getattr(self.editor, '_memory_background_path', '') or ''
        if path and not getattr(self.editor, '_cached_bg_label_stats_path', ''):
            self.editor._cached_bg_label_stats_path = path

        if rewrite_disk:
            for image_path in list(getattr(self.editor, 'background_images', []) or []):
                json_path = f"{os.path.splitext(image_path)[0]}.json"
                if not os.path.isfile(json_path):
                    continue
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except Exception:
                    continue
                if not isinstance(data, dict):
                    continue
                shapes = data.get('shapes')
                if not isinstance(shapes, list):
                    continue
                changed = False
                for shape in shapes:
                    if isinstance(shape, dict) and shape.get('label') == old_label:
                        shape['label'] = new_label
                        changed = True
                if not changed:
                    continue
                try:
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass

        self.label_list_changed.emit()
        self.data_changed.emit()
        return True

    def rename_paste_label(self, old_label, new_label):
        """Rename a paste label in memory lists and canvas items."""
        old_label = (old_label or "").strip()
        new_label = (new_label or "").strip()
        if not old_label or not new_label or old_label == new_label:
            return False

        paste_list = getattr(self.editor, 'paste_label_list', None)
        if paste_list is not None:
            for i in range(paste_list.count()):
                item = paste_list.item(i)
                if item and item.text() == old_label:
                    item.setText(new_label)

        for item in getattr(self.editor, 'canvas_items', []) or []:
            if isinstance(item, dict) and item.get('label') == old_label:
                item['label'] = new_label
        for index, items in list(getattr(self.editor, 'canvas_items_dict', {}).items()):
            for item in items or []:
                if isinstance(item, dict) and item.get('label') == old_label:
                    item['label'] = new_label

        self._transfer_label_color(old_label, new_label, move_if_unused=True)

        self.data_changed.emit()
        return True

    def update_global_labels(self):
        """更新全局标签集合"""
        for index in self.editor.detection_boxes_dict:
            for box in self.editor.detection_boxes_dict[index]:
                if isinstance(box.get("label"), str) and box.get("label").strip():
                    self.editor.global_labels.add(box["label"])
    
    def update_label_list(self):
        """更新标签列表显示"""
        self.update_global_labels()
        self.editor.label_list.clear()

        if self.editor.current_background is None:
            return

        mode = getattr(self.editor, '_bg_label_list_mode', 'stats')
        self.editor.global_labels = {
            label for label in self.editor.global_labels
            if isinstance(label, str) and label.strip()
        }
        bg_labels = getattr(self.editor, 'background_dataset_labels', set()) or set()
        bg_labels = {
            label for label in bg_labels
            if isinstance(label, str) and label.strip()
        }

        label_counts = {}
        for box in self.editor.detection_boxes:
            if isinstance(box.get("label"), str) and box.get("label").strip():
                label = box["label"]
                label_counts[label] = label_counts.get(label, 0) + 1

        if mode == 'all':
            # One row per detection box on the current image (order = box order).
            # Qt.ItemDataRole.UserRole == 0x0100 (avoid Qt mock AttributeError in tests)
            for box_index, box in enumerate(self.editor.detection_boxes):
                label = box.get("label")
                if not (isinstance(label, str) and label.strip()):
                    continue
                item = QListWidgetItem(label)
                if hasattr(item, 'setData'):
                    item.setData(0x0100, box_index)
                self.editor.label_list.addItem(item)
            return

        all_labels = (
            set(self.editor.global_labels)
            | set(bg_labels)
            | set(label_counts.keys())
        )
        label_count_list = []
        for label in all_labels:
            count = label_counts.get(label, 0)
            label_count_list.append((label, count))

        label_count_list.sort(key=lambda x: (-x[1], x[0].casefold()))

        for label, count in label_count_list:
            item = QListWidgetItem(f"{label} ({count})")
            self.editor.label_list.addItem(item)
