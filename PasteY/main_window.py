"""
主窗口模块 - ImageEditor 主窗口逻辑（协调器）
"""
import os
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QApplication
from PyQt5.QtCore import QPoint

from .config import WINDOW_CONFIG, THUMBNAIL_CONFIG
from .utils import create_app_icon
from .save_manager import SaveManager
from .label_manager import LabelManager
from .ui_builder import UIBuilderMixin
from .image_loader import ImageLoaderMixin
from .paste_engine import PasteEngineMixin
from .event_handler import EventHandlerMixin


class ImageEditor(UIBuilderMixin, ImageLoaderMixin, PasteEngineMixin,
                   EventHandlerMixin, QMainWindow):
    """贴图标注工具主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("贴图标注工具")
        self.resize(WINDOW_CONFIG['default_width'], WINDOW_CONFIG['default_height'])

        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.setWindowIcon(create_app_icon(script_dir))

        self._init_data()
        self.init_ui()
        self._connect_manager_signals()
        self.update_label_list()
        self.installEventFilterRecursive(self)

    def _init_data(self):
        """初始化数据结构"""
        self.background_images = []
        self.current_background = None
        self.current_background_index = -1
        self.small_images = []
        self.canvas_items_dict = {}
        self.canvas_items = []
        self.selected_item = None
        self.is_dragging = False
        self.is_resizing = False
        self.drag_offset = QPoint(0, 0)
        self._busy = False

        self.detection_boxes_dict = {}
        self.detection_boxes = []
        self.global_labels = set()

        self.is_thumbnail_mode = True
        self.thumbnail_grid_width = THUMBNAIL_CONFIG['grid_width']
        self.thumbnail_grid_height = THUMBNAIL_CONFIG['grid_height']
        self.thumbnail_spacing = THUMBNAIL_CONFIG['spacing']

        self.save_manager = SaveManager(self, self)
        self.label_manager = LabelManager(self, self)

    def _connect_manager_signals(self):
        """连接管理器信号 → 编辑器 UI 刷新（需在 init_ui 之后调用）"""
        self.label_manager.data_changed.connect(self.canvas.update)
        self.label_manager.label_list_changed.connect(self.update_label_list)
        self.save_manager.save_completed.connect(self._on_save_completed)
        self.save_manager.label_list_changed.connect(self.update_label_list)

    # ===== 委托方法 - 保持对外接口不变 =====

    def save_json(self, image_path, image_name, label_prefix, canvas_items=None,
                  image_width=None, image_height=None, current_index=None):
        """生成并保存 JSON 文件"""
        self.save_manager.save_json(
            image_path, image_name, label_prefix,
            canvas_items, image_width, image_height, current_index
        )

    def auto_save_current_canvas(self):
        """自动保存当前画布"""
        self.save_manager.auto_save_current_canvas()

    def save_canvas(self):
        """保存当前画布"""
        self.save_manager.save_canvas()

    def save_all_canvas(self):
        """保存所有画布"""
        self.save_manager.save_all_canvas()

    def add_label(self, label_name=None):
        """增加标签"""
        self.label_manager.add_label(label_name)

    def delete_label(self):
        """删除标签"""
        self.label_manager.delete_label()

    def update_global_labels(self):
        """更新全局标签列表"""
        self.label_manager.update_global_labels()

    def update_label_list(self):
        """更新标签列表显示"""
        self.label_manager.update_label_list()

    def _on_save_completed(self):
        """保存完成后刷新 UI"""
        if self.current_background_index >= 0:
            self.background_list.setCurrentRow(self.current_background_index)
        self.update_file_count()
        self.canvas.update()


# 程序入口
def main():
    """程序入口函数"""
    import sys
    import warnings

    warnings.simplefilter("ignore", DeprecationWarning)

    app = QApplication(sys.argv)
    editor = ImageEditor()
    editor.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
