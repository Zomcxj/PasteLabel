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
from .theme import ThemeManager
from .dwm import set_titlebar_dark, is_available


class ImageEditor(UIBuilderMixin, ImageLoaderMixin, PasteEngineMixin,
                   EventHandlerMixin, QMainWindow):
    """贴图标注工具主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PasteLabel")
        self.resize(WINDOW_CONFIG['default_width'], WINDOW_CONFIG['default_height'])

        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.setWindowIcon(create_app_icon(script_dir))

        self._init_data()
        self.init_ui()
        self._apply_theme()
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

    def showEvent(self, event):
        """窗口显示后设置标题栏颜色（winId 必须在 show 之后获取）"""
        super().showEvent(event)
        is_dark = ThemeManager.get_mode().value == "dark"
        hwnd = int(self.winId())
        set_titlebar_dark(hwnd, is_dark)

    def _apply_theme(self):
        """应用当前主题样式"""
        app = QApplication.instance()
        app.setStyleSheet(ThemeManager.get_stylesheet())
        if hasattr(self, 'theme_btn'):
            is_dark = ThemeManager.get_mode().value == "dark"
            self.theme_btn.setText("🌙" if is_dark else "☀")
        if hasattr(self, 'prefix_input'):
            has_text = bool(self.prefix_input.text().strip())
            self.prefix_input.setProperty("placeholder", not has_text)
            self.prefix_input.style().unpolish(self.prefix_input)
            self.prefix_input.style().polish(self.prefix_input)
        self.canvas.update()

    def toggle_theme(self):
        """切换主题"""
        ThemeManager.toggle()
        self._apply_theme()
        is_dark = ThemeManager.get_mode().value == "dark"
        hwnd = int(self.winId())
        set_titlebar_dark(hwnd, is_dark)
        mode_name = "深色" if is_dark else "浅色"
        self.status_label.setText(f"已切换到{mode_name}主题")
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(2000, lambda: self.status_label.setText(""))

    def toggle_language(self):
        """切换中英文"""
        from . import i18n
        i18n.toggle_lang()
        self._refresh_ui_texts()
        lang_name = "中文" if i18n.get_lang() == "zh" else "English"
        self.status_label.setText(f"Language: {lang_name}")
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(2000, lambda: self.status_label.setText(""))

    def _refresh_ui_texts(self):
        """刷新所有界面文字"""
        from . import i18n
        tr = i18n.t
        self.draw_box_btn.setText(tr("绘制BOX"))
        self.draw_box_btn.setToolTip(tr("绘制检测框"))
        self.auto_save_checkbox.setText(tr("自动保存"))
        self.show_labels_checkbox.setText(tr("显示BOX"))
        self.show_label_names_checkbox.setText(tr("显示Label"))
        self.auto_label_checkbox.setText(tr("贴图标签"))
        self.prefix_checkbox.setText(tr("添加文件名前缀"))
        self.random_paste_btn.setText(tr("随机贴图"))
        self.batch_paste_btn.setText(tr("一键贴图"))
        is_thumb = self.is_thumbnail_mode
        self.toggle_view_btn.setText(tr("列表视图") if is_thumb else tr("缩略视图"))
        self.clear_btn.setText(tr("清空画布"))
        self.save_btn.setText(tr("保存图片"))
        self.save_all_btn.setText(tr("全部保存"))
        self.lang_btn.setToolTip(tr("切换中英文"))
        self.theme_btn.setToolTip(tr("切换深色/浅色主题"))
        if hasattr(self, 'bg_list_group'):
            self.bg_list_group.setTitle(tr("背景图列表"))
        if hasattr(self, 'label_group'):
            self.label_group.setTitle(tr("标签管理"))
        if hasattr(self, 'paste_group'):
            self.paste_group.setTitle(tr("贴图列表"))
        if hasattr(self, 'bg_label_header_lbl'):
            self.bg_label_header_lbl.setText(tr("背景图标签"))
        if hasattr(self, 'paste_label_header_lbl'):
            self.paste_label_header_lbl.setText(tr("贴图标签_list"))
        if hasattr(self, 'bg_lbl'):
            self.bg_lbl.setText(tr("背景图:"))
        if hasattr(self, 'paste_lbl'):
            self.paste_lbl.setText(tr("贴图:"))
        if hasattr(self, 'label_lbl'):
            self.label_lbl.setText(tr("标签:"))
        if hasattr(self, 'paste_count_lbl'):
            self.paste_count_lbl.setText(tr("贴图个数:"))
        if hasattr(self, 'size_lbl'):
            self.size_lbl.setText(tr("短边尺寸:"))
        if hasattr(self, 'upload_a_btn'):
            self.upload_a_btn.setToolTip(tr("选择背景图片"))
        if hasattr(self, 'load_folder_btn'):
            self.load_folder_btn.setToolTip(tr("加载文件夹图片"))
        if hasattr(self, 'upload_b_btn'):
            self.upload_b_btn.setToolTip(tr("选择贴图"))
        if hasattr(self, 'load_small_folder_btn'):
            self.load_small_folder_btn.setToolTip(tr("加载贴图文件夹"))
        if hasattr(self, 'upload_paste_label_btn'):
            self.upload_paste_label_btn.setToolTip(tr("选择标签文件"))
        if hasattr(self, 'random_paste_btn'):
            self.random_paste_btn.setToolTip(tr("随机贴图"))
        if hasattr(self, 'batch_paste_btn'):
            self.batch_paste_btn.setToolTip(tr("一键贴图"))
        if hasattr(self, 'clear_btn'):
            self.clear_btn.setToolTip(tr("清空画布"))
        if hasattr(self, 'save_btn'):
            self.save_btn.setToolTip(tr("保存图片"))
        if hasattr(self, 'save_all_btn'):
            self.save_all_btn.setToolTip(tr("全部保存"))


# 程序入口
def main():
    """程序入口函数"""
    import sys
    import warnings

    warnings.simplefilter("ignore", DeprecationWarning)

    app = QApplication(sys.argv)

    from PyQt5.QtGui import QFontDatabase
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    font_dir = os.path.join(base, "ico_image", "fonts")
    for name in ["JetBrainsMono-Regular.ttf", "JetBrainsMono-Medium.ttf", "JetBrainsMono-Bold.ttf"]:
        fpath = os.path.join(font_dir, name)
        if os.path.exists(fpath):
            QFontDatabase.addApplicationFont(fpath)

    editor = ImageEditor()
    editor.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
