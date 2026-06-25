"""
事件处理混入 - 负责键盘、窗口事件和绘制模式切换
"""
import os
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QEvent

from ..core.utils import extract_label_name
from ..core.config import SHORTCUT_CONFIG


class EventHandlerMixin:
    """事件处理混入类 - 键盘事件、事件过滤器、绘制模式、背景图切换"""

    def _get_shortcut(self, action):
        """获取快捷键配置"""
        if hasattr(self, 'shortcut_config'):
            return self.shortcut_config.get(action, SHORTCUT_CONFIG.get(action, ''))
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

    def keyPressEvent(self, event):
        """键盘按下事件"""
        if self._match_shortcut(event, 'prev_image'):
            self.switch_background(-1)
        elif self._match_shortcut(event, 'next_image'):
            self.switch_background(1)
        elif self._match_shortcut(event, 'toggle_labels'):
            current_state = self.show_labels_checkbox.isChecked()
            self.show_labels_checkbox.setChecked(not current_state)
        elif self._match_shortcut(event, 'toggle_label_names'):
            if hasattr(self, 'show_label_names_checkbox'):
                current_state = self.show_label_names_checkbox.isChecked()
                self.show_label_names_checkbox.setChecked(not current_state)
        elif self._match_shortcut(event, 'toggle_grid'):
            self.toggle_grid()
        elif self._match_shortcut(event, 'toggle_auto_save'):
            current_state = self.auto_save_checkbox.isChecked()
            self.auto_save_checkbox.setChecked(not current_state)
            self.auto_save_current_canvas()
        elif self._match_shortcut(event, 'toggle_paste_names'):
            current_state = self.show_paste_names_checkbox.isChecked()
            self.show_paste_names_checkbox.setChecked(not current_state)
            self.canvas.update()
        elif self._match_shortcut(event, 'draw_box'):
            self.toggle_draw_mode()
        elif self._match_shortcut(event, 'quit_draw'):
            if self.canvas.is_drawing_box:
                self.canvas.is_drawing_box = False
                self.canvas.draw_start_pos = None
                self.canvas.temp_draw_box = None
                self.canvas.setCursor(Qt.ArrowCursor)
                if hasattr(self, 'draw_box_btn'):
                    self.draw_box_btn.setText("绘制BOX(W)")
                self.canvas.update()
        elif self._match_shortcut(event, 'delete_selected'):
            if self.canvas.selected_box is not None and 0 <= self.canvas.selected_box < len(self.detection_boxes):
                self.save_undo_state()
                del self.detection_boxes[self.canvas.selected_box]
                self.canvas.selected_box = None
                if self.current_background_index >= 0:
                    self.detection_boxes_dict[self.current_background_index] = self.detection_boxes.copy()
                self.update_label_list()
                self.canvas.update()

                if self.current_background and self.current_background_index >= 0:
                    background_path = self.background_images[self.current_background_index]
                    background_name = os.path.basename(background_path)
                    self.save_json(background_path, background_name, "", canvas_items=[])
        elif self._match_shortcut(event, 'undo'):
            self.undo()
        elif self._match_shortcut(event, 'redo'):
            self.redo()

        super().keyPressEvent(event)

    def installEventFilterRecursive(self, widget):
        """递归安装事件过滤器"""
        widget.installEventFilter(self)
        for child in widget.children():
            self.installEventFilterRecursive(child)

    def eventFilter(self, obj, event):
        """事件过滤器"""
        if event.type() == QEvent.KeyPress:
            key = event.key()
            if key == Qt.Key_A:
                self.switch_background(-1)
                return True
            elif key == Qt.Key_D:
                self.switch_background(1)
                return True
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

            self.canvas.setFocus()
            self.canvas.update()

    def switch_background(self, direction):
        """切换背景图"""
        if not self.background_images:
            return

        new_index = self.current_background_index + direction
        self.switch_background_to_index(new_index)

    def switch_background_to_index(self, new_index):
        """切换到指定索引的背景图"""
        if not self.background_images:
            return

        new_index = max(0, min(new_index, len(self.background_images) - 1))

        if new_index == self.current_background_index:
            return

        if hasattr(self, 'auto_save_checkbox') and self.auto_save_checkbox.isChecked():
            if self.canvas_items:
                self.auto_save_current_canvas()

        if self.current_background_index >= 0:
            self.canvas_items_dict[self.current_background_index] = self.canvas_items.copy()
            self.detection_boxes_dict[self.current_background_index] = self.detection_boxes.copy()

        self.current_background_index = new_index

        file_path = self.background_images[new_index]
        pixmap = QPixmap(file_path)
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
        self._update_status_info()
        self.selected_item = None
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
        event.accept()
