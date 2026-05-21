"""
主窗口模块 - ImageEditor 主窗口逻辑
"""
import os
import json
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QListWidget, QListWidgetItem,
    QSplitter, QMessageBox, QScrollArea, QLineEdit, QCheckBox, QSpinBox,
    QProgressDialog, QApplication
)
from PyQt5.QtGui import QPixmap, QIcon, QColor, QPainter
from PyQt5.QtCore import Qt, QPoint, QTimer, QSize, QEvent, QRectF

from .config import (
    WINDOW_CONFIG, PASTE_PARAMS, THUMBNAIL_CONFIG,
    SUPPORTED_IMAGE_EXTENSIONS, LABELME_VERSION, DEFAULT_PREFIX,
    RANDOM_POSITION_CONFIG
)
from .utils import (
    PathUtils, natural_sort_key, create_thumbnail, create_app_icon,
    extract_label_name, calculate_iou
)
from .styles import (
    get_list_style, get_action_button_style, get_spinbox_style,
    get_checkbox_style, get_input_style, get_draw_button_style
)
from .widgets import Canvas
from .dialogs import ProgressDialogFactory, SaveTipDialog, LabelSelectionDialog
from .save_manager import SaveManager
from .label_manager import LabelManager


class ImageEditor(QMainWindow):
    """贴图标注工具主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("贴图标注工具")
        self.resize(WINDOW_CONFIG['default_width'], WINDOW_CONFIG['default_height'])
        
        # 设置窗口图标
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.setWindowIcon(create_app_icon(script_dir))
        
        # 初始化数据
        self._init_data()
        
        # 创建 UI
        self.init_ui()
        
        # 初始化标签列表
        self.update_label_list()
        
        # 安装事件过滤器
        self.installEventFilterRecursive(self)
    
    def _init_data(self):
        """初始化数据结构"""
        self.background_images = []
        self.current_background = None
        self.current_background_index = -1
        self.small_images = []
        self.canvas_items_dict = {}  # 每个背景图的贴图状态
        self.canvas_items = []  # 当前背景图的贴图
        self.selected_item = None
        self.is_dragging = False
        self.is_resizing = False
        self.drag_offset = QPoint(0, 0)
        self._busy = False  # 防重入标志，防止快速点击导致状态竞争
        
        self.detection_boxes_dict = {}  # 每个背景图的检测框
        self.detection_boxes = []  # 当前背景图的检测框
        self.global_labels = set()  # 全局标签集合
        
        # 视图模式
        self.is_thumbnail_mode = True
        self.thumbnail_grid_width = THUMBNAIL_CONFIG['grid_width']
        self.thumbnail_grid_height = THUMBNAIL_CONFIG['grid_height']
        self.thumbnail_spacing = THUMBNAIL_CONFIG['spacing']
        
        # 初始化管理器
        self.save_manager = SaveManager(self)
        self.label_manager = LabelManager(self)
    
    def init_ui(self):
        """初始化用户界面"""
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # 创建工具栏
        self._create_toolbar(main_layout)
        
        # 创建分割器（画布 + 控制面板）
        splitter = self._create_splitter()
        main_layout.addWidget(splitter)
        
        # 设置拉伸因子
        main_layout.setStretch(0, 0)
        main_layout.setStretch(1, 1)
        
        self.setCentralWidget(central_widget)
        
        # 状态栏
        self.status_label = QLabel("")
        self.statusBar().addWidget(self.status_label)
    
    def _create_toolbar(self, layout):
        """创建工具栏"""
        upload_layout = QHBoxLayout()
        
        # 图标路径
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # 尝试不同的图标路径
        def get_icon_path(icon_name):
            icon_paths = [
                # 开发环境路径
                os.path.join(script_dir, "../ico_image", icon_name),
                # 打包环境路径
                os.path.join(script_dir, "ico_image", icon_name),
                # 当前目录
                os.path.join(os.getcwd(), "ico_image", icon_name),
                # 绝对路径（备用）
                os.path.abspath(os.path.join(script_dir, "..", "ico_image", icon_name))
            ]
            for path in icon_paths:
                if os.path.exists(path):
                    return path
            return None
        
        file_icon_path = get_icon_path("file-os.png")
        folder_icon_path = get_icon_path("folders.png")
        
        # 背景图上传按钮
        self.upload_a_btn = self._create_icon_button(
            file_icon_path, self.upload_background, "选择背景图片"
        )
        upload_layout.addWidget(QLabel("背景图:"))
        upload_layout.addWidget(self.upload_a_btn)
        
        # 文件夹加载按钮
        upload_layout.addSpacing(2)
        self.load_folder_btn = self._create_icon_button(
            folder_icon_path, self.load_folder_images, "加载文件夹图片"
        )
        upload_layout.addWidget(self.load_folder_btn)
        
        # 贴图上传按钮
        upload_layout.addSpacing(2)
        self.upload_b_btn = self._create_icon_button(
            file_icon_path, self.upload_small_images, "选择贴图"
        )
        upload_layout.addWidget(QLabel("贴图:"))
        upload_layout.addWidget(self.upload_b_btn)
        
        # 贴图文件夹加载按钮
        upload_layout.addSpacing(2)
        self.load_small_folder_btn = self._create_icon_button(
            folder_icon_path, self.load_small_folder_images, "加载贴图文件夹"
        )
        upload_layout.addWidget(self.load_small_folder_btn)
        
        # 标签上传按钮
        upload_layout.addSpacing(2)
        self.upload_paste_label_btn = self._create_icon_button(
            file_icon_path, self.upload_paste_labels, "选择标签文件"
        )
        upload_layout.addWidget(QLabel("标签:"))
        upload_layout.addWidget(self.upload_paste_label_btn)
        
        # 分隔符
        upload_layout.addSpacing(2)
        separator = QLabel("|")
        separator.setStyleSheet("color: gray; font-weight: bold;")
        upload_layout.addWidget(separator)
        
        # 绘制检测框按钮
        upload_layout.addSpacing(10)
        self.draw_box_btn = QPushButton("绘制BOX(W)")
        self.draw_box_btn.clicked.connect(self.toggle_draw_mode)
        self.draw_box_btn.setMaximumWidth(100)
        self.draw_box_btn.setStyleSheet(get_draw_button_style())
        upload_layout.addWidget(self.draw_box_btn)
        
        # 复选框
        self._add_checkboxes(upload_layout)
        
        # 前缀输入框
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
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 1px;
            }
            QPushButton:hover {
                background-color: rgba(33, 150, 243, 0.1);
                border-color: rgba(33, 150, 243, 0.3);
            }
            QPushButton:pressed {
                background-color: rgba(33, 150, 243, 0.2);
                border-color: rgba(33, 150, 243, 0.5);
            }
        """)
        return btn
    
    def _add_checkboxes(self, layout):
        """添加复选框"""
        # 自动保存
        layout.addSpacing(10)
        self.auto_save_checkbox = QCheckBox("自动保存(G)")
        self.auto_save_checkbox.setChecked(False)
        self.auto_save_checkbox.setStyleSheet(get_checkbox_style("#4CAF50"))
        layout.addWidget(self.auto_save_checkbox)
        
        # 显示检测框
        layout.addSpacing(10)
        self.show_labels_checkbox = QCheckBox("显示BOX(R)")
        self.show_labels_checkbox.setChecked(False)
        self.show_labels_checkbox.stateChanged.connect(self.on_labels_checkbox_changed)
        self.show_labels_checkbox.setStyleSheet(get_checkbox_style("#2196F3"))
        layout.addWidget(self.show_labels_checkbox)
        
        # 显示类别名
        layout.addSpacing(10)
        self.show_label_names_checkbox = QCheckBox("显示Label(T)")
        self.show_label_names_checkbox.setChecked(True)
        self.show_label_names_checkbox.stateChanged.connect(self.on_labels_checkbox_changed)
        self.show_label_names_checkbox.setStyleSheet(get_checkbox_style("#2196F3"))
        layout.addWidget(self.show_label_names_checkbox)
        
        # 自动标签
        layout.addSpacing(10)
        self.auto_label_checkbox = QCheckBox("贴图标签")
        self.auto_label_checkbox.setChecked(True)
        self.auto_label_checkbox.setStyleSheet(get_checkbox_style("#2196F3"))
        layout.addWidget(self.auto_label_checkbox)
        
        # 添加文件名前缀
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
    
    def _validate_size_range(self):
        """验证尺寸范围，确保最小值不大于最大值"""
        min_size = self.min_size_spin.value()
        max_size = self.max_size_spin.value()
        
        # 确保最小值不大于最大值
        if min_size > max_size:
            # 显示提示信息
            self.status_label.setText("最小值不能大于最大值")
            QTimer.singleShot(2000, lambda: self.status_label.setText(""))
            # 恢复到之前的有效值
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
        
        # 左侧画布
        canvas_widget = QWidget()
        canvas_layout = QVBoxLayout(canvas_widget)
        self.canvas = Canvas(self)
        canvas_scroll = QScrollArea()
        canvas_scroll.setWidget(self.canvas)
        canvas_scroll.setWidgetResizable(True)
        canvas_layout.addWidget(canvas_scroll)
        splitter.addWidget(canvas_widget)
        
        # 右侧控制面板
        control_widget = self._create_control_panel()
        splitter.addWidget(control_widget)
        
        # 设置拉伸因子
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([1000, 300])
        
        return splitter
    
    def _create_control_panel(self):
        """创建控制面板"""
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)
        
        # 背景图列表
        self._create_background_list_section(control_layout)
        
        # 标签列表
        self._create_label_list_section(control_layout)
        
        # 贴图列表
        self._create_small_list_section(control_layout)
        
        # 底部按钮
        self._create_bottom_buttons(control_layout)
        
        return control_widget
    
    def _create_background_list_section(self, layout):
        """创建背景图列表区域"""
        bg_list_layout = QHBoxLayout()
        bg_list_layout.addWidget(QLabel("背景图列表"))
        
        # 文件计数显示
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
        
        # 背景图标签列表
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
        # 使用信号连接替代 monkey-patching mousePressEvent/mouseReleaseEvent
        # 避免在PyQt5中直接调用 C++ 虚方法导致的潜在崩溃（快速点击时）
        self.label_list.itemPressed.connect(self.label_list_item_pressed)
        self.label_list.itemClicked.connect(self.label_list_item_clicked)
        self.pressed_label = None
        original_label_layout.addWidget(self.label_list)
        
        # 贴图标签列表
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
        
        # 随机贴图按钮
        self.random_paste_btn = QPushButton("随机贴图")
        self.random_paste_btn.clicked.connect(self.random_paste_images)
        self.random_paste_btn.setMinimumWidth(70)
        self.random_paste_btn.setStyleSheet(get_action_button_style("#E3F2FD", "#1976D2"))
        small_list_layout.addWidget(self.random_paste_btn)
        small_list_layout.addSpacing(5)
        
        # 一键贴图按钮
        self.batch_paste_btn = QPushButton("一键贴图")
        self.batch_paste_btn.clicked.connect(self.batch_paste_images)
        self.batch_paste_btn.setMinimumWidth(70)
        self.batch_paste_btn.setStyleSheet(get_action_button_style("#E3F2FD", "#1976D2"))
        small_list_layout.addWidget(self.batch_paste_btn)
        small_list_layout.addSpacing(5)
        
        # 视图切换按钮
        self.toggle_view_btn = QPushButton("列表视图")
        self.toggle_view_btn.clicked.connect(self.toggle_view_mode)
        self.toggle_view_btn.setMinimumWidth(70)
        self.toggle_view_btn.setStyleSheet(get_action_button_style("#FFF3E0", "#E65100"))
        small_list_layout.addWidget(self.toggle_view_btn)
        
        small_list_layout.addStretch()
        layout.addLayout(small_list_layout)
        
        # 贴图参数
        self._create_paste_params(layout)
        
        # 贴图列表控件
        self.small_list = QListWidget()
        self.small_list.itemClicked.connect(self.add_small_to_canvas)
        self._configure_small_list()
        self.small_list.setStyleSheet(get_list_style())
        layout.addWidget(self.small_list)
    
    def _create_paste_params(self, layout):
        """创建贴图参数设置"""
        paste_params_layout = QHBoxLayout()
        paste_params_layout.setContentsMargins(0, 5, 0, 5)
        
        # 贴图个数
        paste_params_layout.addWidget(QLabel("贴图个数:"))
        self.paste_count_spin = QSpinBox()
        self.paste_count_spin.setMinimum(PASTE_PARAMS['min_count'])
        self.paste_count_spin.setMaximum(PASTE_PARAMS['max_count'])
        self.paste_count_spin.setValue(PASTE_PARAMS['default_count'])
        self.paste_count_spin.setMinimumWidth(50)
        self.paste_count_spin.setStyleSheet(get_spinbox_style())
        paste_params_layout.addWidget(self.paste_count_spin)
        paste_params_layout.addSpacing(10)
        
        # 尺寸范围
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
        
        # 添加尺寸范围验证
        self.min_size_spin.valueChanged.connect(self._on_min_size_changed)
        self.max_size_spin.valueChanged.connect(self._on_max_size_changed)
        # 初始设置范围
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
    
    def _create_top_toolbar(self, layout):
        """创建顶部工具栏"""
        upload_layout = QHBoxLayout()
        upload_layout.setContentsMargins(0, 5, 0, 5)
        
        # 分隔符
        upload_layout.addSpacing(10)
        separator = QLabel("|")
        separator.setStyleSheet("color: gray; font-weight: bold;")
        upload_layout.addWidget(separator)
        
        # 贴图参数设置
        upload_layout.addSpacing(10)
        upload_layout.addWidget(QLabel("贴图个数:"))
        self.paste_count_spin = QSpinBox()
        self.paste_count_spin.setMinimum(1)
        self.paste_count_spin.setMaximum(20)
        self.paste_count_spin.setValue(1)
        self.paste_count_spin.setMinimumWidth(50)
        self.paste_count_spin.setStyleSheet("""
            QSpinBox {
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                padding: 4px 8px;
                font-size: 12px;
                background-color: white;
            }
            QSpinBox:hover {
                border-color: #BBDEFB;
            }
        """)
        upload_layout.addWidget(self.paste_count_spin)
        
        upload_layout.addSpacing(15)
        upload_layout.addWidget(QLabel("短边尺寸:"))
        
        # 最小尺寸
        self.min_size_spin = QSpinBox()
        self.min_size_spin.setMinimum(15)
        self.min_size_spin.setMaximum(100)
        self.min_size_spin.setValue(30)
        self.min_size_spin.setMinimumWidth(50)
        self.min_size_spin.setStyleSheet("""
            QSpinBox {
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                padding: 4px 8px;
                font-size: 12px;
                background-color: white;
            }
            QSpinBox:hover {
                border-color: #BBDEFB;
            }
        """)
        upload_layout.addWidget(self.min_size_spin)
        
        upload_layout.addWidget(QLabel("-"))
        
        # 最大尺寸
        self.max_size_spin = QSpinBox()
        self.max_size_spin.setMinimum(30)
        self.max_size_spin.setMaximum(200)
        self.max_size_spin.setValue(60)
        self.max_size_spin.setMinimumWidth(50)
        self.max_size_spin.setStyleSheet("""
            QSpinBox {
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                padding: 4px 8px;
                font-size: 12px;
                background-color: white;
            }
            QSpinBox:hover {
                border-color: #BBDEFB;
            }
        """)
        upload_layout.addWidget(self.max_size_spin)
        
        # 连接 valueChanged 信号（箭头按钮调整）
        self.min_size_spin.valueChanged.connect(self._on_min_size_changed)
        self.max_size_spin.valueChanged.connect(self._on_max_size_changed)
        
        # 连接 editingFinished 信号（手动输入验证）
        self.min_size_spin.editingFinished.connect(self._on_min_size_edit_finished)
        self.max_size_spin.editingFinished.connect(self._on_max_size_edit_finished)
        
        # 绘制检测框按钮
        self.draw_box_btn = QPushButton("绘制检测框")
        self.draw_box_btn.clicked.connect(self._on_draw_box_clicked)
        self.draw_box_btn.setStyleSheet(get_action_button_style("#E3F2FD", "#0288D1"))
        upload_layout.addWidget(self.draw_box_btn)
        
        upload_layout.addStretch()
        layout.addLayout(upload_layout)

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
    
    def on_prefix_input_focus_in(self, event):
        """前缀输入框获得焦点"""
        if self.prefix_input.text() == self.default_prefix:
            self.prefix_input.setText("")
            self.prefix_input.setStyleSheet("""
                QLineEdit {
                    border: 1px solid #E0E0E0;
                    border-radius: 8px;
                    padding: 4px 8px;
                    font-size: 12px;
                    background-color: white;
                    color: black;
                }
                QLineEdit:hover {
                    border-color: #BBDEFB;
                }
            """)
        QLineEdit.focusInEvent(self.prefix_input, event)
    
    def on_prefix_input_focus_out(self, event):
        """前缀输入框失去焦点"""
        if not self.prefix_input.text().strip():
            self.prefix_input.setText(self.default_prefix)
            self.prefix_input.setStyleSheet("""
                QLineEdit {
                    border: 1px solid #E0E0E0;
                    border-radius: 8px;
                    padding: 4px 8px;
                    font-size: 12px;
                    background-color: white;
                    color: gray;
                }
                QLineEdit:hover {
                    border-color: #BBDEFB;
                }
            """)
        else:
            self.prefix_input.setStyleSheet("""
                QLineEdit {
                    border: 1px solid #E0E0E0;
                    border-radius: 8px;
                    padding: 4px 8px;
                    font-size: 12px;
                    background-color: white;
                    color: black;
                }
                QLineEdit:hover {
                    border-color: #BBDEFB;
                }
            """)
        QLineEdit.focusOutEvent(self.prefix_input, event)
    
    def upload_background(self):
        """上传背景图片"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择背景图片", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if files:
            self.background_images.clear()
            self.background_list.clear()
            self.current_background = None
            self.detection_boxes_dict.clear()
            self.canvas_items_dict.clear()
            
            for file in files:
                pixmap = QPixmap(file)
                if not pixmap.isNull():
                    new_index = len(self.background_images)
                    self.background_images.append(file)
                    display_path = PathUtils.to_display_path(file)
                    item = QListWidgetItem(display_path)
                    item.setData(Qt.UserRole, new_index)
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
    
    def load_folder_images(self):
        """从文件夹加载背景图"""
        folder_path = QFileDialog.getExistingDirectory(self, "选择图片文件夹", "")
        if not folder_path:
            return
        
        self.background_images.clear()
        self.background_list.clear()
        self.current_background = None
        self.detection_boxes_dict.clear()
        
        for file_name in sorted(os.listdir(folder_path), key=natural_sort_key):
            ext = os.path.splitext(file_name)[1].lower()
            if ext in SUPPORTED_IMAGE_EXTENSIONS:
                file_path = os.path.join(folder_path, file_name)
                new_index = len(self.background_images)
                self.background_images.append(file_path)
                display_path = PathUtils.to_display_path(file_path)
                item = QListWidgetItem(display_path)
                item.setData(Qt.UserRole, new_index)
                self.background_list.addItem(item)
                
                self.canvas_items_dict[new_index] = []
                self.detection_boxes_dict[new_index] = []
        
        if self.background_images:
            self.current_background_index = 0
            self.background_list.setCurrentRow(0)
            self.load_image_by_index(0)
            self.update_label_list()
            self.update_file_count()
        else:
            QMessageBox.warning(self, "警告", "该文件夹中没有找到支持的图片文件")
            self.update_file_count()
    
    def upload_small_images(self):
        """上传贴图"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择贴图片", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if files:
            self.small_images.clear()
            self.small_list.clear()
            
            for file in files:
                pixmap = QPixmap(file)
                if not pixmap.isNull():
                    self.small_images.append((file, pixmap))
                    file_name = os.path.basename(file)
                    self.add_list_item(file_name, pixmap)
        
        self._update_paste_count_spin()
        self._refresh_small_list_view()
    
    def load_small_folder_images(self):
        """从文件夹加载贴图"""
        folder_path = QFileDialog.getExistingDirectory(self, "选择贴图文件夹", "")
        if not folder_path:
            return
        
        self.small_images.clear()
        self.small_list.clear()
        
        loaded_count = 0
        for file_name in sorted(os.listdir(folder_path), key=natural_sort_key):
            ext = os.path.splitext(file_name)[1].lower()
            if ext in SUPPORTED_IMAGE_EXTENSIONS:
                file_path = os.path.join(folder_path, file_name)
                pixmap = QPixmap(file_path)
                if not pixmap.isNull():
                    self.small_images.append((file_path, pixmap))
                    self.add_list_item(file_name, pixmap)
                    loaded_count += 1
        
        if loaded_count == 0:
            QMessageBox.warning(self, "警告", "该文件夹中没有找到支持的图片文件")
        
        self._update_paste_count_spin()
        self._refresh_small_list_view()
    
    def _update_paste_count_spin(self):
        """更新贴图个数输入框"""
        if hasattr(self, 'paste_count_spin'):
            if len(self.small_images) <= 5:
                self.paste_count_spin.setValue(len(self.small_images))
                self.paste_count_spin.setMaximum(len(self.small_images))
            else:
                self.paste_count_spin.setMaximum(len(self.small_images))
    
    def _refresh_small_list_view(self):
        """刷新贴图列表视图"""
        if hasattr(self, 'is_thumbnail_mode'):
            if self.is_thumbnail_mode:
                self._configure_small_list()
            else:
                self.small_list.setViewMode(QListWidget.ListMode)
                self.small_list.setIconSize(QSize())
                self.small_list.setGridSize(QSize())
                self.small_list.setSpacing(0)
                self.small_list.setWrapping(False)
                self.small_list.setFlow(QListWidget.TopToBottom)
                self.small_list.setVerticalScrollMode(QListWidget.ScrollPerItem)
            
            self.refresh_list_items()
            self.small_list.scrollToTop()
            self.small_list.updateGeometry()
            self.small_list.repaint()
    
    def add_list_item(self, file_name, pixmap):
        """添加列表项"""
        item = QListWidgetItem(file_name)
        
        if self.is_thumbnail_mode:
            thumb_pixmap = create_thumbnail(pixmap, self.thumbnail_grid_width, self.thumbnail_grid_height)
            item.setIcon(QIcon(thumb_pixmap))
            item.setSizeHint(QSize(self.thumbnail_grid_width, self.thumbnail_grid_height + 20))
        
        item.setData(Qt.UserRole, len(self.small_images) - 1)
        self.small_list.addItem(item)
    
    def refresh_list_items(self):
        """刷新列表项"""
        self.small_list.clear()
        for idx, (file_path, pixmap) in enumerate(self.small_images):
            file_name = os.path.basename(file_path)
            item = QListWidgetItem(file_name)
            
            if self.is_thumbnail_mode:
                thumb_pixmap = create_thumbnail(pixmap, self.thumbnail_grid_width, self.thumbnail_grid_height)
                item.setIcon(QIcon(thumb_pixmap))
                item.setSizeHint(QSize(self.thumbnail_grid_width, self.thumbnail_grid_height + 20))
            
            item.setData(Qt.UserRole, idx)
            self.small_list.addItem(item)
    
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
    
    def upload_paste_labels(self):
        """上传贴图标签文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择贴图标签文件", "", "Text Files (*.txt)"
        )
        if file_path:
            try:
                labels = []
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            parts = line.split()
                            if parts:
                                labels.append(parts[0])
                
                if labels:
                    self.paste_label_list.clear()
                    for label in labels:
                        self.paste_label_list.addItem(label)
                else:
                    QMessageBox.warning(self, "警告", "未找到有效的标签")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"读取标签文件失败：{e}")
    
    def load_detection_boxes(self, file_path):
        """加载检测框 JSON 文件"""
        base_name = os.path.splitext(file_path)[0]
        json_path = f"{base_name}.json"
        detection_boxes = []
        
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "shapes" in data:
                        shapes = data["shapes"]
                        if isinstance(shapes, list):
                            for shape in shapes:
                                if isinstance(shape, dict) and all(key in shape for key in ["label", "points"]):
                                    label = shape["label"]
                                    points = shape["points"]
                                    
                                    if len(points) >= 2:
                                        x_coords = [point[0] for point in points]
                                        y_coords = [point[1] for point in points]
                                        x = min(x_coords)
                                        y = min(y_coords)
                                        width = max(x_coords) - x
                                        height = max(y_coords) - y
                                        
                                        detection_boxes.append({
                                            "x": x,
                                            "y": y,
                                            "width": width,
                                            "height": height,
                                            "label": label
                                        })
            except Exception as e:
                print(f"加载检测框文件失败：{e}")
        
        return detection_boxes
    
    def load_image_by_index(self, index):
        """加载指定索引的图片"""
        if 0 <= index < len(self.background_images):
            file_path = self.background_images[index]
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                self.current_background = pixmap
                
                if index in self.detection_boxes_dict and len(self.detection_boxes_dict[index]) > 0:
                    self.detection_boxes = self.detection_boxes_dict[index].copy()
                else:
                    self.detection_boxes = self.load_detection_boxes(file_path)
                    self.detection_boxes_dict[index] = self.detection_boxes.copy()
                
                self.canvas.background_scale = 1.0
                self.canvas.background_offset = QPoint(0, 0)
                self.canvas.is_manual_scale = False
                self.update_label_list()
                self.canvas.update()
            else:
                print(f"警告: 图片加载失败或为空: {file_path}")
    
    def select_background(self, item):
        """选择背景图"""
        if self._busy:
            return
        try:
            if item is None:
                return
            index = item.data(Qt.UserRole)
            if index is None:
                return
            
            # 保存当前状态
            if self.current_background_index >= 0:
                self.canvas_items_dict[self.current_background_index] = self.canvas_items.copy()
                self.detection_boxes_dict[self.current_background_index] = self.detection_boxes.copy()
                background_path = self.background_images[self.current_background_index]
                background_name = os.path.basename(background_path)
                self.save_json(background_path, background_name, "", canvas_items=[])
            
            self.current_background_index = index
            
            if index not in self.canvas_items_dict:
                self.canvas_items_dict[index] = []
            self.canvas_items = self.canvas_items_dict[index].copy()
            
            if 0 <= index < len(self.background_images):
                file_path = self.background_images[index]
                pixmap = QPixmap(file_path)
                if not pixmap.isNull():
                    self.current_background = pixmap
                    
                    if index in self.detection_boxes_dict and len(self.detection_boxes_dict[index]) > 0:
                        self.detection_boxes = self.detection_boxes_dict[index].copy()
                    else:
                        self.detection_boxes = self.load_detection_boxes(file_path)
                        self.detection_boxes_dict[index] = self.detection_boxes.copy()
                else:
                    self.current_background = None
                    self.detection_boxes = []
            
            self.update_label_list()
            self.canvas.background_scale = 1.0
            self.canvas.background_offset = QPoint(0, 0)
            self.canvas.is_manual_scale = False
            self.selected_item = None
            self.canvas.update()
            
            total = len(self.background_images)
            if total > 0:
                current = index + 1
                self.file_count_label.setText(f"[ {current} / {total} ]")
                self.file_count_label.show()
            else:
                self.file_count_label.hide()
        except Exception as e:
            import traceback
            error_msg = "".join(traceback.format_exc())
            self._log_error(f"select_background 错误: {e}\n{error_msg}")
    
    def update_file_count(self):
        """更新文件计数显示"""
        total = len(self.background_images)
        if total > 0:
            current = self.current_background_index + 1 if self.current_background_index >= 0 else 1
            self.file_count_label.setText(f"[ {current} / {total} ]")
            self.file_count_label.show()
        else:
            self.file_count_label.hide()
    
    def _log_error(self, message):
        """记录错误信息"""
        try:
            from datetime import datetime
            log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash_log.txt")
            with open(log_path, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] {message}\n")
        except Exception:
            pass  # 忽略日志写入错误
    
    def label_list_item_pressed(self, item):
        """标签列表按下项目 - 记录按下的标签用于高亮检测框"""
        try:
            if item is None:
                return
            item_text = item.text()
            # 从文本中提取纯标签名称，去掉个数后缀如 "(5)"
            if " (" in item_text:
                self.pressed_label = item_text.split(" (")[0]
            else:
                self.pressed_label = item_text
            # 触发画布重绘，显示对应的检测框高亮
            self.canvas.update()
        except Exception as e:
            import traceback
            error_msg = "".join(traceback.format_exc())
            self._log_error(f"label_list_item_pressed 错误: {e}\n{error_msg}")
    
    def label_list_item_clicked(self, item):
        """标签列表点击项目释放 - 清除高亮"""
        try:
            self.pressed_label = None
            self.canvas.update()
        except Exception as e:
            import traceback
            error_msg = "".join(traceback.format_exc())
            self._log_error(f"label_list_item_clicked 错误: {e}\n{error_msg}")
    
    def on_labels_checkbox_changed(self):
        """标签复选框变化"""
        self.canvas.update()
    
    def update_global_labels(self):
        """更新全局标签列表"""
        self.label_manager.update_global_labels()

    def update_label_list(self):
        """更新标签列表显示"""
        self.label_manager.update_label_list()

    # 贴图相关方法
    
    def add_small_to_canvas(self, item):
        """添加贴图到画布"""
        if self._busy:
            return
        index = item.data(Qt.UserRole)
        pixmap = self.small_images[index][1]
        
        if self.current_background is None:
            return
        
        # 计算初始大小和位置
        base_scale_factor = 0.5 * self.canvas.background_scale
        scale_factor = max(0.1, min(base_scale_factor, 2.0))
        
        width = pixmap.width() * scale_factor
        height = pixmap.height() * scale_factor
        
        # 确保最小边不小于 35
        aspect_ratio = width / height
        if width < height:
            width = 35
            height = width / aspect_ratio
        else:
            height = 35
            width = height * aspect_ratio
        
        # 放在背景图中心
        bg_width = self.current_background.width()
        bg_height = self.current_background.height()
        x = max(0, (bg_width - width) / 2)
        y = max(0, (bg_height - height) / 2)
        
        rect = QRectF(x, y, width, height)
        paste_label = self._get_paste_label(index)
        
        self.canvas_items.append((pixmap, rect, paste_label))
        self.canvas.update()
    
    def _get_paste_label(self, index):
        """获取贴图标签"""
        paste_label = "paste"
        
        if hasattr(self, 'auto_label_checkbox') and self.auto_label_checkbox.isChecked():
            image_path = self.small_images[index][0]
            image_name = os.path.basename(image_path)
            label_part = image_name.split('_')[0]
            label_part = os.path.splitext(label_part)[0]
            
            if label_part:
                paste_label = label_part
                
                # 检查标签是否存在
                label_exists = False
                for i in range(self.paste_label_list.count()):
                    existing_label = self.paste_label_list.item(i).text()
                    pure_label = extract_label_name(existing_label)
                    if pure_label == paste_label:
                        label_exists = True
                        break
                
                if not label_exists:
                    self.paste_label_list.addItem(paste_label)
        
        elif hasattr(self, 'paste_label_list'):
            if self.paste_label_list.count() == 0:
                self.paste_label_list.addItem("paste")
            else:
                selected_items = self.paste_label_list.selectedItems()
                if selected_items:
                    paste_label = selected_items[0].text()
                else:
                    paste_label = self.paste_label_list.item(0).text()
        
        return paste_label
    
    def clear_canvas(self):
        """清空画布"""
        if self._busy:
            return
        self.canvas_items.clear()
        if self.current_background_index >= 0:
            self.canvas_items_dict[self.current_background_index] = self.canvas_items.copy()
        self.selected_item = None
        self.canvas.update()
    
    def random_paste_images(self, background=None, detection_boxes=None):
        """随机贴图"""
        import random
        
        if not self.small_images or not self.current_background:
            return
        
        # 验证尺寸范围，确保最小值 < 最大值
        self._validate_size_range()
        
        current_background = background if background else self.current_background
        current_detection_boxes = detection_boxes if detection_boxes else self.detection_boxes
        
        self.canvas_items.clear()
        
        # 获取检测框
        boxes = []
        for box in current_detection_boxes:
            boxes.append((box['x'], box['y'], box['x'] + box['width'], box['y'] + box['height']))
        
        num_paste = self.paste_count_spin.value()
        selected_indices = random.choices(range(len(self.small_images)), k=num_paste)
        
        pasted_boxes = []
        
        for idx in selected_indices:
            file_path, pixmap = self.small_images[idx]
            
            # 计算大小
            aspect_ratio = pixmap.width() / pixmap.height()
            min_size = self.min_size_spin.value()
            max_size = self.max_size_spin.value()
            target_size = random.randint(min_size, max_size)
            
            if pixmap.width() > pixmap.height():
                new_width = target_size
                new_height = new_width / aspect_ratio
            else:
                new_height = target_size
                new_width = new_height * aspect_ratio
            
            # 确保最小尺寸
            if min(new_width, new_height) < min_size:
                if new_width < new_height:
                    new_width = min_size
                    new_height = new_width / aspect_ratio
                else:
                    new_height = min_size
                    new_width = new_height * aspect_ratio
            
            # 寻找有效位置
            max_x = max(50, min(current_background.width() - new_width, current_background.width() - 100))
            max_y = max(200, current_background.height() - new_height)
            
            valid_position = False
            x, y = 50, 50
            
            # 背景图太小无法放置贴图时跳过
            if max_x <= 50 or max_y <= 200:
                continue
            
            for _ in range(RANDOM_POSITION_CONFIG['max_retries']):
                x = random.randint(50, int(max_x))
                y = random.randint(200, int(max_y))
                
                new_box = (x, y, x + new_width, y + new_height)
                
                # 检查与检测框重叠
                overlap = False
                for box in boxes:
                    iou = calculate_iou(new_box, box)
                    if iou > RANDOM_POSITION_CONFIG['overlap_iou_detection']:
                        overlap = True
                        break
                
                if overlap:
                    continue
                
                # 检查与已贴图重叠
                iou_ok = True
                for pasted_box in pasted_boxes:
                    iou = calculate_iou(new_box, pasted_box)
                    if iou > RANDOM_POSITION_CONFIG['overlap_iou_pasted']:
                        iou_ok = False
                        break
                
                if iou_ok:
                    valid_position = True
                    break
            
            if valid_position:
                rect = QRectF(x, y, new_width, new_height)
                paste_label = self._get_paste_label(idx)
                self.canvas_items.append((pixmap, rect, paste_label))
                pasted_boxes.append(new_box)
        
        if not background:
            self.canvas.update()
        
        if self.current_background_index >= 0:
            self.canvas_items_dict[self.current_background_index] = self.canvas_items.copy()
    
    def batch_paste_images(self):
        """从当前图片开始依次处理所有图片，应用随机贴图，然后返回当前图片"""
        if not self.small_images:
            return
        
        if not self.background_images:
            return
        
        # 创建进度条对话框
        total_count = len(self.background_images)
        start_index = self.current_background_index if self.current_background_index >= 0 else 0
        process_count = total_count - start_index
        
        progress_dialog = QProgressDialog("正在一键贴图...", "取消", 0, process_count, self)
        progress_dialog.setWindowTitle("一键贴图进度")
        progress_dialog.setMinimumWidth(400)
        progress_dialog.setModal(True)
        # 设置进度条样式
        progress_dialog.setStyleSheet("""
            QProgressDialog {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 12px;
            }
            QProgressBar {
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                background-color: #F5F5F5;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-radius: 6px;
            }
            QPushButton {
                background-color: #E3F2FD;
                border: 1px solid #2196F3;
                border-radius: 8px;
                padding: 4px 12px;
                font-size: 12px;
                color: #1976D2;
            }
            QPushButton:hover {
                background-color: #BBDEFB;
            }
        """)
        
        # 居中显示
        screen_geometry = QApplication.desktop().screenGeometry()
        dialog_geometry = progress_dialog.geometry()
        x = (screen_geometry.width() - dialog_geometry.width()) // 2
        y = (screen_geometry.height() - dialog_geometry.height()) // 2
        progress_dialog.move(x, y)
        
        # 显示进度条
        progress_dialog.show()
        
        # 保存当前状态
        original_index = self.current_background_index
        original_background = self.current_background
        original_detection_boxes = self.detection_boxes.copy()
        original_canvas_items = self.canvas_items.copy()
        
        # 从当前图片开始处理所有图片
        processed_count = 0
        
        for i in range(start_index, total_count):
            # 检查是否取消
            if progress_dialog.wasCanceled():
                break
            
            # 加载图片（仅用于获取尺寸和检测框，不更新UI）
            file_path = self.background_images[i]
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                # 加载对应图片的检测框
                if i in self.detection_boxes_dict and len(self.detection_boxes_dict[i]) > 0:
                    temp_detection_boxes = self.detection_boxes_dict[i].copy()
                else:
                    temp_detection_boxes = self.load_detection_boxes(file_path)
                    self.detection_boxes_dict[i] = temp_detection_boxes.copy()
                
                # 临时设置索引
                self.current_background_index = i
                self.canvas_items = self.canvas_items_dict.get(i, []).copy()
                
                # 应用随机贴图（使用临时背景和检测框）
                self.random_paste_images(background=pixmap, detection_boxes=temp_detection_boxes)
                
                # 保存贴图状态
                self.canvas_items_dict[i] = self.canvas_items.copy()
                
                processed_count += 1
                
                # 更新进度
                progress_dialog.setValue(processed_count)
                progress_dialog.setLabelText(f"正在处理第 {i+1} 张图片，共 {total_count} 张")
                
                # 处理事件，确保进度条更新
                QApplication.processEvents()
        
        # 完成进度
        progress_dialog.setValue(process_count)
        
        # 恢复原始状态
        if original_index >= 0:
            self.current_background_index = original_index
            self.current_background = original_background
            self.detection_boxes = original_detection_boxes
            # 从canvas_items_dict中获取当前图片的最新状态，而不是恢复原始状态
            self.canvas_items = self.canvas_items_dict.get(original_index, []).copy()
            self.canvas.update()

    # 保存相关方法
    
    def get_save_info(self):
        """获取保存信息"""
        if self.current_background is None or self.current_background_index < 0:
            return None
        
        original_file_path = self.background_images[self.current_background_index]
        original_file_name = os.path.basename(original_file_path)
        
        background_dir = os.path.dirname(original_file_path)
        output_dir = f"{background_dir}_paste_output"
        os.makedirs(output_dir, exist_ok=True)
        
        prefix = ""
        if hasattr(self, 'prefix_checkbox') and self.prefix_checkbox.isChecked():
            prefix = self.prefix_input.text().strip()
            if not prefix:
                prefix = "paste"
        
        base_name = f"{prefix}_{original_file_name}" if prefix else original_file_name
        file_path = os.path.join(output_dir, base_name)
        
        return (file_path, base_name, prefix)
    
    def auto_save_current_canvas(self):
        """自动保存当前画布"""
        self.save_manager.auto_save_current_canvas()
    
    def save_canvas(self):
        """保存当前画布"""
        self.save_manager.save_canvas()
    def save_all_canvas(self):
        """保存所有画布"""
        self.save_manager.save_all_canvas()
    
    def save_json(self, image_path, image_name, label_prefix, canvas_items=None, 
                 image_width=None, image_height=None, current_index=None):
        """生成并保存 JSON 文件"""
        self.save_manager.save_json(
            image_path, image_name, label_prefix,
            canvas_items, image_width, image_height, current_index
        )
    
    def add_label(self, label_name=None):
        """增加标签"""
        self.label_manager.add_label(label_name)
    
    def delete_label(self):
        """删除标签"""
        self.label_manager.delete_label()
    def keyPressEvent(self, event):
        """键盘按下事件"""
        if event.key() == Qt.Key_A:
            self.switch_background(-1)
        elif event.key() == Qt.Key_D:
            self.switch_background(1)
        elif event.key() == Qt.Key_R:
            current_state = self.show_labels_checkbox.isChecked()
            self.show_labels_checkbox.setChecked(not current_state)
            self.on_labels_checkbox_changed()
        elif event.key() == Qt.Key_T:
            if hasattr(self, 'show_label_names_checkbox'):
                current_state = self.show_label_names_checkbox.isChecked()
                self.show_label_names_checkbox.setChecked(not current_state)
                self.on_labels_checkbox_changed()
        elif event.key() == Qt.Key_W:
            self.toggle_draw_mode()
        elif event.key() == Qt.Key_Q:
            if self.canvas.is_drawing_box:
                self.canvas.is_drawing_box = False
                self.canvas.draw_start_pos = None
                self.canvas.temp_draw_box = None
                self.canvas.setCursor(Qt.ArrowCursor)
                if hasattr(self, 'draw_box_btn'):
                    self.draw_box_btn.setText("绘制 BOX(W)")
                self.canvas.update()
        elif event.key() == Qt.Key_Delete or event.key() == Qt.Key_E:
            if self.canvas.selected_box is not None and 0 <= self.canvas.selected_box < len(self.detection_boxes):
                del self.detection_boxes[self.canvas.selected_box]
                self.canvas.selected_box = None
                if self.current_background_index >= 0:
                    self.detection_boxes_dict[self.current_background_index] = self.detection_boxes.copy()
                self.update_label_list()
                self.canvas.update()
                
                if self.current_background and self.current_background_index >= 0:
                    background_path = self.background_images[self.current_background_index]
                    background_name = os.path.basename(background_path)
                    self.save_json(background_path, background_name, "", canvas_items=[])
        elif event.key() == Qt.Key_G:
            current_state = self.auto_save_checkbox.isChecked()
            self.auto_save_checkbox.setChecked(not current_state)
            self.auto_save_current_canvas()
        
        super().keyPressEvent(event)
    
    def installEventFilterRecursive(self, widget):
        """递归安装事件过滤器"""
        widget.installEventFilter(self)
        for child in widget.children():
            self.installEventFilterRecursive(child)
    
    def eventFilter(self, obj, event):
        """事件过滤器"""
        if event.type() == QEvent.KeyPress:
            key = event.key()
            if key == Qt.Key_A:
                self.switch_background(-1)
                return True
            elif key == Qt.Key_D:
                self.switch_background(1)
                return True
        return super().eventFilter(obj, event)
    
    def toggle_draw_mode(self):
        """切换绘制模式"""
        if not self.background_images or self.current_background_index < 0:
            return
        
        if not self.canvas.is_drawing_box:
            self.canvas.is_drawing_box = True
            self.canvas.setCursor(Qt.CrossCursor)
            
            self.selected_item = None
            self.canvas.selected_box = None
            
            self.canvas.setFocus()
            self.canvas.update()
    
    def switch_background(self, direction):
        """切换背景图"""
        if not self.background_images:
            return
        
        # 自动保存
        if hasattr(self, 'auto_save_checkbox') and self.auto_save_checkbox.isChecked():
            if self.canvas_items:
                self.auto_save_current_canvas()
        
        # 保存当前状态
        if self.current_background_index >= 0:
            self.canvas_items_dict[self.current_background_index] = self.canvas_items.copy()
            self.detection_boxes_dict[self.current_background_index] = self.detection_boxes.copy()
        
        new_index = self.current_background_index + direction
        new_index = max(0, min(new_index, len(self.background_images) - 1))
        
        if new_index == self.current_background_index:
            return
        
        self.current_background_index = new_index
        
        file_path = self.background_images[new_index]
        pixmap = QPixmap(file_path)
        if not pixmap.isNull():
            self.current_background = pixmap
            
            if new_index in self.detection_boxes_dict and len(self.detection_boxes_dict[new_index]) > 0:
                self.detection_boxes = self.detection_boxes_dict[new_index].copy()
            else:
                self.detection_boxes = self.load_detection_boxes(file_path)
                self.detection_boxes_dict[new_index] = self.detection_boxes.copy()
        else:
            self.current_background = None
            self.detection_boxes = []
        
        if new_index not in self.canvas_items_dict:
            self.canvas_items_dict[new_index] = []
        self.canvas_items = self.canvas_items_dict[new_index].copy()
        
        self.update_label_list()
        self.canvas.background_scale = 1.0
        self.canvas.background_offset = QPoint(0, 0)
        self.canvas.is_manual_scale = False
        
        self.background_list.setCurrentRow(new_index)
        self.update_file_count()
        self.selected_item = None
        self.canvas.update()

    def closeEvent(self, event):
        """关闭窗口事件 - 直接关闭，不弹确认框"""
        event.accept()


# 程序入口
def main():
    """程序入口函数"""
    import sys
    import warnings
    
    # 忽略废弃警告
    warnings.simplefilter("ignore", DeprecationWarning)
    
    app = QApplication(sys.argv)
    editor = ImageEditor()
    editor.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
