"""
UI 构建混入 - 负责所有界面控件的创建和布局
"""
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QSplitter, QScrollArea,
    QLineEdit, QCheckBox, QSpinBox, QGroupBox, QFrame
)
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QDrag
from PyQt5.QtCore import Qt, QSize, QTimer, QPoint, QMimeData, QUrl

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


class DragOutListWidget(QListWidget):
    """支持拖出文件的列表控件"""
    def mouseMoveEvent(self, event):
        item = self.itemAt(event.pos())
        if item and event.buttons() & Qt.LeftButton:
            file_path = item.data(Qt.UserRole + 1)
            if file_path and os.path.isfile(file_path):
                drag = QDrag(self)
                mime = QMimeData()
                mime.setUrls([QUrl.fromLocalFile(file_path)])
                drag.setMimeData(mime)
                drag.exec_(Qt.CopyAction)
                return
        super().mouseMoveEvent(event)


class UIBuilderMixin:
    """UI 构建混入类 - 创建工具栏、控制面板、画布等界面元素"""

    def init_ui(self):
        """初始化用户界面"""
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._create_toolbar(main_layout)

        splitter = self._create_splitter()
        main_layout.addWidget(splitter)

        main_layout.setStretch(0, 0)
        main_layout.setStretch(1, 1)

        self.setCentralWidget(central_widget)

        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        self.statusBar().addWidget(self.status_label)
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
        self.upload_a_btn = self._create_svg_button(
            SVG_FILE, self.upload_background, tr("选择背景图片"), bg_color, "bgBtn"
        )
        upload_layout.addWidget(self.upload_a_btn)

        self.load_folder_btn = self._create_svg_button(
            SVG_FOLDER, self.load_folder_images, tr("加载文件夹图片"), bg_color, "bgBtn"
        )
        upload_layout.addWidget(self.load_folder_btn)

        upload_layout.addSpacing(2)
        self.paste_lbl = QLabel(tr("贴图:"))
        upload_layout.addWidget(self.paste_lbl)
        self.upload_b_btn = self._create_svg_button(
            SVG_FILE, self.upload_small_images, tr("选择贴图"), paste_color, "pasteBtn"
        )
        upload_layout.addWidget(self.upload_b_btn)

        self.load_small_folder_btn = self._create_svg_button(
            SVG_FOLDER, self.load_small_folder_images, tr("加载贴图文件夹"), paste_color, "pasteBtn"
        )
        upload_layout.addWidget(self.load_small_folder_btn)

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

        self.theme_btn = QPushButton("☀")
        self.theme_btn.setObjectName("themeBtn")
        self.theme_btn.setFixedSize(28, 28)
        self.theme_btn.setToolTip("切换深色/浅色主题")
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
        self.show_labels_checkbox.setChecked(False)
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
        from PyQt5.QtWidgets import QMenu, QAction

        self.options_btn = QPushButton(tr("选项"))
        self.options_btn.setObjectName("optionsBtn")
        self.options_btn.setMinimumWidth(60)
        self.options_btn.setToolTip(tr("选项设置"))

        self.options_menu = QMenu()
        self.options_menu.setObjectName("optionsMenu")
        self.options_menu.setMinimumWidth(200)

        self._draw_box_action = QAction("  " + tr("绘制BOX"), self)
        self._draw_box_action.triggered.connect(self.toggle_draw_mode)
        self.options_menu.addAction(self._draw_box_action)
        self.options_menu.addSeparator()

        items = [
            (tr("显示BOX"), "toggle_labels", self.show_labels_checkbox),
            (tr("显示Label"), "toggle_label_names", self.show_label_names_checkbox),
            (tr("自动保存"), "toggle_auto_save", self.auto_save_checkbox),
            (tr("显示网格"), "toggle_grid", self.show_grid_checkbox),
            (tr("显示贴图名"), "toggle_paste_names", self.show_paste_names_checkbox),
            (tr("添加文件名前缀"), None, self.prefix_checkbox),
        ]

        self._menu_actions = []
        for text, shortcut_action, checkbox in items:
            sc = self._get_shortcut(shortcut_action) if shortcut_action else ''
            label = f"{text}\t{sc}" if sc else text
            action = QAction(label, self)
            action.setCheckable(True)
            action.setChecked(checkbox.isChecked())
            action.triggered.connect(lambda checked, cb=checkbox: cb.setChecked(checked))
            checkbox.stateChanged.connect(lambda state, a=action: a.setChecked(state == Qt.Checked))
            self.options_menu.addAction(action)
            self._menu_actions.append((action, checkbox, shortcut_action))

        self.options_btn.setMenu(self.options_menu)
        layout.addWidget(self.options_btn)

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
        control_widget.setMinimumWidth(350)
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
        self.file_count_label = QLabel()
        self.file_count_label.setObjectName("fileCountLabel")
        self.file_count_label.hide()
        header_layout.addWidget(self.file_count_label)
        header_layout.addStretch()
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
        self.random_paste_btn.clicked.connect(self.random_paste_images)
        self.random_paste_btn.setToolTip(tr("随机贴图"))
        small_list_layout.addWidget(self.random_paste_btn, 1)

        self.batch_paste_btn = QPushButton(tr("一键贴图"))
        self.batch_paste_btn.setObjectName("accentBtn")
        self.batch_paste_btn.clicked.connect(self.batch_paste_images)
        self.batch_paste_btn.setToolTip(tr("一键贴图"))
        small_list_layout.addWidget(self.batch_paste_btn, 1)

        self.toggle_view_btn = QPushButton(tr("列表视图"))
        self.toggle_view_btn.setObjectName("warningBtn")
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
        self.clear_btn.clicked.connect(self.clear_canvas)
        self.clear_btn.setToolTip(tr("清空画布"))

        self.save_btn = QPushButton(tr("保存图片"))
        self.save_btn.setObjectName("successBtn")
        self.save_btn.clicked.connect(self.save_canvas)
        self.save_btn.setToolTip(tr("保存图片"))

        self.save_all_btn = QPushButton(tr("全部保存"))
        self.save_all_btn.setObjectName("successBtn")
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
