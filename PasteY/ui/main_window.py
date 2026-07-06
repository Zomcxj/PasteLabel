"""
主窗口模块 - ImageEditor 主窗口逻辑（协调器）
"""
import os
import sys
from datetime import datetime
from PyQt5.QtWidgets import QMainWindow, QApplication
from PyQt5.QtCore import QPoint, Qt, QUrl
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QDrag

from ..core.config import WINDOW_CONFIG, THUMBNAIL_CONFIG
from ..core.utils import create_app_icon
from ..engine.save_manager import SaveManager
from ..engine.label_manager import LabelManager
from .ui_builder import UIBuilderMixin
from ..engine.image_loader import ImageLoaderMixin
from ..engine.paste_engine import PasteEngineMixin
from ..engine.event_handler import EventHandlerMixin
from .i18n import t as tr
from .theme import ThemeManager, ThemeMode
from .dwm import set_titlebar_dark
from .settings_dialog import SettingsDialog


class ImageEditor(UIBuilderMixin, ImageLoaderMixin, PasteEngineMixin,
                   EventHandlerMixin, QMainWindow):
    """贴图标注工具主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PasteLabel")
        self.resize(WINDOW_CONFIG['default_width'], WINDOW_CONFIG['default_height'])

        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.setWindowIcon(create_app_icon(script_dir))

        self._load_settings()
        self._init_data()
        self._is_delete_view = False
        self._nav_step = 1
        self.edit_mode = 'paste'
        self.init_ui()
        self._apply_theme()
        self._refresh_ui_texts()
        self._connect_manager_signals()
        self.update_label_list()
        self.installEventFilterRecursive(self)
        self.setup_shortcuts()
        self.setAcceptDrops(True)

    def _load_settings(self):
        """从配置文件加载主题和语言设置"""
        from ..core import config_manager
        from . import i18n
        from .theme import ThemeManager, ThemeMode

        settings = config_manager.load_all()

        theme = settings.get('theme', 'light')
        ThemeManager.set_mode(ThemeMode.DARK if theme == 'dark' else ThemeMode.LIGHT)

        language = settings.get('language', 'zh')
        i18n.set_lang(language)

        self.shortcut_config = settings.get('shortcuts', {})
        self._max_labels = settings.get('max_labels', 3)

        from ..core.config import GRID_CONFIG
        if settings.get('grid_line_width') is not None:
            GRID_CONFIG['line_width'] = settings['grid_line_width']
        if settings.get('grid_alpha') is not None:
            GRID_CONFIG['alpha'] = settings['grid_alpha']

    def _init_data(self):
        """初始化数据结构"""
        from PyQt5.QtWidgets import QLineEdit
        from ..core.config import DEFAULT_PREFIX

        self.background_images = []
        self.current_background = None
        self.current_background_index = -1
        self.small_images = []
        self._handy_background_path = ""
        self._handy_paste_path = ""
        self._handy_label_path = ""
        self.canvas_items_dict = {}
        self.canvas_items = []
        self.selected_item = None
        self.is_dragging = False
        self.is_resizing = False
        self._canvas_drag_active = False
        self.drag_offset = QPoint(0, 0)
        self._busy = False

        self.detection_boxes_dict = {}
        self.detection_boxes = []
        self.global_labels = set()

        self.prefix_input = QLineEdit()
        self.prefix_input.setText(DEFAULT_PREFIX)
        self.prefix_checkbox_state = True
        self.default_prefix = DEFAULT_PREFIX

        self.is_thumbnail_mode = True
        self.thumbnail_grid_width = THUMBNAIL_CONFIG['grid_width']
        self.thumbnail_grid_height = THUMBNAIL_CONFIG['grid_height']
        self.thumbnail_spacing = THUMBNAIL_CONFIG['spacing']

        self.save_manager = SaveManager(self, self)
        self.label_manager = LabelManager(self, self)

        from ..engine.undo_manager import UndoManager
        self.undo_manager = UndoManager()

    def _connect_manager_signals(self):
        """连接管理器信号 → 编辑器 UI 刷新（需在 init_ui 之后调用）"""
        self.label_manager.data_changed.connect(self.canvas.update)
        self.label_manager.label_list_changed.connect(self.update_label_list)
        self.save_manager.save_completed.connect(self._on_save_completed)
        self.save_manager.label_list_changed.connect(self.update_label_list)
        self._is_delete_view = False

    def _save_handy_record_on_close(self):
        """关闭时保存当前素材来源路径组合。"""
        from ..core import config_manager

        record = {
            'note': '',
            'background_path': self._handy_background_path,
            'paste_path': self._handy_paste_path,
            'label_path': self._handy_label_path,
            'background_index': self.current_background_index if self.current_background_index >= 0 else 0,
            'edit_mode': getattr(self, 'edit_mode', 'paste'),
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        for existing in config_manager.load_handy_records():
            if all(existing.get(k) == record[k] for k in ('background_path', 'paste_path', 'label_path')):
                record['note'] = existing.get('note', '')
                break
        config_manager.upsert_handy_record(record)

    def load_handy_record(self, record):
        """用巧手记录替换当前打开的背景图、贴图和标签来源。"""
        self._clear_handy_content()
        missing = []

        bg_path = record.get('background_path') or ''
        paste_path = record.get('paste_path') or ''
        label_path = record.get('label_path') or ''
        saved_index = int(record.get('background_index', 0) or 0)

        if bg_path:
            if os.path.isdir(bg_path):
                self.load_background_folder(bg_path)
                if self.background_images:
                    self.switch_background_to_index(saved_index)
            else:
                missing.append(bg_path)
        if paste_path:
            if os.path.isdir(paste_path):
                self.load_paste_folder(paste_path)
            else:
                missing.append(paste_path)
        if label_path:
            if os.path.isfile(label_path):
                self.load_paste_label_file(label_path)
            else:
                missing.append(label_path)

        self.update_file_count()
        if missing and hasattr(self, 'status_label'):
            self.status_label.setText(f"{tr('路径不存在')}: {missing[0]}")

    def _clear_handy_content(self):
        """加载记录前清空当前素材，避免新旧内容混在一起。"""
        self.background_images.clear()
        self.small_images.clear()
        self.canvas_items_dict.clear()
        self.detection_boxes_dict.clear()
        self.canvas_items.clear()
        self.detection_boxes.clear()
        self.global_labels.clear()
        self.current_background = None
        self.current_background_index = -1
        self.selected_item = None
        self._handy_background_path = ""
        self._handy_paste_path = ""
        self._handy_label_path = ""
        for widget_name in ('background_list', 'small_list', 'label_list'):
            if hasattr(self, widget_name):
                getattr(self, widget_name).clear()
        if hasattr(self, 'paste_label_list'):
            self.paste_label_list.clear()
            self.paste_label_list.addItem('paste')
        if hasattr(self, 'canvas'):
            self.canvas.update()

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
        self._update_status_info()
        self.canvas.update()

    def _update_mode_seg_style(self, animated=False):
        """刷新模式分段按钮的选中样式（照搬MemoPaws）"""
        if not hasattr(self, 'btn_paste_mode'):
            return
        from .theme import ThemeManager, ThemeMode, DARK_THEME, LIGHT_THEME
        is_dark = ThemeManager.get_mode() == ThemeMode.DARK
        t = DARK_THEME if is_dark else LIGHT_THEME
        is_paste = self.edit_mode == 'paste'
        self.btn_paste_mode.blockSignals(True)
        self.btn_annotate_mode.blockSignals(True)
        self.btn_paste_mode.setChecked(is_paste)
        self.btn_annotate_mode.setChecked(not is_paste)
        self.btn_paste_mode.blockSignals(False)
        self.btn_annotate_mode.blockSignals(False)
        btn_ss = f"QPushButton {{ background: transparent; color: {t['accent']}; border: none; font-size: 11px; font-weight: bold; padding: 3px 8px; }}"
        active_text_ss = f"QPushButton {{ background: transparent; color: #FFFFFF; border: none; font-size: 11px; font-weight: bold; padding: 3px 8px; }}"
        self.btn_paste_mode.setStyleSheet(active_text_ss if is_paste else btn_ss)
        self.btn_annotate_mode.setStyleSheet(active_text_ss if not is_paste else btn_ss)
        if hasattr(self, 'mode_seg_ctrl'):
            self.mode_seg_ctrl.set_accent(t['accent'])
            self.mode_seg_ctrl.update_position(animated=animated)
        if hasattr(self, 'mode_seg'):
            self.mode_seg.setStyleSheet(f"""
                QFrame {{
                    background-color: {t['accent_light']};
                    border: 1px solid {t['accent']};
                    border-radius: 5px;
                }}
            """)

    def _toggle_edit_mode(self):
        """切换标注/贴图模式"""
        sender = self.sender()
        if sender == self.btn_paste_mode:
            self.edit_mode = 'paste'
        else:
            self.edit_mode = 'annotate'
        self._update_mode_seg_style(animated=True)
        from PyQt5.QtCore import QTimer
        mode_text = "Annotate" if self.edit_mode == 'annotate' else "Paste"
        self.status_label.setText(f"Mode: {mode_text}")
        QTimer.singleShot(2000, lambda: self.status_label.setText(""))

    def _toggle_view_path(self):
        """切换工作路径/移除路径视图"""
        from . import i18n
        _tr = i18n.t
        self._is_delete_view = not self._is_delete_view
        if self._is_delete_view:
            self.view_toggle_btn.setText(_tr("移除路径"))
            self._saved_work_index = self.current_background_index
            self._show_delete_view()
            saved_del = getattr(self, '_saved_delete_idx', 0)
            if self._delete_files and saved_del < len(self._delete_files):
                self._delete_current_idx = saved_del
                self._load_delete_image(saved_del)
                self.background_list.setCurrentRow(saved_del)
            for sc in getattr(self, '_shortcuts', []):
                key = sc.key().toString()
                if key in ('W', 'Q', 'Delete'):
                    sc.setEnabled(False)
            if hasattr(self, 'draw_box_btn'):
                self.draw_box_btn.setEnabled(False)
        else:
            self.view_toggle_btn.setText(_tr("工作路径"))
            self._saved_delete_idx = getattr(self, '_delete_current_idx', 0)
            saved = getattr(self, '_saved_work_index', 0)
            self._show_work_view()
            if self.background_images and saved < len(self.background_images):
                self.current_background_index = saved
                from PyQt5.QtGui import QPixmap
                pixmap = QPixmap(self.background_images[saved])
                if not pixmap.isNull():
                    self.current_background = pixmap
                    self.detection_boxes = self.detection_boxes_dict.get(saved, []).copy()
                    self.canvas_items = self.canvas_items_dict.get(saved, [])
                    self.canvas.reset_view()
                    self.canvas.repaint()
                    self.update_label_list()
                self.update_file_count()
                if saved < self.background_list.count():
                    self.background_list.setCurrentRow(saved)
            for sc in getattr(self, '_shortcuts', []):
                sc.setEnabled(True)
            if hasattr(self, 'draw_box_btn'):
                self.draw_box_btn.setEnabled(True)
        from PyQt5.QtCore import QTimer
        mode_text = "Removed" if self._is_delete_view else "Work"
        self.status_label.setText(f"Path: {mode_text}")
        QTimer.singleShot(2000, lambda: self.status_label.setText(""))

    def _show_work_view(self):
        """显示工作路径列表"""
        self.background_list.clear()
        from ..core.utils import PathUtils
        from ..core.config import SUPPORTED_IMAGE_EXTENSIONS
        for i, path in enumerate(self.background_images):
            ext = os.path.splitext(path)[1].lower()
            if ext in SUPPORTED_IMAGE_EXTENSIONS:
                from PyQt5.QtWidgets import QListWidgetItem
                item = QListWidgetItem(PathUtils.to_display_path(path))
                item.setData(Qt.UserRole, i)
                self.background_list.addItem(item)
        if 0 <= self.current_background_index < self.background_list.count():
            self.background_list.setCurrentRow(self.current_background_index)
            self.update_file_count()
        elif self.background_images:
            self.current_background_index = 0
            self.background_list.setCurrentRow(0)
            from PyQt5.QtGui import QPixmap
            pixmap = QPixmap(self.background_images[0])
            if not pixmap.isNull():
                self.current_background = pixmap
                self.detection_boxes = self.detection_boxes_dict.get(0, []).copy()
                self.canvas_items = self.canvas_items_dict.get(0, [])
                self.canvas.reset_view()
                self.canvas.repaint()
                self.update_label_list()
            self.update_file_count()

    def _show_delete_view(self):
        """显示移除路径列表"""
        self.background_list.clear()
        from ..core.config import SUPPORTED_IMAGE_EXTENSIONS
        self._delete_files = []
        if self.background_images:
            delete_dir = os.path.join(
                os.path.dirname(self.background_images[0]), '_delete_')
            if os.path.isdir(delete_dir):
                from ..core.utils import PathUtils
                for f in sorted(os.listdir(delete_dir)):
                    fp = os.path.join(delete_dir, f)
                    ext = os.path.splitext(f)[1].lower()
                    if os.path.isfile(fp) and ext in SUPPORTED_IMAGE_EXTENSIONS:
                        self._delete_files.append(fp)
                        self.background_list.addItem(PathUtils.to_display_path(fp))
        if self._delete_files:
            target = getattr(self, '_saved_delete_idx', 0)
            target = min(target, len(self._delete_files) - 1)
            self._delete_current_idx = target
            self._load_delete_image(target)
            self.background_list.blockSignals(True)
            self.background_list.setCurrentRow(target)
            self.background_list.blockSignals(False)
            filename = os.path.basename(self._delete_files[target])
            total = len(self._delete_files)
            if self.current_background:
                w = self.current_background.width()
                h = self.current_background.height()
                self.setWindowTitle(f"PasteLabel - {filename} [{w} x {h}] [{target + 1} / {total}]")
            else:
                self.setWindowTitle(f"PasteLabel - {filename} [{target + 1} / {total}]")
        else:
            self.setWindowTitle("PasteLabel")
            self.current_background = None
            self.detection_boxes = []
            self.canvas_items = []
            self.canvas.repaint()
        self.update_label_list()

    def _load_delete_image(self, idx):
        """加载移除路径图片到画布"""
        from PyQt5.QtGui import QPixmap
        if 0 <= idx < len(self._delete_files):
            pixmap = QPixmap(self._delete_files[idx])
            if not pixmap.isNull():
                self.current_background = pixmap
                self.canvas.background_scale = 1.0
                self.canvas.is_manual_scale = False
                self.canvas.reset_view()
                self.canvas.selected_box = None
                self.selected_item = None
                self.canvas_items = []
                self.detection_boxes = self.load_detection_boxes(self._delete_files[idx])
                self.update_label_list()
                self.canvas.repaint()

    def _remove_to_delete(self, idx):
        """移除文件到 _delete_ 文件夹"""
        import shutil
        if idx < 0 or idx >= len(self.background_images):
            return
        file_path = self.background_images[idx]

        delete_dir = os.path.join(os.path.dirname(file_path), '_delete_')
        os.makedirs(delete_dir, exist_ok=True)

        shutil.move(file_path, os.path.join(delete_dir, os.path.basename(file_path)))
        json_path = os.path.splitext(file_path)[0] + '.json'
        if os.path.isfile(json_path):
            shutil.move(json_path, os.path.join(delete_dir, os.path.basename(json_path)))

        self.background_images.pop(idx)
        if idx in self.canvas_items_dict:
            del self.canvas_items_dict[idx]
        if idx in self.detection_boxes_dict:
            del self.detection_boxes_dict[idx]

        new_idx = min(idx, len(self.background_images) - 1)
        if self.background_images:
            self.current_background_index = new_idx
            from PyQt5.QtGui import QPixmap
            pixmap = QPixmap(self.background_images[new_idx])
            if not pixmap.isNull():
                self.current_background = pixmap
                self.canvas.reset_view()
                self.canvas.update()
        else:
            self.current_background = None
            self.current_background_index = -1

        self._show_delete_view()
        self.update_file_count()

    def _restore_from_delete(self, idx):
        """从 _delete_ 恢复文件"""
        import shutil
        if idx < 0 or idx >= self.background_list.count():
            return
        item = self.background_list.item(idx)
        text = item.text()
        delete_dir = os.path.join(
            os.path.dirname(self.background_images[0]) if self.background_images else '', '_delete_')

        for f in os.listdir(delete_dir):
            if f in text or text.endswith(f):
                src = os.path.join(delete_dir, f)
                dst = os.path.join(os.path.dirname(delete_dir), f)
                shutil.move(src, dst)
                self.background_images.append(dst)
                self.canvas_items_dict[len(self.background_images) - 1] = []
                self.detection_boxes_dict[len(self.background_images) - 1] = []
                break

        self.current_background_index = len(self.background_images) - 1
        self._show_delete_view()
        self.update_file_count()

    def _show_label_stats(self):
        """显示标签统计弹窗"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView
        from .theme import ThemeManager
        from . import i18n
        tr = i18n.t

        t = ThemeManager.get_theme()
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("标签统计"))
        dialog.setMinimumSize(400, 300)
        from PyQt5.QtCore import QTimer
        def _sync():
            hwnd = int(dialog.winId())
            from .dwm import set_titlebar_dark
            set_titlebar_dark(hwnd, is_dark)
        is_dark = ThemeManager.get_mode().value == "dark"
        QTimer.singleShot(30, _sync)
        dialog.setStyleSheet(f"""
            QDialog {{ background-color: {t['widget_bg']}; color: {t['text_primary']}; }}
            QTableWidget {{ background-color: {t['widget_bg']}; color: {t['text_primary']};
                border: 1px solid {t['border_color']}; gridline-color: {t['border_color']}; }}
            QTableWidget::item {{ padding: 4px; }}
            QTableWidget::item:selected {{ background-color: {t['accent_light']}; color: {t['accent']}; }}
            QHeaderView::section {{ background-color: {t['panel_bg']}; color: {t['text_primary']};
                border: 1px solid {t['border_color']}; padding: 4px; font-weight: bold; }}
            QTableWidget QTableCornerButton::section {{ background-color: {t['panel_bg']};
                border: 1px solid {t['border_color']}; }}
        """)

        layout = QVBoxLayout(dialog)

        bg_label = QLabel(tr("背景图标签"))
        bg_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(bg_label)

        bg_stats = {}
        for idx, file_path in enumerate(self.background_images):
            boxes = self.detection_boxes_dict.get(idx, [])
            for box in boxes:
                lbl = box.get("label", "")
                if lbl:
                    bg_stats[lbl] = bg_stats.get(lbl, 0) + 1

        bg_table = QTableWidget(len(bg_stats), 2)
        bg_table.setHorizontalHeaderLabels([tr("类别"), tr("数量")])
        bg_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for row, (label, count) in enumerate(sorted(bg_stats.items(), key=lambda x: -x[1])):
            bg_table.setItem(row, 0, QTableWidgetItem(label))
            bg_table.setItem(row, 1, QTableWidgetItem(str(count)))
        layout.addWidget(bg_table)

        paste_label = QLabel(tr("贴图标签_list"))
        paste_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(paste_label)

        paste_stats = {}
        for _, _, lbl in self.canvas_items:
            if lbl:
                paste_stats[lbl] = paste_stats.get(lbl, 0) + 1

        paste_table = QTableWidget(len(paste_stats), 2)
        paste_table.setHorizontalHeaderLabels([tr("类别"), tr("数量")])
        paste_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for row, (label, count) in enumerate(sorted(paste_stats.items(), key=lambda x: -x[1])):
            paste_table.setItem(row, 0, QTableWidgetItem(label))
            paste_table.setItem(row, 1, QTableWidgetItem(str(count)))
        layout.addWidget(paste_table)

        total = QLabel(
            f"{tr('总计')}: {tr('背景图标签')} {sum(bg_stats.values())} {tr('个')} | "
            f"{tr('贴图标签_list')} {sum(paste_stats.values())} {tr('个')}"
        )
        total.setStyleSheet("font-size: 12px; margin-top: 8px;")
        layout.addWidget(total)

        from .dialog_helpers import center_on_parent
        center_on_parent(dialog, self)
        dialog.exec_()

    def showEvent(self, event):
        """窗口显示后设置标题栏颜色（winId 必须在 show 之后获取）"""
        super().showEvent(event)
        from PyQt5.QtCore import QTimer
        is_dark = ThemeManager.get_mode().value == "dark"
        QTimer.singleShot(30, lambda: self._set_titlebar_dark(is_dark))

    def _set_titlebar_dark(self, dark):
        """设置系统标题栏颜色"""
        hwnd = int(self.winId())
        set_titlebar_dark(hwnd, dark)

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

    def _update_status_info(self):
        """更新状态栏信息"""
        info = self.get_image_info()
        if info:
            stats = self.get_label_stats()
            stats_text = " | ".join([f"{k}:{v}" for k, v in list(stats.items())[:3]])
            self.status_label.setText(
                f"Paste: {info['paste_count']} Box: {info['box_count']}"
                + (f" | {stats_text}" if stats_text else "")
            )

    def toggle_theme(self):
        """切换主题"""
        from ..core import config_manager
        ThemeManager.toggle()
        self._apply_theme()
        self._update_mode_seg_style()
        is_dark = ThemeManager.get_mode().value == "dark"
        self._set_titlebar_dark(is_dark)
        config_manager.save_theme('dark' if is_dark else 'light')
        self.status_label.setText(f"Theme: {'Dark' if is_dark else 'Light'}")
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(2000, lambda: self.status_label.setText(""))

    def toggle_language(self):
        """切换中英文"""
        from . import i18n
        from ..core import config_manager
        i18n.toggle_lang()
        config_manager.save_language(i18n.get_lang())
        self._refresh_ui_texts()
        lang_name = "Chinese" if i18n.get_lang() == "zh" else "English"
        self.status_label.setText(f"Language: {lang_name}")
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(2000, lambda: self.status_label.setText(""))

    def _refresh_ui_texts(self):
        """刷新所有界面文字"""
        from . import i18n
        tr = i18n.t
        if hasattr(self, 'draw_box_btn'):
            sc = self._get_shortcut('draw_box')
            self.draw_box_btn.setText(f"{tr('绘制BOX')}({sc})")
            self.draw_box_btn.setToolTip(tr("绘制检测框"))
        self.auto_save_checkbox.setText(tr("自动保存"))
        self.show_labels_checkbox.setText(tr("显示BOX"))
        self.show_label_names_checkbox.setText(tr("显示Label"))
        self.auto_label_checkbox.setText(tr("贴图标签"))
        self.prefix_checkbox.setText(tr("添加文件名前缀"))
        self.show_grid_checkbox.setText(tr("显示网格"))
        self.show_paste_names_checkbox.setText(tr("显示贴图名"))
        self.random_paste_btn.setText(tr("随机贴图"))
        self.batch_paste_btn.setText(tr("一键贴图"))
        is_thumb = self.is_thumbnail_mode
        self.toggle_view_btn.setText(tr("列表视图") if is_thumb else tr("缩略视图"))
        self.clear_btn.setText(tr("清空画布"))
        self.save_btn.setText(tr("保存图片"))
        self.save_all_btn.setText(tr("全部保存"))
        if hasattr(self, 'view_stats_btn'):
            self.view_stats_btn.setText(tr("查看"))
            self.view_stats_btn.setToolTip(tr("标签统计"))
        if hasattr(self, 'view_toggle_btn'):
            if self._is_delete_view:
                self.view_toggle_btn.setText(tr("移除路径"))
            else:
                self.view_toggle_btn.setText(tr("工作路径"))
        if hasattr(self, 'btn_paste_mode'):
            from . import i18n
            is_en = i18n.get_lang() == "en"
            if is_en:
                self.btn_paste_mode.setText("Paste")
                self.btn_annotate_mode.setText("Annotate")
            else:
                self.btn_paste_mode.setText(tr("贴图"))
                self.btn_annotate_mode.setText(tr("标注"))
            self._update_mode_seg_style()
        if hasattr(self, 'step_label'):
            self.step_label.setText(tr("步长："))
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
        if hasattr(self, 'options_btn'):
            self.options_btn.setText(tr("选项"))
        if hasattr(self, 'handy_btn'):
            self.handy_btn.setText(tr("巧手"))
            self.handy_btn.setToolTip(tr("巧手记录"))
        if hasattr(self, '_draw_box_action'):
            sc = self._get_shortcut('draw_box')
            self._draw_box_action.setText(f"  {tr('绘制BOX')}\t{sc}")
        if hasattr(self, '_menu_actions'):
            menu_texts = [tr("显示BOX"), tr("显示Label"),
                         tr("自动保存"), tr("显示网格"), tr("显示贴图名"), tr("添加文件名前缀")]
            for i, item in enumerate(self._menu_actions):
                action = item[0]
                shortcut_action = item[2] if len(item) > 2 else None
                if i < len(menu_texts):
                    text = menu_texts[i]
                    sc = self._get_shortcut(shortcut_action) if shortcut_action else ''
                    action.setText(f"{text}\t{sc}" if sc else text)
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

    def _refresh_menu_shortcuts(self):
        """刷新选项菜单中的快捷键显示"""
        from . import i18n
        tr = i18n.t
        if hasattr(self, '_draw_box_action'):
            sc = self._get_shortcut('draw_box')
            self._draw_box_action.setText(f"  {tr('绘制BOX')}\t{sc}")
        if hasattr(self, '_menu_actions'):
            menu_texts = [tr("显示BOX"), tr("显示Label"),
                         tr("自动保存"), tr("显示网格"), tr("显示贴图名"), tr("添加文件名前缀")]
            for i, item in enumerate(self._menu_actions):
                action = item[0]
                shortcut_action = item[2] if len(item) > 2 else None
                if i < len(menu_texts):
                    text = menu_texts[i]
                    sc = self._get_shortcut(shortcut_action) if shortcut_action else ''
                    action.setText(f"{text}\t{sc}" if sc else text)
        if hasattr(self, 'draw_box_btn'):
            sc = self._get_shortcut('draw_box')
            self.draw_box_btn.setText(f"{tr('绘制BOX')}({sc})")

    def save_undo_state(self):
        """保存撤销状态"""
        self.undo_manager.save_state(self.canvas_items, self.detection_boxes)

    def undo(self):
        """撤销"""
        self.canvas_items, self.detection_boxes = self.undo_manager.undo(
            self.canvas_items, self.detection_boxes
        )
        self.canvas.update()
        self.update_label_list()

    def redo(self):
        """重做"""
        self.canvas_items, self.detection_boxes = self.undo_manager.redo(
            self.canvas_items, self.detection_boxes
        )
        self.canvas.update()
        self.update_label_list()

    def toggle_grid(self):
        """切换网格显示"""
        if hasattr(self, 'show_grid_checkbox'):
            self.show_grid_checkbox.setChecked(not self.show_grid_checkbox.isChecked())
            self.canvas.update()

    def open_settings(self):
        """打开设置对话框"""
        dialog = SettingsDialog(self)
        dialog.exec_()

    def get_image_info(self):
        """获取当前图片信息"""
        if self.current_background is None:
            return None
        info = {
            'width': self.current_background.width(),
            'height': self.current_background.height(),
            'path': self.background_images[self.current_background_index] if self.current_background_index >= 0 else '',
            'paste_count': len(self.canvas_items),
            'box_count': len(self.detection_boxes),
        }
        return info

    def get_label_stats(self):
        """获取标签统计"""
        stats = {}
        for _, _, label in self.canvas_items:
            stats[label] = stats.get(label, 0) + 1
        for box in self.detection_boxes:
            label = box.get('label', 'unknown')
            stats[label] = stats.get(label, 0) + 1
        return stats


