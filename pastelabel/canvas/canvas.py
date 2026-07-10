"""
Canvas 控件 - 由 CanvasRendererMixin + CanvasInteractionMixin 组合而成
"""
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QPoint, QRectF

from ..core.config import BACKGROUND_SCALE_CONFIG, WINDOW_CONFIG
from .canvas_renderer import CanvasRendererMixin
from .canvas_interaction import CanvasInteractionMixin


class Canvas(CanvasRendererMixin, CanvasInteractionMixin, QWidget):
    """画布控件 - 用于显示和编辑背景图、贴图、检测框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._editor = parent
        self.setMinimumSize(
            WINDOW_CONFIG.get('min_width', 1024),
            WINDOW_CONFIG.get('min_height', 768)
        )

        # 拖动相关
        self.drag_start = QPoint()
        self.resize_handle = None
        self.resize_start = QPoint()
        self.hover_resize_target = None
        self.hover_resize_handle = None

        # 背景图缩放和偏移
        self.background_scale = BACKGROUND_SCALE_CONFIG['default_scale']
        self.background_offset = QPoint(0, 0)
        self.is_dragging_background = False
        self.is_manual_scale = False

        # 贴图相关
        self.is_dragging_item = False
        self.selected_item_size = None

        # 检测框相关
        self.selected_box = None
        self.selected_boxes = []
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
        self._drag_out_pending = False

        # 设置焦点策略和鼠标追踪
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)

    def get_background_rect(self):
        """获取背景图在画布上的实际绘制矩形"""
        if self._editor.current_background is None:
            return None

        bg_w = self._editor.current_background.width()
        bg_h = self._editor.current_background.height()
        if bg_w <= 0 or bg_h <= 0:
            return None

        if not self.is_manual_scale:
            scale_x = self.width() / bg_w
            scale_y = self.height() / bg_h
            self.background_scale = min(scale_x, scale_y)
            self.background_offset = QPoint(0, 0)

        scaled_width = bg_w * self.background_scale
        scaled_height = bg_h * self.background_scale

        x = (self.width() - scaled_width) // 2 + self.background_offset.x()
        y = (self.height() - scaled_height) // 2 + self.background_offset.y()

        return QRectF(x, y, scaled_width, scaled_height)

    def reset_view(self):
        """重置画布视图为适应窗口"""
        if self._editor.current_background is None:
            return
        bg_w = self._editor.current_background.width()
        bg_h = self._editor.current_background.height()
        if bg_w > 0 and bg_h > 0:
            scale_x = self.width() / bg_w
            scale_y = self.height() / bg_h
            self.background_scale = min(scale_x, scale_y)
        else:
            self.background_scale = 1.0
        self.background_offset = QPoint(0, 0)
        self.is_manual_scale = True

    def find_item_at_position(self, pos):
        """查找指定位置的贴图索引"""
        if self._editor.current_background is None:
            return None

        background_rect = self.get_background_rect()
        if background_rect is None:
            return None

        for i in range(len(self._editor.canvas_items) - 1, -1, -1):
            pixmap, rect, label = self._editor.canvas_items[i]

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
        if not self._editor.current_background:
            return

        info = self._editor.get_image_info()
        stats = self._editor.get_label_stats()
        stats_parts = [f"{k}:{v}" for k, v in list(stats.items())[
            :self._editor._max_labels if hasattr(self._editor, '_max_labels') else 3
        ]]

        if self.mouse_inside:
            background_rect = self.get_background_rect()
            if background_rect:
                rel_x = self.mouse_pos.x() - background_rect.left()
                rel_y = self.mouse_pos.y() - background_rect.top()
                orig_x = rel_x / self.background_scale
                orig_y = rel_y / self.background_scale

                parts = []
                if info:
                    parts.append(f"Paste:{info['paste_count']} Box:{info['box_count']}")
                parts.append(f"X:{int(orig_x)} Y:{int(orig_y)}")

                if self.selected_item_size:
                    w, h = self.selected_item_size
                    parts.append(f"W:{int(w)} H:{int(h)}")
                elif (self.selected_box is not None and
                      0 <= self.selected_box < len(self._editor.detection_boxes)):
                    box = self._editor.detection_boxes[self.selected_box]
                    parts.append(f"W:{int(box['width'])} H:{int(box['height'])}")
                elif self.is_drawing_box and self.temp_draw_box:
                    w = self.temp_draw_box.width() / self.background_scale
                    h = self.temp_draw_box.height() / self.background_scale
                    parts.append(f"W:{int(w)} H:{int(h)}")

                if stats_parts:
                    parts.append(" ".join(stats_parts))

                prefix = "[移除路径] " if self._editor._is_delete_view else ""
                self._editor.status_label.setText(prefix + " | ".join(parts))
                return

        # 鼠标不在canvas上：只显示 Paste/Box + 类别
        parts = []
        if info:
            parts.append(f"Paste:{info['paste_count']} Box:{info['box_count']}")
        if stats_parts:
            parts.append(" ".join(stats_parts))
        if parts:
            prefix = "[移除路径] " if self._editor._is_delete_view else ""
            self._editor.status_label.setText(prefix + " | ".join(parts))
