"""
Canvas 右键菜单 - 贴图标签管理
"""
from PyQt5.QtWidgets import QMenu, QAction, QInputDialog
from PyQt5.QtCore import QPoint

from ..core.utils import extract_label_name


class CanvasMenuMixin:
    """右键菜单逻辑"""

    def _handle_right_click(self, mouse_pos):
        item_index = self.find_item_at_position(mouse_pos)
        if item_index is not None:
            self._show_paste_context_menu(item_index, mouse_pos)
            return True
        return False

    def _show_paste_context_menu(self, item_index, mouse_pos):
        menu = QMenu(self)

        label_items = []
        for i in range(self.parent.paste_label_list.count()):
            label = self.parent.paste_label_list.item(i).text()
            pure_label = extract_label_name(label)
            label_items.append(pure_label)

        for label in label_items:
            action = QAction(label, self)
            action.triggered.connect(
                lambda checked, l=label, idx=item_index: self.change_item_label(idx, l)
            )
            menu.addAction(action)

        menu.addSeparator()

        new_label_action = QAction("添加新标签", self)
        new_label_action.triggered.connect(
            lambda checked, idx=item_index: self.add_new_label(idx)
        )
        menu.addAction(new_label_action)

        menu.exec_(QPoint(self.mapToGlobal(mouse_pos)))

    def change_item_label(self, item_index, new_label):
        if 0 <= item_index < len(self.parent.canvas_items):
            pixmap, rect, _ = self.parent.canvas_items[item_index]
            self.parent.canvas_items[item_index] = (pixmap, rect, new_label)
            self.update()

    def add_new_label(self, item_index):
        new_label, ok = QInputDialog.getText(
            self, "添加新标签", "请输入新标签名称："
        )
        if ok and new_label.strip():
            new_label = new_label.strip()
            self.parent.paste_label_list.addItem(new_label)

            if 0 <= item_index < len(self.parent.canvas_items):
                pixmap, rect, _ = self.parent.canvas_items[item_index]
                self.parent.canvas_items[item_index] = (pixmap, rect, new_label)
                self.update()
