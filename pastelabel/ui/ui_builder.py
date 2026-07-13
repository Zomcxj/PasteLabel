"""
UI 构建混入 - 负责所有界面控件的创建和布局
"""
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QSplitter, QScrollArea,
    QLineEdit, QCheckBox, QSpinBox, QGroupBox, QFrame, QMenu, QApplication
)
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QDrag
from PyQt5.QtCore import Qt, QSize, QTimer, QPoint, QMimeData, QUrl
from PyQt5.QtWidgets import QWidgetAction
from .segmented_control import AnimatedSegmentedControl

from ..core.config import WINDOW_CONFIG, PASTE_PARAMS, THUMBNAIL_CONFIG, DEFAULT_PREFIX
from ..core.utils import create_thumbnail
from ..canvas import Canvas
from .theme import ThemeManager
from .i18n import t as tr

try:
    from PyQt5.QtSvg import QSvgRenderer
    _has_svg = True
except ImportError:
    _has_svg = False


def _load_svg_icon(svg_data, size=16, color="#999"):
    if not _has_svg:
        return QPixmap(size, size)
    svg_data = svg_data.replace('currentColor', color)
    renderer = QSvgRenderer(bytearray(svg_data.encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap


SVG_FILE = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke="currentColor" stroke-width="2" fill="none" stroke-linejoin="round"/><polyline points="14,2 14,8 20,8" stroke="currentColor" stroke-width="2" fill="none" stroke-linejoin="round"/></svg>'
SVG_FOLDER = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" stroke="currentColor" stroke-width="2" fill="none" stroke-linejoin="round"/></svg>'
SUN_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>'
MOON_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>'


class DragOutListWidget(QListWidget):
    """支持拖出文件的列表控件"""
    _drag_start_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start_pos and event.buttons() & Qt.LeftButton:
            delta = event.pos() - self._drag_start_pos
            if abs(delta.x()) > 20 or abs(delta.y()) > 20:
                item = self.itemAt(self._drag_start_pos)
                if item:
                    file_path = item.data(Qt.UserRole + 1)
                    if file_path and os.path.isfile(file_path):
                        drag = QDrag(self)
                        mime = QMimeData()
                        mime.setUrls([QUrl.fromLocalFile(file_path)])
                        drag.setMimeData(mime)
                        drag.exec_(Qt.CopyAction)
                        self._drag_start_pos = None
                        return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_start_pos = None
        super().mouseReleaseEvent(event)


class HoverDismissPopup(QWidget):
    """鼠标移出后自动收起的轻量弹层。"""

    def leaveEvent(self, event):
        super().leaveEvent(event)
        focus_widget = QApplication.focusWidget()
        if isinstance(focus_widget, QLineEdit) and self.isAncestorOf(focus_widget):
            return
        self.hide()


class HoverKeepMenu(QMenu):
    """点击菜单项不关闭，鼠标移开后关闭。"""

    def mouseReleaseEvent(self, event):
        action = self.actionAt(event.pos())
        if action and action.isEnabled():
            if action == self.actions()[0]:
                action.triggered.emit(False)
                event.accept()
                return
            action.trigger()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.hide()


class UIBuilderMixin:
    """UI 构建混入类 - 创建工具栏、控制面板、画布等界面元素"""

    def init_ui(self):
        """初始化用户界面"""
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._create_toolbar(main_layout)

        self.shortcut_status_label = QLabel("")
        self.shortcut_status_label.setObjectName("shortcutStatusLabel")
        self.shortcut_status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.shortcut_status_label.setMinimumHeight(24)
        main_layout.addWidget(self.shortcut_status_label)

        splitter = self._create_splitter()
        main_layout.addWidget(splitter)

        main_layout.setStretch(0, 0)
        main_layout.setStretch(1, 0)
        main_layout.setStretch(2, 1)

        self.setCentralWidget(central_widget)

        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.statusBar().addWidget(self.status_label, 1)
        self.statusBar().show()

    def _create_toolbar(self, layout):
        """创建工具栏"""
        toolbar_widget = QWidget()
        toolbar_widget.setObjectName("toolbar")
        upload_layout = QHBoxLayout(toolbar_widget)
        upload_layout.setSpacing(4)
        upload_layout.setContentsMargins(4, 4, 4, 4)

        t = ThemeManager.get_theme()
        color = t['text_secondary']

        bg_color = "#2196F3"
        paste_color = "#4CAF50"
        label_color = "#FF9800"

        self.bg_lbl = QLabel(tr("背景图:"))
        upload_layout.addWidget(self.bg_lbl)
        self.load_folder_btn = self._create_svg_button(
            SVG_FOLDER, self.load_folder_images, tr("加载文件夹图片"), bg_color, "bgBtn"
        )
        upload_layout.addWidget(self.load_folder_btn)

        self.upload_a_btn = self._create_svg_button(
            SVG_FILE, self.upload_background, tr("选择背景图片"), bg_color, "bgBtn"
        )
        upload_layout.addWidget(self.upload_a_btn)

        upload_layout.addSpacing(2)
        self.paste_lbl = QLabel(tr("贴图:"))
        upload_layout.addWidget(self.paste_lbl)
        self.load_small_folder_btn = self._create_svg_button(
            SVG_FOLDER, self.load_small_folder_images, tr("加载贴图文件夹"), paste_color, "pasteBtn"
        )
        upload_layout.addWidget(self.load_small_folder_btn)

        self.upload_b_btn = self._create_svg_button(
            SVG_FILE, self.upload_small_images, tr("选择贴图"), paste_color, "pasteBtn"
        )
        upload_layout.addWidget(self.upload_b_btn)

        upload_layout.addSpacing(2)
        self.label_lbl = QLabel(tr("标签:"))
        upload_layout.addWidget(self.label_lbl)
        self.upload_paste_label_btn = self._create_svg_button(
            SVG_FILE, self.upload_paste_labels, tr("选择标签文件"), label_color, "labelBtn"
        )
        upload_layout.addWidget(self.upload_paste_label_btn)

        upload_layout.addSpacing(8)
        self._add_separator(upload_layout)
        upload_layout.addSpacing(8)

        self._init_checkboxes()
        self._init_prefix_checkbox()
        self._create_options_menu(upload_layout)

        upload_layout.addStretch()

        self.lang_btn = QPushButton("中/EN")
        self.lang_btn.setObjectName("langBtn")
        self.lang_btn.setFixedSize(42, 28)
        self.lang_btn.setToolTip(tr("切换中英文"))
        self.lang_btn.clicked.connect(self.toggle_language)
        upload_layout.addWidget(self.lang_btn)

        self.theme_btn = QPushButton("")
        self.theme_btn.setObjectName("themeBtn")
        self.theme_btn.setFixedSize(28, 28)
        self.theme_btn.setToolTip(tr("切换深色/浅色主题"))
        self.theme_btn.setIcon(QIcon(_load_svg_icon(SUN_SVG, 16, "#D4AF37")))
        self.theme_btn.clicked.connect(self.toggle_theme)
        upload_layout.addWidget(self.theme_btn)

        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setObjectName("settingsBtn")
        self.settings_btn.setFixedSize(28, 28)
        self.settings_btn.setToolTip("设置快捷键")
        self.settings_btn.clicked.connect(self.open_settings)
        upload_layout.addWidget(self.settings_btn)

        layout.addWidget(toolbar_widget)

    def _create_svg_button(self, svg_data, slot, tooltip, color, obj_name=None):
        """创建 SVG 图标按钮"""
        btn = QPushButton("")
        btn.setObjectName(obj_name or "iconBtn")
        btn.setIcon(QIcon(_load_svg_icon(svg_data, 14, color)))
        btn.clicked.connect(slot)
        btn.setFixedSize(24, 24)
        btn.setToolTip(tooltip)
        return btn

    def _add_separator(self, layout):
        """添加垂直分隔线"""
        sep = QFrame()
        sep.setObjectName("toolbarSep")
        sep.setFrameShape(QFrame.VLine)
        sep.setFrameShadow(QFrame.Sunken)
        sep.setFixedHeight(20)
        layout.addWidget(sep)

    def _on_grid_changed(self):
        """网格复选框状态变化"""
        if hasattr(self, 'canvas'):
            self.canvas.update()

    def _init_checkboxes(self):
        """初始化隐藏的复选框"""
        self.show_labels_checkbox = QCheckBox(tr("显示BOX"))
        self.show_labels_checkbox.setObjectName("showBoxCb")
        self.show_labels_checkbox.setChecked(True)
        self.show_labels_checkbox.stateChanged.connect(self.on_labels_checkbox_changed)

        self.show_label_names_checkbox = QCheckBox(tr("显示Label"))
        self.show_label_names_checkbox.setObjectName("showLabelCb")
        self.show_label_names_checkbox.setChecked(True)
        self.show_label_names_checkbox.stateChanged.connect(self.on_labels_checkbox_changed)

        self.auto_label_checkbox = QCheckBox(tr("贴图标签"))
        self.auto_label_checkbox.setObjectName("autoLabelCb")
        self.auto_label_checkbox.setChecked(True)

        self.auto_save_checkbox = QCheckBox(tr("自动保存"))
        self.auto_save_checkbox.setObjectName("autoSaveCb")
        self.auto_save_checkbox.setChecked(False)

        self.show_grid_checkbox = QCheckBox(tr("显示网格"))
        self.show_grid_checkbox.setObjectName("gridCb")
        self.show_grid_checkbox.setChecked(False)
        self.show_grid_checkbox.stateChanged.connect(self._on_grid_changed)

        self.show_paste_names_checkbox = QCheckBox(tr("显示贴图名"))
        self.show_paste_names_checkbox.setObjectName("pasteNameCb")
        self.show_paste_names_checkbox.setChecked(True)
        self.show_paste_names_checkbox.stateChanged.connect(self._on_grid_changed)

    def _init_prefix_checkbox(self):
        """初始化前缀复选框"""
        self.prefix_checkbox = QCheckBox(tr("添加文件名前缀"))
        self.prefix_checkbox.setObjectName("prefixCb")
        self.prefix_checkbox.setChecked(True)

    def _create_options_menu(self, layout):
        """创建选项下拉菜单按钮"""

        self.cache_btn = QPushButton(tr("缓存"))
        self.cache_btn.setObjectName("optionsBtn")
        self.cache_btn.setFixedWidth(70)
        self.cache_btn.setFixedHeight(24)
        self.cache_btn.setToolTip(tr("复制缓存管理"))
        self.cache_menu = None
        layout.addWidget(self.cache_btn)
        self._rebuild_label_cache_menu()

        layout.addSpacing(4)

        self.options_btn = QPushButton(tr("选项"))
        self.options_btn.setObjectName("optionsBtn")
        self.options_btn.setFixedHeight(24)
        self.options_btn.setFixedWidth(70)
        self.options_btn.setToolTip(tr("选项设置"))
        self.options_menu = HoverKeepMenu()
        self.options_menu.setObjectName("optionsMenu")
        self.options_menu.setMinimumWidth(200)

        sc_w = self._get_shortcut('draw_box')
        self._draw_box_action = self.options_menu.addAction(f"{tr('绘制BOX')}\t{sc_w}")
        self._draw_box_action.setCheckable(True)
        self._draw_box_action.setChecked(False)
        self._draw_box_action.triggered.connect(self._trigger_draw_box_menu_action)

        items = [
            (tr("显示BOX"), "toggle_labels", self.show_labels_checkbox),
            (tr("显示Label"), "toggle_label_names", self.show_label_names_checkbox),
            (tr("自动保存"), "toggle_auto_save", self.auto_save_checkbox),
            (tr("显示网格"), "toggle_grid", self.show_grid_checkbox),
            (tr("显示贴图名"), "toggle_paste_names", self.show_paste_names_checkbox),
        ]

        self._menu_actions = []
        for text, shortcut_action, checkbox in items:
            sc = self._get_shortcut(shortcut_action) if shortcut_action else ''
            label = f"{text}\t{sc}" if sc else text
            action = self.options_menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(checkbox.isChecked())
            action.triggered.connect(lambda checked, cb=checkbox: cb.setChecked(checked))
            checkbox.stateChanged.connect(lambda state, a=action: a.setChecked(state == Qt.Checked))
            self._menu_actions.append((action, checkbox, shortcut_action))

        self.options_menu.addSeparator()

        prefix_action = self.options_menu.addAction(tr("添加文件名前缀"))
        prefix_action.setCheckable(True)
        prefix_action.setChecked(self.prefix_checkbox.isChecked())
        prefix_action.triggered.connect(lambda checked, cb=self.prefix_checkbox: cb.setChecked(checked))
        self.prefix_checkbox.stateChanged.connect(lambda state, a=prefix_action: a.setChecked(state == Qt.Checked))
        self._menu_actions.append((prefix_action, self.prefix_checkbox, None))

        self.canvas_copy_action = self.options_menu.addAction(tr("画布图片复制"))
        self.canvas_copy_action.setCheckable(True)
        self.canvas_copy_action.setChecked(getattr(self, '_canvas_image_copy_enabled', False))
        self.canvas_copy_action.triggered.connect(self._on_canvas_copy_menu_changed)
        self._menu_actions.append((self.canvas_copy_action, None, None))

        self.magnifier_action = self.options_menu.addAction(tr("窗口放大器"))
        self.magnifier_action.setCheckable(True)
        self.magnifier_action.setChecked(getattr(self, '_magnifier_enabled', False))
        self.magnifier_action.triggered.connect(self._on_magnifier_menu_changed)
        self._menu_actions.append((self.magnifier_action, None, None))

        self.options_btn.setMenu(self.options_menu)
        layout.addWidget(self.options_btn)

        layout.addSpacing(4)

        self.memory_btn = QPushButton(tr("记忆"))
        self.memory_btn.setObjectName("optionsBtn")
        self.memory_btn.setFixedWidth(70)
        self.memory_btn.setFixedHeight(24)
        self.memory_btn.setToolTip(tr("记忆记录"))
        self.memory_btn.clicked.connect(self._show_memory_records)
        layout.addWidget(self.memory_btn)

        layout.addSpacing(4)

        self.view_stats_btn = QPushButton(tr("统计"))
        self.view_stats_btn.setObjectName("optionsBtn")
        self.view_stats_btn.setFixedHeight(24)
        self.view_stats_btn.setFixedWidth(70)
        self.view_stats_btn.setToolTip(tr("标签统计"))
        self.view_stats_btn.clicked.connect(self._show_label_stats)
        layout.addWidget(self.view_stats_btn)

        layout.addSpacing(4)

        self.mode_seg = QFrame()
        self.mode_seg.setObjectName("modeSeg")
        self.mode_seg.setFixedWidth(150)
        self.mode_seg.setFixedHeight(24)
        self.mode_seg.setContentsMargins(0, 0, 0, 0)
        mode_layout = QHBoxLayout(self.mode_seg)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(0)

        self.btn_annotate_mode = QPushButton(tr("标注"))
        self.btn_annotate_mode.setObjectName("modeSegBtn")
        self.btn_annotate_mode.setCheckable(True)
        self.btn_annotate_mode.setChecked(True)
        self.btn_annotate_mode.setFixedWidth(74)
        self.btn_annotate_mode.setFixedHeight(22)
        self.btn_annotate_mode.clicked.connect(lambda: self._toggle_edit_mode())
        mode_layout.addWidget(self.btn_annotate_mode)

        self.btn_paste_mode = QPushButton(tr("贴图"))
        self.btn_paste_mode.setObjectName("modeSegBtn")
        self.btn_paste_mode.setCheckable(True)
        self.btn_paste_mode.setFixedWidth(74)
        self.btn_paste_mode.setFixedHeight(22)
        self.btn_paste_mode.clicked.connect(lambda: self._toggle_edit_mode())
        mode_layout.addWidget(self.btn_paste_mode)

        self.mode_seg_ctrl = AnimatedSegmentedControl(self.mode_seg, self.btn_annotate_mode, self.btn_paste_mode)
        self.mode_seg_ctrl.set_accent(ThemeManager.get_theme()["interaction_active"])
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, lambda: self.mode_seg_ctrl.update_position(animated=False))
        layout.addWidget(self.mode_seg)

    def _rebuild_label_cache_menu(self):
        if not hasattr(self, 'cache_btn'):
            return

        if getattr(self, 'cache_menu', None) is None:
            menu = HoverKeepMenu(self)
            menu.setObjectName("cacheMenu")
            menu.setMinimumWidth(200)
            self.cache_menu = menu
            self.cache_btn.setMenu(menu)
        else:
            menu = self.cache_menu
            menu.clear()

        for index, slot in enumerate(getattr(self, 'label_cache_slots', [])):
            action = QWidgetAction(menu)
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(8, 4, 8, 4)
            row_layout.setSpacing(8)

            lock_btn = QPushButton(tr("上锁") if slot.get('locked') else tr("解锁"))
            lock_btn.setCursor(Qt.PointingHandCursor)
            lock_btn.clicked.connect(lambda checked=False, idx=index, btn=lock_btn: self._toggle_cache_slot_lock_from_popup(idx, btn))
            row_layout.addWidget(lock_btn, 0)

            copied_at = slot.get('copied_at') or '--:--:--'
            middle_widget = QWidget()
            middle_layout = QHBoxLayout(middle_widget)
            middle_layout.setContentsMargins(0, 0, 0, 0)
            middle_layout.setSpacing(2)

            slot_name_input = QLineEdit(slot.get('name', f"{tr('缓存槽')}{index + 1}"))
            slot_name_input.setObjectName("cacheSlotName")
            slot_name_input.setFrame(False)
            slot_name_input.setAttribute(Qt.WA_InputMethodEnabled, True)
            slot_name_input.setFixedWidth(slot_name_input.fontMetrics().horizontalAdvance("测" * 9) + 24)
            slot_name_input.setProperty("active", index == getattr(self, 'active_label_cache_slot', 0))
            slot_name_input.editingFinished.connect(
                lambda idx=index, field=slot_name_input: self._commit_cache_slot_name(idx, field)
            )
            middle_layout.addWidget(slot_name_input, 1)

            time_label = QLabel(copied_at)
            middle_layout.addWidget(time_label, 0)
            row_layout.addWidget(middle_widget, 1)

            shortcut_label = QLabel(slot.get('shortcut', ''))
            shortcut_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row_layout.addWidget(shortcut_label, 0)

            action.setDefaultWidget(row_widget)
            menu.addAction(action)

    def _handle_cache_slot_row_click(self, slot_index):
        self.set_active_label_cache_slot(slot_index)

    def _commit_cache_slot_name(self, slot_index, field):
        if slot_index < 0 or slot_index >= len(getattr(self, 'label_cache_slots', [])):
            return
        text = str(field.text() or '').strip()
        if not text:
            text = f"{tr('缓存槽')}{slot_index + 1}"
            field.setText(text)
        self.label_cache_slots[slot_index]['name'] = text
        self._save_label_cache_slots()

    def _toggle_cache_slot_lock_from_popup(self, slot_index, btn):
        if slot_index < 0 or slot_index >= len(getattr(self, 'label_cache_slots', [])):
            return
        self.label_cache_slots[slot_index]['locked'] = not self.label_cache_slots[slot_index].get('locked')
        self._save_label_cache_slots()
        btn.setText(tr("上锁") if self.label_cache_slots[slot_index].get('locked') else tr("解锁"))

    def _trigger_draw_box_menu_action(self, checked=False):
        self._draw_box_action.setChecked(False)
        self.toggle_draw_mode()

    def _rebuild_options_popup(self):
        if getattr(self, 'options_menu', None) is not None:
            self.options_menu.deleteLater()

        popup_flags = Qt.Popup | Qt.FramelessWindowHint
        no_shadow_flag = getattr(Qt, 'NoDropShadowWindowHint', None)
        if no_shadow_flag is not None:
            popup_flags |= no_shadow_flag
        popup = HoverDismissPopup(self, popup_flags)
        popup.setObjectName("optionsPopup")
        popup_layout = QVBoxLayout(popup)
        popup_layout.setContentsMargins(4, 4, 4, 4)
        popup_layout.setSpacing(2)

        self._option_popup_rows = []
        self._draw_box_action = QPushButton()
        self._draw_box_action.clicked.connect(self.toggle_draw_mode)
        popup_layout.addWidget(self._draw_box_action)

        items = [
            (tr("显示BOX"), "toggle_labels", self.show_labels_checkbox, lambda cb=self.show_labels_checkbox: cb.setChecked(not cb.isChecked()), lambda cb=self.show_labels_checkbox: cb.isChecked()),
            (tr("显示Label"), "toggle_label_names", self.show_label_names_checkbox, lambda cb=self.show_label_names_checkbox: cb.setChecked(not cb.isChecked()), lambda cb=self.show_label_names_checkbox: cb.isChecked()),
            (tr("自动保存"), "toggle_auto_save", self.auto_save_checkbox, lambda cb=self.auto_save_checkbox: cb.setChecked(not cb.isChecked()), lambda cb=self.auto_save_checkbox: cb.isChecked()),
            (tr("显示网格"), "toggle_grid", self.show_grid_checkbox, lambda cb=self.show_grid_checkbox: cb.setChecked(not cb.isChecked()), lambda cb=self.show_grid_checkbox: cb.isChecked()),
            (tr("显示贴图名"), "toggle_paste_names", self.show_paste_names_checkbox, lambda cb=self.show_paste_names_checkbox: cb.setChecked(not cb.isChecked()), lambda cb=self.show_paste_names_checkbox: cb.isChecked()),
            (tr("添加文件名前缀"), None, self.prefix_checkbox, lambda cb=self.prefix_checkbox: cb.setChecked(not cb.isChecked()), lambda cb=self.prefix_checkbox: cb.isChecked()),
            (tr("画布图片复制"), None, None, lambda: self._on_canvas_copy_menu_changed(not getattr(self, '_canvas_image_copy_enabled', False)), lambda: getattr(self, '_canvas_image_copy_enabled', False)),
            (tr("窗口放大器"), None, None, lambda: self._on_magnifier_menu_changed(not getattr(self, '_magnifier_enabled', False)), lambda: getattr(self, '_magnifier_enabled', False)),
        ]
        for text, shortcut_action, checkbox, handler, getter in items:
            button = QPushButton()
            button.clicked.connect(handler)
            if checkbox is not None:
                checkbox.stateChanged.connect(lambda state: self._refresh_options_popup_texts())
            popup_layout.addWidget(button)
            self._option_popup_rows.append((button, text, shortcut_action, getter))

        self.options_menu = popup
        self._refresh_options_popup_texts()

    def _refresh_options_popup_texts(self):
        if hasattr(self, '_draw_box_action'):
            sc = self._get_shortcut('draw_box')
            self._draw_box_action.setText(f"{tr('绘制BOX')}    {sc}" if sc else tr('绘制BOX'))
        for button, text, shortcut_action, getter in getattr(self, '_option_popup_rows', []):
            sc = self._get_shortcut(shortcut_action) if shortcut_action else ''
            prefix = "√ " if getter() else ""
            button.setText(f"{prefix}{text}    {sc}" if sc else f"{prefix}{text}")

    def _toggle_options_popup(self):
        if getattr(self, 'options_menu', None) is None:
            self._rebuild_options_popup()
        if self.options_menu.isVisible():
            self.options_menu.hide()
            return
        self._refresh_options_popup_texts()
        global_pos = self.options_btn.mapToGlobal(QPoint(0, self.options_btn.height()))
        self.options_menu.move(global_pos)
        self.options_menu.show()

    def _on_canvas_copy_menu_changed(self, checked):
        """切换画布图片复制功能（仅保留在顶部选项菜单中）。"""
        self._canvas_image_copy_enabled = bool(checked)
        if hasattr(self, 'canvas_copy_action'):
            self.canvas_copy_action.setChecked(self._canvas_image_copy_enabled)
        from ..core import config_manager
        config_manager.save_all(canvas_image_copy_enabled=self._canvas_image_copy_enabled)

    def _on_magnifier_menu_changed(self, checked):
        """切换窗口放大器，直接重绘画布即可生效。"""
        self._magnifier_enabled = bool(checked)
        if hasattr(self, 'magnifier_action'):
            self.magnifier_action.setChecked(self._magnifier_enabled)
        from ..core import config_manager
        config_manager.save_all(magnifier_enabled=self._magnifier_enabled)
        if hasattr(self, 'canvas'):
            self.canvas.update()

    def _show_memory_records(self):
        """显示记忆记录弹窗"""
        from .memory_dialog import MemoryRecordsDialog
        MemoryRecordsDialog(self).exec_()

    def _validate_size_range(self):
        """验证尺寸范围，确保最小值不大于最大值"""
        min_size = self.min_size_spin.value()
        max_size = self.max_size_spin.value()
        if min_size > max_size:
            self.status_label.setText("Min cannot exceed Max")
            QTimer.singleShot(2000, lambda: self.status_label.setText(""))
            self.min_size_spin.setValue(max_size)

    def _on_min_size_changed(self, value):
        """最小值变化时更新最大值的范围"""
        self.max_size_spin.setMinimum(max(value, 30))

    def _on_max_size_changed(self, value):
        """最大值变化时更新最小值的范围"""
        self.min_size_spin.setMaximum(min(value, 100))

    def _create_splitter(self):
        """创建分割器"""
        canvas_widget = QWidget()
        canvas_layout = QVBoxLayout(canvas_widget)
        self.canvas = Canvas(self)
        canvas_scroll = QScrollArea()
        canvas_scroll.setObjectName("canvasScroll")
        canvas_scroll.setWidget(self.canvas)
        canvas_scroll.setWidgetResizable(True)
        canvas_layout.addWidget(canvas_scroll)

        control_widget = self._create_control_panel()
        control_widget.setFixedWidth(350)

        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.addWidget(canvas_widget, 1)
        container_layout.addWidget(control_widget, 0)

        return container

    def _create_control_panel(self):
        """创建控制面板"""
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)
        control_layout.setSpacing(6)
        control_layout.setContentsMargins(6, 6, 6, 6)

        self._create_background_list_section(control_layout)
        self._create_label_list_section(control_layout)
        self._create_small_list_section(control_layout)
        self._create_bottom_buttons(control_layout)

        return control_widget

    def _create_background_list_section(self, layout):
        """创建背景图列表区域"""
        self.bg_list_group = QGroupBox(tr("背景图列表"))
        group = self.bg_list_group
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(6, 14, 6, 6)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        self.prev_img_btn = QPushButton("◀")
        self.prev_img_btn.setObjectName("navBtn")
        self.prev_img_btn.setFixedWidth(36)
        self.prev_img_btn.setFixedHeight(22)
        header_layout.addWidget(self.prev_img_btn)

        self.next_img_btn = QPushButton("▶")
        self.next_img_btn.setObjectName("navBtn")
        self.next_img_btn.setFixedWidth(36)
        self.next_img_btn.setFixedHeight(22)
        header_layout.addWidget(self.next_img_btn)

        header_layout.addSpacing(4)

        self.step_label = QLabel(tr("步长："))
        self.step_label.setFixedHeight(22)
        header_layout.addWidget(self.step_label)

        self.step_spin = QSpinBox()
        self.step_spin.setRange(1, 10)
        self.step_spin.setValue(1)
        self.step_spin.setFixedWidth(60)
        self.step_spin.setFixedHeight(22)
        self.step_spin.setAlignment(Qt.AlignCenter)
        self.step_spin.setButtonSymbols(QSpinBox.PlusMinus)
        header_layout.addWidget(self.step_spin)

        header_layout.addSpacing(4)

        self.view_toggle_btn = QPushButton(tr("工作路径"))
        self.view_toggle_btn.setObjectName("warningBtn")
        self.view_toggle_btn.setMinimumWidth(60)
        self.view_toggle_btn.setFixedHeight(22)
        self.view_toggle_btn.clicked.connect(self._toggle_view_path)
        header_layout.addWidget(self.view_toggle_btn, 1)

        self.prev_img_btn.clicked.connect(lambda: self.switch_background(-1))
        self.next_img_btn.clicked.connect(lambda: self.switch_background(1))
        self.step_spin.valueChanged.connect(lambda v: setattr(self, '_nav_step', v))

        group_layout.addLayout(header_layout)

        self.background_list = DragOutListWidget()
        self.background_list.setObjectName("bgList")
        self.background_list.itemClicked.connect(self.select_background)
        self.background_list.setMinimumHeight(80)
        group_layout.addWidget(self.background_list)

        layout.addWidget(group)

    def _create_label_list_section(self, layout):
        """创建标签列表区域"""
        self.label_group = QGroupBox(tr("标签管理"))
        group = self.label_group
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(6, 14, 6, 6)

        label_layout = QHBoxLayout()

        original_label_layout = QVBoxLayout()
        self.bg_label_header_lbl = QLabel(tr("背景图标签"))
        original_label_header = QHBoxLayout()
        original_label_header.addWidget(self.bg_label_header_lbl)
        original_label_header.addStretch()
        original_label_layout.addLayout(original_label_header)

        self.label_list = QListWidget()
        self.label_list.setObjectName("labelList")
        self.label_list.setMinimumHeight(100)
        self.label_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.label_list.customContextMenuRequested.connect(self.label_manager.show_label_context_menu)
        self.label_list.itemPressed.connect(self.label_list_item_pressed)
        self.label_list.itemClicked.connect(self.label_list_item_clicked)
        self.pressed_label = None
        original_label_layout.addWidget(self.label_list)

        paste_label_layout = QVBoxLayout()
        self.paste_label_header_lbl = QLabel(tr("贴图标签_list"))
        paste_label_header = QHBoxLayout()
        paste_label_header.addWidget(self.paste_label_header_lbl)
        paste_label_header.addStretch()
        paste_label_layout.addLayout(paste_label_header)

        self.paste_label_list = QListWidget()
        self.paste_label_list.setObjectName("pasteLabelList")
        self.paste_label_list.setMinimumHeight(100)
        self.paste_label_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.paste_label_list.customContextMenuRequested.connect(
            self.label_manager.show_paste_label_context_menu
        )
        default_item = QListWidgetItem("paste")
        self.paste_label_list.addItem(default_item)
        self.paste_label_list.itemPressed.connect(self.label_list_item_pressed)
        self.paste_label_list.itemClicked.connect(self.label_list_item_clicked)
        paste_label_layout.addWidget(self.paste_label_list)

        label_layout.addLayout(original_label_layout)
        label_layout.addLayout(paste_label_layout)
        label_layout.setStretch(0, 1)
        label_layout.setStretch(1, 1)
        group_layout.addLayout(label_layout)

        layout.addWidget(group)

    def _create_small_list_section(self, layout):
        """创建贴图列表区域"""
        self.paste_group = QGroupBox(tr("贴图列表"))
        group = self.paste_group
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(6, 14, 6, 6)

        small_list_layout = QHBoxLayout()

        self.random_paste_btn = QPushButton(tr("随机贴图"))
        self.random_paste_btn.setObjectName("accentBtn")
        self.random_paste_btn.setFixedHeight(22)
        self.random_paste_btn.clicked.connect(self.random_paste_images)
        self.random_paste_btn.setToolTip(tr("随机贴图"))
        small_list_layout.addWidget(self.random_paste_btn, 1)

        self.batch_paste_btn = QPushButton(tr("一键贴图"))
        self.batch_paste_btn.setObjectName("accentBtn")
        self.batch_paste_btn.setFixedHeight(22)
        self.batch_paste_btn.clicked.connect(self.batch_paste_images)
        self.batch_paste_btn.setToolTip(tr("一键贴图"))
        small_list_layout.addWidget(self.batch_paste_btn, 1)

        self.toggle_view_btn = QPushButton(tr("列表视图"))
        self.toggle_view_btn.setObjectName("warningBtn")
        self.toggle_view_btn.setFixedHeight(22)
        self.toggle_view_btn.clicked.connect(self.toggle_view_mode)
        small_list_layout.addWidget(self.toggle_view_btn, 1)

        small_list_layout.addStretch()
        group_layout.addLayout(small_list_layout)

        self._create_paste_params(group_layout)

        self.small_list = QListWidget()
        self.small_list.setObjectName("smallList")
        self.small_list.itemClicked.connect(self.add_small_to_canvas)
        self._configure_small_list()
        group_layout.addWidget(self.small_list)

        layout.addWidget(group)

    def _create_paste_params(self, layout):
        """创建贴图参数设置"""
        paste_params_layout = QHBoxLayout()
        paste_params_layout.setContentsMargins(0, 5, 0, 5)

        self.paste_count_lbl = QLabel(tr("贴图个数:"))
        paste_params_layout.addWidget(self.paste_count_lbl)
        self.paste_count_spin = QSpinBox()
        self.paste_count_spin.setObjectName("paramSpin")
        self.paste_count_spin.setMinimum(PASTE_PARAMS['min_count'])
        self.paste_count_spin.setMaximum(PASTE_PARAMS['max_count'])
        self.paste_count_spin.setValue(PASTE_PARAMS['default_count'])
        self.paste_count_spin.setMinimumWidth(50)
        paste_params_layout.addWidget(self.paste_count_spin)
        paste_params_layout.addSpacing(10)

        self.size_lbl = QLabel(tr("短边尺寸:"))
        paste_params_layout.addWidget(self.size_lbl)
        self.min_size_spin = QSpinBox()
        self.min_size_spin.setObjectName("paramSpin")
        self.min_size_spin.setMinimum(15)
        self.min_size_spin.setMaximum(100)
        self.min_size_spin.setValue(30)
        self.min_size_spin.setMinimumWidth(55)
        paste_params_layout.addWidget(self.min_size_spin)

        paste_params_layout.addWidget(QLabel("-"))

        self.max_size_spin = QSpinBox()
        self.max_size_spin.setObjectName("paramSpin")
        self.max_size_spin.setMinimum(30)
        self.max_size_spin.setMaximum(200)
        self.max_size_spin.setValue(60)
        self.max_size_spin.setMinimumWidth(55)
        paste_params_layout.addWidget(self.max_size_spin)

        self.min_size_spin.valueChanged.connect(self._on_min_size_changed)
        self.max_size_spin.valueChanged.connect(self._on_max_size_changed)
        self._on_min_size_changed(self.min_size_spin.value())
        self._on_max_size_changed(self.max_size_spin.value())

        paste_params_layout.addStretch()
        layout.addLayout(paste_params_layout)

    def _configure_small_list(self):
        """配置贴图列表"""
        if self.is_thumbnail_mode:
            self.small_list.setViewMode(QListWidget.IconMode)
            self.small_list.setIconSize(QSize(
                self.thumbnail_grid_width, self.thumbnail_grid_height
            ))
            self.small_list.setGridSize(QSize(
                self.thumbnail_grid_width, self.thumbnail_grid_height + 20
            ))
            self.small_list.setSpacing(self.thumbnail_spacing)
            self.small_list.setWrapping(True)
            self.small_list.setFlow(QListWidget.LeftToRight)
            self.small_list.setResizeMode(QListWidget.Adjust)
            self.small_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
            self.small_list.setHorizontalScrollMode(QListWidget.ScrollPerPixel)

    def _create_bottom_buttons(self, layout):
        """创建底部按钮"""
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 4, 0, 0)

        self.clear_btn = QPushButton(tr("清空画布"))
        self.clear_btn.setObjectName("dangerBtn")
        self.clear_btn.setFixedHeight(22)
        self.clear_btn.clicked.connect(self.clear_canvas)
        self.clear_btn.setToolTip(tr("清空画布"))

        self.save_btn = QPushButton(tr("保存图片"))
        self.save_btn.setObjectName("successBtn")
        self.save_btn.setFixedHeight(22)
        self.save_btn.clicked.connect(self.save_canvas)
        self.save_btn.setToolTip(tr("保存图片"))

        self.save_all_btn = QPushButton(tr("全部保存"))
        self.save_all_btn.setObjectName("successBtn")
        self.save_all_btn.setFixedHeight(22)
        self.save_all_btn.clicked.connect(self.save_all_canvas)
        self.save_all_btn.setToolTip(tr("全部保存"))

        button_layout.addWidget(self.clear_btn, 1)
        button_layout.addWidget(self.save_btn, 1)
        button_layout.addWidget(self.save_all_btn, 1)
        layout.addLayout(button_layout)

    def toggle_view_mode(self):
        """切换视图模式"""
        self.is_thumbnail_mode = not self.is_thumbnail_mode

        if self.is_thumbnail_mode:
            self.toggle_view_btn.setText(tr("列表视图"))
        else:
            self.toggle_view_btn.setText(tr("缩略视图"))

        self.small_list.clear()
        self._configure_small_list() if self.is_thumbnail_mode else self._set_list_mode()
        self.refresh_list_items()
        self.small_list.scrollToTop()
        self.small_list.updateGeometry()
        self.small_list.repaint()

        mode_text = "Thumbnail" if self.is_thumbnail_mode else "List"
        self.status_label.setText(f"View: {mode_text}")
        QTimer.singleShot(2000, lambda: self.status_label.setText(""))

    def _set_list_mode(self):
        """设置列表模式"""
        self.small_list.setViewMode(QListWidget.ListMode)
        self.small_list.setIconSize(QSize())
        self.small_list.setGridSize(QSize())
        self.small_list.setSpacing(0)
        self.small_list.setWrapping(False)
        self.small_list.setFlow(QListWidget.TopToBottom)
        self.small_list.setVerticalScrollMode(QListWidget.ScrollPerItem)
