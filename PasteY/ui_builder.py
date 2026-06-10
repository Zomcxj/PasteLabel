"""
UI 构建混入 - 负责所有界面控件的创建和布局
"""
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QSplitter, QScrollArea,
    QLineEdit, QCheckBox, QSpinBox
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QSize, QTimer

from .config import WINDOW_CONFIG, PASTE_PARAMS, THUMBNAIL_CONFIG, DEFAULT_PREFIX
from .utils import create_thumbnail
from .styles import (
    get_list_style, get_action_button_style, get_spinbox_style,
    get_checkbox_style, get_input_style, get_draw_button_style,
    get_icon_button_style, get_prefix_input_focus_style
)
from .widgets import Canvas


class UIBuilderMixin:
    """UI 构建混入类 - 创建工具栏、控制面板、画布等界面元素"""

    def init_ui(self):
        """初始化用户界面"""
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        self._create_toolbar(main_layout)

        splitter = self._create_splitter()
        main_layout.addWidget(splitter)

        main_layout.setStretch(0, 0)
        main_layout.setStretch(1, 1)

        self.setCentralWidget(central_widget)

        self.status_label = QLabel("")
        self.statusBar().addWidget(self.status_label)

    def _create_toolbar(self, layout):
        """创建工具栏"""
        upload_layout = QHBoxLayout()

        script_dir = os.path.dirname(os.path.abspath(__file__))

        def get_icon_path(icon_name):
            icon_paths = [
                os.path.join(script_dir, "../ico_image", icon_name),
                os.path.join(script_dir, "ico_image", icon_name),
                os.path.join(os.getcwd(), "ico_image", icon_name),
                os.path.abspath(os.path.join(script_dir, "..", "ico_image", icon_name))
            ]
            for path in icon_paths:
                if os.path.exists(path):
                    return path
            return None

        file_icon_path = get_icon_path("file-os.png")
        folder_icon_path = get_icon_path("folders.png")

        self.upload_a_btn = self._create_icon_button(
            file_icon_path, self.upload_background, "选择背景图片"
        )
        upload_layout.addWidget(QLabel("背景图:"))
        upload_layout.addWidget(self.upload_a_btn)

        upload_layout.addSpacing(2)
        self.load_folder_btn = self._create_icon_button(
            folder_icon_path, self.load_folder_images, "加载文件夹图片"
        )
        upload_layout.addWidget(self.load_folder_btn)

        upload_layout.addSpacing(2)
        self.upload_b_btn = self._create_icon_button(
            file_icon_path, self.upload_small_images, "选择贴图"
        )
        upload_layout.addWidget(QLabel("贴图:"))
        upload_layout.addWidget(self.upload_b_btn)

        upload_layout.addSpacing(2)
        self.load_small_folder_btn = self._create_icon_button(
            folder_icon_path, self.load_small_folder_images, "加载贴图文件夹"
        )
        upload_layout.addWidget(self.load_small_folder_btn)

        upload_layout.addSpacing(2)
        self.upload_paste_label_btn = self._create_icon_button(
            file_icon_path, self.upload_paste_labels, "选择标签文件"
        )
        upload_layout.addWidget(QLabel("标签:"))
        upload_layout.addWidget(self.upload_paste_label_btn)

        upload_layout.addSpacing(2)
        separator = QLabel("|")
        separator.setStyleSheet("color: gray; font-weight: bold;")
        upload_layout.addWidget(separator)

        upload_layout.addSpacing(10)
        self.draw_box_btn = QPushButton("绘制BOX(W)")
        self.draw_box_btn.clicked.connect(self.toggle_draw_mode)
        self.draw_box_btn.setMaximumWidth(100)
        self.draw_box_btn.setStyleSheet(get_draw_button_style())
        upload_layout.addWidget(self.draw_box_btn)

        self._add_checkboxes(upload_layout)
        self._add_prefix_input(upload_layout)

        upload_layout.addStretch()
        layout.addLayout(upload_layout)

    def _create_icon_button(self, icon_path, slot, tooltip):
        """创建图标按钮"""
        btn = QPushButton("")
        if os.path.exists(icon_path):
            btn.setIcon(QIcon(icon_path))
        btn.clicked.connect(slot)
        btn.setMaximumWidth(30)
        btn.setToolTip(tooltip)
        btn.setStyleSheet(get_icon_button_style())
        return btn

    def _add_checkboxes(self, layout):
        """添加复选框"""
        layout.addSpacing(10)
        self.auto_save_checkbox = QCheckBox("自动保存(G)")
        self.auto_save_checkbox.setChecked(False)
        self.auto_save_checkbox.setStyleSheet(get_checkbox_style("#4CAF50"))
        layout.addWidget(self.auto_save_checkbox)

        layout.addSpacing(10)
        self.show_labels_checkbox = QCheckBox("显示BOX(R)")
        self.show_labels_checkbox.setChecked(False)
        self.show_labels_checkbox.stateChanged.connect(self.on_labels_checkbox_changed)
        self.show_labels_checkbox.setStyleSheet(get_checkbox_style("#2196F3"))
        layout.addWidget(self.show_labels_checkbox)

        layout.addSpacing(10)
        self.show_label_names_checkbox = QCheckBox("显示Label(T)")
        self.show_label_names_checkbox.setChecked(True)
        self.show_label_names_checkbox.stateChanged.connect(self.on_labels_checkbox_changed)
        self.show_label_names_checkbox.setStyleSheet(get_checkbox_style("#2196F3"))
        layout.addWidget(self.show_label_names_checkbox)

        layout.addSpacing(10)
        self.auto_label_checkbox = QCheckBox("贴图标签")
        self.auto_label_checkbox.setChecked(True)
        self.auto_label_checkbox.setStyleSheet(get_checkbox_style("#2196F3"))
        layout.addWidget(self.auto_label_checkbox)

        layout.addSpacing(10)
        self.prefix_checkbox = QCheckBox("添加文件名前缀")
        self.prefix_checkbox.setChecked(True)
        self.prefix_checkbox.setStyleSheet(get_checkbox_style("#2196F3"))
        layout.addWidget(self.prefix_checkbox)

    def _add_prefix_input(self, layout):
        """添加前缀输入框"""
        layout.addSpacing(8)
        self.prefix_input = QLineEdit()
        self.default_prefix = DEFAULT_PREFIX
        self.prefix_input.setText(self.default_prefix)
        self.prefix_input.setStyleSheet(get_input_style())
        self.prefix_input.focusInEvent = self.on_prefix_input_focus_in
        self.prefix_input.focusOutEvent = self.on_prefix_input_focus_out
        self.prefix_input.setMaximumWidth(90)
        layout.addWidget(self.prefix_input)

    def on_prefix_input_focus_in(self, event):
        """前缀输入框获得焦点"""
        if self.prefix_input.text() == self.default_prefix:
            self.prefix_input.setText("")
            self.prefix_input.setStyleSheet(get_prefix_input_focus_style("black"))
        QLineEdit.focusInEvent(self.prefix_input, event)

    def on_prefix_input_focus_out(self, event):
        """前缀输入框失去焦点"""
        if not self.prefix_input.text().strip():
            self.prefix_input.setText(self.default_prefix)
            self.prefix_input.setStyleSheet(get_prefix_input_focus_style("gray"))
        else:
            self.prefix_input.setStyleSheet(get_prefix_input_focus_style("black"))
        QLineEdit.focusOutEvent(self.prefix_input, event)

    def _validate_size_range(self):
        """验证尺寸范围，确保最小值不大于最大值"""
        min_size = self.min_size_spin.value()
        max_size = self.max_size_spin.value()
        if min_size > max_size:
            self.status_label.setText("最小值不能大于最大值")
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
        splitter = QSplitter(Qt.Horizontal)

        canvas_widget = QWidget()
        canvas_layout = QVBoxLayout(canvas_widget)
        self.canvas = Canvas(self)
        canvas_scroll = QScrollArea()
        canvas_scroll.setWidget(self.canvas)
        canvas_scroll.setWidgetResizable(True)
        canvas_layout.addWidget(canvas_scroll)
        splitter.addWidget(canvas_widget)

        control_widget = self._create_control_panel()
        splitter.addWidget(control_widget)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([1000, 300])

        return splitter

    def _create_control_panel(self):
        """创建控制面板"""
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)

        self._create_background_list_section(control_layout)
        self._create_label_list_section(control_layout)
        self._create_small_list_section(control_layout)
        self._create_bottom_buttons(control_layout)

        return control_widget

    def _create_background_list_section(self, layout):
        """创建背景图列表区域"""
        bg_list_layout = QHBoxLayout()
        bg_list_layout.addWidget(QLabel("背景图列表"))

        self.file_count_label = QLabel()
        self.file_count_label.hide()
        bg_list_layout.addWidget(self.file_count_label)
        bg_list_layout.addStretch()
        layout.addLayout(bg_list_layout)

        self.background_list = QListWidget()
        self.background_list.itemClicked.connect(self.select_background)
        self.background_list.setStyleSheet(get_list_style())
        layout.addWidget(self.background_list)

    def _create_label_list_section(self, layout):
        """创建标签列表区域"""
        label_layout = QHBoxLayout()

        original_label_layout = QVBoxLayout()
        original_label_header = QHBoxLayout()
        original_label_header.addWidget(QLabel("背景图标签"))
        original_label_header.addStretch()
        original_label_layout.addLayout(original_label_header)

        self.label_list = QListWidget()
        self.label_list.setMinimumHeight(150)
        self.label_list.setStyleSheet(get_list_style())
        self.label_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.label_list.customContextMenuRequested.connect(self.label_manager.show_label_context_menu)
        self.label_list.itemPressed.connect(self.label_list_item_pressed)
        self.label_list.itemClicked.connect(self.label_list_item_clicked)
        self.pressed_label = None
        original_label_layout.addWidget(self.label_list)

        paste_label_layout = QVBoxLayout()
        paste_label_header = QHBoxLayout()
        paste_label_header.addWidget(QLabel("贴图标签"))
        paste_label_header.addStretch()
        paste_label_layout.addLayout(paste_label_header)

        self.paste_label_list = QListWidget()
        self.paste_label_list.setMinimumHeight(150)
        self.paste_label_list.setStyleSheet(get_list_style())
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
        layout.addLayout(label_layout)

    def _create_small_list_section(self, layout):
        """创建贴图列表区域"""
        small_list_layout = QHBoxLayout()
        small_list_layout.addWidget(QLabel("贴图列表"))

        self.random_paste_btn = QPushButton("随机贴图")
        self.random_paste_btn.clicked.connect(self.random_paste_images)
        self.random_paste_btn.setMinimumWidth(70)
        self.random_paste_btn.setStyleSheet(get_action_button_style("#E3F2FD", "#1976D2"))
        small_list_layout.addWidget(self.random_paste_btn)
        small_list_layout.addSpacing(5)

        self.batch_paste_btn = QPushButton("一键贴图")
        self.batch_paste_btn.clicked.connect(self.batch_paste_images)
        self.batch_paste_btn.setMinimumWidth(70)
        self.batch_paste_btn.setStyleSheet(get_action_button_style("#E3F2FD", "#1976D2"))
        small_list_layout.addWidget(self.batch_paste_btn)
        small_list_layout.addSpacing(5)

        self.toggle_view_btn = QPushButton("列表视图")
        self.toggle_view_btn.clicked.connect(self.toggle_view_mode)
        self.toggle_view_btn.setMinimumWidth(70)
        self.toggle_view_btn.setStyleSheet(get_action_button_style("#FFF3E0", "#E65100"))
        small_list_layout.addWidget(self.toggle_view_btn)

        small_list_layout.addStretch()
        layout.addLayout(small_list_layout)

        self._create_paste_params(layout)

        self.small_list = QListWidget()
        self.small_list.itemClicked.connect(self.add_small_to_canvas)
        self._configure_small_list()
        self.small_list.setStyleSheet(get_list_style())
        layout.addWidget(self.small_list)

    def _create_paste_params(self, layout):
        """创建贴图参数设置"""
        paste_params_layout = QHBoxLayout()
        paste_params_layout.setContentsMargins(0, 5, 0, 5)

        paste_params_layout.addWidget(QLabel("贴图个数:"))
        self.paste_count_spin = QSpinBox()
        self.paste_count_spin.setMinimum(PASTE_PARAMS['min_count'])
        self.paste_count_spin.setMaximum(PASTE_PARAMS['max_count'])
        self.paste_count_spin.setValue(PASTE_PARAMS['default_count'])
        self.paste_count_spin.setMinimumWidth(50)
        self.paste_count_spin.setStyleSheet(get_spinbox_style())
        paste_params_layout.addWidget(self.paste_count_spin)
        paste_params_layout.addSpacing(10)

        paste_params_layout.addWidget(QLabel("短边尺寸:"))
        self.min_size_spin = QSpinBox()
        self.min_size_spin.setMinimum(15)
        self.min_size_spin.setMaximum(100)
        self.min_size_spin.setValue(30)
        self.min_size_spin.setMinimumWidth(55)
        self.min_size_spin.setStyleSheet(get_spinbox_style())
        paste_params_layout.addWidget(self.min_size_spin)

        paste_params_layout.addWidget(QLabel("-"))

        self.max_size_spin = QSpinBox()
        self.max_size_spin.setMinimum(30)
        self.max_size_spin.setMaximum(200)
        self.max_size_spin.setValue(60)
        self.max_size_spin.setMinimumWidth(55)
        self.max_size_spin.setStyleSheet(get_spinbox_style())
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
        button_layout.setContentsMargins(0, 5, 0, 0)

        self.clear_btn = QPushButton("清空画布")
        self.clear_btn.clicked.connect(self.clear_canvas)
        self.clear_btn.setStyleSheet(get_action_button_style("#FFEBEE", "#C62828"))

        self.save_btn = QPushButton("保存图片")
        self.save_btn.clicked.connect(self.save_canvas)
        self.save_btn.setStyleSheet(get_action_button_style("#E8F5E9", "#2E7D32"))

        self.save_all_btn = QPushButton("全部保存")
        self.save_all_btn.clicked.connect(self.save_all_canvas)
        self.save_all_btn.setStyleSheet(get_action_button_style("#E8F5E9", "#2E7D32"))

        button_layout.addWidget(self.clear_btn)
        button_layout.addSpacing(10)
        button_layout.addWidget(self.save_btn)
        button_layout.addSpacing(10)
        button_layout.addWidget(self.save_all_btn)
        layout.addLayout(button_layout)

    def toggle_view_mode(self):
        """切换视图模式"""
        self.is_thumbnail_mode = not self.is_thumbnail_mode

        if self.is_thumbnail_mode:
            self.toggle_view_btn.setText("列表视图")
        else:
            self.toggle_view_btn.setText("缩略视图")

        self.small_list.clear()
        self._configure_small_list() if self.is_thumbnail_mode else self._set_list_mode()
        self.refresh_list_items()
        self.small_list.scrollToTop()
        self.small_list.updateGeometry()
        self.small_list.repaint()

        mode_text = "缩略图模式" if self.is_thumbnail_mode else "列表模式"
        self.status_label.setText(f"已切换到{mode_text}")
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
