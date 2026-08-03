"""
主窗口模块 - ImageEditor 主窗口逻辑（协调器）
"""
import os
import sys
from datetime import datetime
from PyQt5.QtWidgets import QMainWindow, QApplication
from PyQt5.QtCore import QPoint, Qt, QUrl, QTimer, QRectF
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QDrag, QIcon

from ..core.config import WINDOW_CONFIG, THUMBNAIL_CONFIG, MAGNIFIER_CONFIG, DETECTION_BOX_WHEEL_CONFIG, CROSSHAIR_CONFIG, BOX_BORDER_CONFIG
from ..core.utils import create_app_icon
from ..engine.save_manager import SaveManager
from ..engine.label_manager import LabelManager
from .ui_builder import UIBuilderMixin, _load_svg_icon, SUN_SVG, MOON_SVG
from ..engine.image_loader import ImageLoaderMixin
from ..engine.paste_engine import PasteEngineMixin
from ..engine.event_handler import EventHandlerMixin
from .i18n import t as tr
from .theme import ThemeManager, ThemeMode
from .dwm import set_titlebar_dark
from .settings_dialog import SettingsDialog
from .processing_panel import ProcessingPanel


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
        self.edit_mode = 'annotate'
        self.init_ui()
        self._apply_theme()
        self._refresh_ui_texts()
        self._connect_manager_signals()
        self.update_label_list()
        self.installEventFilterRecursive(self)
        self.setup_shortcuts()
        self.setAcceptDrops(True)
        self._apply_paste_label_visibility()
        if hasattr(self, 'auto_save_b_checkbox'):
            self.auto_save_b_checkbox.setChecked(self.edit_mode == 'annotate')
            self.auto_save_p_checkbox.setChecked(self.edit_mode == 'paste')
        self._apply_paste_label_visibility()

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
        self.label_colors = settings.get('label_colors', [])
        self.label_color_map = settings.get('label_color_map', {})
        self._label_color_map_palette = tuple(self.label_colors)
        self._max_labels = settings.get('max_labels', 3)
        self.label_cache_slots = settings.get('label_cache_slots', [])
        self.active_label_cache_slot = 0
        self._label_cache_copy_counter = max(
            [int(slot.get('copy_order', 0) or 0) for slot in self.label_cache_slots] or [0]
        )

        from ..core.config import GRID_CONFIG, DETECTION_BOX_CONFIG, PASTE_ITEM_CONFIG, NUDGE_CONFIG, DETECTION_BOX_WHEEL_CONFIG, CROSSHAIR_CONFIG
        if settings.get('grid_line_width') is not None:
            GRID_CONFIG['line_width'] = settings['grid_line_width']
        if settings.get('grid_alpha') is not None:
            GRID_CONFIG['alpha'] = settings['grid_alpha']
        if settings.get('resize_handle_size') is not None:
            handle_size = max(3, min(15, int(settings['resize_handle_size'])))
            DETECTION_BOX_CONFIG['resize_handle_size'] = handle_size
            PASTE_ITEM_CONFIG['handle_size'] = handle_size
        if settings.get('label_font_size') is not None:
            DETECTION_BOX_CONFIG['label_font_size'] = max(5, min(15, int(settings['label_font_size'])))
        if settings.get('label_position') in ('outside', 'inside'):
            DETECTION_BOX_CONFIG['label_position'] = settings['label_position']
        self._canvas_image_copy_enabled = bool(settings.get('canvas_image_copy_enabled', False))
        self._magnifier_enabled = bool(settings.get('magnifier_enabled', False))
        MAGNIFIER_CONFIG['zoom'] = max(0.8, min(3.0, float(settings.get('magnifier_zoom', MAGNIFIER_CONFIG['zoom']))))
        MAGNIFIER_CONFIG['size'] = max(80, min(400, int(settings.get('magnifier_size', MAGNIFIER_CONFIG['size']))))
        pos = settings.get('magnifier_position', MAGNIFIER_CONFIG['position'])
        MAGNIFIER_CONFIG['position'] = pos if pos in ('side', 'center') else 'side'
        NUDGE_CONFIG['step'] = max(1, min(5, int(settings.get('nudge_step', NUDGE_CONFIG['step']))))
        DETECTION_BOX_WHEEL_CONFIG['detection_box_scale_step'] = max(0.01, min(0.30, float(settings.get('detection_box_scale_step', DETECTION_BOX_WHEEL_CONFIG['detection_box_scale_step']))))
        DETECTION_BOX_WHEEL_CONFIG['paste_item_scale_step'] = max(0.01, min(0.30, float(settings.get('paste_item_scale_step', DETECTION_BOX_WHEEL_CONFIG['paste_item_scale_step']))))
        DETECTION_BOX_WHEEL_CONFIG['edge_step'] = max(1, min(50, int(settings.get('detection_box_wheel_edge_step', DETECTION_BOX_WHEEL_CONFIG['edge_step']))))
        CROSSHAIR_CONFIG['width'] = max(0.5, min(3.0, float(settings.get('crosshair_width', CROSSHAIR_CONFIG['width']))))
        color = str(settings.get('crosshair_color', CROSSHAIR_CONFIG['color']))
        CROSSHAIR_CONFIG['color'] = color if len(color) == 7 and color.startswith('#') else CROSSHAIR_CONFIG['color']
        CROSSHAIR_CONFIG['alpha'] = max(0, min(255, int(settings.get('crosshair_alpha', CROSSHAIR_CONFIG['alpha']))))
        from ..core.config import BOX_BORDER_CONFIG
        BOX_BORDER_CONFIG['width'] = max(1, min(4, float(settings.get('box_border_width', BOX_BORDER_CONFIG['width']))))

    def _init_data(self):
        """初始化数据结构"""
        from PyQt5.QtWidgets import QLineEdit
        from ..core.config import DEFAULT_PREFIX

        self.background_images = []
        self.current_background = None
        self.current_background_index = -1
        self.small_images = []
        self._memory_background_path = ""
        self._memory_paste_path = ""
        self._memory_label_path = ""
        self.canvas_items_dict = {}
        self.canvas_items = []
        self.selected_item = None
        self.is_dragging = False
        self.is_resizing = False
        self._canvas_drag_active = False
        if not hasattr(self, '_canvas_image_copy_enabled'):
            self._canvas_image_copy_enabled = False
        if not hasattr(self, '_magnifier_enabled'):
            self._magnifier_enabled = False
        self.drag_offset = QPoint(0, 0)
        self._busy = False

        self.detection_boxes_dict = {}
        self.detection_boxes = []
        self._last_paste_slot = None
        self._last_paste_start = -1
        self._last_paste_count = 0
        self.global_labels = set()
        self.background_dataset_labels = set()
        self._bg_label_list_mode = 'stats'
        self.pressed_box_index = None
        self._bg_annotation_filter = 'all'  # all | annotated | unannotated | empty
        self._bg_filter_saved_index = 0
        self._cached_bg_label_stats = []
        self._cached_bg_label_stats_path = ""
        self._background_label_scan_generation = 0
        self._background_label_scan_worker = None
        self._background_label_scan_workers = set()
        self._background_label_scan_pending = False
        self._background_label_scan_completed = False

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

    def get_label_color(self, label):
        """获取标签颜色并缓存首次分配，避免标签顺序影响已有颜色。"""
        from ..core import config_manager
        color = config_manager.get_label_color(
            self._get_session_labels(), label, self.label_colors,
            self.label_color_map if (
                not hasattr(self, '_label_color_map_palette')
                or tuple(self.label_colors) == self._label_color_map_palette
            ) else {},
        )
        if label and label not in self.label_color_map:
            self.label_color_map[label] = color
            config_manager.save_all(
                label_colors=self.label_colors,
                label_color_map=self.label_color_map,
            )
            self._label_color_map_palette = tuple(self.label_colors)
        return color

    def _get_session_labels(self):
        """收集当前打开文件夹中用于共享色板的全部标签。"""
        labels = [box.get('label', '') for boxes in self.detection_boxes_dict.values() for box in boxes]
        labels.extend(box.get('label', '') for box in self.detection_boxes)
        labels.extend(item[2] for item in self.canvas_items)
        labels.extend(
            item[2] for idx, items in self.canvas_items_dict.items()
            if idx != self.current_background_index for item in items
        )
        return labels

    def _get_session_paste_stats(self):
        """按图片聚合当前会话的贴图标签。"""
        stats = {}
        for idx in range(len(self.background_images)):
            items = self.canvas_items if idx == self.current_background_index else self.canvas_items_dict.get(idx, [])
            for _, _, label in items:
                if label:
                    stats[label] = stats.get(label, 0) + 1
        return stats

    def _save_label_cache_slots(self):
        from ..core import config_manager
        config_manager.save_all(label_cache_slots=self.label_cache_slots)

    def _get_next_writable_label_cache_slot_index(self):
        writable_slots = [
            (index, slot) for index, slot in enumerate(self.label_cache_slots)
            if not slot.get('locked')
        ]
        if not writable_slots:
            return None
        return min(
            writable_slots,
            key=lambda item: int(item[1].get('copy_order', 0) or 0),
        )[0]

    def _reset_label_cache_slots(self):
        for index, slot in enumerate(self.label_cache_slots):
            default_shortcut = str(index + 1)
            default_name = f"{tr('缓存槽')}{index + 1}"
            slot['name'] = default_name
            slot['locked'] = False
            slot['items'] = []
            slot['copied_at'] = ''
            slot['copy_order'] = 0
            slot['shortcut'] = str(slot.get('shortcut') or default_shortcut)
        self.active_label_cache_slot = 0
        self._label_cache_copy_counter = 0

    def set_active_label_cache_slot(self, slot_index):
        if slot_index < 0 or slot_index >= len(self.label_cache_slots):
            return
        self.active_label_cache_slot = slot_index
        self._rebuild_label_cache_menu()

    def _get_selected_detection_boxes(self):
        multi_indexes = [
            index for index in getattr(self.canvas, 'selected_boxes', [])
            if 0 <= index < len(self.detection_boxes)
        ]
        if multi_indexes:
            return [dict(self.detection_boxes[index]) for index in multi_indexes]

        index = getattr(self.canvas, 'selected_box', None)
        if index is None or index < 0 or index >= len(self.detection_boxes):
            return []
        return [dict(self.detection_boxes[index])]

    def copy_selected_labels_to_active_cache_slot(self):
        items = self._get_selected_detection_boxes()
        if not items and getattr(self, 'canvas', None):
            # hover 选中态可能还没同步到 selected_box，需要补一次同步。
            check_hover = getattr(self.canvas, '_check_hover', None)
            if callable(check_hover):
                check_hover()
                items = self._get_selected_detection_boxes()
        if not items:
            self.status_label.setText(tr("无可复制标签"))
            return
        slot_index = ImageEditor._get_next_writable_label_cache_slot_index(self)
        if slot_index is None:
            self.status_label.setText(tr("没有可写入的缓存槽"))
            return
        self.active_label_cache_slot = slot_index
        slot = self.label_cache_slots[slot_index]
        self._label_cache_copy_counter = getattr(self, '_label_cache_copy_counter', 0) + 1
        slot['items'] = items
        slot['copied_at'] = datetime.now().strftime('%H:%M:%S')
        slot['copy_order'] = self._label_cache_copy_counter
        self._last_paste_slot = None
        self._save_label_cache_slots()
        self._rebuild_label_cache_menu()

    def paste_label_cache_slot(self, slot_index):
        if self._is_delete_view or self.current_background is None:
            return
        if slot_index < 0 or slot_index >= len(self.label_cache_slots):
            return
        slot = self.label_cache_slots[slot_index]
        if not slot.get('items'):
            self.status_label.setText(tr("缓存槽为空"))
            return
        pasted_group = []
        for box in slot['items']:
            pasted_group.append((
                QRectF(box['x'], box['y'], box['width'], box['height']),
                box['label'],
            ))
        adjusted_group = self._offset_overlapping_paste_group(pasted_group)
        if adjusted_group:
            self.save_undo_state()
            self._last_paste_start = len(self.detection_boxes)
        for rect, label in adjusted_group:
            self.detection_boxes.append({
                'x': rect.x(),
                'y': rect.y(),
                'width': rect.width(),
                'height': rect.height(),
                'label': label,
            })
        if adjusted_group:
            self._last_paste_slot = slot_index
            self._last_paste_count = len(adjusted_group)
        if adjusted_group and self.current_background_index >= 0:
            self.detection_boxes_dict[self.current_background_index] = self.detection_boxes.copy()
        self.update_label_list()
        self.canvas.update()

    def _sync_pasted_boxes_to_cache(self):
        if self._last_paste_slot is None or self._last_paste_count <= 0:
            return
        start = self._last_paste_start
        end = start + self._last_paste_count
        if start < 0 or end > len(self.detection_boxes):
            return
        slot = self.label_cache_slots[self._last_paste_slot]
        slot['items'] = [dict(self.detection_boxes[i]) for i in range(start, end)]
        self._save_label_cache_slots()

    def toggle_label_cache_slot_lock(self, slot_index):
        if slot_index < 0 or slot_index >= len(self.label_cache_slots):
            return
        self.label_cache_slots[slot_index]['locked'] = not self.label_cache_slots[slot_index].get('locked')
        self._save_label_cache_slots()
        self._rebuild_label_cache_menu()

    def clear_label_cache_slot(self, slot_index):
        if slot_index < 0 or slot_index >= len(self.label_cache_slots):
            return
        if self.label_cache_slots[slot_index].get('locked'):
            return
        self.label_cache_slots[slot_index]['items'] = []
        self.label_cache_slots[slot_index]['copied_at'] = ''
        self.label_cache_slots[slot_index]['copy_order'] = 0
        self._save_label_cache_slots()
        self._rebuild_label_cache_menu()

    def rename_label_cache_slot(self, slot_index, name):
        if slot_index < 0 or slot_index >= len(self.label_cache_slots):
            return
        text = str(name or '').strip()
        if not text:
            text = f"{tr('缓存槽')}{slot_index + 1}"
        self.label_cache_slots[slot_index]['name'] = text
        self._save_label_cache_slots()
        self._rebuild_label_cache_menu()

    def _connect_manager_signals(self):
        """连接管理器信号 → 编辑器 UI 刷新（需在 init_ui 之后调用）"""
        self.label_manager.data_changed.connect(self.canvas.update)
        self.label_manager.label_list_changed.connect(self.update_label_list)
        self.save_manager.save_completed.connect(self._on_save_completed)
        self.save_manager.label_list_changed.connect(self.update_label_list)
        self._is_delete_view = False

    def _build_bg_label_stats_snapshot(self):
        """Build background label stats snapshot for memory / stats restore."""
        from ..engine.image_loader import collect_background_label_counts

        counts = collect_background_label_counts(list(self.background_images or []))
        for lbl in getattr(self, 'background_dataset_labels', set()) or set():
            counts.setdefault(lbl, 0)
        for lbl in getattr(self, 'global_labels', set()) or set():
            if lbl in counts or lbl in (getattr(self, 'background_dataset_labels', set()) or set()):
                counts.setdefault(lbl, 0)
        stats = []
        for label, count in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
            color = ''
            if hasattr(self, 'get_label_color'):
                try:
                    color = self.get_label_color(label)
                except Exception:
                    color = self.label_color_map.get(label, '') if hasattr(self, 'label_color_map') else ''
            elif hasattr(self, 'label_color_map'):
                color = self.label_color_map.get(label, '')
            stats.append({'label': label, 'count': int(count), 'color': color or ''})
        return stats

    def _save_memory_record_on_close(self):
        """关闭时保存当前素材来源路径组合。"""
        from ..core import config_manager

        bg_stats = self._build_bg_label_stats_snapshot()
        self._cached_bg_label_stats = bg_stats
        self._cached_bg_label_stats_path = self._memory_background_path or ''
        record = {
            'note': '',
            'background_path': self._memory_background_path,
            'paste_path': self._memory_paste_path,
            'label_path': self._memory_label_path,
            'background_index': self.current_background_index if self.current_background_index >= 0 else 0,
            'edit_mode': getattr(self, 'edit_mode', 'paste'),
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'bg_label_stats': bg_stats,
        }
        for existing in config_manager.load_memory_records():
            if all(existing.get(k) == record[k] for k in ('background_path', 'paste_path', 'label_path')):
                record['note'] = existing.get('note', '')
                break
        config_manager.upsert_memory_record(record)
        self._reset_label_cache_slots()
        self._save_label_cache_slots()

    def load_memory_record(self, record):
        """用记忆记录替换当前打开的背景图、贴图和标签来源。"""
        # 记忆弹窗关闭后直接等待加载完成，不再在画布上显示加载动画。
        QApplication.processEvents()
        self._load_memory_record_now(record)

    def _load_memory_record_now(self, record):
        """实际加载记忆记录。"""
        self._clear_memory_content()
        missing = []

        bg_path = record.get('background_path') or ''
        paste_path = record.get('paste_path') or ''
        label_path = record.get('label_path') or ''
        saved_index = int(record.get('background_index', 0) or 0)

        target_background_index = None
        if bg_path:
            if os.path.isdir(bg_path):
                self.load_background_folder(bg_path, load_first=False)
                QApplication.processEvents()
                if self.background_images:
                    target_background_index = max(0, min(saved_index, len(self.background_images) - 1))
                    QApplication.processEvents()
            else:
                missing.append(bg_path)
        if paste_path:
            if os.path.isdir(paste_path):
                self.load_paste_folder(paste_path)
                QApplication.processEvents()
            else:
                missing.append(paste_path)
        if label_path:
            if os.path.isfile(label_path):
                self.load_paste_label_file(label_path)
                QApplication.processEvents()
            else:
                missing.append(label_path)

        edit_mode = record.get('edit_mode')
        if edit_mode not in ('paste', 'annotate'):
            edit_mode = 'annotate' if label_path and not paste_path else 'paste'
        self._set_edit_mode(edit_mode, animated=False)

        stats = record.get('bg_label_stats') or []
        if isinstance(stats, list):
            self._cached_bg_label_stats = list(stats)
            self._cached_bg_label_stats_path = bg_path or ''
            restored = {
                str(item.get('label', '')).strip()
                for item in stats
                if isinstance(item, dict) and str(item.get('label', '')).strip()
            }
            if restored:
                if not hasattr(self, 'background_dataset_labels'):
                    self.background_dataset_labels = set()
                self.background_dataset_labels.update(restored)
                self.global_labels.update(restored)
                for item in stats:
                    if not isinstance(item, dict):
                        continue
                    label = str(item.get('label', '')).strip()
                    color = str(item.get('color', '') or '').strip()
                    if label and color and hasattr(self, 'label_color_map'):
                        self.label_color_map.setdefault(label, color)
                if hasattr(self, 'update_label_list'):
                    self.update_label_list()

        self.update_file_count()
        if target_background_index is not None:
            self.switch_background_to_index(target_background_index)
        if missing and hasattr(self, 'status_label'):
            self.status_label.setText(f"{tr('路径不存在')}: {missing[0]}")

    def _clear_memory_content(self):
        """加载记录前清空当前素材，避免新旧内容混在一起。"""
        self.background_images.clear()
        self.small_images.clear()
        self.canvas_items_dict.clear()
        self.detection_boxes_dict.clear()
        self.canvas_items.clear()
        self.detection_boxes.clear()
        self.global_labels.clear()
        if hasattr(self, 'background_dataset_labels'):
            self.background_dataset_labels.clear()
        else:
            self.background_dataset_labels = set()
        self._cached_bg_label_stats = []
        self._cached_bg_label_stats_path = ""
        self._background_label_scan_pending = False
        self._background_label_scan_completed = False
        self._background_label_scan_in_progress = False
        self.current_background = None
        self.current_background_index = -1
        self.selected_item = None
        self._memory_background_path = ""
        self._memory_paste_path = ""
        self._memory_label_path = ""
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

    def auto_save_background(self):
        self.save_manager.auto_save_background()
    def auto_save_project(self):
        self.save_manager.auto_save_project()

    def save_current_json(self):
        """保存当前图的标注 JSON。"""
        self.save_manager.save_current_json()

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
        """同步模式分段控件的选中状态和指示器位置。"""
        if not hasattr(self, 'btn_paste_mode'):
            return
        is_paste = self.edit_mode == 'paste'
        self.btn_paste_mode.blockSignals(True)
        self.btn_annotate_mode.blockSignals(True)
        self.btn_paste_mode.setChecked(is_paste)
        self.btn_annotate_mode.setChecked(not is_paste)
        self.btn_paste_mode.blockSignals(False)
        self.btn_annotate_mode.blockSignals(False)
        if hasattr(self, 'mode_seg_ctrl'):
            self.mode_seg_ctrl.set_accent(ThemeManager.get_theme()["interaction_active"])
            self.mode_seg_ctrl.update_position(animated=animated)

    def _apply_mode_visibility_defaults(self):
        """模式切换时重置显示项，避免上个模式的显示状态串到当前模式。"""
        if not hasattr(self, 'show_label_names_checkbox'):
            return
        is_annotate = self.edit_mode == 'annotate'
        if hasattr(self, 'show_labels_checkbox'):
            self.show_labels_checkbox.setChecked(is_annotate)
        self.show_label_names_checkbox.setChecked(is_annotate)
        if hasattr(self, 'show_paste_names_checkbox'):
            self.show_paste_names_checkbox.setChecked(not is_annotate)

    def _toggle_edit_mode(self):
        """切换标注/贴图模式"""
        sender = self.sender()
        if sender == self.btn_paste_mode:
            self._set_edit_mode('paste', animated=True)
        else:
            self._set_edit_mode('annotate', animated=True)

    def _set_edit_mode(self, mode, animated=False):
        self.edit_mode = 'annotate' if mode == 'annotate' else 'paste'
        self.selected_item = None
        if hasattr(self, 'canvas'):
            self.canvas.selected_item_size = None
            self.canvas.selected_box = None
            self.canvas.selected_boxes = []
            self.canvas.hover_resize_target = None
            self.canvas.hover_resize_handle = None
            self.canvas.update()
        self._apply_mode_visibility_defaults()
        self._update_mode_seg_style(animated=animated)
        self._apply_paste_label_visibility()
        if hasattr(self, 'auto_save_b_checkbox'):
            is_annotate = self.edit_mode == 'annotate'
            self.auto_save_b_checkbox.setChecked(is_annotate)
            self.auto_save_p_checkbox.setChecked(not is_annotate)
            self.auto_save_b_checkbox.setText(f"{tr('自动保存B')}({tr('标注')})" if is_annotate else tr("自动保存B"))
            self.auto_save_p_checkbox.setText(f"{tr('自动保存P')}({tr('贴图')})" if not is_annotate else tr("自动保存P"))
        from PyQt5.QtCore import QTimer
        mode_text = "Annotate" if self.edit_mode == 'annotate' else "Paste"
        self.status_label.setText(f"Mode: {mode_text}")
        QTimer.singleShot(2000, lambda: self.status_label.setText(""))

    def _apply_paste_label_visibility(self):
        """Annotate: hide paste label column + paste list; paste: show both."""
        show = getattr(self, 'edit_mode', 'paste') != 'annotate'
        if hasattr(self, 'paste_label_column'):
            self.paste_label_column.setVisible(show)
        else:
            if hasattr(self, 'paste_label_list'):
                self.paste_label_list.setVisible(show)
            if hasattr(self, 'paste_label_header_lbl'):
                self.paste_label_header_lbl.setVisible(show)

        paste_group = getattr(self, 'paste_group', None)
        paste_header = getattr(self, 'paste_group_header', None)
        if paste_group is not None:
            paste_group.setVisible(show)
            if show and paste_header is not None:
                paste_header._expanded = True
                key = paste_header.property('title_key') or '贴图列表'
                paste_header.setText(f"▼  {tr(key)}")
                for section in getattr(self, '_side_sections', []) or []:
                    if section.get('header') is paste_header:
                        section['content'].setVisible(True)
                        break
            if hasattr(self, '_update_side_panel_stretches'):
                self._update_side_panel_stretches()

    def _toggle_bg_label_list_mode(self):
        """Switch background label list between stats counts and per-box rows."""
        current = getattr(self, '_bg_label_list_mode', 'stats')
        self._bg_label_list_mode = 'all' if current == 'stats' else 'stats'
        self._refresh_bg_label_mode_button()
        self.update_label_list()

    def _refresh_bg_label_mode_button(self):
        btn = getattr(self, 'bg_label_mode_btn', None)
        if btn is None:
            return
        from PyQt5.QtCore import QSize
        from PyQt5.QtGui import QIcon
        mode = getattr(self, '_bg_label_list_mode', 'stats')
        # stats: show "rows" icon (click → list); list: show "bars" icon (click → stats)
        if mode == 'all':
            btn.setIcon(QIcon(self._bg_label_mode_icon('stats')))
            btn.setToolTip(tr("切换到统计计数"))
        else:
            btn.setIcon(QIcon(self._bg_label_mode_icon('list')))
            btn.setToolTip(tr("切换到每框一行"))
        btn.setText("")
        btn.setIconSize(QSize(14, 14))

    def _bg_label_mode_icon(self, kind):
        """Paint a tiny mode glyph: list rows or count bars."""
        from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen
        from PyQt5.QtCore import Qt
        size = 14
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        color = QColor("#c0c4cc")
        if hasattr(self, 'theme_manager') and getattr(self, 'is_dark_theme', True) is False:
            color = QColor("#5a5e66")
        p.setPen(QPen(color, 1.6))
        if kind == 'list':
            # three equal horizontal rows
            for y in (3, 7, 11):
                p.drawLine(2, y, 12, y)
        else:
            # three vertical bars of different height (stats)
            p.setBrush(color)
            p.setPen(Qt.NoPen)
            p.drawRect(2, 8, 2, 5)
            p.drawRect(6, 4, 2, 9)
            p.drawRect(10, 6, 2, 7)
        p.end()
        return pm

    def _cycle_bg_annotation_filter(self):
        """Cycle background list filter: all → annotated → unannotated → empty."""
        order = ('all', 'annotated', 'unannotated', 'empty')
        current = getattr(self, '_bg_annotation_filter', 'all')
        try:
            idx = order.index(current)
        except ValueError:
            idx = 0
        next_mode = order[(idx + 1) % len(order)]
        if current == 'all' and next_mode != 'all':
            self._bg_filter_saved_index = self.current_background_index
        self._bg_annotation_filter = next_mode
        self._refresh_bg_filter_button()
        self._apply_bg_annotation_filter(navigate=True)

    def _refresh_bg_filter_button(self):
        btn = getattr(self, 'bg_filter_btn', None)
        if btn is None:
            return
        mode = getattr(self, '_bg_annotation_filter', 'all')
        tips = {
            'all': tr("筛选：全部"),
            'annotated': tr("筛选：已标注"),
            'unannotated': tr("筛选：未标注"),
            'empty': tr("筛选：空标签"),
        }
        from PyQt5.QtCore import QSize
        from ..engine.image_loader import _status_icon
        icon_key = mode if mode in ('all', 'annotated', 'unannotated', 'empty') else 'all'
        btn.setText("")
        btn.setIcon(_status_icon(icon_key, size=14))
        btn.setIconSize(QSize(14, 14))
        btn.setToolTip(tips.get(mode, tips['all']))
        in_delete = getattr(self, '_is_delete_view', False)
        btn.setVisible(not in_delete)

    def _apply_bg_annotation_filter(self, navigate=False):
        """Hide list rows that do not match the current annotation filter."""
        if getattr(self, '_is_delete_view', False):
            return
        bg_list = getattr(self, 'background_list', None)
        if bg_list is None:
            return
        mode = getattr(self, '_bg_annotation_filter', 'all')
        first_visible_row = None
        for row in range(bg_list.count()):
            item = bg_list.item(row)
            if item is None:
                continue
            status = item.data(Qt.UserRole + 2)
            if status is None:
                path = item.data(Qt.UserRole + 1)
                if not path:
                    idx = item.data(Qt.UserRole)
                    if isinstance(idx, int) and 0 <= idx < len(self.background_images):
                        path = self.background_images[idx]
                from ..engine.image_loader import annotation_status_for_image, decorate_background_list_item
                if path:
                    status = decorate_background_list_item(item, path, item.data(Qt.UserRole))
                else:
                    status = 'unannotated'
            visible = (mode == 'all') or (status == mode)
            item.setHidden(not visible)
            if visible and first_visible_row is None:
                first_visible_row = row

        if not navigate:
            return

        if mode in ('unannotated', 'empty'):
            target_row = first_visible_row
        else:
            # all / annotated: restore remembered work position when possible
            saved = getattr(self, '_bg_filter_saved_index', self.current_background_index)
            target_row = self._find_bg_list_row_for_index(saved)
            if target_row is None or (bg_list.item(target_row) and bg_list.item(target_row).isHidden()):
                if mode == 'annotated':
                    target_row = first_visible_row
                else:
                    target_row = self._find_bg_list_row_for_index(saved)
                    if target_row is None:
                        target_row = first_visible_row

        if target_row is None:
            return
        item = bg_list.item(target_row)
        if item is None:
            return
        bg_list.setCurrentRow(target_row)
        self.select_background(item)

    def _find_bg_list_row_for_index(self, image_index):
        bg_list = getattr(self, 'background_list', None)
        if bg_list is None or not isinstance(image_index, int):
            return None
        for row in range(bg_list.count()):
            item = bg_list.item(row)
            if item is None:
                continue
            if item.data(Qt.UserRole) == image_index:
                return row
        if 0 <= image_index < bg_list.count():
            return image_index
        return None

    def _refresh_background_item_status(self, image_index=None, image_path=None):
        """Refresh status icon for one background list row after save/load."""
        if getattr(self, '_is_delete_view', False):
            return
        bg_list = getattr(self, 'background_list', None)
        if bg_list is None:
            return
        from ..engine.image_loader import decorate_background_list_item
        if image_path is None and isinstance(image_index, int):
            if 0 <= image_index < len(self.background_images):
                image_path = self.background_images[image_index]
        if not image_path:
            return
        target_row = self._find_bg_list_row_for_index(image_index) if isinstance(image_index, int) else None
        if target_row is None:
            for row in range(bg_list.count()):
                item = bg_list.item(row)
                if item and item.data(Qt.UserRole + 1) == image_path:
                    target_row = row
                    break
        if target_row is None:
            return
        item = bg_list.item(target_row)
        if item is None:
            return
        idx = item.data(Qt.UserRole)
        if idx is None:
            idx = image_index
        decorate_background_list_item(item, image_path, idx)
        mode = getattr(self, '_bg_annotation_filter', 'all')
        status = item.data(Qt.UserRole + 2)
        visible = (mode == 'all') or (status == mode)
        item.setHidden(not visible)

    def _toggle_view_path(self):
        """切换工作路径/移除路径视图"""
        from . import i18n
        _tr = i18n.t
        self._is_delete_view = not self._is_delete_view
        if self._is_delete_view:
            self.view_toggle_btn.setText(_tr("移除路径"))
            self._saved_work_index = self.current_background_index
            self._show_delete_view()
            self._refresh_bg_filter_button()
            saved_del = getattr(self, '_saved_delete_idx', 0)
            if self._delete_files and saved_del < len(self._delete_files):
                self._delete_current_idx = saved_del
                self._load_delete_image(saved_del)
                self.background_list.setCurrentRow(saved_del)
            disabled_keys = {'W', 'Q', self._get_shortcut('delete_selected')}
            for sc in getattr(self, '_shortcuts', []):
                key = sc.key().toString()
                if key in disabled_keys:
                    sc.setEnabled(False)
            if hasattr(self, 'draw_box_btn'):
                self.draw_box_btn.setEnabled(False)
            self.canvas._clear_selection()
            self.canvas.is_drawing_box = False
            self.canvas.draw_start_pos = None
            self.canvas.temp_draw_box = None
        else:
            self.view_toggle_btn.setText(_tr("工作路径"))
            self._saved_delete_idx = getattr(self, '_delete_current_idx', 0)
            saved = getattr(self, '_saved_work_index', 0)
            self._show_work_view()
            self._refresh_bg_filter_button()
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
                row = self._find_bg_list_row_for_index(saved)
                if row is not None:
                    self.background_list.setCurrentRow(row)
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
        from ..engine.image_loader import decorate_background_list_item
        for i, path in enumerate(self.background_images):
            ext = os.path.splitext(path)[1].lower()
            if ext in SUPPORTED_IMAGE_EXTENSIONS:
                from PyQt5.QtWidgets import QListWidgetItem
                item = QListWidgetItem(PathUtils.to_display_path(path))
                decorate_background_list_item(item, path, i)
                self.background_list.addItem(item)
        self._refresh_bg_filter_button()
        self._apply_bg_annotation_filter(navigate=False)
        if 0 <= self.current_background_index < self.background_list.count():
            row = self._find_bg_list_row_for_index(self.current_background_index)
            if row is not None:
                self.background_list.setCurrentRow(row)
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
                self.canvas.selected_boxes = []
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

    def _collect_bg_stats_for_dialog(self):
        """Background label counts: prefer memory cache, else scan sidecar JSONs."""
        cached = getattr(self, '_cached_bg_label_stats', None) or []
        current_path = getattr(self, '_memory_background_path', '') or ''
        # Prefer any non-empty live cache (renames/canvas edits update it without path).
        if cached:
            bg_stats = {}
            for item in cached:
                if not isinstance(item, dict):
                    continue
                label = str(item.get('label', '') or '').strip()
                if not label:
                    continue
                try:
                    count = max(0, int(item.get('count', 0) or 0))
                except (TypeError, ValueError):
                    count = 0
                bg_stats[label] = count
                color = str(item.get('color', '') or '').strip()
                if color and hasattr(self, 'label_color_map'):
                    self.label_color_map.setdefault(label, color)
            if bg_stats:
                return bg_stats

        from ..engine.image_loader import collect_background_label_counts
        bg_stats = collect_background_label_counts(list(self.background_images or []))
        for lbl in getattr(self, 'background_dataset_labels', set()) or set():
            bg_stats.setdefault(lbl, 0)
        for lbl in self.global_labels:
            if lbl in bg_stats or lbl in (getattr(self, 'background_dataset_labels', set()) or set()):
                bg_stats.setdefault(lbl, 0)
        self._cached_bg_label_stats = [
            {'label': label, 'count': count, 'color': self.get_label_color(label)}
            for label, count in sorted(bg_stats.items(), key=lambda x: (-x[1], x[0]))
        ]
        self._cached_bg_label_stats_path = current_path
        return bg_stats

    def _show_label_stats(self):
        """显示标签统计弹窗"""
        from PyQt5.QtWidgets import (
            QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
            QHeaderView, QPushButton, QWidget, QAbstractItemView,
        )
        from PyQt5.QtCore import Qt as QtCore
        from .dialog_helpers import center_on_parent
        from .theme import ThemeManager
        from . import i18n
        tr = i18n.t

        class _StatsDialog(QDialog):
            def showEvent(self, event):
                super().showEvent(event)
                center_on_parent(self, self.parent())

        t = ThemeManager.get_theme()
        dialog = _StatsDialog(self)
        dialog.setWindowTitle(tr("标签统计"))
        dialog.setMinimumSize(540, 600)
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

        bg_header = QPushButton(f"▼  {tr('背景图标签')}")
        bg_header.setFlat(True)
        bg_header.setCursor(Qt.PointingHandCursor)
        bg_header.setStyleSheet("border: none; text-align: left; font-weight: bold; font-size: 13px; padding: 2px 0;")
        bg_header.setFixedHeight(24)
        layout.addWidget(bg_header)

        bg_stats = self._collect_bg_stats_for_dialog()

        bg_table = QTableWidget(len(bg_stats), 3)
        bg_table.setHorizontalHeaderLabels([tr("类别"), tr("数量"), tr("颜色")])
        bg_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        bg_table.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.SelectedClicked
        )
        for row, (label, count) in enumerate(sorted(bg_stats.items(), key=lambda x: -x[1])):
            label_item = QTableWidgetItem(label)
            label_item.setFlags(label_item.flags() | QtCore.ItemIsEditable)
            label_item.setData(QtCore.UserRole, label)
            bg_table.setItem(row, 0, label_item)
            count_item = QTableWidgetItem(str(count))
            count_item.setFlags(count_item.flags() & ~QtCore.ItemIsEditable)
            bg_table.setItem(row, 1, count_item)
            color_button = QPushButton()
            self._set_label_color_button(color_button, self.get_label_color(label))
            color_button.clicked.connect(lambda _, value=label, button=color_button: self._change_label_color(value, dialog, button))
            bg_table.setCellWidget(row, 2, color_button)

        def _on_bg_label_changed(item):
            if item is None or item.column() != 0:
                return
            old_label = item.data(QtCore.UserRole) or ''
            new_label = (item.text() or '').strip()
            if not old_label:
                return
            if not new_label or new_label == old_label:
                bg_table.blockSignals(True)
                item.setText(old_label)
                bg_table.blockSignals(False)
                return
            existing = {
                (bg_table.item(r, 0).text() if bg_table.item(r, 0) else '')
                for r in range(bg_table.rowCount()) if r != item.row()
            }
            if new_label in existing:
                bg_table.blockSignals(True)
                item.setText(old_label)
                bg_table.blockSignals(False)
                return
            if self.label_manager.rename_detection_label(old_label, new_label):
                item.setData(QtCore.UserRole, new_label)
                # Rebuild table from live cache so counts/colors/merged rows stay in sync.
                self._reload_stats_bg_table(bg_table, dialog)
                if hasattr(self, 'update_label_list'):
                    self.update_label_list()
                if (hasattr(self, '_processing_panel') and self._processing_panel
                        and self._processing_panel.isVisible()):
                    self._update_processing_panel_labels()
                self.canvas.update()
            else:
                bg_table.blockSignals(True)
                item.setText(old_label)
                bg_table.blockSignals(False)

        bg_table.itemChanged.connect(_on_bg_label_changed)
        dialog._bg_table = bg_table
        dialog._on_bg_label_changed = _on_bg_label_changed
        bg_container = QWidget()
        bg_cl = QVBoxLayout(bg_container)
        bg_cl.setContentsMargins(0, 0, 0, 0)
        bg_cl.addWidget(bg_table)
        layout.addWidget(bg_container)
        bg_expanded = True
        def _toggle_bg():
            nonlocal bg_expanded
            bg_expanded = not bg_expanded
            bg_container.setVisible(bg_expanded)
            bg_header.setText(f"{'▼' if bg_expanded else '▶'}  {tr('背景图标签')}")
        bg_header.clicked.connect(_toggle_bg)

        paste_header = QPushButton(f"▼  {tr('贴图标签_list')}")
        paste_header.setFlat(True)
        paste_header.setCursor(Qt.PointingHandCursor)
        paste_header.setStyleSheet("border: none; text-align: left; font-weight: bold; font-size: 13px; padding: 2px 0;")
        paste_header.setFixedHeight(24)
        layout.addWidget(paste_header)

        paste_stats = self._get_session_paste_stats()

        paste_table = QTableWidget(len(paste_stats), 3)
        paste_table.setHorizontalHeaderLabels([tr("类别"), tr("数量"), tr("颜色")])
        paste_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        paste_table.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.SelectedClicked
        )
        for row, (label, count) in enumerate(sorted(paste_stats.items(), key=lambda x: -x[1])):
            label_item = QTableWidgetItem(label)
            label_item.setFlags(label_item.flags() | QtCore.ItemIsEditable)
            label_item.setData(QtCore.UserRole, label)
            paste_table.setItem(row, 0, label_item)
            count_item = QTableWidgetItem(str(count))
            count_item.setFlags(count_item.flags() & ~QtCore.ItemIsEditable)
            paste_table.setItem(row, 1, count_item)
            color_button = QPushButton()
            self._set_label_color_button(color_button, self.get_label_color(label))
            color_button.clicked.connect(lambda _, value=label, button=color_button: self._change_label_color(value, dialog, button))
            paste_table.setCellWidget(row, 2, color_button)

        def _on_paste_label_changed(item):
            if item is None or item.column() != 0:
                return
            old_label = item.data(QtCore.UserRole) or ''
            new_label = (item.text() or '').strip()
            if not old_label:
                return
            if not new_label or new_label == old_label:
                paste_table.blockSignals(True)
                item.setText(old_label)
                paste_table.blockSignals(False)
                return
            existing = {
                (paste_table.item(r, 0).text() if paste_table.item(r, 0) else '')
                for r in range(paste_table.rowCount()) if r != item.row()
            }
            if new_label in existing:
                paste_table.blockSignals(True)
                item.setText(old_label)
                paste_table.blockSignals(False)
                return
            if self.label_manager.rename_paste_label(old_label, new_label):
                item.setData(QtCore.UserRole, new_label)
                color_btn = paste_table.cellWidget(item.row(), 2)
                if color_btn is not None:
                    try:
                        color_btn.clicked.disconnect()
                    except TypeError:
                        pass
                    color_btn.clicked.connect(
                        lambda _, value=new_label, button=color_btn: self._change_label_color(value, dialog, button)
                    )
                    self._set_label_color_button(color_btn, self.get_label_color(new_label))
                self.canvas.update()
            else:
                paste_table.blockSignals(True)
                item.setText(old_label)
                paste_table.blockSignals(False)

        paste_table.itemChanged.connect(_on_paste_label_changed)
        paste_container = QWidget()
        paste_cl = QVBoxLayout(paste_container)
        paste_cl.setContentsMargins(0, 0, 0, 0)
        paste_cl.addWidget(paste_table)
        layout.addWidget(paste_container)
        paste_expanded = True
        def _toggle_paste():
            nonlocal paste_expanded
            paste_expanded = not paste_expanded
            paste_container.setVisible(paste_expanded)
            paste_header.setText(f"{'▼' if paste_expanded else '▶'}  {tr('贴图标签_list')}")
        paste_header.clicked.connect(_toggle_paste)

        total = QLabel(
            f"{tr('总计')}: {tr('背景图标签')} {sum(bg_stats.values())} {tr('个')} | "
            f"{tr('贴图标签_list')} {sum(paste_stats.values())} {tr('个')}"
        )
        total.setStyleSheet("font-size: 12px; margin-top: 8px;")
        layout.addWidget(total)

        dialog.exec_()

    def _reload_stats_bg_table(self, bg_table, dialog):
        """Rebuild stats dialog background table from live cache after rename/color."""
        from PyQt5.QtWidgets import QTableWidgetItem, QPushButton
        from PyQt5.QtCore import Qt as QtCore
        bg_stats = self._collect_bg_stats_for_dialog()
        rows = sorted(bg_stats.items(), key=lambda x: (-x[1], x[0]))
        bg_table.blockSignals(True)
        bg_table.setRowCount(len(rows))
        for row, (label, count) in enumerate(rows):
            label_item = QTableWidgetItem(label)
            label_item.setFlags(label_item.flags() | QtCore.ItemIsEditable)
            label_item.setData(QtCore.UserRole, label)
            bg_table.setItem(row, 0, label_item)
            count_item = QTableWidgetItem(str(count))
            count_item.setFlags(count_item.flags() & ~QtCore.ItemIsEditable)
            bg_table.setItem(row, 1, count_item)
            color_button = QPushButton()
            self._set_label_color_button(color_button, self.get_label_color(label))
            color_button.clicked.connect(
                lambda _, value=label, button=color_button: self._change_label_color(value, dialog, button)
            )
            bg_table.setCellWidget(row, 2, color_button)
        bg_table.blockSignals(False)

    def _set_label_color_button(self, button, color):
        button.setText(color)
        button.setStyleSheet(
            f"QPushButton {{ background-color: {color}; color: #FFFFFF; border: 1px solid {color}; }}"
        )

    def _change_label_color(self, label, parent, color_button=None):
        """修改指定类别的颜色。"""
        from ..core import config_manager
        from PyQt5.QtGui import QColor
        from .dialog_helpers import ThemedColorDialog
        if not label:
            return
        dialog = ThemedColorDialog(parent)
        dialog.setWindowTitle(tr("颜色"))
        dialog.setCurrentColor(QColor(self.get_label_color(label)))
        if dialog.exec_() != 1:
            return
        color = dialog.currentColor()
        if not color.isValid():
            return
        self.label_color_map[label] = color.name()
        config_manager.save_all(
            label_colors=self.label_colors,
            label_color_map=self.label_color_map,
        )
        cached = getattr(self, '_cached_bg_label_stats', None)
        if isinstance(cached, list):
            for item in cached:
                if isinstance(item, dict) and item.get('label') == label:
                    item['color'] = color.name()
        if color_button is not None:
            self._set_label_color_button(color_button, color.name())
        self.canvas.update()

    def showEvent(self, event):
        """窗口显示后设置标题栏颜色（winId 必须在 show 之后获取）"""
        super().showEvent(event)
        from PyQt5.QtCore import QTimer
        is_dark = ThemeManager.get_mode().value == "dark"
        QTimer.singleShot(30, lambda: self._set_titlebar_dark(is_dark))

    def _set_titlebar_dark(self, dark, force_refresh=False):
        """设置系统标题栏颜色"""
        hwnd = int(self.winId())
        set_titlebar_dark(hwnd, dark, force_refresh=force_refresh)

    def _sync_all_titlebars(self, dark, force_refresh=False):
        """同步所有已创建顶层窗口的系统标题栏颜色。"""
        app = QApplication.instance()
        if app is None:
            return
        for widget in app.topLevelWidgets():
            if not widget.isWindow():
                continue
            try:
                set_titlebar_dark(int(widget.winId()), dark, force_refresh=force_refresh)
            except Exception:
                pass

    def _apply_app_palette(self):
        """同步 Qt 调色板，补足 Win10 原生控件/窗口背景刷新。"""
        app = QApplication.instance()
        if app is None:
            return
        try:
            from PyQt5.QtGui import QPalette, QColor
        except ImportError:
            return
        t = ThemeManager.get_theme()
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(t['window_bg']))
        palette.setColor(QPalette.WindowText, QColor(t['text_primary']))
        palette.setColor(QPalette.Base, QColor(t['widget_bg']))
        palette.setColor(QPalette.AlternateBase, QColor(t['panel_bg']))
        palette.setColor(QPalette.Text, QColor(t['text_primary']))
        palette.setColor(QPalette.Button, QColor(t['widget_bg']))
        palette.setColor(QPalette.ButtonText, QColor(t['text_primary']))
        palette.setColor(QPalette.Highlight, QColor(t['accent']))
        palette.setColor(QPalette.HighlightedText, QColor(t['widget_bg']))
        palette.setColor(QPalette.ToolTipBase, QColor(t['tooltip_bg']))
        palette.setColor(QPalette.ToolTipText, QColor(t['tooltip_text']))
        palette.setColor(QPalette.Disabled, QPalette.Text, QColor(t['text_disabled']))
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(t['text_disabled']))
        app.setPalette(palette)

    def _apply_theme(self):
        """应用当前主题样式"""
        app = QApplication.instance()
        self._apply_app_palette()
        app.setStyleSheet(ThemeManager.get_stylesheet())
        for widget in app.topLevelWidgets():
            try:
                widget.style().unpolish(widget)
                widget.style().polish(widget)
                widget.update()
            except Exception:
                pass
        if hasattr(self, 'theme_btn'):
            is_dark = ThemeManager.get_mode().value == "dark"
            svg = MOON_SVG if is_dark else SUN_SVG
            icon = QIcon(_load_svg_icon(svg, 16, "#D4AF37"))
            self.theme_btn.setIcon(icon)
        if hasattr(self, 'prefix_input'):
            has_text = bool(self.prefix_input.text().strip())
            self.prefix_input.setProperty("placeholder", not has_text)
            self.prefix_input.style().unpolish(self.prefix_input)
            self.prefix_input.style().polish(self.prefix_input)
        self._update_mode_seg_style()
        if hasattr(self, 'canvas'):
            self.canvas.update()
        app.processEvents()

    def _update_status_info(self):
        """更新状态栏信息"""
        info = self.get_image_info()
        if info:
            stats = self.get_label_stats()
            stats_text = " | ".join([f"{k}:{v}" for k, v in list(stats.items())[:3]])
            self.status_label.setText(
                f"Box: {info['box_count']} Paste: {info['paste_count']}"
                + (f" | {stats_text}" if stats_text else "")
            )

    def toggle_theme(self):
        """切换主题"""
        from ..core import config_manager
        ThemeManager.toggle()
        self._apply_theme()
        self._update_mode_seg_style()
        is_dark = ThemeManager.get_mode().value == "dark"
        self._sync_all_titlebars(is_dark, force_refresh=True)
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(80, lambda: self._sync_all_titlebars(is_dark, force_refresh=True))
        config_manager.save_theme('dark' if is_dark else 'light')
        self.status_label.setText(f"Theme: {'Dark' if is_dark else 'Light'}")
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
        self.auto_save_b_checkbox.setText(tr("自动保存B"))
        self.auto_save_p_checkbox.setText(tr("自动保存P"))
        if hasattr(self, 'edit_mode'):
            self.auto_save_b_checkbox.setText(
                f"{tr('自动保存B')}({tr('标注')})" if self.edit_mode == 'annotate' else tr("自动保存B"))
            self.auto_save_p_checkbox.setText(
                f"{tr('自动保存P')}({tr('贴图')})" if self.edit_mode == 'paste' else tr("自动保存P"))
        self.show_labels_checkbox.setText(tr("显示BOX"))
        self.show_label_names_checkbox.setText(tr("显示Label"))
        self.auto_label_checkbox.setText(tr("贴图标签"))
        self.prefix_checkbox.setText(tr("添加文件名前缀"))
        self.show_paste_names_checkbox.setText(tr("显示贴图名"))
        self.show_grid_checkbox.setText(tr("显示网格线"))
        self.random_paste_btn.setText(tr("随机贴图"))
        self.batch_paste_btn.setText(tr("一键贴图"))
        is_thumb = self.is_thumbnail_mode
        self.toggle_view_btn.setText(tr("列表视图") if is_thumb else tr("缩略视图"))
        self.clear_btn.setText(tr("清空画布"))
        self.save_btn.setText(tr("保存图片"))
        self.save_all_btn.setText(tr("全部保存"))
        if hasattr(self, 'view_stats_btn'):
            self.view_stats_btn.setText(tr("统计"))
            self.view_stats_btn.setToolTip(tr("标签统计"))
        if hasattr(self, '_refresh_bg_label_mode_button'):
            self._refresh_bg_label_mode_button()
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
        for header_name in ('bg_list_header', 'label_group_header', 'paste_group_header'):
            header = getattr(self, header_name, None)
            if header is None:
                continue
            key = header.property('title_key') or ''
            expanded = getattr(header, '_expanded', True)
            if key:
                header.setText(f"{'▼' if expanded else '▶'}  {tr(key)}")
        if hasattr(self, 'bg_list_group') and hasattr(self.bg_list_group, 'setTitle'):
            self.bg_list_group.setTitle(tr("背景图列表"))
        if hasattr(self, 'label_group') and hasattr(self.label_group, 'setTitle'):
            self.label_group.setTitle(tr("标签管理"))
        if hasattr(self, 'paste_group') and hasattr(self.paste_group, 'setTitle'):
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
        if hasattr(self, 'cache_btn'):
            self.cache_btn.setText(tr("缓存"))
            self.cache_btn.setToolTip(tr("复制缓存管理"))
        if hasattr(self, 'memory_btn'):
            self.memory_btn.setText(tr("记忆"))
            self.memory_btn.setToolTip(tr("记忆记录"))
        if hasattr(self, 'process_btn'):
            self.process_btn.setText(tr("导出"))
            self.process_btn.setToolTip(tr("数据处理"))
        if hasattr(self, '_rebuild_label_cache_menu'):
            self._rebuild_label_cache_menu()
        if hasattr(self, '_draw_box_action'):
            sc = self._get_shortcut('draw_box')
            self._draw_box_action.setText(f"{tr('绘制BOX')}\t{sc}")
        if hasattr(self, '_menu_actions'):
            menu_texts = [tr("显示BOX"), tr("显示Label"),
                          tr("显示贴图名"),
                          tr("自动保存B"), tr("自动保存P"),
                          tr("显示网格线"),
                          tr("添加文件名前缀"), tr("画布图片复制"),
                          tr("窗口放大器")]
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
        if hasattr(self, '_update_shortcut_status_label'):
            self._update_shortcut_status_label()

    def _refresh_menu_shortcuts(self):
        """刷新选项菜单中的快捷键显示"""
        from . import i18n
        tr = i18n.t
        if hasattr(self, '_draw_box_action'):
            sc = self._get_shortcut('draw_box')
            self._draw_box_action.setText(f"{tr('绘制BOX')}\t{sc}")
        if hasattr(self, '_menu_actions'):
            menu_texts = [tr("显示BOX"), tr("显示Label"),
                          tr("显示贴图名"),
                          tr("自动保存B"), tr("自动保存P"),
                          tr("显示网格线"),
                          tr("添加文件名前缀"), tr("画布图片复制"),
                          tr("窗口放大器")]
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
        if hasattr(self, '_update_shortcut_status_label'):
            self._update_shortcut_status_label()

    def save_undo_state(self):
        """保存撤销状态"""
        if self._is_delete_view:
            return
        self.undo_manager.save_state(self.canvas_items, self.detection_boxes)

    def undo(self):
        """撤销"""
        if self._is_delete_view:
            return
        self.canvas_items, self.detection_boxes = self.undo_manager.undo(
            self.canvas_items, self.detection_boxes
        )
        self.canvas.update()
        self.update_label_list()

    def redo(self):
        """重做"""
        if self._is_delete_view:
            return
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

    def _toggle_processing_panel(self):
        if not hasattr(self, '_processing_panel') or self._processing_panel is None:
            self._processing_panel = ProcessingPanel(self)
        if self._processing_panel.isVisible():
            self._processing_panel.hide()
        else:
            self._update_processing_panel_labels()
            self._processing_panel.show()
            self._center_processing_panel()

    def _update_processing_panel_labels(self):
        if hasattr(self, '_processing_panel') and self._processing_panel:
            self._processing_panel._refresh_texts()
            self._processing_panel._update_labels_list()

    def _center_processing_panel(self):
        if not hasattr(self, '_processing_panel') or not self._processing_panel:
            return
        parent_geo = self.geometry()
        child_geo = self._processing_panel.geometry()
        x = parent_geo.x() + (parent_geo.width() - child_geo.width()) // 2
        y = parent_geo.y() + (parent_geo.height() - child_geo.height()) // 2
        self._processing_panel.move(x, y)

    def closeEvent(self, event):
        if hasattr(self, '_processing_panel') and self._processing_panel and any(w.isRunning() for w in self._processing_panel._workers):
            from PyQt5.QtWidgets import QMessageBox
            from .dwm import set_titlebar_dark
            from .i18n import t as _t
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Warning)
            box.setWindowTitle(tr("提示"))
            box.setText(tr("数据处理正在进行中，无法关闭主界面"))
            ok_btn = box.addButton(_t("确定"), QMessageBox.AcceptRole)
            box.setDefaultButton(ok_btn)
            hwnd = int(box.winId())
            set_titlebar_dark(hwnd, True)
            box.exec_()
            event.ignore()
            return
        if not self._cleanup_background_label_scan_worker():
            event.ignore()
            return
        if hasattr(self, '_processing_panel') and self._processing_panel:
            self._processing_panel.close()
        if self.current_background_index >= 0:
            self.canvas_items_dict[self.current_background_index] = self.canvas_items.copy()
            self.detection_boxes_dict[self.current_background_index] = self.detection_boxes.copy()
            self.save_current_json()
        if hasattr(self, '_save_memory_record_on_close'):
            self._save_memory_record_on_close()
        event.accept()

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
                from ..engine.image_loader import decorate_background_list_item
                item = QListWidgetItem(display_path)
                decorate_background_list_item(item, file, new_index)
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

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
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
