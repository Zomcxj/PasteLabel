"""
图片加载混入 - 负责背景图、贴图、检测框的加载和管理
"""
import os
import json
from PyQt5.QtWidgets import (
    QFileDialog, QListWidgetItem, QMessageBox
)
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, QSize

from ..core.config import SUPPORTED_IMAGE_EXTENSIONS
from ..core.utils import PathUtils, natural_sort_key, create_thumbnail


class ImageLoaderMixin:
    """图片加载混入类 - 加载背景图、贴图、检测框"""

    def upload_background(self):
        """上传背景图片"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择背景图片", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if files:
            self.background_images.clear()
            self.background_list.clear()
            self.current_background = None
            self.detection_boxes_dict.clear()
            self.canvas_items_dict.clear()

            for file in files:
                pixmap = QPixmap(file)
                if not pixmap.isNull():
                    new_index = len(self.background_images)
                    self.background_images.append(file)
                    display_path = PathUtils.to_display_path(file)
                    item = QListWidgetItem(display_path)
                    item.setData(Qt.UserRole, new_index)
                    self.background_list.addItem(item)

                    self.canvas_items_dict[new_index] = []
                    self.detection_boxes_dict[new_index] = self.load_detection_boxes(file)

                    if self.current_background is None:
                        self.current_background = pixmap
                        self.current_background_index = new_index
                        self.canvas_items = []
                        self.detection_boxes = self.detection_boxes_dict[new_index].copy()
                        self.update_label_list()
                        self.canvas.background_scale = 1.0
                        self.canvas.is_manual_scale = False
                        self.canvas.update()

        self.update_file_count()

    def load_folder_images(self):
        """从文件夹加载背景图"""
        folder_path = QFileDialog.getExistingDirectory(self, "选择图片文件夹", "")
        if not folder_path:
            return

        self.background_images.clear()
        self.background_list.clear()
        self.current_background = None
        self.detection_boxes_dict.clear()

        for file_name in sorted(os.listdir(folder_path), key=natural_sort_key):
            ext = os.path.splitext(file_name)[1].lower()
            if ext in SUPPORTED_IMAGE_EXTENSIONS:
                file_path = os.path.join(folder_path, file_name)
                new_index = len(self.background_images)
                self.background_images.append(file_path)
                display_path = PathUtils.to_display_path(file_path)
                item = QListWidgetItem(display_path)
                item.setData(Qt.UserRole, new_index)
                self.background_list.addItem(item)

                self.canvas_items_dict[new_index] = []
                self.detection_boxes_dict[new_index] = []

        if self.background_images:
            self.current_background_index = 0
            self.background_list.setCurrentRow(0)
            self.load_image_by_index(0)
            self.update_label_list()
            self.update_file_count()
        else:
            QMessageBox.warning(self, "警告", "该文件夹中没有找到支持的图片文件")
            self.update_file_count()

    def upload_small_images(self):
        """上传贴图"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择贴图片", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if files:
            self.small_images.clear()
            self.small_list.clear()

            for file in files:
                pixmap = QPixmap(file)
                if not pixmap.isNull():
                    self.small_images.append((file, pixmap))
                    file_name = os.path.basename(file)
                    self.add_list_item(file_name, pixmap)

        self._update_paste_count_spin()
        self._refresh_small_list_view()

    def load_small_folder_images(self):
        """从文件夹加载贴图"""
        folder_path = QFileDialog.getExistingDirectory(self, "选择贴图文件夹", "")
        if not folder_path:
            return

        self.small_images.clear()
        self.small_list.clear()

        loaded_count = 0
        for file_name in sorted(os.listdir(folder_path), key=natural_sort_key):
            ext = os.path.splitext(file_name)[1].lower()
            if ext in SUPPORTED_IMAGE_EXTENSIONS:
                file_path = os.path.join(folder_path, file_name)
                pixmap = QPixmap(file_path)
                if not pixmap.isNull():
                    self.small_images.append((file_path, pixmap))
                    self.add_list_item(file_name, pixmap)
                    loaded_count += 1

        if loaded_count == 0:
            QMessageBox.warning(self, "警告", "该文件夹中没有找到支持的图片文件")

        self._update_paste_count_spin()
        self._refresh_small_list_view()

    def _update_paste_count_spin(self):
        """更新贴图个数输入框"""
        if hasattr(self, 'paste_count_spin'):
            if len(self.small_images) <= 5:
                self.paste_count_spin.setValue(len(self.small_images))
                self.paste_count_spin.setMaximum(len(self.small_images))
            else:
                self.paste_count_spin.setMaximum(len(self.small_images))

    def _refresh_small_list_view(self):
        """刷新贴图列表视图"""
        if hasattr(self, 'is_thumbnail_mode'):
            if self.is_thumbnail_mode:
                self._configure_small_list()
            else:
                self.small_list.setViewMode(QListWidget.ListMode)
                self.small_list.setIconSize(QSize())
                self.small_list.setGridSize(QSize())
                self.small_list.setSpacing(0)
                self.small_list.setWrapping(False)
                self.small_list.setFlow(QListWidget.TopToBottom)
                self.small_list.setVerticalScrollMode(QListWidget.ScrollPerItem)

            self.refresh_list_items()
            self.small_list.scrollToTop()
            self.small_list.updateGeometry()
            self.small_list.repaint()

    def add_list_item(self, file_name, pixmap):
        """添加列表项"""
        item = QListWidgetItem(file_name)

        if self.is_thumbnail_mode:
            thumb_pixmap = create_thumbnail(pixmap, self.thumbnail_grid_width, self.thumbnail_grid_height)
            item.setIcon(QIcon(thumb_pixmap))
            item.setSizeHint(QSize(self.thumbnail_grid_width, self.thumbnail_grid_height + 20))

        item.setData(Qt.UserRole, len(self.small_images) - 1)
        self.small_list.addItem(item)

    def refresh_list_items(self):
        """刷新列表项"""
        self.small_list.clear()
        for idx, (file_path, pixmap) in enumerate(self.small_images):
            file_name = os.path.basename(file_path)
            item = QListWidgetItem(file_name)

            if self.is_thumbnail_mode:
                thumb_pixmap = create_thumbnail(pixmap, self.thumbnail_grid_width, self.thumbnail_grid_height)
                item.setIcon(QIcon(thumb_pixmap))
                item.setSizeHint(QSize(self.thumbnail_grid_width, self.thumbnail_grid_height + 20))

            item.setData(Qt.UserRole, idx)
            self.small_list.addItem(item)

    def upload_paste_labels(self):
        """上传贴图标签文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择贴图标签文件", "", "Text Files (*.txt)"
        )
        if file_path:
            try:
                labels = []
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            parts = line.split()
                            if parts:
                                labels.append(parts[0])

                if labels:
                    self.paste_label_list.clear()
                    for label in labels:
                        self.paste_label_list.addItem(label)
                else:
                    QMessageBox.warning(self, "警告", "未找到有效的标签")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"读取标签文件失败：{e}")

    def _load_detection_boxes_for_index(self, index, file_path):
        """加载指定索引的检测框（优先从缓存，否则从文件）"""
        if index in self.detection_boxes_dict and len(self.detection_boxes_dict[index]) > 0:
            self.detection_boxes = self.detection_boxes_dict[index].copy()
        else:
            self.detection_boxes = self.load_detection_boxes(file_path)
            self.detection_boxes_dict[index] = self.detection_boxes.copy()

    def load_detection_boxes(self, file_path):
        """加载检测框 JSON 文件"""
        base_name = os.path.splitext(file_path)[0]
        json_path = f"{base_name}.json"
        detection_boxes = []

        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "shapes" in data:
                        shapes = data["shapes"]
                        if isinstance(shapes, list):
                            for shape in shapes:
                                if isinstance(shape, dict) and all(key in shape for key in ["label", "points"]):
                                    label = shape["label"]
                                    points = shape["points"]

                                    if len(points) >= 2:
                                        x_coords = [point[0] for point in points]
                                        y_coords = [point[1] for point in points]
                                        x = min(x_coords)
                                        y = min(y_coords)
                                        width = max(x_coords) - x
                                        height = max(y_coords) - y

                                        detection_boxes.append({
                                            "x": x,
                                            "y": y,
                                            "width": width,
                                            "height": height,
                                            "label": label
                                        })
            except Exception as e:
                print(f"加载检测框文件失败：{e}")

        return detection_boxes

    def load_image_by_index(self, index):
        """加载指定索引的图片"""
        if 0 <= index < len(self.background_images):
            file_path = self.background_images[index]
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                self.current_background = pixmap
                self._load_detection_boxes_for_index(index, file_path)
                self.canvas.reset_view()
                self.update_label_list()
                self.canvas.update()
            else:
                print(f"警告: 图片加载失败或为空: {file_path}")

    def select_background(self, item):
        """选择背景图"""
        if self._busy:
            return
        try:
            if item is None:
                return
            index = item.data(Qt.UserRole)
            if index is None:
                return

            if self.current_background_index >= 0:
                self.canvas_items_dict[self.current_background_index] = self.canvas_items.copy()
                self.detection_boxes_dict[self.current_background_index] = self.detection_boxes.copy()
                background_path = self.background_images[self.current_background_index]
                background_name = os.path.basename(background_path)
                self.save_json(background_path, background_name, "", canvas_items=[])

            self.current_background_index = index

            if index not in self.canvas_items_dict:
                self.canvas_items_dict[index] = []
            self.canvas_items = self.canvas_items_dict[index].copy()

            if 0 <= index < len(self.background_images):
                file_path = self.background_images[index]
                pixmap = QPixmap(file_path)
                if not pixmap.isNull():
                    self.current_background = pixmap
                    self._load_detection_boxes_for_index(index, file_path)
                else:
                    self.current_background = None
                    self.detection_boxes = []

            self.update_label_list()
            self.canvas.reset_view()
            self.selected_item = None
            self.canvas.update()

            total = len(self.background_images)
            if total > 0:
                current = index + 1
                self.file_count_label.setText(f"[ {current} / {total} ]")
                self.file_count_label.show()
            else:
                self.file_count_label.hide()
        except Exception as e:
            import traceback
            error_msg = "".join(traceback.format_exc())
            self._log_error(f"select_background 错误: {e}\n{error_msg}")

    def update_file_count(self):
        """更新文件计数显示"""
        total = len(self.background_images)
        if total > 0:
            current = self.current_background_index + 1 if self.current_background_index >= 0 else 1
            self.file_count_label.setText(f"[ {current} / {total} ]")
            self.file_count_label.show()
        else:
            self.file_count_label.hide()

    def _log_error(self, message):
        """记录错误信息"""
        try:
            from datetime import datetime
            log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash_log.txt")
            with open(log_path, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] {message}\n")
        except Exception:
            pass
