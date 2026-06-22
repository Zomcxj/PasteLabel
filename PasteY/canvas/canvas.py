"""
Canvas 控件 - 由 CanvasRendererMixin + CanvasInteractionMixin 组合而成
"""
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QPoint, QRectF

from ..core.config import BACKGROUND_SCALE_CONFIG
from .canvas_renderer import CanvasRendererMixin
from .canvas_interaction import CanvasInteractionMixin


class Canvas(CanvasRendererMixin, CanvasInteractionMixin, QWidget):
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
        self.is_manual_scale = False

        # 贴图相关
        self.is_dragging_item = False
        self.selected_item_size = None

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

    def get_background_rect(self):
        """获取背景图在画布上的实际绘制矩形"""
        if self.parent.current_background is None:
            return None

        if not self.is_manual_scale:
            scale_x = self.width() / self.parent.current_background.width()
            scale_y = self.height() / self.parent.current_background.height()
            self.background_scale = min(scale_x, scale_y)
            self.background_offset = QPoint(0, 0)

        scaled_width = self.parent.current_background.width() * self.background_scale
        scaled_height = self.parent.current_background.height() * self.background_scale

        x = (self.width() - scaled_width) // 2 + self.background_offset.x()
        y = (self.height() - scaled_height) // 2 + self.background_offset.y()

        return QRectF(x, y, scaled_width, scaled_height)

    def reset_view(self):
        """重置画布视图状态（缩放、偏移）"""
        self.background_scale = 1.0
        self.background_offset = QPoint(0, 0)
        self.is_manual_scale = False

    def find_item_at_position(self, pos):
        """查找指定位置的贴图索引"""
        if self.parent.current_background is None:
            return None

        background_rect = self.get_background_rect()
        if background_rect is None:
            return None

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
        """更新状态栏显示 - 追加鼠标坐标到已有信息"""
        if not self.parent.current_background or not self.mouse_inside:
            return

        background_rect = self.get_background_rect()
        if background_rect is None:
            return

        rel_x = self.mouse_pos.x() - background_rect.left()
        rel_y = self.mouse_pos.y() - background_rect.top()
        orig_x = rel_x / self.background_scale
        orig_y = rel_y / self.background_scale

        coord_text = f"X: {int(orig_x)}, Y: {int(orig_y)}"

        if self.selected_item_size:
            w, h = self.selected_item_size
            coord_text += f" | W: {int(w)}, H: {int(h)}"
        elif (self.selected_box is not None and
              0 <= self.selected_box < len(self.parent.detection_boxes)):
            box = self.parent.detection_boxes[self.selected_box]
            coord_text += f" | W: {int(box['width'])}, H: {int(box['height'])}"
        elif self.is_drawing_box and self.temp_draw_box:
            w = self.temp_draw_box.width() / self.background_scale
            h = self.temp_draw_box.height() / self.background_scale
            coord_text += f" | W: {int(w)}, H: {int(h)}"

        info = self.parent.get_image_info()
        if info:
            stats = self.parent.get_label_stats()
            stats_text = " | ".join([f"{k}:{v}" for k, v in list(stats.items())[:3]])
            base = f"{info['width']}x{info['height']} | Paste: {info['paste_count']} Box: {info['box_count']}"
            if stats_text:
                base += f" | {stats_text}"
            self.parent.status_label.setText(f"{base}  {coord_text}")
        else:
            self.parent.status_label.setText(coord_text)
