"""
事件处理混入 - 负责键盘、窗口事件和绘制模式切换
"""
import os
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QEvent

from ..core.utils import extract_label_name


class EventHandlerMixin:
    """事件处理混入类 - 键盘事件、事件过滤器、绘制模式、背景图切换"""

    def keyPressEvent(self, event):
        """键盘按下事件"""
        modifiers = event.modifiers()

        if event.key() == Qt.Key_A:
            self.switch_background(-1)
        elif event.key() == Qt.Key_D:
            self.switch_background(1)
        elif event.key() == Qt.Key_R:
            current_state = self.show_labels_checkbox.isChecked()
            self.show_labels_checkbox.setChecked(not current_state)
            self.on_labels_checkbox_changed()
        elif event.key() == Qt.Key_T:
            if hasattr(self, 'show_label_names_checkbox'):
                current_state = self.show_label_names_checkbox.isChecked()
                self.show_label_names_checkbox.setChecked(not current_state)
                self.on_labels_checkbox_changed()
        elif event.key() == Qt.Key_G and modifiers & Qt.ControlModifier:
            self.toggle_grid()
        elif event.key() == Qt.Key_G and not modifiers:
            current_state = self.auto_save_checkbox.isChecked()
            self.auto_save_checkbox.setChecked(not current_state)
            self.auto_save_current_canvas()
        elif event.key() == Qt.Key_F and not modifiers:
            current_state = self.show_paste_names_checkbox.isChecked()
            self.show_paste_names_checkbox.setChecked(not current_state)
            self.canvas.update()
        elif event.key() == Qt.Key_W:
            self.toggle_draw_mode()
        elif event.key() == Qt.Key_Q:
            if self.canvas.is_drawing_box:
                self.canvas.is_drawing_box = False
                self.canvas.draw_start_pos = None
                self.canvas.temp_draw_box = None
                self.canvas.setCursor(Qt.ArrowCursor)
                if hasattr(self, 'draw_box_btn'):
                    self.draw_box_btn.setText("绘制BOX(W)")
                self.canvas.update()
        elif event.key() == Qt.Key_Delete or event.key() == Qt.Key_E:
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
        elif event.key() == Qt.Key_Z and modifiers & Qt.ControlModifier:
            self.undo()
        elif event.key() == Qt.Key_Y and modifiers & Qt.ControlModifier:
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
            error_msg = "".join(traceback.format_exc())
            self._log_error(f"label_list_item_pressed 错误: {e}\n{error_msg}")

    def label_list_item_clicked(self, item):
        """标签列表点击项目释放 - 清除高亮"""
        try:
            self.pressed_label = None
            self.canvas.update()
        except Exception as e:
            import traceback
            error_msg = "".join(traceback.format_exc())
            self._log_error(f"label_list_item_clicked 错误: {e}\n{error_msg}")

    def closeEvent(self, event):
        """关闭窗口事件 - 直接关闭，不弹确认框"""
        event.accept()
