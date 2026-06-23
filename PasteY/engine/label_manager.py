"""
标签管理器模块 - 管理标签的增删改查操作
"""

from typing import TYPE_CHECKING
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QMenu, QAction, QInputDialog, QMessageBox, QListWidgetItem

from ..core.utils import extract_label_name

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
            modify_action = menu.addAction("修改标签")
            modify_action.triggered.connect(self.modify_paste_label)
            
            delete_action = menu.addAction("删除标签")
            delete_action.triggered.connect(self.delete_paste_label)
            
            menu.addSeparator()
        
        add_action = menu.addAction("增加标签")
        add_action.triggered.connect(self.add_paste_label)
        
        menu.exec_(self.editor.paste_label_list.mapToGlobal(position))
    
    def add_paste_label(self):
        """增加贴图标签"""
        label_name, ok = QInputDialog.getText(
            self.editor, "增加贴图标签", "请输入新的贴图标签名称:"
        )
        
        if ok and label_name.strip():
            label_name = label_name.strip()
            
            existing_labels = set()
            for i in range(self.editor.paste_label_list.count()):
                existing_labels.add(self.editor.paste_label_list.item(i).text())
            
            if label_name in existing_labels:
                QMessageBox.warning(self.editor, "警告", "标签名称已存在，请输入不同的名称")
                return
            
            self.editor.paste_label_list.addItem(label_name)
    
    def modify_paste_label(self):
        """修改贴图标签"""
        selected_items = self.editor.paste_label_list.selectedItems()
        if not selected_items:
            return
        
        old_label = selected_items[0].text()
        new_label, ok = QInputDialog.getText(
            self.editor, "修改贴图标签", f"请输入新的贴图标签名称:", text=old_label
        )
        
        if ok and new_label.strip():
            new_label = new_label.strip()
            
            existing_labels = set()
            for i in range(self.editor.paste_label_list.count()):
                existing_labels.add(self.editor.paste_label_list.item(i).text())
            
            if new_label in existing_labels and new_label != old_label:
                QMessageBox.warning(self.editor, "警告", "标签名称已存在，请输入不同的名称")
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
        
        reply = QMessageBox.question(
            self.editor, "确认删除", 
            f"确定要删除贴图标签 '{label_to_delete}' 吗？删除后，所有使用该标签的贴图也会被删除。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
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
            modify_action = menu.addAction("修改标签")
            modify_action.triggered.connect(self.modify_label)
            
            delete_action = menu.addAction("删除标签")
            delete_action.triggered.connect(self.delete_label)
            
            menu.addSeparator()
        
        add_action = menu.addAction("增加标签")
        add_action.triggered.connect(self.add_label)
        
        menu.exec_(self.editor.label_list.mapToGlobal(position))
    
    def modify_label(self):
        """修改标签名称"""
        selected_items = self.editor.label_list.selectedItems()
        if not selected_items:
            return
        
        # 从列表中获取旧标签名称（去除计数部分）
        old_label_text = selected_items[0].text()
        old_label = extract_label_name(old_label_text)
        
        # 输入新标签名称
        new_label, ok = QInputDialog.getText(
            self.editor, "修改标签", f"请输入新的标签名称:", text=old_label
        )
        
        if ok and new_label.strip():
            new_label = new_label.strip()
            
            # 更新检测框中的标签
            for box in self.editor.detection_boxes:
                if box.get("label") == old_label:
                    box["label"] = new_label
            
            # 更新 detection_boxes_dict 中的标签
            for index in self.editor.detection_boxes_dict:
                for box in self.editor.detection_boxes_dict[index]:
                    if box.get("label") == old_label:
                        box["label"] = new_label
            
            # 更新全局标签
            if old_label in self.editor.global_labels:
                self.editor.global_labels.remove(old_label)
                self.editor.global_labels.add(new_label)
            
            self.label_list_changed.emit()
            self.data_changed.emit()
    
    def delete_label(self):
        """删除标签"""
        selected_items = self.editor.label_list.selectedItems()
        if not selected_items:
            return
        
        label_text = selected_items[0].text()
        label_to_delete = extract_label_name(label_text)
        
        reply = QMessageBox.question(
            self.editor, "确认删除",
            f"确定要删除标签 '{label_to_delete}' 吗？\n将从所有背景中删除该标签的检测框。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 从当前检测框中删除
            self.editor.detection_boxes = [
                box for box in self.editor.detection_boxes
                if box.get("label") != label_to_delete
            ]
            self.editor.canvas.selected_box = None
            
            # 从所有背景的检测框中删除
            for index in self.editor.detection_boxes_dict:
                self.editor.detection_boxes_dict[index] = [
                    box for box in self.editor.detection_boxes_dict[index]
                    if box.get("label") != label_to_delete
                ]
            
            # 更新全局标签
            if label_to_delete in self.editor.global_labels:
                self.editor.global_labels.remove(label_to_delete)
            
            self.label_list_changed.emit()
            self.data_changed.emit()
    
    def add_label(self, label_name=None):
        """添加标签"""
        if label_name is None:
            label_name, ok = QInputDialog.getText(
                self.editor, "增加标签", "请输入新的标签名称:"
            )
            if not (ok and label_name.strip()):
                return
            label_name = label_name.strip()
        
        if label_name not in self.editor.global_labels:
            self.editor.global_labels.add(label_name)
            self.label_list_changed.emit()
    
    def update_global_labels(self):
        """更新全局标签集合"""
        for index in self.editor.detection_boxes_dict:
            for box in self.editor.detection_boxes_dict[index]:
                if "label" in box:
                    self.editor.global_labels.add(box["label"])
    
    def update_label_list(self):
        """更新标签列表显示"""
        self.update_global_labels()
        self.editor.label_list.clear()
        
        if self.editor.current_background is None:
            return
        
        label_counts = {}
        for box in self.editor.detection_boxes:
            if "label" in box:
                label = box["label"]
                label_counts[label] = label_counts.get(label, 0) + 1
        
        label_count_list = []
        for label in self.editor.global_labels:
            count = label_counts.get(label, 0)
            label_count_list.append((label, count))
        
        label_count_list.sort(key=lambda x: (-x[1], x[0]))
        
        for label, count in label_count_list:
            item = QListWidgetItem(f"{label} ({count})")
            self.editor.label_list.addItem(item)