# 程序入口
    # ========== 拖拽：拖入图片文件上传 ==========

    def dragEnterEvent(self, event: QDragEnterEvent):
        """接受图片和JSON文件拖入"""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                ext = os.path.splitext(url.toLocalFile())[1].lower()
                if ext in ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.json'):
                    event.acceptProposedAction()
                    return

    def dropEvent(self, event: QDropEvent):
        """处理拖入的图片和JSON文件"""
        from ..core.config import SUPPORTED_IMAGE_EXTENSIONS
        existing = {os.path.normpath(p) for p in self.background_images}
        images = []
        jsons = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            norm_path = os.path.normpath(path)
            ext = os.path.splitext(path)[1].lower()
            if ext in SUPPORTED_IMAGE_EXTENSIONS:
                if norm_path not in existing:
                    images.append(path)
            elif ext == '.json':
                jsons.append(path)
        if images:
            self._append_background_images(images)
        if jsons:
            self._apply_dropped_json(jsons)
        event.acceptProposedAction()

    def _append_background_images(self, files):
        """追加背景图片（不替换已有，自动去重）"""
        from PyQt5.QtGui import QPixmap
        from PyQt5.QtWidgets import QApplication
        from ..core.utils import PathUtils
        first_new = len(self.background_images)
        for file in files:
            if file in self.background_images:
                continue
            pixmap = QPixmap(file)
            if not pixmap.isNull():
                new_index = len(self.background_images)
                self.background_images.append(file)
                display_path = PathUtils.to_display_path(file)
                from PyQt5.QtWidgets import QListWidgetItem
                item = QListWidgetItem(display_path)
                item.setData(Qt.UserRole, new_index)
                item.setData(Qt.UserRole + 1, file)
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
        if self.background_images:
            self.background_list.setCurrentRow(first_new)

    def _apply_dropped_json(self, json_files):
        """将拖入的JSON标签文件按文件名匹配应用到对应背景图"""
        import json as _json
        if not json_files:
            return
        for jf in json_files:
            if not os.path.isfile(jf):
                continue
            try:
                with open(jf, 'r', encoding='utf-8') as f:
                    data = _json.load(f)
                if not isinstance(data, dict) or 'shapes' not in data:
                    continue
                boxes = []
                for shape in data['shapes']:
                    if not isinstance(shape, dict):
                        continue
                    if not all(k in shape for k in ('label', 'points')):
                        continue
                    points = shape['points']
                    if len(points) < 2:
                        continue
                    xs = [p[0] for p in points]
                    ys = [p[1] for p in points]
                    boxes.append({
                        'x': min(xs), 'y': min(ys),
                        'width': max(xs) - min(xs),
                        'height': max(ys) - min(ys),
                        'label': shape['label'],
                    })
                if not boxes:
                    continue
                json_stem = os.path.splitext(os.path.basename(jf))[0]
                target_index = -1
                for idx, img_path in enumerate(self.background_images):
                    img_stem = os.path.splitext(os.path.basename(img_path))[0]
                    if img_stem == json_stem:
                        target_index = idx
                        break
                if target_index < 0:
                    target_index = self.current_background_index
                if target_index < 0:
                    continue
                existing = self.detection_boxes_dict.get(target_index, [])
                existing.extend(boxes)
                self.detection_boxes_dict[target_index] = existing
                if target_index == self.current_background_index:
                    self.detection_boxes = self.detection_boxes_dict[target_index].copy()
            except Exception as e:
                from ..core.exception_hook import _write_log
                _write_log(f"拖入JSON加载失败: {jf}, {e}")

        self.update_label_list()
        self.canvas.update()


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
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
