"""
保存管理器模块 - 处理贴图保存、JSON 生成等逻辑
"""

import os
import json
from PyQt5.QtCore import QRectF
from .config import LABELME_VERSION, DEFAULT_PREFIX


class SaveManager:
    """保存管理器 - 管理贴图的保存操作"""
    
    def __init__(self, editor):
        """
        :param editor: ImageEditor 实例引用
        """
        self.editor = editor
    
    def get_save_info(self):
        """获取保存信息"""
        if self.editor.current_background is None or self.editor.current_background_index < 0:
            return None
        
        original_file_path = self.editor.background_images[self.editor.current_background_index]
        original_file_name = os.path.basename(original_file_path)
        
        background_dir = os.path.dirname(original_file_path)
        output_dir = f"{background_dir}_paste_output"
        os.makedirs(output_dir, exist_ok=True)
        
        prefix = ""
        if hasattr(self.editor, 'prefix_checkbox') and self.editor.prefix_checkbox.isChecked():
            prefix = self.editor.prefix_input.text().strip()
            if not prefix:
                prefix = DEFAULT_PREFIX
        
        base_name = f"{prefix}_{original_file_name}" if prefix else original_file_name
        file_path = os.path.join(output_dir, base_name)
        
        return (file_path, base_name, prefix)
    
    def auto_save_current_canvas(self):
        """自动保存当前画布"""
        from PyQt5.QtGui import QPixmap, QPainter, QColor
        
        if self.editor.current_background is None or not self.editor.canvas_items:
            return
        
        save_info = self.get_save_info()
        if not save_info:
            return
        
        file_path, base_name, prefix = save_info
        
        result = QPixmap(self.editor.current_background.size())
        painter = QPainter(result)
        painter.fillRect(result.rect(), QColor(255, 255, 255))
        painter.drawPixmap(0, 0, self.editor.current_background)
        
        for pixmap, rect, label in self.editor.canvas_items:
            painter.drawPixmap(rect.toRect(), pixmap)
        
        painter.end()
        if not result.save(file_path):
            print(f"自动保存失败: {file_path}")
        self.save_json(file_path, base_name, prefix)
    
    def save_canvas(self):
        """保存当前画布"""
        from PyQt5.QtWidgets import QMessageBox
        from PyQt5.QtGui import QPixmap, QPainter, QColor
        from .dialogs import SaveTipDialog
        
        if self.editor.current_background is None:
            QMessageBox.warning(self.editor, "警告", "请先选择背景图片")
            return
        
        save_info = self.get_save_info()
        if not save_info:
            QMessageBox.warning(self.editor, "警告", "无法获取保存信息")
            return
        
        file_path, base_name, prefix = save_info
        
        result = QPixmap(self.editor.current_background.size())
        painter = QPainter(result)
        painter.fillRect(result.rect(), QColor(255, 255, 255))
        painter.drawPixmap(0, 0, self.editor.current_background)
        
        for pixmap, rect, label in self.editor.canvas_items:
            painter.drawPixmap(rect.toRect(), pixmap)
        
        painter.end()
        save_success = result.save(file_path)
        
        self.save_json(file_path, base_name, prefix)
        
        SaveTipDialog.show_save_tip(self.editor, file_path, save_success and os.path.exists(file_path))
    
    def save_all_canvas(self):
        """保存所有画布"""
        from PyQt5.QtWidgets import QMessageBox, QApplication
        from PyQt5.QtGui import QPixmap, QPainter, QColor
        from .dialogs import ProgressDialogFactory
        
        if not self.editor.background_images:
            QMessageBox.warning(self.editor, "警告", "没有背景图片可保存")
            return
        
        progress_dialog = ProgressDialogFactory.create_progress_dialog(
            self.editor, "保存进度", "正在保存所有图片...", len(self.editor.background_images)
        )
        progress_dialog.show()
        QApplication.processEvents()  # 确保进度条立即显示
        
        original_background = self.editor.current_background
        original_index = self.editor.current_background_index
        original_canvas_items = self.editor.canvas_items.copy()
        
        saved_count = 0
        for i, file_path in enumerate(self.editor.background_images):
            if progress_dialog.wasCanceled():
                break
            
            progress_dialog.setValue(i)
            progress_dialog.setLabelText(f"正在保存第 {i+1} 张图片...")
            
            pixmap = QPixmap(file_path)
            if pixmap.isNull():
                continue
            
            temp_canvas_items = self.editor.canvas_items_dict.get(i, [])
            
            original_file_name = os.path.basename(file_path)
            background_dir = os.path.dirname(file_path)
            output_dir = f"{background_dir}_paste_output"
            os.makedirs(output_dir, exist_ok=True)
            
            prefix = ""
            if hasattr(self.editor, 'prefix_checkbox') and self.editor.prefix_checkbox.isChecked():
                prefix = self.editor.prefix_input.text().strip()
                if not prefix:
                    prefix = DEFAULT_PREFIX
            
            base_name = f"{prefix}_{original_file_name}" if prefix else original_file_name
            save_file_path = os.path.join(output_dir, base_name)
            
            result = QPixmap(pixmap.size())
            painter = QPainter(result)
            painter.fillRect(result.rect(), QColor(255, 255, 255))
            painter.drawPixmap(0, 0, pixmap)
            
            for p_pixmap, rect, label in temp_canvas_items:
                painter.drawPixmap(rect.toRect(), p_pixmap)
            
            painter.end()
            if not result.save(save_file_path):
                print(f"批量保存失败: {save_file_path}")
            
            self.save_json(save_file_path, base_name, prefix, temp_canvas_items,
                          pixmap.width(), pixmap.height(), i)
            
            saved_count += 1
            
            # 处理事件，确保进度条更新
            QApplication.processEvents()
        
        progress_dialog.setValue(len(self.editor.background_images))
        
        # 关闭进度对话框
        progress_dialog.close()
        
        # 显示保存结果
        from PyQt5.QtWidgets import QMessageBox
        if saved_count > 0:
            QMessageBox.information(
                self.editor, "保存完成",
                f"全部保存完成！\n成功保存 {saved_count} 张图片。"
            )
        else:
            QMessageBox.warning(
                self.editor, "保存结果",
                "没有保存任何图片。"
            )
        
        if original_index >= 0:
            self.editor.current_background = original_background
            self.editor.current_background_index = original_index
            self.editor.canvas_items = original_canvas_items
            self.editor.background_list.setCurrentRow(original_index)
            self.editor.update_file_count()
            self.editor.canvas.update()
        
        self.editor.update_label_list()
    
    def save_json(self, image_path, image_name, label_prefix, canvas_items=None,
                 image_width=None, image_height=None, current_index=None):
        """生成并保存 JSON 文件"""
        json_path = os.path.splitext(image_path)[0] + '.json'
        
        items_to_use = canvas_items if canvas_items is not None else self.editor.canvas_items
        width = image_width if image_width is not None else (
            self.editor.current_background.width() if self.editor.current_background else 0
        )
        height = image_height if image_height is not None else (
            self.editor.current_background.height() if self.editor.current_background else 0
        )
        index_to_use = current_index if current_index is not None else self.editor.current_background_index
        
        json_data = {
            "version": LABELME_VERSION,
            "flags": {},
            "shapes": [],
            "imagePath": image_name,
            "imageData": None,
            "imageHeight": height,
            "imageWidth": width
        }
        
        # 添加贴图
        for pixmap, rect, label in items_to_use:
            x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
            points = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]
            
            shape = {
                "label": label,
                "points": points,
                "group_id": None,
                "description": "",
                "shape_type": "rectangle",
                "flags": {}
            }
            json_data["shapes"].append(shape)
        
        # 添加检测框
        if index_to_use >= 0 and index_to_use in self.editor.detection_boxes_dict:
            for box in self.editor.detection_boxes_dict[index_to_use]:
                x, y, w, h = box['x'], box['y'], box['width'], box['height']
                label = box['label']
                points = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]
                
                shape = {
                    "label": label,
                    "points": points,
                    "group_id": None,
                    "description": "",
                    "shape_type": "rectangle",
                    "flags": {}
                }
                json_data["shapes"].append(shape)
        
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存 JSON 失败: {json_path}, 错误: {e}")
