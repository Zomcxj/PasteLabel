"""
自定义控件模块 - Canvas 等控件
"""
import os
from PyQt5.QtWidgets import QWidget, QMenu, QAction, QInputDialog
from PyQt5.QtGui import (
    QPainter, QPixmap, QColor, QPen, QFontMetrics
)
from PyQt5.QtCore import Qt, QPoint, QPointF, QRectF, QSizeF

from .config import (
    BACKGROUND_SCALE_CONFIG, DETECTION_BOX_CONFIG, PASTE_ITEM_CONFIG
)
from .utils import calculate_iou, extract_label_name


class Canvas(QWidget):
    """画布控件 - 用于显示和编辑背景图、贴图、检测框"""
    
    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent
        self.setMinimumSize(
            BACKGROUND_SCALE_CONFIG.get('canvas_min_width', 800),
            BACKGROUND_SCALE_CONFIG.get('canvas_min_height', 600)
        )
        
        # 拖动相关
        self.drag_start = QPoint()
        self.resize_handle = None
        self.resize_start = QPoint()
        
        # 背景图缩放和偏移
        self.background_scale = BACKGROUND_SCALE_CONFIG['default_scale']
        self.background_offset = QPoint(0, 0)
        self.is_dragging_background = False
        self.is_manual_scale = False  # 是否手动缩放
        
        # 贴图相关
        self.is_dragging_item = False
        self.selected_item_size = None  # 当前选中贴图的大小 (width, height)
        
        # 检测框相关
        self.selected_box = None
        self.is_dragging_box = False
        self.box_drag_start = QPoint()
        self.is_resizing_box = False
        self.box_resize_start = QPoint()
        
        # 绘制模式相关
        self.is_drawing_box = False
        self.draw_start_pos = None
        self.temp_draw_box = None
        
        # 鼠标状态跟踪
        self.mouse_inside = False
        self.mouse_pos = QPoint(0, 0)
        
        # 设置焦点策略和鼠标追踪
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
    
    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 获取背景图矩形
        background_rect = self.get_background_rect()
        
        # 绘制背景
        if self.parent.current_background is not None and background_rect:
            self._draw_background(painter, background_rect)
        else:
            painter.fillRect(self.rect(), QColor(230, 230, 230))
        
        # 绘制贴图
        if background_rect:
            self._draw_paste_items(painter, background_rect)
        
        # 绘制检测框
        if (self.parent.show_labels_checkbox.isChecked() and 
            background_rect and self.parent.detection_boxes):
            self._draw_detection_boxes(painter, background_rect)
        
        # 绘制临时检测框（正在绘制中）
        if self.is_drawing_box:
            self._draw_temp_box(painter)
    
    def _draw_background(self, painter, background_rect):
        """绘制背景图"""
        painter.drawPixmap(
            int(background_rect.left()),
            int(background_rect.top()),
            int(background_rect.width()),
            int(background_rect.height()),
            self.parent.current_background
        )
    
    def _draw_paste_items(self, painter, background_rect):
        """绘制所有贴图"""
        for i, (pixmap, rect, label) in enumerate(self.parent.canvas_items):
            # 计算贴图在画布上的位置和大小
            item_x = (rect.x() * self.background_scale) + background_rect.left()
            item_y = (rect.y() * self.background_scale) + background_rect.top()
            item_width = rect.width() * self.background_scale
            item_height = rect.height() * self.background_scale
            
            item_rect = QRectF(item_x, item_y, item_width, item_height)
            is_selected = (i == self.parent.selected_item)
            
            # 检查鼠标悬停（只更新状态，不跳过绘制）
            self._check_mouse_hover(item_rect, i)
            
            # 绘制贴图（所有贴图都要绘制）
            self._draw_single_paste_item(
                painter, pixmap, item_rect, label, is_selected
            )
    
    def _check_mouse_hover(self, item_rect, item_index):
        """检查鼠标是否悬停在贴图上，如果是则自动选中
        注意：不在此处调用 self.update()，避免 paintEvent 内触发重绘循环。
        重绘由后续的 mouseMoveEvent 触发。
        """
        mouse_pos = self.mouse_pos
        if item_rect.contains(mouse_pos):
            if self.parent.selected_item != item_index:
                self.parent.selected_item = item_index
                _, rect, _ = self.parent.canvas_items[item_index]
                self.selected_item_size = (rect.width(), rect.height())
            return True
        return False
    
    def _draw_single_paste_item(self, painter, pixmap, item_rect, label, is_selected):
        """绘制单个贴图"""
        item_x = item_rect.left()
        item_y = item_rect.top()
        item_width = item_rect.width()
        item_height = item_rect.height()
        
        if is_selected:
            # 选中状态：绘制透明蒙版
            self._draw_selected_paste(painter, pixmap, item_rect, label)
        else:
            # 正常状态
            painter.drawPixmap(
                int(item_x), int(item_y),
                int(item_width), int(item_height),
                pixmap
            )
        
        # 绘制边框
        border_color = QColor(*PASTE_ITEM_CONFIG['border_color'])
        pen_width = (PASTE_ITEM_CONFIG['border_width_selected'] if is_selected 
                    else PASTE_ITEM_CONFIG['border_width_normal'])
        pen = QPen(border_color, pen_width)
        painter.setPen(pen)
        painter.drawRect(int(item_x), int(item_y), int(item_width), int(item_height))
        
        # 绘制缩放手柄（仅选中时）
        if is_selected:
            self._draw_resize_handle(painter, item_rect, border_color)
        
        # 绘制标签
        self._draw_paste_label(painter, item_x, item_y, label, is_selected)
    
    def _draw_selected_paste(self, painter, pixmap, item_rect, label):
        """绘制选中的贴图（带透明蒙版）"""
        temp_pixmap = QPixmap(int(item_rect.width()), int(item_rect.height()))
        temp_pixmap.fill(Qt.transparent)
        temp_painter = QPainter(temp_pixmap)
        
        # 绘制原始贴图
        temp_painter.drawPixmap(
            0, 0, int(item_rect.width()), int(item_rect.height()), pixmap
        )
        
        # 添加天蓝色透明蒙版
        overlay_color = QColor(135, 206, 250, 80)
        temp_painter.fillRect(
            0, 0, int(item_rect.width()), int(item_rect.height()), overlay_color
        )
        temp_painter.end()
        
        painter.drawPixmap(
            int(item_rect.left()), int(item_rect.top()),
            temp_pixmap
        )
    
    def _draw_resize_handle(self, painter, item_rect, color):
        """绘制右下角缩放手柄"""
        handle_size = PASTE_ITEM_CONFIG['handle_size']
        br_handle = item_rect.bottomRight()
        painter.fillRect(
            int(br_handle.x() - handle_size),
            int(br_handle.y() - handle_size),
            handle_size, handle_size,
            color
        )
    
    def _draw_paste_label(self, painter, x, y, label, is_selected):
        """绘制贴图标签"""
        font = painter.font()
        metrics = QFontMetrics(font)
        text_width = metrics.width(label)
        text_height = metrics.height()
        
        # 绘制背景
        bg_color = QColor(*PASTE_ITEM_CONFIG['border_color'])
        painter.fillRect(int(x), int(y) - text_height, text_width, text_height, bg_color)
        
        # 绘制文本
        painter.setPen(QColor(0, 0, 0))
        painter.setFont(font)
        painter.drawText(int(x), int(y) - 2, label)
    
    def _draw_detection_boxes(self, painter, background_rect):
        """绘制所有检测框"""
        for i, box in enumerate(self.parent.detection_boxes):
            # 跳过无效的检测框
            if box["width"] <= 0 or box["height"] <= 0:
                continue
            
            # 计算检测框在画布上的位置
            box_x = box["x"] * self.background_scale + background_rect.left()
            box_y = box["y"] * self.background_scale + background_rect.top()
            box_width = box["width"] * self.background_scale
            box_height = box["height"] * self.background_scale
            
            is_selected = (i == self.selected_box)
            is_pressed_label = self._is_pressed_label(box)
            
            # 绘制检测框
            self._draw_single_detection_box(
                painter, box_x, box_y, box_width, box_height,
                box.get("label", ""), is_selected, is_pressed_label
            )
    
    def _is_pressed_label(self, box):
        """检查检测框是否是当前按下的标签"""
        if not hasattr(self.parent, 'pressed_label') or self.parent.pressed_label is None:
            return False
        return box.get('label') == self.parent.pressed_label
    
    def _draw_single_detection_box(self, painter, x, y, width, height, label, 
                                   is_selected, is_pressed_label):
        """绘制单个检测框"""
        # 确定颜色和样式
        if is_selected:
            fill_color = QColor(*DETECTION_BOX_CONFIG['fill_color_selected'])
            border_color = QColor(*DETECTION_BOX_CONFIG['border_color_selected'])
            pen_width = 3
        elif is_pressed_label:
            fill_color = QColor(255, 165, 0, 50)
            border_color = QColor(255, 165, 0)
            pen_width = 3
        else:
            fill_color = None
            border_color = QColor(*DETECTION_BOX_CONFIG['border_color_normal'])
            pen_width = 2
        
        # 绘制填充
        if fill_color:
            painter.fillRect(int(x), int(y), int(width), int(height), fill_color)
        
        # 绘制边框
        pen = QPen(border_color, pen_width)
        painter.setPen(pen)
        painter.drawRect(int(x), int(y), int(width), int(height))
        
        # 绘制标签文本
        if label and getattr(self.parent, 'show_label_names_checkbox', None) and self.parent.show_label_names_checkbox.isChecked():
            self._draw_box_label(painter, x, y, label, border_color)
        
        # 绘制调整手柄（仅选中时）
        if is_selected:
            self._draw_box_handles(painter, x, y, width, height, border_color)
    
    def _draw_box_label(self, painter, x, y, label, bg_color):
        """绘制检测框标签"""
        font = painter.font()
        metrics = QFontMetrics(font)
        text_width = metrics.width(label)
        text_height = metrics.height()
        
        # 绘制背景
        painter.fillRect(int(x), int(y) - text_height, text_width, text_height, bg_color)
        
        # 绘制文本
        painter.setPen(QColor(0, 0, 0))
        painter.setFont(font)
        painter.drawText(int(x), int(y) - 2, label)
    
    def _draw_box_handles(self, painter, x, y, width, height, color):
        """绘制检测框的四个调整手柄"""
        handle_size = DETECTION_BOX_CONFIG['resize_handle_size']
        
        # 四个角的手柄都在检测框内部
        # 左上角：手柄的右下角对齐到检测框的左上角点
        painter.fillRect(
            int(x), int(y),
            handle_size, handle_size,
            color
        )
        
        # 右上角：手柄的左下角对齐到检测框的右上角点
        painter.fillRect(
            int(x + width - handle_size), int(y),
            handle_size, handle_size,
            color
        )
        
        # 左下角：手柄的右上角对齐到检测框的左下角点
        painter.fillRect(
            int(x), int(y + height - handle_size),
            handle_size, handle_size,
            color
        )
        
        # 右下角：手柄的左上角对齐到检测框的右下角点
        painter.fillRect(
            int(x + width - handle_size), int(y + height - handle_size),
            handle_size, handle_size,
            color
        )
    
    def _draw_temp_box(self, painter):
        """绘制临时检测框（正在绘制中）"""
        # 绘制虚线框
        if self.temp_draw_box is not None and self.draw_start_pos is not None:
            pen = QPen(QColor(0, 255, 0), 2, Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(self.temp_draw_box)
        
        # 绘制十字虚线
        if self.mouse_pos is not None:
            cross_pen = QPen(QColor(0, 255, 128), 1, Qt.DashLine)
            painter.setPen(cross_pen)
            
            # 水平线
            painter.drawLine(
                QPointF(0, self.mouse_pos.y()),
                QPointF(self.width(), self.mouse_pos.y())
            )
            # 垂直线
            painter.drawLine(
                QPointF(self.mouse_pos.x(), 0),
                QPointF(self.mouse_pos.x(), self.height())
            )
    
    def get_background_rect(self):
        """获取背景图在画布上的实际绘制矩形"""
        if self.parent.current_background is None:
            return None
        
        # 如果没有手动缩放，则自动适配窗口大小
        if not self.is_manual_scale:
            scale_x = self.width() / self.parent.current_background.width()
            scale_y = self.height() / self.parent.current_background.height()
            self.background_scale = min(scale_x, scale_y)
            # 重置偏移量，确保背景图居中
            self.background_offset = QPoint(0, 0)
        
        scaled_width = self.parent.current_background.width() * self.background_scale
        scaled_height = self.parent.current_background.height() * self.background_scale
        
        x = (self.width() - scaled_width) // 2 + self.background_offset.x()
        y = (self.height() - scaled_height) // 2 + self.background_offset.y()
        
        return QRectF(x, y, scaled_width, scaled_height)
    
    def find_item_at_position(self, pos):
        """查找指定位置的贴图索引"""
        if self.parent.current_background is None:
            return None
        
        background_rect = self.get_background_rect()
        if background_rect is None:
            return None
        
        # 从后往前遍历（上层优先）
        for i in range(len(self.parent.canvas_items) - 1, -1, -1):
            pixmap, rect, label = self.parent.canvas_items[i]
            
            item_x = (rect.x() * self.background_scale) + background_rect.left()
            item_y = (rect.y() * self.background_scale) + background_rect.top()
            item_width = rect.width() * self.background_scale
            item_height = rect.height() * self.background_scale
            
            if (item_x <= pos.x() <= item_x + item_width and
                item_y <= pos.y() <= item_y + item_height):
                return i
        
        return None
    
    def update_status_label(self):
        """更新状态栏显示"""
        if not self.parent.current_background or not self.mouse_inside:
            self.parent.status_label.setText("")
            return
        
        background_rect = self.get_background_rect()
        if background_rect is None:
            return
        
        # 转换为原图坐标
        rel_x = self.mouse_pos.x() - background_rect.left()
        rel_y = self.mouse_pos.y() - background_rect.top()
        orig_x = rel_x / self.background_scale
        orig_y = rel_y / self.background_scale
        
        status_text = f"X: {int(orig_x)}, Y: {int(orig_y)}"
        
        # 添加尺寸信息
        if self.selected_item_size:
            w, h = self.selected_item_size
            status_text += f" | W: {int(w)}, H: {int(h)}"
        elif (self.selected_box is not None and 
              0 <= self.selected_box < len(self.parent.detection_boxes)):
            box = self.parent.detection_boxes[self.selected_box]
            status_text += f" | W: {int(box['width'])}, H: {int(box['height'])}"
        elif self.is_drawing_box and self.temp_draw_box:
            w = self.temp_draw_box.width() / self.background_scale
            h = self.temp_draw_box.height() / self.background_scale
            status_text += f" | W: {int(w)}, H: {int(h)}"
        
        self.parent.status_label.setText(status_text)
    
    def enterEvent(self, event):
        """鼠标进入事件"""
        self.mouse_inside = True
        self.update_status_label()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开事件"""
        self.mouse_inside = False
        self.update_status_label()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """鼠标按下事件 - 将在单独文件中详细实现"""
        # 由于代码较长，将分为多个方法处理
        self._handle_mouse_press(event)
    
    def _handle_mouse_press(self, event):
        """处理鼠标按下事件的入口"""
        self.setFocus()
        mouse_pos = event.pos()
        
        # 绘制模式处理
        if self.is_drawing_box and event.button() == Qt.LeftButton:
            if self._handle_drawing_press(mouse_pos):
                return
        
        # 右键菜单
        if event.button() == Qt.RightButton:
            if self._handle_right_click(mouse_pos):
                return
        elif event.button() != Qt.LeftButton:
            return
        
        # 左键点击处理
        self._handle_left_click(mouse_pos)
    
    def _handle_drawing_press(self, mouse_pos):
        """处理绘制模式下的鼠标按下"""
        if (not self.parent.background_images or 
            self.parent.current_background_index < 0):
            return True
        
        background_rect = self.get_background_rect()
        if not background_rect or not background_rect.contains(mouse_pos):
            return True
        
        if self.draw_start_pos is None:
            # 第一次点击
            self.draw_start_pos = mouse_pos
            self.temp_draw_box = QRectF(mouse_pos, QSizeF())
            self.selected_box = None
            self.parent.selected_item = None
            self.update_status_label()
            self.update()
        else:
            # 第二次点击 - 完成绘制
            self._complete_drawing(mouse_pos)
        
        return True
    
    def _complete_drawing(self, mouse_pos):
        """完成检测框绘制"""
        from .dialogs import LabelSelectionDialog
        
        background_rect = self.get_background_rect()
        constrained_pos = self._constrain_to_background(mouse_pos, background_rect)
        
        # 计算矩形
        x1 = min(self.draw_start_pos.x(), constrained_pos.x())
        y1 = min(self.draw_start_pos.y(), constrained_pos.y())
        x2 = max(self.draw_start_pos.x(), constrained_pos.x())
        y2 = max(self.draw_start_pos.y(), constrained_pos.y())
        
        self.temp_draw_box = QRectF(x1, y1, x2 - x1, y2 - y1)
        
        # 转换为背景图坐标
        x = (self.temp_draw_box.left() - background_rect.left()) / self.background_scale
        y = (self.temp_draw_box.top() - background_rect.top()) / self.background_scale
        width = self.temp_draw_box.width() / self.background_scale
        height = self.temp_draw_box.height() / self.background_scale
        
        self.update_status_label()
        
        # 验证有效性
        if (x <= 0 and y <= 0) or width <= 3 or height <= 3:
            self._reset_drawing_state()
            return
        
        # 显示标签选择对话框
        label_items = []
        for i in range(self.parent.label_list.count()):
            label_items.append(self.parent.label_list.item(i).text())
        
        selected_label = LabelSelectionDialog.select_label(self, label_items)
        
        if selected_label:
            self._create_detection_box(x, y, width, height, selected_label)
        
        self._reset_drawing_state()
    
    def _constrain_to_background(self, pos, background_rect):
        """限制位置在背景图范围内"""
        constrained = pos
        constrained.setX(max(background_rect.left(), min(constrained.x(), background_rect.right())))
        constrained.setY(max(background_rect.top(), min(constrained.y(), background_rect.bottom())))
        return constrained
    
    def _create_detection_box(self, x, y, width, height, label):
        """创建检测框并保存"""
        # 确保坐标为正值
        x = max(0, x)
        y = max(0, y)
        width = max(1, width)
        height = max(1, height)
        
        new_box = {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "label": label
        }
        
        self.parent.detection_boxes.append(new_box)
        
        # 更新字典
        if self.parent.current_background_index >= 0:
            self.parent.detection_boxes_dict[
                self.parent.current_background_index
            ] = self.parent.detection_boxes.copy()
        
        # 更新标签列表
        self.parent.update_label_list()
        
        # 保存 JSON
        self._save_current_detection_boxes()
    
    def _reset_drawing_state(self):
        """重置绘制状态"""
        self.draw_start_pos = None
        self.temp_draw_box = None
        self.is_drawing_box = False
        self.setCursor(Qt.ArrowCursor)
        
        if hasattr(self.parent, 'draw_box_btn'):
            self.parent.draw_box_btn.setText("绘制 BOX(W)")
        
        self.update()
    
    def _handle_right_click(self, mouse_pos):
        """处理右键点击"""
        item_index = self.find_item_at_position(mouse_pos)
        if item_index is not None:
            self._show_paste_context_menu(item_index, mouse_pos)
            return True
        return False
    
    def _show_paste_context_menu(self, item_index, mouse_pos):
        """显示贴图右键菜单"""
        menu = QMenu(self)
        
        # 获取贴图标签列表
        label_items = []
        for i in range(self.parent.paste_label_list.count()):
            label = self.parent.paste_label_list.item(i).text()
            pure_label = extract_label_name(label)
            label_items.append(pure_label)
        
        # 添加标签选项
        for label in label_items:
            action = QAction(label, self)
            action.triggered.connect(
                lambda checked, l=label, idx=item_index: self.change_item_label(idx, l)
            )
            menu.addAction(action)
        
        menu.addSeparator()
        
        # 添加新标签选项
        new_label_action = QAction("添加新标签", self)
        new_label_action.triggered.connect(
            lambda checked, idx=item_index: self.add_new_label(idx)
        )
        menu.addAction(new_label_action)
        
        menu.exec_(QPoint(self.mapToGlobal(mouse_pos)))
    
    def _handle_left_click(self, mouse_pos):
        """处理左键点击"""
        # 检查贴图
        item_at_pos = self.find_item_at_position(mouse_pos)
        if item_at_pos is not None:
            self._handle_item_click(item_at_pos, mouse_pos)
            return
        
        # 检查检测框
        if self.parent.show_labels_checkbox.isChecked() and self.parent.current_background:
            if self._handle_detection_box_click(mouse_pos):
                return
        
        # 检查背景图
        if self.parent.current_background:
            if self._handle_background_click(mouse_pos):
                return
        
        # 点击空白区域
        self._clear_selection()
    
    def _handle_item_click(self, item_index, mouse_pos):
        """处理贴图点击"""
        self.selected_box = None
        _, rect, _ = self.parent.canvas_items[item_index]
        
        if self.parent.selected_item != item_index:
            self.parent.selected_item = item_index
            self.selected_item_size = (rect.width(), rect.height())
            self.update()
        
        # 检查缩放手柄
        if self._check_resize_handle(mouse_pos, rect):
            return
        
        # 开始拖拽
        background_rect = self.get_background_rect()
        if background_rect:
            item_x = (rect.x() * self.background_scale) + background_rect.left()
            item_y = (rect.y() * self.background_scale) + background_rect.top()
            item_rect = QRectF(item_x, item_y, rect.width() * self.background_scale, 
                              rect.height() * self.background_scale)
            self.drag_start = mouse_pos - item_rect.topLeft()
            self.is_dragging_item = True
    
    def _check_resize_handle(self, mouse_pos, rect):
        """检查是否点击了缩放手柄"""
        if not self.parent.current_background:
            return False
        
        background_rect = self.get_background_rect()
        item_x = (rect.x() * self.background_scale) + background_rect.left()
        item_y = (rect.y() * self.background_scale) + background_rect.top()
        item_width = rect.width() * self.background_scale
        item_height = rect.height() * self.background_scale
        item_rect = QRectF(item_x, item_y, item_width, item_height)
        
        handle_size = 8
        br_handle = item_rect.bottomRight()
        
        if (abs(mouse_pos.x() - br_handle.x()) <= handle_size and
            abs(mouse_pos.y() - br_handle.y()) <= handle_size):
            self.resize_handle = 'br'
            self.resize_start = mouse_pos
            return True
        
        return False
    
    def _handle_detection_box_click(self, mouse_pos):
        """处理检测框点击"""
        background_rect = self.get_background_rect()
        if not background_rect:
            return False
        
        for i, box in enumerate(self.parent.detection_boxes):
            box_x = box["x"] * self.background_scale + background_rect.left()
            box_y = box["y"] * self.background_scale + background_rect.top()
            box_width = box["width"] * self.background_scale
            box_height = box["height"] * self.background_scale
            
            if self._check_box_handle(mouse_pos, box_x, box_y, box_width, box_height, i):
                return True
            
            box_rect = QRectF(box_x, box_y, box_width, box_height)
            if box_rect.contains(mouse_pos):
                self.selected_box = i
                self.box_drag_start = mouse_pos
                self.is_dragging_box = True
                self.parent.selected_item = None
                self.selected_item_size = None
                self.update_status_label()
                self.update()
                return True
        
        return False
    
    def _check_box_handle(self, mouse_pos, x, y, width, height, box_index):
        """检查是否点击了检测框的调整手柄"""
        handle_size = 8
        
        handles = {
            "br": (x + width, y + height),
            "tl": (x, y),
            "tr": (x + width, y),
            "bl": (x, y + height),
        }
        
        for handle_name, (hx, hy) in handles.items():
            handle_rect = QRectF(
                hx - handle_size if 'r' in handle_name else hx,
                hy - handle_size if 'b' in handle_name else hy,
                handle_size, handle_size
            )
            
            if handle_rect.contains(mouse_pos):
                self.selected_box = box_index
                self.box_resize_start = mouse_pos
                self.is_resizing_box = True
                self.resize_handle = handle_name
                self.parent.selected_item = None
                self.selected_item_size = None
                self.update_status_label()
                self.update()
                return True
        
        return False
    
    def _handle_background_click(self, mouse_pos):
        """处理背景图点击"""
        background_rect = self.get_background_rect()
        if not background_rect.contains(mouse_pos):
            return False
        
        scaled_width = self.parent.current_background.width() * self.background_scale
        scaled_height = self.parent.current_background.height() * self.background_scale
        
        if scaled_width > self.width() or scaled_height > self.height():
            self._clear_selection()
            self.drag_start = mouse_pos
            self.is_dragging_background = True
            return True
        
        self._clear_selection()
        self.update_status_label()
        self.update()
        return True
    
    def _clear_selection(self):
        """清除所有选择状态"""
        self.parent.selected_item = None
        self.selected_item_size = None
        self.selected_box = None
        self.update_status_label()
        self.update()
    
    def change_item_label(self, item_index, new_label):
        """更改贴图标签"""
        if 0 <= item_index < len(self.parent.canvas_items):
            pixmap, rect, _ = self.parent.canvas_items[item_index]
            self.parent.canvas_items[item_index] = (pixmap, rect, new_label)
            self.update()
    
    def add_new_label(self, item_index):
        """添加新标签到贴图"""
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
    
    def _save_current_detection_boxes(self):
        """保存当前检测框到 JSON 文件"""
        if self.parent.current_background and self.parent.current_background_index >= 0:
            background_path = self.parent.background_images[self.parent.current_background_index]
            background_name = os.path.basename(background_path)
            self.parent.save_json(background_path, background_name, "", canvas_items=[])
    
    # 其他鼠标事件将在 widgets.py 中继续实现...
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 完整版"""
        self.mouse_pos = event.pos()
        self.update_status_label()
        
        # 绘制模式
        if self.is_drawing_box:
            if self.draw_start_pos:
                bg_rect = self.get_background_rect()
                if bg_rect:
                    c = self._constrain_to_background(self.mouse_pos, bg_rect)
                    x1 = min(self.draw_start_pos.x(), c.x())
                    y1 = min(self.draw_start_pos.y(), c.y())
                    x2 = max(self.draw_start_pos.x(), c.x())
                    y2 = max(self.draw_start_pos.y(), c.y())
                    self.temp_draw_box = QRectF(x1, y1, x2 - x1, y2 - y1)
                else:
                    x1 = min(self.draw_start_pos.x(), self.mouse_pos.x())
                    y1 = min(self.draw_start_pos.y(), self.mouse_pos.y())
                    x2 = max(self.draw_start_pos.x(), self.mouse_pos.x())
                    y2 = max(self.draw_start_pos.y(), self.mouse_pos.y())
                    self.temp_draw_box = QRectF(x1, y1, x2 - x1, y2 - y1)
            self.update()
            return
        
        # 拖动背景
        if self.is_dragging_background:
            delta = self.mouse_pos - self.drag_start
            self.background_offset += delta
            self.drag_start = self.mouse_pos
            self.update()
            return
        
        # 拖动检测框
        if self.is_dragging_box and self.selected_box is not None:
            self._drag_box()
            return
        
        # 调整检测框
        if self.is_resizing_box and self.selected_box is not None:
            self._resize_box()
            return
        
        # 拖动贴图
        if self.is_dragging_item and self.parent.selected_item is not None:
            self._drag_item()
            return
        
        # 缩放贴图
        if self.resize_handle and self.parent.selected_item is not None:
            self._scale_item()
            return
        
        self.update()
    
    def _drag_box(self):
        """拖动检测框"""
        delta = self.mouse_pos - self.box_drag_start
        bg_rect = self.get_background_rect()
        
        if bg_rect:
            dx = delta.x() / self.background_scale
            dy = delta.y() / self.background_scale
            box = self.parent.detection_boxes[self.selected_box]
            
            nx = box["x"] + dx
            ny = box["y"] + dy
            
            if self.parent.current_background:
                bw = self.parent.current_background.width()
                bh = self.parent.current_background.height()
                nx = max(0, min(nx, bw - box["width"]))
                ny = max(0, min(ny, bh - box["height"]))
            
            box["x"] = nx
            box["y"] = ny
            self.box_drag_start = self.mouse_pos
            
            if self.parent.current_background_index in self.parent.detection_boxes_dict:
                self.parent.detection_boxes_dict[self.parent.current_background_index][self.selected_box] = box.copy()
            
            self._save_current_detection_boxes()
            self.update()
    
    def _resize_box(self):
        """调整检测框大小"""
        delta = self.mouse_pos - self.box_resize_start
        bg_rect = self.get_background_rect()
        
        if bg_rect:
            dx = delta.x() / self.background_scale
            dy = delta.y() / self.background_scale
            box = self.parent.detection_boxes[self.selected_box]
            x, y, w, h = box["x"], box["y"], box["width"], box["height"]
            
            nx, ny, nw, nh = x, y, w, h
            
            if self.resize_handle == "br":
                nw = max(10, w + dx)
                nh = max(10, h + dy)
            elif self.resize_handle == "tl":
                nx = max(0, min(x + dx, x + w - 10))
                ny = max(0, min(y + dy, y + h - 10))
                nw = w + x - nx
                nh = h + y - ny
            elif self.resize_handle == "tr":
                nw = max(10, w + dx)
                ny = max(0, min(y + dy, y + h - 10))
                nh = h + y - ny
            elif self.resize_handle == "bl":
                nx = max(0, min(x + dx, x + w - 10))
                nw = w + x - nx
                nh = max(10, h + dy)
            
            box["x"], box["y"], box["width"], box["height"] = nx, ny, nw, nh
            self.box_resize_start = self.mouse_pos
            
            if self.parent.current_background_index in self.parent.detection_boxes_dict:
                self.parent.detection_boxes_dict[self.parent.current_background_index][self.selected_box] = box.copy()
            
            self._save_current_detection_boxes()
            self.update()
    
    def _drag_item(self):
        """拖动贴图"""
        bg_rect = self.get_background_rect()
        if bg_rect:
            p, rect, label = self.parent.canvas_items[self.parent.selected_item]
            np = self.mouse_pos - self.drag_start
            nx = (np.x() - bg_rect.left()) / self.background_scale
            ny = (np.y() - bg_rect.top()) / self.background_scale
            
            nx = max(0, nx)
            ny = max(0, ny)
            
            if self.parent.current_background:
                bw = self.parent.current_background.width()
                bh = self.parent.current_background.height()
                nx = min(nx, bw - rect.width())
                ny = min(ny, bh - rect.height())
            
            nr = QRectF(nx, ny, rect.width(), rect.height())
            self.parent.canvas_items[self.parent.selected_item] = (p, nr, label)
            self.update()
    
    def _scale_item(self):
        """缩放贴图"""
        if self.parent.current_background:
            p, rect, label = self.parent.canvas_items[self.parent.selected_item]
            nr = QRectF(rect)
            
            bg_rect = self.get_background_rect()
            ix = (rect.x() * self.background_scale) + bg_rect.left()
            iy = (rect.y() * self.background_scale) + bg_rect.top()
            iw = rect.width() * self.background_scale
            ih = rect.height() * self.background_scale
            
            if self.resize_handle == 'br':
                nw = max(15, self.mouse_pos.x() - ix)
                nh = max(15, self.mouse_pos.y() - iy)
                
                wr = nw / iw
                hr = nh / ih
                sr = min(wr, hr)
                
                new_w = rect.width() * sr
                new_h = rect.height() * sr
                
                if self.parent.current_background:
                    bw = self.parent.current_background.width()
                    bh = self.parent.current_background.height()
                    new_w = min(new_w, bw - rect.x())
                    new_h = min(new_h, bh - rect.y())
                
                nr.setWidth(new_w)
                nr.setHeight(new_h)
            
            self.parent.canvas_items[self.parent.selected_item] = (p, nr, label)
            self.selected_item_size = (new_w, new_h)
            self.update()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        self.is_dragging_item = False
        self.is_dragging_background = False
        self.is_dragging_box = False
        self.is_resizing_box = False
        self.resize_handle = None
        self.update()
    
    def wheelEvent(self, event):
        """滚轮事件"""
        if not self.parent.current_background:
            return
        
        # 选中贴图时缩放贴图
        if self.parent.selected_item is not None:
            self._scale_selected_item(event)
        # 选中检测框时缩放检测框
        elif self.selected_box is not None:
            self._scale_selected_box(event)
        # Ctrl 按下时缩放背景图
        elif event.modifiers() & Qt.ControlModifier:
            self._scale_background(event)
        
        self.update()
    
    def _scale_selected_item(self, event):
        """缩放选中的贴图"""
        delta = event.angleDelta().y()
        scale_factor = 1.1 if delta > 0 else 0.9
        
        pixmap, rect, label = self.parent.canvas_items[self.parent.selected_item]
        aspect_ratio = rect.width() / rect.height()
        
        new_width = rect.width() * scale_factor
        new_height = new_width / aspect_ratio if aspect_ratio >= 1 else rect.height() * scale_factor
        
        # 限制大小
        bg_short_side = min(self.parent.current_background.width(), 
                          self.parent.current_background.height())
        min_size = 10
        max_size = bg_short_side * 0.9
        
        new_width = max(min_size, min(new_width, max_size))
        new_height = max(min_size, min(new_height, max_size))
        
        # 保持中心不变
        center_x = rect.center().x()
        center_y = rect.center().y()
        
        new_rect = QRectF(
            center_x - new_width / 2,
            center_y - new_height / 2,
            new_width, new_height
        )
        
        self.parent.canvas_items[self.parent.selected_item] = (pixmap, new_rect, label)
        self.selected_item_size = (new_width, new_height)
    
    def _scale_selected_box(self, event):
        """缩放选中的检测框"""
        delta = event.angleDelta().y()
        scale_factor = 1.03 if delta > 0 else 0.97
        
        box = self.parent.detection_boxes[self.selected_box]
        x, y, width, height = box["x"], box["y"], box["width"], box["height"]
        aspect_ratio = width / height
        
        new_width = width * scale_factor
        new_height = new_width / aspect_ratio if aspect_ratio >= 1 else height * scale_factor
        
        # 限制大小
        bg_size = min(self.parent.current_background.width(), 
                     self.parent.current_background.height())
        min_size = 10
        max_size = bg_size * 0.9
        
        new_width = max(min_size, min(new_width, max_size))
        new_height = max(min_size, min(new_height, max_size))
        
        # 保持中心不变
        center_x = x + width / 2
        center_y = y + height / 2
        
        new_x = center_x - new_width / 2
        new_y = center_y - new_height / 2
        
        # 限制在背景图内
        new_x = max(0, min(new_x, self.parent.current_background.width() - new_width))
        new_y = max(0, min(new_y, self.parent.current_background.height() - new_height))
        
        box["x"] = new_x
        box["y"] = new_y
        box["width"] = new_width
        box["height"] = new_height
        
        if self.parent.current_background_index in self.parent.detection_boxes_dict:
            self.parent.detection_boxes_dict[
                self.parent.current_background_index
            ][self.selected_box] = box.copy()
    
    def _scale_background(self, event):
        """缩放背景图"""
        delta = event.angleDelta().y()
        scale_factor = 1.1 if delta > 0 else 0.9
        
        self.background_scale *= scale_factor
        self.background_scale = max(
            BACKGROUND_SCALE_CONFIG['min_scale'],
            min(self.background_scale, BACKGROUND_SCALE_CONFIG['max_scale'])
        )
        self.is_manual_scale = True
    
    def keyPressEvent(self, event):
        """键盘按下事件"""
        if event.key() == Qt.Key_Delete or event.key() == Qt.Key_E:
            if self.parent.selected_item is not None:
                del self.parent.canvas_items[self.parent.selected_item]
                self.parent.selected_item = None
                self.selected_item_size = None
                self.update_status_label()
                self.update()
        elif event.key() == Qt.Key_F and event.modifiers() & Qt.ControlModifier:
            self.background_scale = 1.0
            self.background_offset = QPoint(0, 0)
            self.is_manual_scale = False
            self.update()
        elif event.key() == Qt.Key_Q:
            if self.is_drawing_box:
                self.is_drawing_box = False
                self.draw_start_pos = None
                self.temp_draw_box = None
                self.setCursor(Qt.ArrowCursor)
                if hasattr(self.parent, 'draw_box_btn'):
                    self.parent.draw_box_btn.setText("绘制 BOX(W)")
                self.update()
        super().keyPressEvent(event)
    
    def resizeEvent(self, event):
        """窗口大小变化事件"""
        self.update()
        super().resizeEvent(event)
