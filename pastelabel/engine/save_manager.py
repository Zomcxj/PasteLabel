"""
保存管理器模块 - 处理贴图保存、JSON 生成等逻辑
"""

import os
import json
from typing import TYPE_CHECKING
from PyQt5.QtCore import pyqtSignal, QObject, Qt, QRectF
from PyQt5.QtGui import QPixmap, QPainter, QColor
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QApplication
from ..core.config import LABELME_VERSION, DEFAULT_PREFIX
from ..core.utils import PathUtils, calculate_iou
from ..ui.i18n import t as tr

if TYPE_CHECKING:
    from ..core.editor_protocol import EditorProtocol


class _SyncTitleBarDialog(QDialog):
    """标题栏同步的对话框"""
    def __init__(self, msg_type, title, text, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(280)
        self.setMaximumWidth(400)
        self.setObjectName("syncDialog")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        text_layout = QHBoxLayout()
        text_layout.setSpacing(8)

        icon_label = QLabel("⚠")
        icon_label.setStyleSheet("background: transparent; font-size: 20px; color: #FF9800;")
        icon_label.setFixedWidth(24)

        text_label = QLabel(text)
        text_label.setWordWrap(True)
        text_label.setStyleSheet("background: transparent; font-size: 13px;")

        text_layout.addWidget(icon_label)
        text_layout.addWidget(text_label, 1)
        layout.addLayout(text_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        from ..ui import i18n
        tr = i18n.t
        ok_btn = QPushButton(tr("确定"))
        ok_btn.setObjectName("successBtn")
        ok_btn.setFixedWidth(80)
        from ..ui.theme import ThemeManager
        ok_btn.setStyleSheet(ThemeManager.get_dialog_button_style())
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

    def showEvent(self, event):
        super().showEvent(event)
        from ..ui.dialog_helpers import center_on_parent
        center_on_parent(self)
        self._sync()

    def _sync(self):
        from ..ui.dwm import set_titlebar_dark
        from ..ui.theme import ThemeManager
        is_dark = ThemeManager.get_mode().value == "dark"
        hwnd = int(self.winId())
        set_titlebar_dark(hwnd, is_dark)


def _show_messagebox(msg_type, parent, title, text):
    """显示同步标题栏颜色的对话框"""
    from ..ui import i18n
    tr = i18n.t
    dialog = _SyncTitleBarDialog(msg_type, tr(title), tr(text), parent)
    dialog.exec_()


class SaveManager(QObject):
    """保存管理器 - 管理贴图的保存操作"""

    # 信号：保存完成后通知编辑器刷新 UI
    save_completed = pyqtSignal()
    label_list_changed = pyqtSignal()

    def __init__(self, editor: "EditorProtocol", parent=None):
        """
        :param editor: 实现 EditorProtocol 的编辑器实例
        """
        super().__init__(parent)
        self.editor = editor
    
    def get_save_info(self):
        """获取保存信息"""
        if self.editor.current_background is None or self.editor.current_background_index < 0:
            return None
        
        original_file_path = self.editor.background_images[self.editor.current_background_index]
        original_file_name = os.path.basename(original_file_path)
        
        output_dir = PathUtils.get_output_dir(original_file_path)
        
        prefix = ""
        if hasattr(self.editor, 'prefix_checkbox') and self.editor.prefix_checkbox.isChecked():
            prefix = self.editor.prefix_input.text().strip()
            if not prefix:
                prefix = DEFAULT_PREFIX
        
        base_name = f"{prefix}_{original_file_name}" if prefix else original_file_name
        file_path = os.path.join(output_dir, base_name)
        
        return (file_path, base_name, prefix)
    
    def _get_save_info_or_none(self):
        if self.editor._is_delete_view or self.editor.current_background is None or not self.editor.canvas_items:
            return None
        return self.get_save_info()

    def auto_save_background(self):
        """自动保存合成图（B）"""
        save_info = self._get_save_info_or_none()
        if not save_info:
            return
        file_path, _, _ = save_info
        result = QPixmap(self.editor.current_background.size())
        painter = QPainter(result)
        painter.fillRect(result.rect(), QColor(255, 255, 255))
        painter.drawPixmap(0, 0, self.editor.current_background)
        for pixmap, rect, label in self.editor.canvas_items:
            painter.drawPixmap(rect.toRect(), pixmap)
        painter.end()
        if not result.save(file_path):
            from ..core.exception_hook import _write_log
            _write_log(f"自动保存B失败: {file_path}")

    def auto_save_project(self):
        """自动保存 JSON（P）"""
        save_info = self._get_save_info_or_none()
        if not save_info:
            return
        file_path, base_name, prefix = save_info
        self.save_json(file_path, base_name, prefix)
    
    def save_canvas(self):
        """保存当前画布"""
        from ..ui.dialogs import SaveTipDialog

        if self.editor._is_delete_view:
            return
        
        if self.editor.current_background is None:
            _show_messagebox("warning", self.editor, tr("警告"), tr("请先选择背景图片"))
            return
        
        save_info = self.get_save_info()
        if not save_info:
            _show_messagebox("warning", self.editor, tr("警告"), tr("无法获取保存信息"))
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
        
        if save_success:
            self.save_json(file_path, base_name, prefix)
        
        SaveTipDialog.show_save_tip(self.editor, file_path, save_success and os.path.exists(file_path))

    def save_current_json(self):
        """仅保存当前图的标注 JSON，供切图和关闭窗口时兜底。"""
        if self.editor._is_delete_view:
            return
        save_info = self.get_save_info()
        if not save_info:
            return
        self.save_json(*save_info)
    
    def save_all_canvas(self):
        """保存所有画布"""
        from ..ui.dialogs import ProgressDialogFactory

        if self.editor._is_delete_view or self.editor._busy:
            return

        if not self.editor.background_images:
            _show_messagebox("warning", self.editor, tr("警告"), tr("没有背景图片可保存"))
            return
        
        self.editor._busy = True

        progress_dialog = ProgressDialogFactory.create_progress_dialog(
            self.editor, tr("保存进度"), tr("正在保存所有图片..."), len(self.editor.background_images)
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
            progress_dialog.setLabelText(f"{tr('正在保存第')} {i+1} {tr('张图片')}...")
            
            pixmap = QPixmap(file_path)
            if pixmap.isNull():
                continue
            
            temp_canvas_items = self.editor.canvas_items_dict.get(i, [])
            
            original_file_name = os.path.basename(file_path)
            output_dir = PathUtils.get_output_dir(file_path)
            
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
                from ..core.exception_hook import _write_log
                _write_log(f"批量保存失败: {save_file_path}")
            
            self.save_json(save_file_path, base_name, prefix, temp_canvas_items,
                          pixmap.width(), pixmap.height(), i)
            
            saved_count += 1
            
            # 处理事件，确保进度条更新
            QApplication.processEvents()
        
        progress_dialog.setValue(len(self.editor.background_images))
        
        # 关闭进度对话框
        progress_dialog.close()
        
        # 显示保存结果
        if saved_count > 0:
            _show_messagebox(
                "information", self.editor, tr("保存完成"),
                f"{tr('全部保存完成！')}\n{tr('成功保存')} {saved_count} {tr('张图片')}。"
            )
        else:
            _show_messagebox(
                "warning", self.editor, tr("保存结果"),
                tr("没有保存任何图片。")
            )
        
        if original_index >= 0:
            self.editor.current_background = original_background
            self.editor.current_background_index = original_index
            self.editor.canvas_items = original_canvas_items
            self.save_completed.emit()
        
        self.label_list_changed.emit()
        self.editor._busy = False
    
    @staticmethod
    def _build_labelme_shape(label, x, y, w, h):
        """构建 LabelMe 格式的 shape 字典"""
        points = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]
        return {
            "label": label,
            "points": points,
            "group_id": None,
            "description": "",
            "shape_type": "rectangle",
            "flags": {}
        }

    @staticmethod
    def _deduplicate_rectangles(items, get_rect):
        """按列表顺序保留同类矩形中首个 IoU 达 98% 的对象。"""
        kept = []
        for item in items:
            rect = get_rect(item)
            box = (rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height())
            if any(calculate_iou(box, (
                saved_rect.x(), saved_rect.y(),
                saved_rect.x() + saved_rect.width(), saved_rect.y() + saved_rect.height(),
            )) >= 0.98 for saved_rect in (get_rect(saved) for saved in kept)):
                continue
            kept.append(item)
        return kept

    def save_json(self, image_path, image_name, label_prefix, canvas_items=None,
                 image_width=None, image_height=None, current_index=None):
        """生成并保存 JSON 文件"""
        if self.editor._is_delete_view:
            return
        json_path = os.path.splitext(image_path)[0] + '.json'
        
        items_to_use = canvas_items if canvas_items is not None else self.editor.canvas_items
        width = image_width if image_width is not None else (
            self.editor.current_background.width() if self.editor.current_background else 0
        )
        height = image_height if image_height is not None else (
            self.editor.current_background.height() if self.editor.current_background else 0
        )
        index_to_use = current_index if current_index is not None else self.editor.current_background_index
        items_to_use = self._deduplicate_rectangles(
            items_to_use,
            lambda item: item[1],
        )
        if canvas_items is None:
            self.editor.canvas_items = items_to_use
        elif isinstance(canvas_items, list):
            canvas_items[:] = items_to_use

        boxes_to_use = []
        if index_to_use >= 0 and index_to_use in self.editor.detection_boxes_dict:
            boxes_to_use = self._deduplicate_rectangles(
                self.editor.detection_boxes_dict[index_to_use],
                lambda box: QRectF(box['x'], box['y'], box['width'], box['height']),
            )
            self.editor.detection_boxes_dict[index_to_use] = boxes_to_use
            if index_to_use == self.editor.current_background_index:
                self.editor.detection_boxes = boxes_to_use.copy()
        
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
            shape = self._build_labelme_shape(
                label, rect.x(), rect.y(), rect.width(), rect.height()
            )
            json_data["shapes"].append(shape)
        
        # 添加检测框
        if index_to_use >= 0:
            for box in boxes_to_use:
                shape = self._build_labelme_shape(
                    box['label'], box['x'], box['y'], box['width'], box['height']
                )
                json_data["shapes"].append(shape)
        
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            from ..core.exception_hook import _write_log
            _write_log(f"保存 JSON 失败: {json_path}, 错误: {e}")
