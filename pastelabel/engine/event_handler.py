"""
事件处理混入 - 负责键盘、窗口事件和绘制模式切换
"""
import os
from PyQt5.QtGui import QPixmap, QKeySequence
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtWidgets import QShortcut

from ..core.utils import extract_label_name
from ..core.config import SHORTCUT_CONFIG, NUDGE_CONFIG
from ..ui.i18n import t as tr


class EventHandlerMixin:
    """事件处理混入类 - 键盘事件、事件过滤器、绘制模式、背景图切换"""

    def _get_shortcut(self, action):
        """获取快捷键配置"""
        sc = getattr(self, 'shortcut_config', None)
        if sc is not None and sc:
            return sc.get(action, SHORTCUT_CONFIG.get(action, ''))
        return SHORTCUT_CONFIG.get(action, '')

    def _match_shortcut(self, event, action):
        """检查事件是否匹配指定快捷键"""
        shortcut = self._get_shortcut(action)
        if not shortcut:
            return False

        parts = shortcut.split('+')
        key_str = parts[-1].strip()
        modifiers_str = '+'.join(parts[:-1]).strip() if len(parts) > 1 else ''

        key_map = {
            'A': Qt.Key_A, 'B': Qt.Key_B, 'C': Qt.Key_C, 'D': Qt.Key_D,
            'E': Qt.Key_E, 'F': Qt.Key_F, 'G': Qt.Key_G, 'H': Qt.Key_H,
            'I': Qt.Key_I, 'J': Qt.Key_J, 'K': Qt.Key_K, 'L': Qt.Key_L,
            'M': Qt.Key_M, 'N': Qt.Key_N, 'O': Qt.Key_O, 'P': Qt.Key_P,
            'Q': Qt.Key_Q, 'R': Qt.Key_R, 'S': Qt.Key_S, 'T': Qt.Key_T,
            'U': Qt.Key_U, 'V': Qt.Key_V, 'W': Qt.Key_W, 'X': Qt.Key_X,
            'Y': Qt.Key_Y, 'Z': Qt.Key_Z,
            '0': Qt.Key_0, '1': Qt.Key_1, '2': Qt.Key_2, '3': Qt.Key_3,
            '4': Qt.Key_4, '5': Qt.Key_5, '6': Qt.Key_6, '7': Qt.Key_7,
            '8': Qt.Key_8, '9': Qt.Key_9,
            'Delete': Qt.Key_Delete, 'Space': Qt.Key_Space,
            'F1': Qt.Key_F1, 'F2': Qt.Key_F2, 'F3': Qt.Key_F3, 'F4': Qt.Key_F4,
            'F5': Qt.Key_F5, 'F6': Qt.Key_F6, 'F7': Qt.Key_F7, 'F8': Qt.Key_F8,
            'F9': Qt.Key_F9, 'F10': Qt.Key_F10, 'F11': Qt.Key_F11, 'F12': Qt.Key_F12,
        }

        target_key = key_map.get(key_str)
        if target_key is None:
            return False

        if event.key() != target_key:
            return False

        modifiers = event.modifiers()
        expected_modifiers = Qt.NoModifier
        if 'Ctrl' in modifiers_str:
            expected_modifiers |= Qt.ControlModifier
        if 'Alt' in modifiers_str:
            expected_modifiers |= Qt.AltModifier
        if 'Shift' in modifiers_str:
            expected_modifiers |= Qt.ShiftModifier

        return modifiers == expected_modifiers

    def setup_shortcuts(self):
        """用 QShortcut 注册所有快捷键（全局生效，不受焦点影响）"""
        step = getattr(self, '_nav_step', 1)
        action_handlers = {
            'prev_image': lambda: self.switch_background(-1),
            'next_image': lambda: self.switch_background(1),
            'toggle_labels': self._toggle_labels,
            'toggle_label_names': self._toggle_label_names,
            'toggle_grid': self.toggle_grid,
            'toggle_auto_save': self._toggle_auto_save,
            'toggle_paste_names': self._toggle_paste_names,
            'draw_box': self.toggle_draw_mode,
            'quit_draw': self._quit_draw,
            'delete_selected': self._delete_selected_box,
            'undo': self.undo,
            'redo': self.redo,
            'remove_image': lambda: self.canvas._remove_current_background(),
            'restore_image': lambda: self.canvas._restore_current_background(),
            'fit_view': lambda: (self.canvas.reset_view(), self.canvas.update()),
            'copy_selected_labels': self.copy_selected_labels_to_active_cache_slot,
        }
        self._shortcuts = []
        for action, handler in action_handlers.items():
            sc_str = self._get_shortcut(action)
            if sc_str:
                seq = QKeySequence(sc_str)
                shortcut = QShortcut(seq, self)
                shortcut.activated.connect(handler)
                self._shortcuts.append(shortcut)
        copy_shortcut = QShortcut(QKeySequence('Ctrl+C'), self)
        copy_shortcut.activated.connect(self.copy_selected_labels_to_active_cache_slot)
        self._shortcuts.append(copy_shortcut)
        paste_shortcut = QShortcut(QKeySequence('Ctrl+V'), self)
        paste_shortcut.activated.connect(
            lambda: self.paste_label_cache_slot(self.active_label_cache_slot)
        )
        self._shortcuts.append(paste_shortcut)
        for slot_index, slot in enumerate(getattr(self, 'label_cache_slots', [])):
            sc_str = slot.get('shortcut', '')
            if sc_str:
                shortcut = QShortcut(QKeySequence(sc_str), self)
                shortcut.activated.connect(lambda idx=slot_index: self.paste_label_cache_slot(idx))
                self._shortcuts.append(shortcut)
        step = NUDGE_CONFIG['step']
        for key_code, dx, dy in [(Qt.Key_Left, -1, 0), (Qt.Key_Right, 1, 0),
                                  (Qt.Key_Up, 0, -1), (Qt.Key_Down, 0, 1)]:
            sc = QShortcut(QKeySequence(key_code), self)
            sc.activated.connect(lambda ddx=dx, ddy=dy: self.canvas._nudge_selected(ddx, ddy))
            self._shortcuts.append(sc)
        self._update_shortcut_status_label()

    def _update_shortcut_status_label(self):
        """刷新顶部快捷键提示条"""
        label = getattr(self, 'shortcut_status_label', None)
        if label is None:
            return

        items = [
            (tr("上一张"), 'prev_image'),
            (tr("下一张"), 'next_image'),
            (tr("绘制BOX"), 'draw_box'),
            (tr("退出绘制"), 'quit_draw'),
            (tr("删除选中"), 'delete_selected'),
        ]
        parts = []
        for name, action in items:
            shortcut = self._get_shortcut(action)
            if shortcut:
                parts.append(f"{name}:{shortcut}")
        label.setText("  |  ".join(parts))

    def update_shortcuts(self):
        """快捷键配置变更后重新注册"""
        for sc in getattr(self, '_shortcuts', []):
            sc.setEnabled(False)
            sc.deleteLater()
        self._shortcuts = []
        self.setup_shortcuts()
        self._update_shortcut_status_label()

    def _toggle_labels(self):
        self.show_labels_checkbox.setChecked(not self.show_labels_checkbox.isChecked())

    def _toggle_label_names(self):
        if hasattr(self, 'show_label_names_checkbox'):
            self.show_label_names_checkbox.setChecked(not self.show_label_names_checkbox.isChecked())

    def _toggle_auto_save(self):
        self.auto_save_checkbox.setChecked(not self.auto_save_checkbox.isChecked())
        self.auto_save_current_canvas()

    def _toggle_paste_names(self):
        self.show_paste_names_checkbox.setChecked(not self.show_paste_names_checkbox.isChecked())
        self.canvas.update()

    def _quit_draw(self):
        if self.canvas.is_drawing_box:
            self.canvas.is_drawing_box = False
            self.canvas.draw_start_pos = None
            self.canvas.temp_draw_box = None
            self.canvas.setCursor(Qt.ArrowCursor)
            if hasattr(self, 'draw_box_btn'):
                sc = self._get_shortcut('draw_box')
                self.draw_box_btn.setText(f"{tr('绘制BOX')}({sc})")
            self.canvas.update()

    def _delete_selected_box(self):
        saved = False
        selected_boxes = sorted({
            index for index in getattr(self.canvas, 'selected_boxes', [])
            if 0 <= index < len(self.detection_boxes)
        }, reverse=True)
        if selected_boxes:
            self.save_undo_state()
            saved = True
            for index in selected_boxes:
                del self.detection_boxes[index]
            self.canvas.selected_box = None
            self.canvas.selected_boxes = []
            if self.current_background_index >= 0:
                self.detection_boxes_dict[self.current_background_index] = \
                    self.detection_boxes.copy()
            self.update_label_list()
            self.canvas.update()
            if self.current_background and self.current_background_index >= 0:
                background_path = self.background_images[self.current_background_index]
                background_name = os.path.basename(background_path)
                self.save_json(background_path, background_name, "", canvas_items=[])

        if (self.canvas.selected_box is not None and
                0 <= self.canvas.selected_box < len(self.detection_boxes)):
            if not saved:
                self.save_undo_state()
                saved = True
            del self.detection_boxes[self.canvas.selected_box]
            self.canvas.selected_box = None
            self.canvas.selected_boxes = []
            if self.current_background_index >= 0:
                self.detection_boxes_dict[self.current_background_index] = \
                    self.detection_boxes.copy()
            self.update_label_list()
            self.canvas.update()
            if self.current_background and self.current_background_index >= 0:
                background_path = self.background_images[self.current_background_index]
                background_name = os.path.basename(background_path)
                self.save_json(background_path, background_name, "", canvas_items=[])

        if (self.selected_item is not None and
                0 <= self.selected_item < len(self.canvas_items)):
            if not saved:
                self.save_undo_state()
            del self.canvas_items[self.selected_item]
            self.selected_item = None
            self.canvas.update()

    def keyPressEvent(self, event):
        """键盘按下事件"""
        super().keyPressEvent(event)

    def installEventFilterRecursive(self, widget):
        """递归安装事件过滤器"""
        widget.installEventFilter(self)
        for child in widget.children():
            self.installEventFilterRecursive(child)

    def eventFilter(self, obj, event):
        return super().eventFilter(obj, event)

    def toggle_draw_mode(self):
        """切换绘制模式"""
        if not self.background_images or self.current_background_index < 0:
            return

        if not self.canvas.is_drawing_box:
            self.canvas.is_drawing_box = True
            self.canvas.setCursor(Qt.CrossCursor)

            self.selected_item = None
            self.canvas.selected_box = None
            self.canvas.selected_boxes = []

            self.canvas.setFocus()
            self.canvas.update()

    def switch_background(self, direction):
        """切换背景图"""
        if self._is_delete_view:
            if not hasattr(self, '_delete_files') or not self._delete_files:
                return
            step = getattr(self, '_nav_step', 1)
            idx = self._delete_current_idx if hasattr(self, '_delete_current_idx') else 0
            new_idx = max(0, min(idx + direction * step, len(self._delete_files) - 1))
            if new_idx != idx:
                self._delete_current_idx = new_idx
                self._load_delete_image(new_idx)
                self.background_list.setCurrentRow(new_idx)
                if self.current_background:
                    filename = os.path.basename(self._delete_files[new_idx])
                    w = self.current_background.width()
                    h = self.current_background.height()
                    total = len(self._delete_files)
                    self.setWindowTitle(f"PasteLabel - {filename} [{w} x {h}] [{new_idx + 1} / {total}]")
        else:
            if not self.background_images:
                return
            step = getattr(self, '_nav_step', 1)
            new_index = self.current_background_index + direction * step
            self.switch_background_to_index(new_index)

    def switch_background_to_index(self, new_index):
        """切换到指定索引的背景图"""
        if not self.background_images:
            return

        new_index = max(0, min(new_index, len(self.background_images) - 1))

        if new_index == self.current_background_index:
            return

        if self.current_background_index >= 0:
            self.canvas_items_dict[self.current_background_index] = self.canvas_items.copy()
            self.detection_boxes_dict[self.current_background_index] = self.detection_boxes.copy()
            self.save_current_json()
            if hasattr(self, 'auto_save_checkbox') and self.auto_save_checkbox.isChecked() and self.canvas_items:
                self.auto_save_current_canvas()

        self.current_background_index = new_index

        file_path = self.background_images[new_index]
        pixmap = self._get_cached_pixmap(file_path)
        if not pixmap.isNull():
            self.current_background = pixmap
            self._load_detection_boxes_for_index(new_index, file_path)
        else:
            self.current_background = None
            self.detection_boxes = []

        if new_index not in self.canvas_items_dict:
            self.canvas_items_dict[new_index] = []
        self.canvas_items = self.canvas_items_dict[new_index].copy()

        self.update_label_list()
        self.canvas.reset_view()

        self.background_list.setCurrentRow(new_index)
        self.update_file_count()
        self.selected_item = None
        self.canvas.selected_box = None
        self.canvas.selected_boxes = []
        self.canvas.update()

    def on_labels_checkbox_changed(self):
        """标签复选框变化"""
        self.canvas.update()

    def label_list_item_pressed(self, item):
        """标签列表按下项目 - 记录按下的标签用于高亮检测框"""
        try:
            if item is None:
                return
            item_text = item.text()
            if " (" in item_text:
                self.pressed_label = extract_label_name(item_text)
            else:
                self.pressed_label = item_text
            self.canvas.update()
        except Exception as e:
            import traceback
            error_msg = traceback.format_exc()
            self._log_error(f"label_list_item_pressed 错误: {e}\n{error_msg}")

    def label_list_item_clicked(self, item):
        """标签列表点击项目释放 - 清除高亮"""
        try:
            self.pressed_label = None
            self.canvas.update()
        except Exception as e:
            import traceback
            error_msg = traceback.format_exc()
            self._log_error(f"label_list_item_clicked 错误: {e}\n{error_msg}")

    def closeEvent(self, event):
        """关闭窗口事件 - 直接关闭，不弹确认框"""
        if self.current_background_index >= 0:
            self.canvas_items_dict[self.current_background_index] = self.canvas_items.copy()
            self.detection_boxes_dict[self.current_background_index] = self.detection_boxes.copy()
            self.save_current_json()
        if hasattr(self, '_save_memory_record_on_close'):
            self._save_memory_record_on_close()
        event.accept()
