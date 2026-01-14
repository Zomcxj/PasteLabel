import sys
import warnings

# 忽略所有废弃警告，特别是 sipPyTypeDict 相关的警告
warnings.simplefilter("ignore", DeprecationWarning)

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QListWidget, QListWidgetItem,
    QSplitter, QMessageBox, QScrollArea, QLineEdit, QCheckBox, QSpinBox,
    QMenu, QInputDialog, QAction, QDialog
)
from PyQt5.QtGui import QPixmap, QPainter, QColor, QBrush, QPen, QIcon, QImage
from PyQt5.QtCore import Qt, QPoint, QPointF, QRectF, QSizeF, QThread, pyqtSignal, QEvent
import os
import re

# class ImageLoaderThread(QThread):
#     """后台线程类，用于加载图片和检测框文件"""
#     progress_signal = pyqtSignal(int, int)  # 当前进度，总进度
#     finished_signal = pyqtSignal(list)  # 加载完成信号，传递加载结果
    
#     def __init__(self, file_paths):
#         super().__init__()
#         self.file_paths = file_paths
    
#     def run(self):
#         """线程运行方法"""
#         results = []  # 存储加载结果：(file_path, pixmap, detection_boxes)
#         total = len(self.file_paths)
#         for i, file_path in enumerate(self.file_paths):
#             # 加载图片
#             pixmap = QPixmap(file_path)
#             if not pixmap.isNull():
#                 # 加载检测框文件
#                 detection_boxes = self.load_detection_boxes(file_path)
#                 results.append((file_path, pixmap, detection_boxes))
#             # 发送进度信号
#             self.progress_signal.emit(i + 1, total)
#         # 发送完成信号
#         self.finished_signal.emit(results)
    
#     def load_detection_boxes(self, file_path):
#         """加载背景图对应的检测框json文件"""
#         import json
        
#         # 生成json文件路径
#         base_name = os.path.splitext(file_path)[0]
#         json_path = f"{base_name}.json"
        
#         detection_boxes = []
        
#         # 检查json文件是否存在
#         if os.path.exists(json_path):
#             try:
#                 with open(json_path, 'r', encoding='utf-8') as f:
#                     data = json.load(f)
                    
#                     # 检查是否为Labelme格式的JSON文件
#                     if isinstance(data, dict) and "shapes" in data:
#                         shapes = data["shapes"]
#                         if isinstance(shapes, list):
#                             for shape in shapes:
#                                 if isinstance(shape, dict) and all(key in shape for key in ["label", "points"]):
#                                     label = shape["label"]
#                                     points = shape["points"]
                                    
#                                     # 对于矩形类型的标注，计算x, y, width, height
#                                     if len(points) >= 2:
#                                         # 计算边界框的最小和最大坐标
#                                         x_coords = [point[0] for point in points]
#                                         y_coords = [point[1] for point in points]
#                                         x = min(x_coords)
#                                         y = min(y_coords)
#                                         width = max(x_coords) - x
#                                         height = max(y_coords) - y
                                        
#                                         detection_boxes.append({
#                                             "x": x,
#                                             "y": y,
#                                             "width": width,
#                                             "height": height,
#                                             "label": label
#                                         })
#             except Exception as e:
#                 print(f"加载检测框文件失败: {e}")
        
#         return detection_boxes

class ImageEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("贴图标注工具")
        self.resize(1600, 1000)  # 1300 800
        
        # 设置窗口图标
        self.setWindowIcon(self.create_app_icon())
        
        # 初始化数据
        self.background_images = []
        self.current_background = None
        self.current_background_index = -1  # 当前背景图索引
        self.small_images = []
        self.canvas_items_dict = {}  # 存储每个背景图的小图状态，key为背景图索引
        self.canvas_items = []  # 当前背景图的小图列表
        self.selected_item = None
        self.is_dragging = False
        self.is_resizing = False
        self.drag_offset = QPoint(0, 0)

        self.detection_boxes_dict = {}  # 存储每个背景图的检测框信息，key为背景图索引
        self.detection_boxes = []  # 当前背景图的检测框列表
        self.global_labels = set()  # 全局标签列表，包含所有背景图的标签
        
        # 创建UI
        self.init_ui()
        
        # 初始化标签列表
        self.update_label_list()
        
        # 为所有子控件安装事件过滤器，确保在任何地方都能响应键盘事件
        self.installEventFilterRecursive(self)
    
    @staticmethod
    def natural_sort_key(s):
        """自然排序键函数，用于正确处理数字和字母的混合排序"""
        def convert(text):
            return int(text) if text.isdigit() else text.lower()
        return [convert(c) for c in re.split('([0-9]+)', s)]
    
    def init_ui(self):
        # 主布局
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # 上传区域
        upload_layout = QHBoxLayout()
        
        # 获取图标路径
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_icon_path = os.path.join(script_dir, "ico_image/file-os.png")
        folder_icon_path = os.path.join(script_dir, "ico_image/folders.png")
        
        # 背景图上传
        self.upload_a_btn = QPushButton("")
        if os.path.exists(file_icon_path):
            self.upload_a_btn.setIcon(QIcon(file_icon_path))
        self.upload_a_btn.clicked.connect(self.upload_background)
        self.upload_a_btn.setMaximumWidth(40)
        self.upload_a_btn.setStyleSheet("background-color: transparent; border: none;")
        upload_layout.addWidget(QLabel("背景图上传:"))
        upload_layout.addWidget(self.upload_a_btn)
        
        # 添加文件夹加载按钮
        upload_layout.addSpacing(5)
        self.load_folder_btn = QPushButton("")
        if os.path.exists(folder_icon_path):
            self.load_folder_btn.setIcon(QIcon(folder_icon_path))
        self.load_folder_btn.clicked.connect(self.load_folder_images)
        self.load_folder_btn.setMaximumWidth(40)
        self.load_folder_btn.setStyleSheet("background-color: transparent; border: none;")
        upload_layout.addWidget(self.load_folder_btn)
        
        # 添加间距
        upload_layout.addSpacing(10)
        
        # 贴图上传
        self.upload_b_btn = QPushButton("")
        if os.path.exists(file_icon_path):
            self.upload_b_btn.setIcon(QIcon(file_icon_path))
        self.upload_b_btn.clicked.connect(self.upload_small_images)
        self.upload_b_btn.setMaximumWidth(40)
        self.upload_b_btn.setStyleSheet("background-color: transparent; border: none;")
        upload_layout.addWidget(QLabel("贴图上传:"))
        upload_layout.addWidget(self.upload_b_btn)
        
        # 添加贴图文件夹加载按钮
        upload_layout.addSpacing(5)
        self.load_small_folder_btn = QPushButton("")
        if os.path.exists(folder_icon_path):
            self.load_small_folder_btn.setIcon(QIcon(folder_icon_path))
        self.load_small_folder_btn.clicked.connect(self.load_small_folder_images)
        self.load_small_folder_btn.setMaximumWidth(40)
        self.load_small_folder_btn.setStyleSheet("background-color: transparent; border: none;")
        upload_layout.addWidget(self.load_small_folder_btn)
        
        # 添加分隔符
        upload_layout.addSpacing(5)
        separator_label = QLabel("|")
        separator_label.setStyleSheet("color: gray; font-weight: bold;")
        upload_layout.addWidget(separator_label)
        
        # 添加绘制检测框按钮
        upload_layout.addSpacing(5)
        self.draw_box_btn = QPushButton("绘制BOX(W)")
        self.draw_box_btn.clicked.connect(self.toggle_draw_mode)
        self.draw_box_btn.setMaximumWidth(90)
        upload_layout.addWidget(self.draw_box_btn)

        # 添加标签显示复选框
        upload_layout.addSpacing(5)
        self.show_labels_checkbox = QCheckBox("显示BOX(R)")
        self.show_labels_checkbox.setChecked(False)
        self.show_labels_checkbox.stateChanged.connect(self.on_labels_checkbox_changed)
        upload_layout.addWidget(self.show_labels_checkbox)
        
        # 添加显示类别名复选框
        upload_layout.addSpacing(5)
        self.show_label_names_checkbox = QCheckBox("显示Label(T)")
        self.show_label_names_checkbox.setChecked(True)
        self.show_label_names_checkbox.stateChanged.connect(self.on_labels_checkbox_changed)
        upload_layout.addWidget(self.show_label_names_checkbox)
        
        # 添加分隔符
        upload_layout.addSpacing(5)
        separator_label = QLabel("|")
        separator_label.setStyleSheet("color: gray; font-weight: bold;")
        upload_layout.addWidget(separator_label)
        
        # 添加图片名前缀输入框
        upload_layout.addSpacing(5)
        self.prefix_label = QLabel("结果命名前缀:")
        upload_layout.addWidget(self.prefix_label)
        self.prefix_input = QLineEdit()
        # 设置默认前缀为 "paste" 并灰度显示
        self.default_prefix = "paste"
        self.prefix_input.setText(self.default_prefix)
        self.prefix_input.setStyleSheet("color: gray;")
        # 连接焦点事件
        self.prefix_input.focusInEvent = self.on_prefix_input_focus_in
        self.prefix_input.focusOutEvent = self.on_prefix_input_focus_out
        self.prefix_input.setMaximumWidth(80)
        upload_layout.addWidget(self.prefix_input)
        

        
        # 右侧添加拉伸空间
        upload_layout.addStretch()
        main_layout.addLayout(upload_layout)
        
        # 工作区 - 分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧画布区域
        canvas_widget = QWidget()
        canvas_layout = QVBoxLayout(canvas_widget)
        self.canvas = Canvas(self)
        canvas_scroll = QScrollArea()
        canvas_scroll.setWidget(self.canvas)
        canvas_scroll.setWidgetResizable(True)
        canvas_layout.addWidget(canvas_scroll)
        splitter.addWidget(canvas_widget)
        
        # 右侧控制面板
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)
        
        # 背景图片列表
        background_list_layout = QHBoxLayout()
        background_list_layout.addWidget(QLabel("背景图列表"))
        # 添加文件列表总数显示（在背景图列表文字同一行）
        self.file_count_label = QLabel()
        self.file_count_label.hide()  # 默认隐藏
        background_list_layout.addWidget(self.file_count_label)
        background_list_layout.addStretch()
        control_layout.addLayout(background_list_layout)
        
        self.background_list = QListWidget()
        self.background_list.itemClicked.connect(self.select_background)
        control_layout.addWidget(self.background_list)
        
        # 背景图标签列表和贴图标签列表
        label_layout = QHBoxLayout()
        
        # 背景图标签列表
        original_label_layout = QVBoxLayout()
        original_label_header = QHBoxLayout()
        original_label_header.addWidget(QLabel("背景图标签"))
        original_label_header.addStretch()
        original_label_layout.addLayout(original_label_header)
        
        self.label_list = QListWidget()
        self.label_list.setMinimumHeight(150)
        # 为背景图标签列表添加右键菜单
        self.label_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.label_list.customContextMenuRequested.connect(self.show_label_context_menu)
        # 为背景图标签列表添加鼠标按下和松开事件处理
        self.label_list.mousePressEvent = self.label_list_mouse_press
        self.label_list.mouseReleaseEvent = self.label_list_mouse_release
        # 记录当前按下的标签
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
        # 为贴图标签列表添加右键菜单
        self.paste_label_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.paste_label_list.customContextMenuRequested.connect(self.show_paste_label_context_menu)
        # 添加默认的"paste"标签
        default_paste_label = QListWidgetItem("paste")
        self.paste_label_list.addItem(default_paste_label)
        paste_label_layout.addWidget(self.paste_label_list)
        
        # 将两个标签列表添加到水平布局
        label_layout.addLayout(original_label_layout)
        label_layout.addLayout(paste_label_layout)
        label_layout.setStretch(0, 1)
        label_layout.setStretch(1, 1)
        control_layout.addLayout(label_layout)
        
        # 贴图片列表
        small_list_layout = QHBoxLayout()
        small_list_layout.addWidget(QLabel("贴图列表"))
        # 添加随机贴图按钮
        self.random_paste_btn = QPushButton("随机贴图")
        self.random_paste_btn.clicked.connect(self.random_paste_images)
        self.random_paste_btn.setMinimumWidth(50)
        small_list_layout.addWidget(self.random_paste_btn)
        # 添加一键贴图按钮
        self.batch_paste_btn = QPushButton("一键贴图")
        self.batch_paste_btn.clicked.connect(self.batch_paste_images)
        self.batch_paste_btn.setMinimumWidth(50)
        small_list_layout.addWidget(self.batch_paste_btn)
        # 添加贴图个数输入框
        small_list_layout.addWidget(QLabel("个数:"))
        self.paste_count_spin = QSpinBox()
        self.paste_count_spin.setMinimum(1)
        self.paste_count_spin.setMaximum(20)
        self.paste_count_spin.setMinimumWidth(50)
        small_list_layout.addWidget(self.paste_count_spin)
        small_list_layout.addStretch()
        control_layout.addLayout(small_list_layout)
        self.small_list = QListWidget()
        self.small_list.itemClicked.connect(self.add_small_to_canvas)
        control_layout.addWidget(self.small_list)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        self.clear_btn = QPushButton("清空画布")
        self.clear_btn.clicked.connect(self.clear_canvas)
        self.save_btn = QPushButton("保存图片")
        self.save_btn.clicked.connect(self.save_canvas)
        self.save_all_btn = QPushButton("全部保存")
        self.save_all_btn.clicked.connect(self.save_all_canvas)
        button_layout.addWidget(self.clear_btn)
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.save_all_btn)
        control_layout.addLayout(button_layout)
        
        splitter.addWidget(control_widget)
        # 设置分割器拉伸因子，右侧控制面板宽度固定
        splitter.setStretchFactor(0, 1)  # 左侧画布区域可拉伸
        splitter.setStretchFactor(1, 0)  # 右侧控制面板宽度固定
        # 设置初始宽度
        splitter.setSizes([1000, 300])
        main_layout.addWidget(splitter)
        
        # 设置主布局的拉伸因子，确保工具栏只占用最小必要空间
        main_layout.setStretch(0, 0)  # upload_layout 的拉伸因子为0
        main_layout.setStretch(1, 1)  # 分割器的拉伸因子为1
        
        self.setCentralWidget(central_widget)
        
        # 使用QMainWindow的状态栏显示信息，不压缩画布区域
        self.status_label = QLabel("")
        self.statusBar().addWidget(self.status_label)
    
    def on_prefix_input_focus_in(self, event):
        """前缀输入框获得焦点时的处理"""
        if self.prefix_input.text() == self.default_prefix:
            self.prefix_input.setText("")
            self.prefix_input.setStyleSheet("color: black;")
        # 调用父类的focusInEvent
        QLineEdit.focusInEvent(self.prefix_input, event)
    
    def on_prefix_input_focus_out(self, event):
        """前缀输入框失去焦点时的处理"""
        if not self.prefix_input.text().strip():
            self.prefix_input.setText(self.default_prefix)
            self.prefix_input.setStyleSheet("color: gray;")
        else:
            self.prefix_input.setStyleSheet("color: black;")
        # 调用父类的focusOutEvent
        QLineEdit.focusOutEvent(self.prefix_input, event)
    
    def upload_background(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择背景图片", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if files:
            # 清空现有背景图列表
            self.background_images.clear()
            self.background_list.clear()
            self.current_background = None
            
            # 清空检测框字典和贴图状态字典
            self.detection_boxes_dict.clear()
            self.canvas_items_dict.clear()
            
            for file in files:
                pixmap = QPixmap(file)
                if not pixmap.isNull():
                    # 获取新添加背景图的索引
                    new_index = len(self.background_images)
                    self.background_images.append(file)
                    # 确保路径显示为全部反斜杠
                    display_path = file.replace('/', '\\')
                    item = QListWidgetItem(display_path)
                    item.setData(Qt.UserRole, new_index)
                    self.background_list.addItem(item)
                    
                    # 初始化该背景图的小图状态为空列表
                    self.canvas_items_dict[new_index] = []
                    
                    # 加载检测框文件
                    self.detection_boxes_dict[new_index] = self.load_detection_boxes(file)
                    
                    # 如果是第一张图片，自动设为当前背景
                    if self.current_background is None:
                        self.current_background = pixmap
                        self.current_background_index = new_index
                        self.canvas_items = []
                        self.detection_boxes = self.detection_boxes_dict[new_index].copy()
                        # 更新背景图标签列表
                        self.update_label_list()
                        # 重置背景图缩放比例，让新背景图自动适配画布
                        self.canvas.background_scale = 1.0
                        self.canvas.is_manual_scale = False  # 重置为自动适配模式
                        self.canvas.update()
        
        # 更新文件计数
        self.update_file_count()
    
    def update_file_count(self):
        """更新文件列表总数显示"""
        total = len(self.background_images)
        if total > 0:
            current = self.current_background_index + 1 if self.current_background_index >= 0 else 1
            self.file_count_label.setText(f"[ {current} / {total} ]")
            self.file_count_label.show()
        else:
            self.file_count_label.hide()
    
    def on_labels_checkbox_changed(self):
        """当检测框显示相关复选框状态变化时更新画布"""
        self.canvas.update()
    
    def load_detection_boxes(self, file_path):
        """加载背景图对应的检测框json文件"""
        import json
        
        # 生成json文件路径
        base_name = os.path.splitext(file_path)[0]
        json_path = f"{base_name}.json"
        
        detection_boxes = []
        
        # 检查json文件是否存在
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # 检查是否为Labelme格式的JSON文件
                    if isinstance(data, dict) and "shapes" in data:
                        shapes = data["shapes"]
                        if isinstance(shapes, list):
                            for shape in shapes:
                                if isinstance(shape, dict) and all(key in shape for key in ["label", "points"]):
                                    label = shape["label"]
                                    points = shape["points"]
                                    
                                    # 对于矩形类型的标注，计算x, y, width, height
                                    if len(points) >= 2:
                                        # 计算边界框的最小和最大坐标
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
                print(f"加载检测框文件失败: {e}")
        
        return detection_boxes
    
    def upload_small_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择贴图片", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if files:
            # 清空现有贴图列表
            self.small_images.clear()
            self.small_list.clear()
            
            for file in files:
                pixmap = QPixmap(file)
                if not pixmap.isNull():
                    self.small_images.append((file, pixmap))
                    # 只显示文件名而不是完整路径
                    file_name = os.path.basename(file)
                    item = QListWidgetItem(file_name)
                    item.setData(Qt.UserRole, len(self.small_images) - 1)
                    self.small_list.addItem(item)
        
        # 更新贴图个数输入框的默认值
        if hasattr(self, 'paste_count_spin'):
            if len(self.small_images) <= 5:
                self.paste_count_spin.setValue(len(self.small_images))
                self.paste_count_spin.setMaximum(len(self.small_images))
            else:
                self.paste_count_spin.setMaximum(len(self.small_images))
    
    def load_image_by_index(self, index):
        """加载指定索引的图片和检测框文件"""
        if 0 <= index < len(self.background_images):
            file_path = self.background_images[index]
            # 加载图片
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                self.current_background = pixmap
                # 优先从dict中获取检测框（保留用户绘制的标签）
                if index in self.detection_boxes_dict and len(self.detection_boxes_dict[index]) > 0:
                    self.detection_boxes = self.detection_boxes_dict[index].copy()
                else:
                    # 如果dict中没有或为空，从文件加载
                    self.detection_boxes = self.load_detection_boxes(file_path)
                    # 保存到dict
                    self.detection_boxes_dict[index] = self.detection_boxes.copy()
                # 重置画布状态
                self.canvas.background_scale = 1.0
                self.canvas.background_offset = QPoint(0, 0)
                self.canvas.is_manual_scale = False  # 重置为自动适配模式
                # 更新标签列表
                self.update_label_list()
                # 刷新画布
                self.canvas.update()

    def select_background(self, item):
        index = item.data(Qt.UserRole)
        
        # 保存当前背景图的状态
        if self.current_background_index >= 0:
            # 保存贴图状态
            self.canvas_items_dict[self.current_background_index] = self.canvas_items.copy()
            # 保存检测框状态
            self.detection_boxes_dict[self.current_background_index] = self.detection_boxes.copy()
            # 同步更新到原始json文件
            background_path = self.background_images[self.current_background_index]
            background_name = os.path.basename(background_path)
            self.save_json(background_path, background_name, "", canvas_items=[])
        
        # 切换到新的背景图
        self.current_background_index = index
        
        # 加载新背景图的贴图状态，如果不存在则初始化空列表
        if index not in self.canvas_items_dict:
            self.canvas_items_dict[index] = []
        self.canvas_items = self.canvas_items_dict[index].copy()
        
        # 加载图片和检测框
        file_path = self.background_images[index]
        pixmap = QPixmap(file_path)
        if not pixmap.isNull():
            self.current_background = pixmap
            # 优先从dict中获取检测框（保留用户绘制的标签）
            if index in self.detection_boxes_dict and len(self.detection_boxes_dict[index]) > 0:
                self.detection_boxes = self.detection_boxes_dict[index].copy()
            else:
                # 如果dict中没有或为空，从文件加载
                self.detection_boxes = self.load_detection_boxes(file_path)
                # 保存到dict
                self.detection_boxes_dict[index] = self.detection_boxes.copy()
        else:
            self.current_background = None
            self.detection_boxes = []
        
        # 更新标签列表
        self.update_label_list()
        
        # 重置背景图缩放比例，让新背景图自动适配画布
        self.canvas.background_scale = 1.0
        self.canvas.background_offset = QPoint(0, 0)
        self.canvas.is_manual_scale = False  # 重置为自动适配模式
        
        # 重置选择状态
        self.selected_item = None
        self.canvas.update()
        
        # 更新右侧序号显示
        total = len(self.background_images)
        if total > 0:
            current = self.current_background_index +1
            self.file_count_label.setText(f"[ {current} / {total} ]")
            self.file_count_label.show()
        else:
            self.file_count_label.hide()
    
    def show_label_context_menu(self, position):
        """显示标签列表的右键菜单"""
        menu = QMenu()
        
        # 获取当前选中的项
        selected_items = self.label_list.selectedItems()
        
        # 添加修改标签选项（只有当有选中项时才显示）
        if selected_items:
            modify_action = menu.addAction("修改标签")
            modify_action.triggered.connect(self.modify_label)
            
            # 添加删除标签选项
            delete_action = menu.addAction("删除标签")
            delete_action.triggered.connect(self.delete_label)
            
            # 添加分隔线
            menu.addSeparator()
        
        # 添加增加标签选项（无论是否有选中项都显示）
        add_action = menu.addAction("增加标签")
        add_action.triggered.connect(self.add_label)
        
        # 显示菜单
        menu.exec_(self.label_list.mapToGlobal(position))
    
    def show_paste_label_context_menu(self, position):
        """显示贴图标签列表的右键菜单"""
        menu = QMenu()
        
        # 获取当前选中的项
        selected_items = self.paste_label_list.selectedItems()
        
        # 添加修改标签选项（只有当有选中项时才显示）
        if selected_items:
            modify_action = menu.addAction("修改标签")
            modify_action.triggered.connect(self.modify_paste_label)
            
            # 添加删除标签选项
            delete_action = menu.addAction("删除标签")
            delete_action.triggered.connect(self.delete_paste_label)
            
            menu.addSeparator()
        
        # 添加增加标签选项
        add_action = menu.addAction("增加标签")
        add_action.triggered.connect(self.add_paste_label)
        
        # 显示菜单
        menu.exec_(self.paste_label_list.mapToGlobal(position))
    
    def add_paste_label(self):
        """增加贴图标签"""
        # 显示输入对话框，让用户输入新的标签名称
        label_name, ok = QInputDialog.getText(self, "增加贴图标签", "请输入新的贴图标签名称:")
        
        # 如果用户点击了确定，并且标签名称不为空
        if ok and label_name.strip():
            label_name = label_name.strip()
            
            # 检查标签是否与现有标签重复
            existing_labels = set()
            for i in range(self.paste_label_list.count()):
                existing_item_text = self.paste_label_list.item(i).text()
                existing_labels.add(existing_item_text)
            
            if label_name in existing_labels:
                QMessageBox.warning(self, "警告", "标签名称已存在，请输入不同的名称")
                return
            
            # 添加新标签到贴图标签列表
            item = QListWidgetItem(label_name)
            self.paste_label_list.addItem(item)
    
    def modify_paste_label(self):
        """修改贴图标签名称"""
        # 获取当前选中的项
        selected_items = self.paste_label_list.selectedItems()
        if not selected_items:
            return
        
        # 获取当前选中的标签
        old_label = selected_items[0].text()
        
        # 显示输入对话框，让用户输入新的标签名称
        new_label, ok = QInputDialog.getText(self, "修改贴图标签", f"请输入新的贴图标签名称:", text=old_label)
        
        # 如果用户点击了确定，并且新标签名称不为空
        if ok and new_label.strip():
            new_label = new_label.strip()
            
            # 检查新标签是否与现有标签重复
            existing_labels = set()
            for i in range(self.paste_label_list.count()):
                existing_item_text = self.paste_label_list.item(i).text()
                existing_labels.add(existing_item_text)
            
            if new_label in existing_labels and new_label != old_label:
                QMessageBox.warning(self, "警告", "标签名称已存在，请输入不同的名称")
                return
            
            # 更新标签名称
            selected_items[0].setText(new_label)
            
            # 同步修改图上所有使用该标签的贴图的标签
            for i in range(len(self.canvas_items)):
                pixmap, rect, label = self.canvas_items[i]
                if label == old_label:
                    self.canvas_items[i] = (pixmap, rect, new_label)
            
            # 更新所有背景图的贴图标签
            for i in range(len(self.background_images)):
                if i in self.canvas_items_dict:
                    updated_items = []
                    for pixmap, rect, label in self.canvas_items_dict[i]:
                        if label == old_label:
                            updated_items.append((pixmap, rect, new_label))
                        else:
                            updated_items.append((pixmap, rect, label))
                    self.canvas_items_dict[i] = updated_items
            
            # 更新画布
            self.canvas.update()
    
    def delete_paste_label(self):
        """删除贴图标签"""
        # 获取当前选中的项
        selected_items = self.paste_label_list.selectedItems()
        if not selected_items:
            return
        
        # 获取要删除的标签
        label_to_delete = selected_items[0].text()
        
        # 显示确认对话框
        reply = QMessageBox.question(self, "确认删除", f"确定要删除贴图标签 '{label_to_delete}' 吗？删除后，所有使用该标签的贴图也会被删除。",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 删除选中的标签
            for item in selected_items:
                self.paste_label_list.takeItem(self.paste_label_list.row(item))
            
            # 删除图上所有使用该标签的贴图
            new_canvas_items = []
            for pixmap, rect, label in self.canvas_items:
                if label != label_to_delete:
                    new_canvas_items.append((pixmap, rect, label))
            self.canvas_items = new_canvas_items
            
            # 删除所有背景图中使用该标签的贴图
            for i in range(len(self.background_images)):
                if i in self.canvas_items_dict:
                    updated_items = []
                    for pixmap, rect, label in self.canvas_items_dict[i]:
                        if label != label_to_delete:
                            updated_items.append((pixmap, rect, label))
                    self.canvas_items_dict[i] = updated_items
            
            # 更新画布
            self.canvas.update()
    
    def update_global_labels(self):
        """更新全局标签列表，收集所有背景图片的标签"""
        # 遍历所有背景图的检测框，收集所有标签
        for index in self.detection_boxes_dict:
            if index in self.detection_boxes_dict:
                for box in self.detection_boxes_dict[index]:
                    if "label" in box:
                        self.global_labels.add(box["label"])
    
    def update_label_list(self):
        """更新标签列表，显示全局标签列表"""
        # 首先更新全局标签列表
        self.update_global_labels()
        
        # 清空标签列表
        self.label_list.clear()
        
        # 如果没有当前背景图，直接返回
        if self.current_background is None:
            return
        
        # 从当前背景图的检测框中统计每个标签出现的次数
        label_counts = {}
        for box in self.detection_boxes:
            if "label" in box:
                label = box["label"]
                if label in label_counts:
                    label_counts[label] += 1
                else:
                    label_counts[label] = 1
        
        # 将标签和个数添加到标签列表，按计数降序排序
        # 创建一个列表，包含(标签, 计数)元组
        label_count_list = []
        for label in self.global_labels:
            count = label_counts.get(label, 0)
            label_count_list.append((label, count))
        
        # 按计数降序排序，如果计数相同则按标签名称排序
        label_count_list.sort(key=lambda x: (-x[1], x[0]))
        
        # 添加到标签列表
        for label, count in label_count_list:
            item = QListWidgetItem(f"{label} ({count})")
            self.label_list.addItem(item)
    
    def modify_label(self):
        """修改标签名称"""
        # 获取当前选中的项
        selected_items = self.label_list.selectedItems()
        if not selected_items:
            return
        
        # 获取当前选中的标签（从文本中提取纯标签名称，去掉个数后缀）
        item_text = selected_items[0].text()
        if " (" in item_text:
            old_label = item_text.split(" (")[0]
        else:
            old_label = item_text
        
        # 显示输入对话框，让用户输入新的标签名称
        new_label, ok = QInputDialog.getText(self, "修改标签", f"请输入新的标签名称:", text=old_label)
        
        # 如果用户点击了确定，并且新标签名称不为空
        if ok and new_label.strip():
            new_label = new_label.strip()
            
            # 检查新标签是否与现有标签重复
            existing_labels = set()
            for i in range(self.label_list.count()):
                existing_item_text = self.label_list.item(i).text()
                if " (" in existing_item_text:
                    existing_label = existing_item_text.split(" (")[0]
                else:
                    existing_label = existing_item_text
                existing_labels.add(existing_label)
            
            if new_label in existing_labels and new_label != old_label:
                QMessageBox.warning(self, "警告", "标签名称已存在，请输入不同的名称")
                return
            
            # 更新当前背景图的检测框中的标签
            for box in self.detection_boxes:
                if box["label"] == old_label:
                    box["label"] = new_label
            
            # 更新所有背景图的检测框中的标签
            for i in range(len(self.background_images)):
                if i in self.detection_boxes_dict:
                    updated_boxes = []
                    for box in self.detection_boxes_dict[i]:
                        if box["label"] == old_label:
                            updated_box = box.copy()
                            updated_box["label"] = new_label
                            updated_boxes.append(updated_box)
                        else:
                            updated_boxes.append(box)
                    self.detection_boxes_dict[i] = updated_boxes
            
            # 更新全局标签列表（替换旧标签为新标签）
            if old_label in self.global_labels:
                self.global_labels.remove(old_label)
            self.global_labels.add(new_label)
            
            # 更新标签列表
            self.update_label_list()
    
    def label_list_mouse_press(self, event):
        """标签列表鼠标按下事件处理"""
        # 调用原始的鼠标按下事件处理
        super(QListWidget, self.label_list).mousePressEvent(event)
        
        # 只处理左键点击，右键不需要触发橙色显示
        if event.button() == Qt.LeftButton:
            # 获取当前选中的项
            selected_items = self.label_list.selectedItems()
            if selected_items:
                # 获取当前选中的标签（从文本中提取纯标签名称，去掉个数后缀）
                item_text = selected_items[0].text()
                if " (" in item_text:
                    self.pressed_label = item_text.split(" (")[0]
                else:
                    self.pressed_label = item_text
                
                # 触发画布重绘，显示对应的检测框蒙版
                if hasattr(self, 'canvas'):
                    self.canvas.update()
    
    def label_list_mouse_release(self, event):
        """标签列表鼠标松开事件处理"""
        # 调用原始的鼠标松开事件处理
        super(QListWidget, self.label_list).mouseReleaseEvent(event)
        
        # 只处理左键点击，右键不需要触发橙色显示
        if event.button() == Qt.LeftButton:
            # 清除当前按下的标签
            self.pressed_label = None
            
            # 触发画布重绘，清除检测框蒙版
            if hasattr(self, 'canvas'):
                self.canvas.update()
    
    def delete_label(self):
        """删除标签"""
        # 获取当前选中的项
        selected_items = self.label_list.selectedItems()
        if not selected_items:
            return
        
        # 获取当前选中的标签（从文本中提取纯标签名称，去掉个数后缀）
        item_text = selected_items[0].text()
        if " (" in item_text:
            label_to_delete = item_text.split(" (")[0]
        else:
            label_to_delete = item_text
        
        # 显示确认对话框，让用户确认是否删除
        reply = QMessageBox.question(self, "确认删除", f"确定要删除标签 '{label_to_delete}' 吗？\n删除后，所有使用该标签的检测框也会被删除。",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        # 如果用户点击了是，删除标签
        if reply == QMessageBox.Yes:
            # 从当前背景图的检测框中移除该标签
            self.detection_boxes = [box for box in self.detection_boxes if box["label"] != label_to_delete]
            
            # 从所有背景图的检测框中移除该标签
            for i in range(len(self.background_images)):
                if i in self.detection_boxes_dict:
                    updated_boxes = [box for box in self.detection_boxes_dict[i] if box["label"] != label_to_delete]
                    self.detection_boxes_dict[i] = updated_boxes
            
            # 从全局标签列表中删除标签
            if label_to_delete in self.global_labels:
                self.global_labels.remove(label_to_delete)
            
            # 保存所有背景图的更新后的检测框到JSON文件
            for i, image_path in enumerate(self.background_images):
                if i in self.detection_boxes_dict:
                    image_name = os.path.basename(image_path)
                    # 调用save_json保存更新后的检测框，传入空的canvas_items确保不包含贴图信息
                    self.save_json(image_path, image_name, "", canvas_items=[], current_index=i)
            
            # 更新标签列表
            self.update_label_list()
            
            # 刷新画布
            self.canvas.update()
    
    def add_label(self, label_name=None):
        """增加新标签"""
        # 如果提供了标签名称，直接使用
        if label_name and label_name.strip():
            new_label = label_name.strip()
            ok = True
        else:
            # 否则显示输入对话框，让用户输入新的标签名称
            new_label, ok = QInputDialog.getText(self, "增加标签", "请输入新的标签名称:")
            
            # 如果用户点击了确定，并且新标签名称不为空
            if ok and new_label.strip():
                new_label = new_label.strip()
            else:
                ok = False
        
        # 如果用户确认添加标签
        if ok:
            # 检查新标签是否与现有标签重复
            existing_labels = set()
            for i in range(self.label_list.count()):
                existing_item_text = self.label_list.item(i).text()
                if " (" in existing_item_text:
                    existing_label = existing_item_text.split(" (")[0]
                else:
                    existing_label = existing_item_text
                existing_labels.add(existing_label)
            
            if new_label in existing_labels:
                QMessageBox.warning(self, "警告", "标签名称已存在，请输入不同的名称")
                return
            
            # 将新标签添加到全局标签列表
            self.global_labels.add(new_label)
            
            # 更新标签列表
            self.update_label_list()
    
    def add_small_to_canvas(self, item):
        index = item.data(Qt.UserRole)
        pixmap = self.small_images[index][1]
        
        if self.current_background is not None:
            # 贴图位置相对于背景图，放在左上角
            # 计算贴图的初始大小，考虑背景图缩放比例
            base_scale_factor = 0.5  # 基础缩放因子
            
            # 根据背景图缩放比例调整贴图大小，确保视觉上合适
            # 当背景图放大时，贴图也适当放大；背景图缩小时，贴图也适当缩小
            scale_factor = base_scale_factor * self.canvas.background_scale
            
            # 限制缩放因子范围，防止贴图过大或过小
            scale_factor = max(0.1, min(scale_factor, 2.0))
            
            width = pixmap.width() * scale_factor
            height = pixmap.height() * scale_factor
            
            # # 确保最小边不小于50，如果小于则等比缩放
            # if min(width, height) < 50:
            aspect_ratio = width / height
            if width < height:
                width = 50
                height = width / aspect_ratio
            else:
                height = 50
                width = height * aspect_ratio
            
            # 单击贴图默认位置为x=50 y=50，不需要IoU判断
            x = 50
            y = 50
            
            # 确保位置在背景图范围内
            max_x = self.current_background.width() - width
            max_y = self.current_background.height() - height
            x = min(x, max_x)
            y = min(y, max_y)
            x = max(0, x)
            y = max(0, y)
            # 创建矩形
            rect = QRectF(
                x, y,  # 相对于背景图的坐标
                width, height
            )
            # 使用默认标签"paste"或选中的贴图标签
            paste_label = "paste"
            if hasattr(self, 'paste_label_list'):
                # 检查贴图标签列表是否为空
                if self.paste_label_list.count() == 0:
                    # 如果为空，添加默认标签"paste"
                    self.paste_label_list.addItem("paste")
                    paste_label = "paste"
                else:
                    # 如果不为空，使用选中的标签或第一个标签
                    selected_items = self.paste_label_list.selectedItems()
                    if selected_items:
                        paste_label = selected_items[0].text()
                    else:
                        # 如果没有选中的标签，使用第一个标签
                        paste_label = self.paste_label_list.item(0).text()
            self.canvas_items.append((pixmap, rect, paste_label))
            self.canvas.update()
    
    def clear_canvas(self):
        # 清除当前背景图的小图列表
        self.canvas_items.clear()
        # 如果当前背景图索引有效，更新字典中的小图状态
        if self.current_background_index >= 0:
            self.canvas_items_dict[self.current_background_index] = self.canvas_items.copy()
        self.selected_item = None
        self.canvas.update()
    
    def random_paste_images(self):
        """随机选择贴图列表中的贴图并添加到画布上"""
        import random
        
        if not self.small_images:
            return
        
        if self.current_background is None:
            return
        
        # 清空画布
        self.canvas_items.clear()
        
        # 获取当前背景图的检测框
        boxes = []
        for box in self.detection_boxes:
            x = box['x']
            y = box['y']
            width = box['width']
            height = box['height']
            boxes.append((x, y, x + width, y + height))
        
        # 使用输入框中设置的贴图个数
        num_paste = self.paste_count_spin.value()
        
        # 随机选择贴图
        selected_indices = random.choices(range(len(self.small_images)), k=num_paste)
        
        pasted_boxes = []
        
        for idx in selected_indices:
            file_path, pixmap = self.small_images[idx]
            
            # 计算贴图大小，保持原始比例
            width = pixmap.width()
            height = pixmap.height()
            aspect_ratio = width / height
            
            # 随机大小（30-70像素）
            target_size = random.randint(30, 70)
            if width > height:
                new_width = target_size
                new_height = new_width / aspect_ratio
            else:
                new_height = target_size
                new_width = new_height * aspect_ratio
            
            # 确保最小边不小于30
            if min(new_width, new_height) < 30:
                if new_width < new_height:
                    new_width = 30
                    new_height = new_width / aspect_ratio
                else:
                    new_height = 30
                    new_width = new_height * aspect_ratio
            
            # 随机位置（在背景图范围内）
            max_x = self.current_background.width() - new_width
            max_y = self.current_background.height() - new_height
            
            # 尝试找到有效的位置
            max_attempts = 1000
            valid_position = False
            x, y = 0, 0
            
            for _ in range(max_attempts):
                if max_x > 0 and max_y > 0:
                    x = random.randint(0, int(max_x))
                    y = random.randint(0, int(max_y))
                else:
                    x = 50
                    y = 50
                
                # 检查是否与标签框重叠（使用IoU计算）
                overlap = False
                new_box = (x, y, x + new_width, y + new_height)
                for box in boxes:
                    bx1, by1, bx2, by2 = box
                    # 计算IoU
                    x1 = max(new_box[0], bx1)
                    y1 = max(new_box[1], by1)
                    x2 = min(new_box[2], bx2)
                    y2 = min(new_box[3], by2)
                    
                    if x2 <= x1 or y2 <= y1:
                        iou = 0.0
                    else:
                        intersection = (x2 - x1) * (y2 - y1)
                        area1 = (new_box[2] - new_box[0]) * (new_box[3] - new_box[1])
                        area2 = (bx2 - bx1) * (by2 - by1)
                        union = area1 + area2 - intersection
                        iou = intersection / union if union > 0 else 0.0
                    
                    if iou > 0.02:
                        overlap = True
                        break
                
                if overlap:
                    continue
                
                # 检查与已贴贴图的IoU
                new_box = (x, y, x + new_width, y + new_height)
                iou_ok = True
                for pasted_box in pasted_boxes:
                    # 计算IoU
                    x1 = max(new_box[0], pasted_box[0])
                    y1 = max(new_box[1], pasted_box[1])
                    x2 = min(new_box[2], pasted_box[2])
                    y2 = min(new_box[3], pasted_box[3])
                    
                    if x2 <= x1 or y2 <= y1:
                        iou = 0.0
                    else:
                        intersection = (x2 - x1) * (y2 - y1)
                        area1 = (new_box[2] - new_box[0]) * (new_box[3] - new_box[1])
                        area2 = (pasted_box[2] - pasted_box[0]) * (pasted_box[3] - pasted_box[1])
                        union = area1 + area2 - intersection
                        iou = intersection / union if union > 0 else 0.0
                    
                    if iou > 0.1:
                        iou_ok = False
                        break
                
                if iou_ok:
                    valid_position = True
                    break
            
            if valid_position:
                # 创建矩形并添加到画布
                rect = QRectF(x, y, new_width, new_height)
                # 使用默认标签"paste"或选中的贴图标签
                paste_label = "paste"
                if hasattr(self, 'paste_label_list'):
                    # 检查贴图标签列表是否为空
                    if self.paste_label_list.count() == 0:
                        # 如果为空，添加默认标签"paste"
                        self.paste_label_list.addItem("paste")
                        paste_label = "paste"
                    else:
                        # 如果不为空，使用选中的标签或第一个标签
                        selected_items = self.paste_label_list.selectedItems()
                        if selected_items:
                            paste_label = selected_items[0].text()
                        else:
                            # 如果没有选中的标签，使用第一个标签
                            paste_label = self.paste_label_list.item(0).text()
                self.canvas_items.append((pixmap, rect, paste_label))
                pasted_boxes.append(new_box)
            else:
                # 如果找不到有效的位置，跳过这个贴图
                continue
        
        # 更新画布
        self.canvas.update()
        
        # 如果当前背景图索引有效，更新字典中的小图状态
        if self.current_background_index >= 0:
            self.canvas_items_dict[self.current_background_index] = self.canvas_items.copy()
    
    def batch_paste_images(self):
        """从当前图片开始依次处理所有图片，应用随机贴图，然后返回当前图片"""
        if not self.small_images:
            return
        
        if not self.background_images:
            return
        
        # 保存当前背景图索引
        original_index = self.current_background_index
        
        # 从当前图片开始处理所有图片
        start_index = original_index if original_index >= 0 else 0
        
        for i in range(start_index, len(self.background_images)):
            # 切换到当前图片
            self.current_background_index = i
            # 加载图片
            file_path = self.background_images[i]
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                self.current_background = pixmap
                self.canvas_items = self.canvas_items_dict.get(i, []).copy()
                self.selected_item = None
                
                # 应用随机贴图
                self.random_paste_images()
        
        # 处理完所有图片后，返回当前图片
        if original_index >= 0:
            self.current_background_index = original_index
            # 加载图片
            file_path = self.background_images[original_index]
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                self.current_background = pixmap
                self.canvas_items = self.canvas_items_dict.get(original_index, []).copy()
                self.selected_item = None
                self.canvas.update()
    

    def save_canvas(self):
        if self.current_background is None:
            QMessageBox.warning(self, "警告", "请先选择背景图片")
            return
        
        # 检查文件前缀
        prefix = self.prefix_input.text().strip()
        if not prefix:
            QMessageBox.warning(self, "警告", "请输入文件前缀")
            return
        
        # 获取背景图的原始文件名
        if self.current_background_index >= 0 and self.current_background_index < len(self.background_images):
            original_file_path = self.background_images[self.current_background_index]
            original_file_name = os.path.basename(original_file_path)
            # 获取文件名和扩展名
            original_name_without_ext, original_ext = os.path.splitext(original_file_name)
            # 使用原始扩展名
            base_name = f"{original_name_without_ext}{original_ext}"
            
            # 生成默认保存路径：背景文件夹同级的 paste_output 文件夹
            background_dir = os.path.dirname(original_file_path)
            output_dir = os.path.join(os.path.dirname(background_dir), "paste_output")
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
        else:
            base_name = "edited_image.png"
            # 如果没有背景图，使用当前目录
            output_dir = os.path.join(os.getcwd(), "paste_output")
            os.makedirs(output_dir, exist_ok=True)
        
        # 添加前缀
        base_name = f"{prefix}_{base_name}"
        
        # 使用默认保存路径
        file_path = os.path.join(output_dir, base_name)
        
        # 创建合成图片
        result = QPixmap(self.current_background.size())
        painter = QPainter(result)
        painter.fillRect(result.rect(), QColor(255, 255, 255))
        
        # 绘制背景
        painter.drawPixmap(0, 0, self.current_background)
        
        # 绘制所有贴图片
        for pixmap, rect, label in self.canvas_items:
            painter.drawPixmap(rect.toRect(), pixmap)
        
        painter.end()
        result.save(file_path)
        
        # 生成并保存JSON文件
        self.save_json(file_path, base_name, prefix)
    
    def save_json(self, image_path, image_name, label_prefix, canvas_items=None, image_width=None, image_height=None, current_index=None):
        """生成并保存包含贴图位置的JSON文件"""
        import json
        
        # 生成JSON文件路径
        json_path = os.path.splitext(image_path)[0] + '.json'
        
        # 使用传入的canvas_items或默认使用当前的
        items_to_use = canvas_items if canvas_items is not None else self.canvas_items
        
        # 使用传入的图片尺寸或默认使用当前背景的尺寸
        width = image_width if image_width is not None else (self.current_background.width() if self.current_background else 0)
        height = image_height if image_height is not None else (self.current_background.height() if self.current_background else 0)
        
        # 使用传入的索引或默认使用当前索引
        index_to_use = current_index if current_index is not None else self.current_background_index
        
        # 准备JSON数据
        json_data = {
            "version": "5.0.1",
            "flags": {},
            "shapes": [],
            "imagePath": image_name,
            "imageData": None,
            "imageHeight": height,
            "imageWidth": width
        }
        
        # 添加贴图位置作为标签
        for i, (pixmap, rect, label) in enumerate(items_to_use):
            # 获取贴图位置和大小
            x = rect.x()
            y = rect.y()
            width = rect.width()
            height = rect.height()
            
            # 计算边界框的四个点（矩形）
            points = [
                [x, y],
                [x + width, y],
                [x + width, y + height],
                [x, y + height]
            ]
            
            # 添加到shapes列表
            shape = {
                "label": label,
                "points": points,
                "group_id": None,
                "description": "",
                "shape_type": "rectangle",
                "flags": {}
            }
            json_data["shapes"].append(shape)
        
        # 添加检测框信息
        if index_to_use >= 0 and index_to_use in self.detection_boxes_dict:
            detection_boxes = self.detection_boxes_dict[index_to_use]
            for box in detection_boxes:
                x = box['x']
                y = box['y']
                width = box['width']
                height = box['height']
                label = box['label']
                
                # 计算边界框的四个点（矩形）
                points = [
                    [x, y],
                    [x + width, y],
                    [x + width, y + height],
                    [x, y + height]
                ]
                
                # 添加到shapes列表
                shape = {
                    "label": label,
                    "points": points,
                    "group_id": None,
                    "description": "",
                    "shape_type": "rectangle",
                    "flags": {}
                }
                json_data["shapes"].append(shape)
        
        # 保存JSON文件
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    def save_all_canvas(self):
        """保存所有背景图片及其贴图"""
        # 检查文件前缀
        prefix = self.prefix_input.text().strip()
        if not prefix:
            QMessageBox.warning(self, "警告", "请输入文件前缀")
            return
        
        # 保存原始状态
        original_background = self.current_background
        original_index = self.current_background_index
        original_canvas_items = self.canvas_items.copy()
        
        # 保存每个背景图片
        saved_count = 0
        for i, file_path in enumerate(self.background_images):
            # 加载图片
            pixmap = QPixmap(file_path)
            if pixmap.isNull():
                continue
            
            # 临时设置当前背景和索引，不更新UI
            temp_background = pixmap
            temp_index = i
            
            temp_canvas_items = []
            if i in self.canvas_items_dict:
                temp_canvas_items = self.canvas_items_dict[i]
            
            # 保存图片
            original_file_name = os.path.basename(file_path)
            original_name_without_ext, original_ext = os.path.splitext(original_file_name)
            base_name = f"{original_name_without_ext}{original_ext}"
            base_name = f"{prefix}_{base_name}"
            
            # 生成默认保存路径：背景文件夹同级的 paste_output 文件夹
            background_dir = os.path.dirname(file_path)
            output_dir = os.path.join(os.path.dirname(background_dir), "paste_output")
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            save_file_path = os.path.join(output_dir, base_name)
            
            # 创建合成图片
            result = QPixmap(pixmap.size())
            painter = QPainter(result)
            painter.fillRect(result.rect(), QColor(255, 255, 255))
            painter.drawPixmap(0, 0, pixmap)
            
            for item_pixmap, rect, label in temp_canvas_items:
                painter.drawPixmap(rect.toRect(), item_pixmap)
            
            painter.end()
            result.save(save_file_path)
            
            # 生成并保存JSON文件
            self.save_json(save_file_path, base_name, prefix, temp_canvas_items, pixmap.width(), pixmap.height(), i)
            
            saved_count += 1
        
        # 恢复原始状态
        if original_index >= 0:
            self.current_background = original_background
            self.current_background_index = original_index
            self.canvas_items = original_canvas_items
            self.background_list.setCurrentRow(original_index)
            self.update_file_count()
            self.canvas.update()
        
        # 更新标签列表，显示当前图片中的标签数
        self.update_label_list()
    
    def create_app_icon(self):
        """从本地img.png文件加载应用图标"""
        # 获取脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # 图标文件路径
        icon_path = os.path.join(script_dir, "ico_image/icoo.png")
        
        # 如果文件存在则加载，否则使用默认图标
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        else:
            # 创建一个简单的默认图标
            icon_size = 64
            pixmap = QPixmap(icon_size, icon_size)
            pixmap.fill(QColor(0, 0, 0))
            return QIcon(pixmap)
    
    def keyPressEvent(self, event):
        """处理键盘事件：A键切换到上一张背景图，D键切换到下一张背景图，R键切换检测框显示/隐藏，R键切换类别名显示/隐藏"""
        if event.key() == Qt.Key_A:
            self.switch_background(-1)  # 上一张
        elif event.key() == Qt.Key_D:
            self.switch_background(1)   # 下一张R
        elif event.key() == Qt.Key_R:
            # 切换检测框显示/隐藏状态
            current_state = self.show_labels_checkbox.isChecked()
            self.show_labels_checkbox.setChecked(not current_state)
            self.on_labels_checkbox_changed()  # 触发更新
        elif event.key() == Qt.Key_T:
            # 切换类别名显示/隐藏状态T
            if hasattr(self, 'show_label_names_checkbox'):
                current_state = self.show_label_names_checkbox.isChecked()
                self.show_label_names_checkbox.setChecked(not current_state)
                self.on_labels_checkbox_changed()  # 触发更新
        elif event.key() == Qt.Key_W:
            # W键进入绘制检测框模式
            self.toggle_draw_mode()
        elif event.key() == Qt.Key_Q:
            # Q键退出绘制模式
            if self.canvas.is_drawing_box:
                self.canvas.is_drawing_box = False
                self.canvas.draw_start_pos = None
                self.canvas.temp_draw_box = None
                # 恢复箭头光标
                self.canvas.setCursor(Qt.ArrowCursor)
                # 更新按钮文本
                if hasattr(self, 'draw_box_btn'):
                    self.draw_box_btn.setText("绘制BOX(W)")
                # 更新画布
                self.canvas.update()
        elif event.key() == Qt.Key_Delete or event.key() == Qt.Key_E:
            # Delete键或E键删除选中的检测框
            if self.canvas.selected_box is not None and 0 <= self.canvas.selected_box < len(self.detection_boxes):
                # 删除选中的检测框
                del self.detection_boxes[self.canvas.selected_box]
                # 更新detection_boxes_dict
                if self.current_background_index >= 0:
                    self.detection_boxes_dict[self.current_background_index] = self.detection_boxes.copy()
                # 重置选中状态
                self.canvas.selected_box = None
                # 更新标签列表
                self.update_label_list()
                # 更新画布
                self.canvas.update()
                # 同步更新到原始json文件
                if self.current_background and self.current_background_index >= 0:
                    # 获取当前背景图的路径
                    background_path = self.background_images[self.current_background_index]
                    # 获取背景图的文件名
                    background_name = os.path.basename(background_path)
                    # 调用save_json方法保存检测框信息，传入空的canvas_items确保不包含贴图信息
                    self.save_json(background_path, background_name, "", canvas_items=[])
        super().keyPressEvent(event)
    
    def installEventFilterRecursive(self, widget):
        """递归为所有子控件安装事件过滤器"""
        widget.installEventFilter(self)
        for child in widget.children():
            self.installEventFilterRecursive(child)
    
    def eventFilter(self, obj, event):
        """事件过滤器，捕获所有键盘事件并处理左右切图的逻辑"""
        if event.type() == QEvent.KeyPress:
            key = event.key()
            if key == Qt.Key_A:
                self.switch_background(-1)  # 上一张
                return True
            elif key == Qt.Key_D:
                self.switch_background(1)   # 下一张
                return True
        return super().eventFilter(obj, event)
    
    def toggle_draw_mode(self):
        """进入绘制检测框模式"""
        # 检查是否有背景图片
        if not self.background_images or self.current_background_index < 0:
            return
        
        # 只有当不在绘制模式时才进入
        if not self.canvas.is_drawing_box:
            # 进入绘制模式
            self.canvas.is_drawing_box = True
            
            # 更新鼠标指针样式为十字光标
            self.canvas.setCursor(Qt.CrossCursor)
            
            # 取消之前的选中状态
            self.selected_item = None
            self.canvas.selected_box = None
            
            # 确保Canvas获得焦点，以便接收键盘事件
            self.canvas.setFocus()
            
            # 更新画布
            self.canvas.update()
    
    def switch_background(self, direction):
        """切换背景图：direction为-1表示上一张，1表示下一张"""
        if not self.background_images:
            return
        
        # 保存当前背景图的状态
        if self.current_background_index >= 0:
            # 保存贴图状态
            self.canvas_items_dict[self.current_background_index] = self.canvas_items.copy()
            # 保存检测框状态
            self.detection_boxes_dict[self.current_background_index] = self.detection_boxes.copy()
        
        # 计算新索引，不循环
        new_index = self.current_background_index + direction
        
        # 边界检查
        if new_index < 0:
            new_index = 0
        elif new_index >= len(self.background_images):
            new_index = len(self.background_images) - 1
        
        # 如果索引没有变化，直接返回
        if new_index == self.current_background_index:
            return
        
        # 切换背景图
        self.current_background_index = new_index
        
        # 加载图片
        file_path = self.background_images[new_index]
        pixmap = QPixmap(file_path)
        if not pixmap.isNull():
            self.current_background = pixmap
            # 加载检测框，优先从dict中获取（保留用户绘制的标签）
            if new_index in self.detection_boxes_dict and len(self.detection_boxes_dict[new_index]) > 0:
                self.detection_boxes = self.detection_boxes_dict[new_index].copy()
            else:
                # 如果dict中没有或为空，从文件加载
                self.detection_boxes = self.load_detection_boxes(file_path)
                # 保存到dict
                self.detection_boxes_dict[new_index] = self.detection_boxes.copy()
        else:
            self.current_background = None
            self.detection_boxes = []
        
        # 加载新背景图的小图状态，如果不存在则初始化空列表
        if new_index not in self.canvas_items_dict:
            self.canvas_items_dict[new_index] = []
        self.canvas_items = self.canvas_items_dict[new_index].copy()
        
        # 更新标签列表
        self.update_label_list()
        
        # 重置背景图缩放比例，让新背景图自动适配画布
        self.canvas.background_scale = 1.0
        self.canvas.background_offset = QPoint(0, 0)
        self.canvas.is_manual_scale = False  # 重置为自动适配模式
        
        # 更新列表选中状态
        self.background_list.setCurrentRow(new_index)
        
        # 更新文件计数
        self.update_file_count()
        
        # 重置选择状态
        self.selected_item = None
        
        # 刷新画布
        self.canvas.update()
    
    def load_folder_images(self):
        """从文件夹加载所有图片作为背景图"""
        # 支持的图片扩展名
        supported_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.gif']
        
        # 选择文件夹
        folder_path = QFileDialog.getExistingDirectory(
            self, "选择图片文件夹", ""
        )
        
        if not folder_path:
            return
        
        # 清空现有背景图列表
        self.background_images.clear()
        self.background_list.clear()
        self.current_background = None
        
        # 清空检测框字典，确保重新加载图片时不会保留之前的检测框数据
        self.detection_boxes_dict.clear()
        
        # 遍历文件夹中的所有文件，只收集路径，不加载图片
        for file_name in sorted(os.listdir(folder_path), key=self.natural_sort_key):
            # 检查文件扩展名
            ext = os.path.splitext(file_name)[1].lower()
            if ext in supported_extensions:
                file_path = os.path.join(folder_path, file_name)
                # 添加到背景图列表（只存储文件路径）
                new_index = len(self.background_images)
                self.background_images.append(file_path)
                # 添加到列表控件，确保路径显示为全部反斜杠
                display_path = file_path.replace('/', '\\')
                item = QListWidgetItem(display_path)
                item.setData(Qt.UserRole, new_index)
                self.background_list.addItem(item)
                
                # 初始化该背景图的小图状态为空列表
                self.canvas_items_dict[new_index] = []
                
                # 初始化检测框字典，稍后在需要时加载
                self.detection_boxes_dict[new_index] = []
        
        # 如果有图片，自动选择第一张
        if self.background_images:
            self.current_background_index = 0
            self.background_list.setCurrentRow(0)
            # 加载第一张图片
            self.load_image_by_index(0)
            # 更新标签列表
            self.update_label_list()
            # 更新文件计数
            self.update_file_count()
        else:
            QMessageBox.warning(
                self, "警告", "该文件夹中没有找到支持的图片文件"
            )
            # 更新文件计数
            self.update_file_count()
    
    def load_small_folder_images(self):
        """从文件夹加载所有图片作为贴图"""
        # 支持的图片扩展名
        supported_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.gif']
        
        # 选择文件夹
        folder_path = QFileDialog.getExistingDirectory(
            self, "选择贴图文件夹", ""
        )
        
        if not folder_path:
            return
        
        # 清空现有贴图列表
        self.small_images.clear()
        self.small_list.clear()
        
        # 遍历文件夹中的所有文件
        loaded_count = 0
        for file_name in sorted(os.listdir(folder_path), key=self.natural_sort_key):
            # 检查文件扩展名
            ext = os.path.splitext(file_name)[1].lower()
            if ext in supported_extensions:
                file_path = os.path.join(folder_path, file_name)
                pixmap = QPixmap(file_path)
                if not pixmap.isNull():
                    # 添加到贴图列表
                    self.small_images.append((file_path, pixmap))
                    # 添加到列表控件，只显示文件名
                    item = QListWidgetItem(file_name)
                    item.setData(Qt.UserRole, len(self.small_images) - 1)
                    self.small_list.addItem(item)
                    loaded_count += 1
        
        if loaded_count == 0:
            QMessageBox.warning(
                self, "警告", "该文件夹中没有找到支持的图片文件"
            )

class Canvas(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.setMinimumSize(800, 600)
        self.drag_start = QPoint()
        self.resize_handle = None
        self.resize_start = QPoint()
        self.background_scale = 1.0  # 背景图缩放比例，默认为1.0，会在paintEvent中自动调整为适配画布
        self.background_offset = QPoint(0, 0)  # 背景图偏移量，用于拖动背景图
        self.is_dragging_background = False  # 是否正在拖动背景图
        self.is_dragging_item = False  # 是否正在拖动贴图
        self.is_manual_scale = False  # 是否手动缩放了背景图（默认false，自动适配）
        self.setFocusPolicy(Qt.StrongFocus)  # 设置焦点策略，使Canvas可以接收键盘事件
        self.setMouseTracking(True)  # 启用鼠标追踪，即使不点击左键也能追踪鼠标移动
        self.mouse_pos = QPoint(0, 0)  # 当前鼠标位置
        self.selected_item_size = None  # 当前选中贴图的大小 (width, height)
        # 检测框编辑相关属性
        self.selected_box = None  # 当前选中的检测框索引
        self.is_dragging_box = False  # 是否正在拖动检测框
        self.box_drag_start = QPoint()  # 检测框拖动的起始位置
        self.is_resizing_box = False  # 是否正在调整检测框大小
        self.box_resize_start = QPoint()  # 检测框调整的起始位置
        
        # 绘制模式相关属性
        self.is_drawing_box = False  # 是否处于绘制检测框模式
        self.draw_start_pos = None  # 绘制起始位置（画布坐标）
        self.temp_draw_box = None  # 临时绘制的检测框（画布坐标）
        
        # 鼠标状态跟踪
        self.mouse_inside = False  # 鼠标是否在画布内部
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景
        background_rect = None
        if self.parent.current_background is not None:
            # 计算缩放比例，使背景图适配画布
            # 如果没有手动缩放，则自动适配窗口大小
            if not self.is_manual_scale:
                scale_x = self.width() / self.parent.current_background.width()
                scale_y = self.height() / self.parent.current_background.height()
                self.background_scale = min(scale_x, scale_y)
                # 重置偏移量，确保背景图居中
                self.background_offset = QPoint(0, 0)
            
            # 计算绘制尺寸
            scaled_width = self.parent.current_background.width() * self.background_scale
            scaled_height = self.parent.current_background.height() * self.background_scale
            
            # 计算居中位置（考虑偏移量）
            x = (self.width() - scaled_width) // 2 + self.background_offset.x()
            y = (self.height() - scaled_height) // 2 + self.background_offset.y()
            
            # 保存背景图的实际绘制矩形
            background_rect = QRectF(x, y, scaled_width, scaled_height)
            
            # 绘制缩放后的背景
            painter.drawPixmap(
                int(x), int(y),
                int(scaled_width), int(scaled_height),
                self.parent.current_background
            )
        else:
            # 绘制空白背景
            painter.fillRect(self.rect(), QColor(230, 230, 230))
        
        # 绘制所有贴图片
        for i, (pixmap, rect, label) in enumerate(self.parent.canvas_items):
            if background_rect is not None:
                # 贴图只能显示在背景图上
                # 计算贴图相对于背景图的位置和大小
                bg_original_width = self.parent.current_background.width()
                bg_original_height = self.parent.current_background.height()
                
                # 将贴图的相对坐标转换为背景图上的绝对坐标
                # 贴图坐标已经是相对于背景图的，现在需要根据背景图的缩放和偏移进行调整
                item_x = (rect.x() * self.background_scale) + background_rect.left()
                item_y = (rect.y() * self.background_scale) + background_rect.top()
                item_width = rect.width() * self.background_scale
                item_height = rect.height() * self.background_scale
                
                # 检查是否为选中的贴图
                is_selected = (i == self.parent.selected_item)
                
                # 绘制贴图
                if is_selected:
                    # 为选中的贴图创建边框颜色对应的透明蒙版
                    temp_pixmap = QPixmap(item_width, item_height)
                    temp_pixmap.fill(Qt.transparent)
                    temp_painter = QPainter(temp_pixmap)
                    
                    # 绘制原始贴图
                    temp_painter.drawPixmap(0, 0, int(item_width), int(item_height), pixmap)
                    
                    # 添加边框颜色的透明蒙版
                    overlay_color = QColor(135, 206, 250, 50)  # 蓝色，50/255透明度
                    temp_painter.fillRect(0, 0, int(item_width), int(item_height), overlay_color)
                    
                    temp_painter.end()
                    
                    # 绘制带透明蒙版的贴图
                    painter.drawPixmap(
                        int(item_x), int(item_y),
                        temp_pixmap
                    )
                else:
                    # 绘制正常贴图
                    painter.drawPixmap(
                        int(item_x), int(item_y),
                        int(item_width), int(item_height),
                        pixmap
                    )
                    
                # 为选中的贴图显示编辑状态
                if is_selected:
                    # 绘制边框
                    pen = QPen(QColor(135, 206, 250), 2)  # 天蓝色边框
                    painter.setPen(pen)
                    painter.drawRect(
                        int(item_x), int(item_y),
                        int(item_width), int(item_height)
                    )
                    
                    # 绘制缩放手柄（只显示右下角）
                    handle_size = 10
                    # 右下角手柄
                    br_handle = QPointF(item_x + item_width, item_y + item_height)
                    painter.fillRect(
                        int(br_handle.x() - handle_size // 2),
                        int(br_handle.y() - handle_size // 2),
                        handle_size, handle_size,
                        QColor(135, 206, 250)  # 天蓝色手柄
                    )
                    
                    # 绘制贴图标签（只在编辑时显示）
                    from PyQt5.QtGui import QFontMetrics
                    text = label
                    font = painter.font()
                    metrics = QFontMetrics(font)
                    text_width = metrics.width(text)
                    text_height = metrics.height()
                    
                    # 绘制天蓝色填充背景
                    painter.fillRect(
                        int(item_x), int(item_y) - text_height,
                        text_width, text_height,
                        QColor(135, 206, 250)  # 天蓝色填充
                    )
                    
                    # 绘制黑色文本
                    painter.setPen(QColor(0, 0, 0))  # 黑色文本
                    painter.setFont(font)
                    painter.drawText(
                        int(item_x), int(item_y) - 2,
                        text
                    )
        
        # 绘制检测框
        if self.parent.show_labels_checkbox.isChecked() and background_rect is not None:
            for i, box in enumerate(self.parent.detection_boxes):
                # 计算检测框在画布上的位置和大小（考虑背景图缩放和偏移）
                box_x = box["x"] * self.background_scale + background_rect.left()
                box_y = box["y"] * self.background_scale + background_rect.top()
                box_width = box["width"] * self.background_scale
                box_height = box["height"] * self.background_scale
                
                # 跳过宽度或高度为0的临时标签框
                if box["width"] <= 0 or box["height"] <= 0:
                    continue
                
                # 检查是否为选中的检测框
                is_selected = (i == self.selected_box)
                
                # 检查是否为当前按下标签对应的检测框
                is_pressed_label = False
                if hasattr(self.parent, 'pressed_label') and self.parent.pressed_label is not None:
                    if 'label' in box and box['label'] == self.parent.pressed_label:
                        is_pressed_label = True
                
                if is_selected:
                    # 绘制选中检测框的填充效果
                    painter.fillRect(
                        int(box_x), int(box_y),
                        int(box_width), int(box_height),
                        QColor(0, 255, 128, 50)  # 半透明淡绿色填充
                    )
                    # 绘制选中检测框的边框
                    pen = QPen(QColor(0, 255, 128), 3)  # 淡绿色边框
                elif is_pressed_label:
                    # 绘制当前按下标签对应的检测框填充效果
                    painter.fillRect(
                        int(box_x), int(box_y),
                        int(box_width), int(box_height),
                        QColor(255, 165, 0, 50)  # 半透明橙色填充
                    )
                    # 绘制当前按下标签对应的检测框边框
                    pen = QPen(QColor(255, 165, 0), 3)  # 橙色边框
                else:
                    # 绘制普通检测框的边框
                    pen = QPen(QColor(0, 255, 128), 2)  # 淡绿色边框
                
                painter.setPen(pen)
                painter.drawRect(
                    int(box_x), int(box_y),
                    int(box_width), int(box_height)
                )
                
                # 绘制标签文本
                if box.get("label") and hasattr(self.parent, 'show_label_names_checkbox') and self.parent.show_label_names_checkbox.isChecked():
                    from PyQt5.QtGui import QFontMetrics
                    text = box["label"]
                    font = painter.font()
                    metrics = QFontMetrics(font)
                    text_width = metrics.width(text)
                    text_height = metrics.height()
                    
                    # 绘制淡绿色填充背景
                    painter.fillRect(
                        int(box_x), int(box_y) - text_height,
                        text_width, text_height,
                        QColor(0, 255, 128)  # 淡绿色填充
                    )
                    
                    # 绘制黑色文本
                    painter.setPen(QColor(0, 0, 0))  # 黑色文本
                    painter.setFont(font)
                    painter.drawText(
                        int(box_x), int(box_y) - 2,
                        text
                    )
                
                # 为选中的检测框绘制调整手柄（四个角）
                if is_selected:
                    handle_size = 8
                    # 左上角
                    tl_handle = QPointF(box_x, box_y)
                    painter.fillRect(
                        int(tl_handle.x() - handle_size // 2),
                        int(tl_handle.y() - handle_size // 2),
                        handle_size, handle_size,
                        QColor(0, 255, 128)  # 淡绿色调整手柄
                    )
                    # 右上角
                    tr_handle = QPointF(box_x + box_width, box_y)
                    painter.fillRect(
                        int(tr_handle.x() - handle_size // 2),
                        int(tr_handle.y() - handle_size // 2),
                        handle_size, handle_size,
                        QColor(0, 255, 128)  # 淡绿色调整手柄
                    )
                    # 左下角
                    bl_handle = QPointF(box_x, box_y + box_height)
                    painter.fillRect(
                        int(bl_handle.x() - handle_size // 2),
                        int(bl_handle.y() - handle_size // 2),
                        handle_size, handle_size,
                        QColor(0, 255, 128)  # 淡绿色调整手柄
                    )
                    # 右下角
                    br_handle = QPointF(box_x + box_width, box_y + box_height)
                    painter.fillRect(
                        int(br_handle.x() - handle_size // 2),
                        int(br_handle.y() - handle_size // 2),
                        handle_size, handle_size,
                        QColor(0, 255, 128)  # 淡绿色调整手柄
                    )
        
        # 绘制临时检测框（正在绘制中的）
        if self.is_drawing_box:
            # 绘制临时检测框（如果已经开始绘制）
            if self.temp_draw_box is not None and self.draw_start_pos is not None:
                pen = QPen(QColor(0, 255, 0), 2, Qt.DashLine)  # 淡绿色虚线
                painter.setPen(pen)
                painter.drawRect(self.temp_draw_box)
            
            # 绘制绿色十字虚线（在鼠标当前位置）
            # 获取鼠标当前位置
            mouse_pos = self.mouse_pos
            if mouse_pos is not None:
                # 设置十字线颜色和样式
                cross_pen = QPen(QColor(0, 255, 128), 1, Qt.DashLine)
                painter.setPen(cross_pen)
                
                # 绘制水平十字线
                painter.drawLine(
                    QPointF(0, mouse_pos.y()),
                    QPointF(self.width(), mouse_pos.y())
                )
                # 绘制垂直十字线
                painter.drawLine(
                    QPointF(mouse_pos.x(), 0),
                    QPointF(mouse_pos.x(), self.height())
                )
    
    def mousePressEvent(self, event):
        # 点击画布时自动获取焦点，以便接收键盘事件
        self.setFocus()
        
        mouse_pos = event.pos()
        
        # 绘制模式下的处理
        if self.is_drawing_box and event.button() == Qt.LeftButton:
            # 检查是否有背景图片
            if not self.parent.background_images or self.parent.current_background_index < 0:
                return
            
            # 检查鼠标点击位置是否在背景图范围内
            background_rect = self.get_background_rect()
            if background_rect is None or not background_rect.contains(mouse_pos):
                return
            
            # 第一次点击：设置起点
            if self.draw_start_pos is None:
                # 开始绘制新的检测框
                self.draw_start_pos = mouse_pos
                self.temp_draw_box = QRectF(mouse_pos, QSizeF())
                # 取消之前的选中状态
                self.selected_box = None
                self.parent.selected_item = None
                
                # 更新状态栏显示，显示起点位置
                self.update_status_label()
                
                self.update()
                return
            # 第二次点击：设置终点并完成绘制
            else:
                # 确保终点不超出背景图范围
                constrained_pos = mouse_pos
                constrained_pos.setX(max(background_rect.left(), min(constrained_pos.x(), background_rect.right())))
                constrained_pos.setY(max(background_rect.top(), min(constrained_pos.y(), background_rect.bottom())))
                
                # 计算矩形的正确位置和大小（支持任意方向绘制）
                x1 = min(self.draw_start_pos.x(), constrained_pos.x())
                y1 = min(self.draw_start_pos.y(), constrained_pos.y())
                x2 = max(self.draw_start_pos.x(), constrained_pos.x())
                y2 = max(self.draw_start_pos.y(), constrained_pos.y())
                
                # 更新临时绘制框
                self.temp_draw_box = QRectF(x1, y1, x2 - x1, y2 - y1)
                
                # 计算检测框在背景图上的实际坐标和大小
                x = (self.temp_draw_box.left() - background_rect.left()) / self.background_scale
                y = (self.temp_draw_box.top() - background_rect.top()) / self.background_scale
                width = self.temp_draw_box.width() / self.background_scale
                height = self.temp_draw_box.height() / self.background_scale
                
                # 更新状态栏显示，显示最终的检测框信息
                self.update_status_label()
                
                # 确保坐标为正值
                x = max(0, x)
                y = max(0, y)
                width = max(1, width)
                height = max(1, height)
                
                # 验证检测框是否有效：坐标不为全0且是一个大于3*3的方形框
                if x <= 0 and y <= 0:
                    # 坐标为全0，不创建检测框
                    # 重置绘制状态
                    self.draw_start_pos = None
                    self.temp_draw_box = None
                    self.update()
                    return
                
                # 确保检测框是一个大于3*3的方形框
                if width <= 3 or height <= 3:
                    # 检测框太小，不创建检测框
                    # 重置绘制状态
                    self.draw_start_pos = None
                    self.temp_draw_box = None
                    self.update()
                    return
                
                # 创建并显示标签选择对话框
                class LabelSelectionDialog(QDialog):
                    def __init__(self, parent, labels):
                        super().__init__(parent)
                        self.setWindowTitle("选择标签")
                        self.setMinimumWidth(400)
                        
                        layout = QVBoxLayout()
                        
                        # 现有标签列表
                        layout.addWidget(QLabel("现有标签："))
                        self.label_list = QListWidget()
                        for label in labels:
                            # 提取纯标签名称，去除"(count)"部分
                            if " (" in label:
                                pure_label = label.split(" (")[0]
                                self.label_list.addItem(pure_label)
                            else:
                                self.label_list.addItem(label)
                        layout.addWidget(self.label_list)
                        
                        # 新标签输入框
                        layout.addWidget(QLabel("或输入新标签："))
                        self.new_label_input = QLineEdit()
                        layout.addWidget(self.new_label_input)
                        
                        # 按钮
                        button_layout = QHBoxLayout()
                        self.ok_btn = QPushButton("确定")
                        self.cancel_btn = QPushButton("取消")
                        button_layout.addStretch()
                        button_layout.addWidget(self.ok_btn)
                        button_layout.addWidget(self.cancel_btn)
                        layout.addLayout(button_layout)
                        
                        self.setLayout(layout)
                        
                        # 连接信号
                        self.ok_btn.clicked.connect(self.accept)
                        self.cancel_btn.clicked.connect(self.reject)
                        
                        # 按下回车键等同于点击确定按钮
                        self.new_label_input.returnPressed.connect(self.accept)
                        
                        # 双击标签列表项等同于点击确定按钮
                        self.label_list.itemDoubleClicked.connect(self.accept)
                        
                    def get_selected_label(self):
                        # 优先返回列表中选中的标签
                        selected_items = self.label_list.selectedItems()
                        if selected_items:
                            return selected_items[0].text()
                        # 如果没有选中，返回输入框中的文本
                        return self.new_label_input.text().strip()
                
                # 获取标签列表中的所有标签
                label_items = []
                for i in range(self.parent.label_list.count()):
                    label_items.append(self.parent.label_list.item(i).text())
                
                # 显示标签选择对话框
                dialog = LabelSelectionDialog(self, label_items)
                if dialog.exec_():
                    selected_label = dialog.get_selected_label()
                    if selected_label:
                        # 检查是否是新标签（需要去除count后缀后比较）
                        is_new_label = True
                        for label in label_items:
                            if " (" in label:
                                pure_label = label.split(" (")[0]
                                if pure_label == selected_label:
                                    is_new_label = False
                                    break
                            elif label == selected_label:
                                is_new_label = False
                                break
                        
                        # 新标签会在创建检测框后自动添加到标签列表中
                        # 因为update_label_list会从检测框中提取标签
                        
                        # 创建新的检测框
                        new_box = {
                            "x": x,
                            "y": y,
                            "width": width,
                            "height": height,
                            "label": selected_label
                        }
                        
                        # 添加到检测框列表
                        self.parent.detection_boxes.append(new_box)
                        
                        # 更新检测框字典
                        if self.parent.current_background_index >= 0:
                            self.parent.detection_boxes_dict[self.parent.current_background_index] = self.parent.detection_boxes.copy()
                        
                        # 更新标签列表
                        self.parent.update_label_list()
                        
                        # 保存检测框到文件
                        if self.parent.current_background and self.parent.current_background_index >= 0:
                            # 获取当前背景图的路径
                            background_path = self.parent.background_images[self.parent.current_background_index]
                            # 获取背景图的文件名
                            background_name = os.path.basename(background_path)
                            # 调用save_json方法保存检测框信息，传入空的canvas_items确保不包含贴图信息
                            self.parent.save_json(background_path, background_name, "", canvas_items=[])
                
                # 重置绘制状态
                self.draw_start_pos = None
                self.temp_draw_box = None
                # 绘制完成后自动退出绘制模式
                self.is_drawing_box = False
                # 恢复箭头光标
                self.setCursor(Qt.ArrowCursor)
                # 更新按钮文本
                if hasattr(self.parent, 'draw_box_btn'):
                    self.parent.draw_box_btn.setText("绘制BOX(W)")
                self.update()
                return
        
        if event.button() == Qt.RightButton:
            # 检查是否点击了贴图
            item_index = self.find_item_at_position(event.pos())
            if item_index is not None:
                # 显示右键菜单，允许用户选择贴图标签
                menu = QMenu(self)
                
                # 获取贴图标签列表中的所有标签
                label_items = []
                for i in range(self.parent.paste_label_list.count()):
                    label = self.parent.paste_label_list.item(i).text()
                    # 提取纯标签名称，去除"(count)"部分
                    if " (" in label:
                        pure_label = label.split(" (")[0]
                        label_items.append(pure_label)
                    else:
                        label_items.append(label)
                
                # 添加标签选择选项
                for label in label_items:
                    action = QAction(label, self)
                    action.triggered.connect(lambda checked, l=label, idx=item_index: self.change_item_label(idx, l))
                    menu.addAction(action)
                
                # 添加分隔线
                menu.addSeparator()
                
                # 添加"添加新标签"选项
                new_label_action = QAction("添加新标签", self)
                new_label_action.triggered.connect(lambda checked, idx=item_index: self.add_new_label(idx))
                menu.addAction(new_label_action)
                
                # 显示菜单
                menu.exec_(event.globalPos())
                return
        elif event.button() != Qt.LeftButton:
            return
        
        # 如果已经有选中的贴图，检查是否点击了缩放手柄或贴图主体
        if self.parent.selected_item is not None:
            pixmap, rect, label = self.parent.canvas_items[self.parent.selected_item]
            if self.parent.current_background is not None:
                # 计算背景图的实际绘制区域
                background_rect = self.get_background_rect()
                
                # 将贴图的相对坐标转换为画布坐标
                item_x = (rect.x() * self.background_scale) + background_rect.left()
                item_y = (rect.y() * self.background_scale) + background_rect.top()
                item_width = rect.width() * self.background_scale
                item_height = rect.height() * self.background_scale
                
                # 计算贴图在画布上的实际矩形
                item_rect = QRectF(item_x, item_y, item_width, item_height)
                
                if item_rect.contains(mouse_pos):
                    # 检查是否点击了缩放手柄（只允许右下角缩放）
                    handle_size = 10
                    br_handle = item_rect.bottomRight()
                    
                    if abs(mouse_pos.x() - br_handle.x()) <= handle_size and \
                       abs(mouse_pos.y() - br_handle.y()) <= handle_size:
                        self.resize_handle = 'br'
                        self.resize_start = mouse_pos
                        return
                    
                    # 点击了图片主体，开始拖拽
                    # 计算相对于贴图左上角的偏移量（画布坐标）
                    self.drag_start = mouse_pos - item_rect.topLeft()
                    self.is_dragging_item = True
                    return
        
        # 检查是否点击了检测框
        if self.parent.show_labels_checkbox.isChecked() and self.parent.current_background is not None:
            background_rect = self.get_background_rect()
            if background_rect is not None:
                for i, box in enumerate(self.parent.detection_boxes):
                    # 计算检测框在画布上的位置
                    box_x = (box["x"] * self.background_scale) + background_rect.left()
                    box_y = (box["y"] * self.background_scale) + background_rect.top()
                    box_width = box["width"] * self.background_scale
                    box_height = box["height"] * self.background_scale
                    box_rect = QRectF(box_x, box_y, box_width, box_height)
                    
                    # 计算调整手柄的位置和区域
                    handle_size = 8
                    # 右下角调整手柄
                    br_handle_center = QPointF(box_x + box_width, box_y + box_height)
                    br_handle_rect = QRectF(
                        br_handle_center.x() - handle_size // 2,
                        br_handle_center.y() - handle_size // 2,
                        handle_size, handle_size
                    )
                    # 左上角调整手柄
                    tl_handle_center = QPointF(box_x, box_y)
                    tl_handle_rect = QRectF(
                        tl_handle_center.x() - handle_size // 2,
                        tl_handle_center.y() - handle_size // 2,
                        handle_size, handle_size
                    )
                    # 右上角调整手柄
                    tr_handle_center = QPointF(box_x + box_width, box_y)
                    tr_handle_rect = QRectF(
                        tr_handle_center.x() - handle_size // 2,
                        tr_handle_center.y() - handle_size // 2,
                        handle_size, handle_size
                    )
                    # 左下角调整手柄
                    bl_handle_center = QPointF(box_x, box_y + box_height)
                    bl_handle_rect = QRectF(
                        bl_handle_center.x() - handle_size // 2,
                        bl_handle_center.y() - handle_size // 2,
                        handle_size, handle_size
                    )
                    
                    if br_handle_rect.contains(mouse_pos):
                        # 点击了右下角调整手柄，开始调整大小
                        self.selected_box = i
                        self.box_resize_start = mouse_pos
                        self.is_resizing_box = True
                        self.resize_handle = "br"  # 记录是哪个手柄
                        # 取消贴图选择
                        self.parent.selected_item = None
                        self.selected_item_size = None
                        
                        # 更新状态栏显示，显示检测框的宽高信息
                        self.update_status_label()
                        
                        self.update()
                        return
                    elif tl_handle_rect.contains(mouse_pos):
                        # 点击了左上角调整手柄，开始调整大小
                        self.selected_box = i
                        self.box_resize_start = mouse_pos
                        self.is_resizing_box = True
                        self.resize_handle = "tl"  # 记录是哪个手柄
                        # 取消贴图选择
                        self.parent.selected_item = None
                        self.selected_item_size = None
                        
                        # 更新状态栏显示，显示检测框的宽高信息
                        self.update_status_label()
                        
                        self.update()
                        return
                    elif tr_handle_rect.contains(mouse_pos):
                        # 点击了右上角调整手柄，开始调整大小
                        self.selected_box = i
                        self.box_resize_start = mouse_pos
                        self.is_resizing_box = True
                        self.resize_handle = "tr"  # 记录是哪个手柄
                        # 取消贴图选择
                        self.parent.selected_item = None
                        self.selected_item_size = None
                        
                        # 更新状态栏显示，显示检测框的宽高信息
                        self.update_status_label()
                        
                        self.update()
                        return
                    elif bl_handle_rect.contains(mouse_pos):
                        # 点击了左下角调整手柄，开始调整大小
                        self.selected_box = i
                        self.box_resize_start = mouse_pos
                        self.is_resizing_box = True
                        self.resize_handle = "bl"  # 记录是哪个手柄
                        # 取消贴图选择
                        self.parent.selected_item = None
                        self.selected_item_size = None
                        
                        # 更新状态栏显示，显示检测框的宽高信息
                        self.update_status_label()
                        
                        self.update()
                        return
                    elif box_rect.contains(mouse_pos):
                        # 选中检测框并开始拖动
                        self.selected_box = i
                        self.box_drag_start = mouse_pos
                        self.is_dragging_box = True
                        # 取消贴图选择
                        self.parent.selected_item = None
                        self.selected_item_size = None
                        
                        # 更新状态栏显示，显示检测框的宽高信息
                        self.update_status_label()
                        
                        self.update()
                        return
        
        # 检查是否点击了背景图，且背景图大于画布
        if self.parent.current_background is not None:
            # 计算背景图的实际绘制区域
            background_rect = self.get_background_rect()
            
            # 检查鼠标是否在背景图上
            if background_rect.contains(mouse_pos):
                # 计算背景图的实际大小
                scaled_width = self.parent.current_background.width() * self.background_scale
                scaled_height = self.parent.current_background.height() * self.background_scale
                
                # 检查背景图是否大于画布
                if scaled_width > self.width() or scaled_height > self.height():
                    # 开始拖动背景图
                    self.drag_start = mouse_pos
                    self.is_dragging_background = True
                    return
        
        # 检查是否点击了贴图
        item_index = self.find_item_at_position(mouse_pos)
        if item_index is not None:
            # 点击了贴图，保持当前状态，不退出编辑
            return
        
        # 点击了空白区域，取消选择
        self.parent.selected_item = None
        self.selected_item_size = None
        self.selected_box = None
        self.update_status_label()
        self.update()
    
    def resizeEvent(self, event):
        # 当窗口大小变化时，触发重新绘制
        # 如果没有手动缩放，背景图会自动适配新的窗口大小
        self.update()
        super().resizeEvent(event)

    def mouseMoveEvent(self, event):
        mouse_pos = event.pos()
        
        # 更新鼠标位置
        self.mouse_pos = mouse_pos
        
        # 更新状态栏显示
        self.update_status_label()
        
        # 绘制模式下的处理
        if self.is_drawing_box:
            # 更新鼠标位置
            self.mouse_pos = mouse_pos
            
            # 如果已经开始绘制，更新临时绘制框的大小
            if self.draw_start_pos is not None:
                # 确保临时绘制框不超出背景图范围
                background_rect = self.get_background_rect()
                if background_rect is not None:
                    # 限制鼠标位置在背景图范围内
                    constrained_pos = mouse_pos
                    constrained_pos.setX(max(background_rect.left(), min(constrained_pos.x(), background_rect.right())))
                    constrained_pos.setY(max(background_rect.top(), min(constrained_pos.y(), background_rect.bottom())))
                    
                    # 计算矩形的正确位置和大小（支持任意方向绘制）
                    x1 = min(self.draw_start_pos.x(), constrained_pos.x())
                    y1 = min(self.draw_start_pos.y(), constrained_pos.y())
                    x2 = max(self.draw_start_pos.x(), constrained_pos.x())
                    y2 = max(self.draw_start_pos.y(), constrained_pos.y())
                    
                    # 更新临时绘制框
                    self.temp_draw_box = QRectF(x1, y1, x2 - x1, y2 - y1)
                    
                    # 更新状态栏显示
                    self.update_status_label()
                else:
                    # 计算矩形的正确位置和大小（支持任意方向绘制）
                    x1 = min(self.draw_start_pos.x(), mouse_pos.x())
                    y1 = min(self.draw_start_pos.y(), mouse_pos.y())
                    x2 = max(self.draw_start_pos.x(), mouse_pos.x())
                    y2 = max(self.draw_start_pos.y(), mouse_pos.y())
                    
                    # 更新临时绘制框
                    self.temp_draw_box = QRectF(x1, y1, x2 - x1, y2 - y1)
            
            # 即使还没有开始绘制，也更新画布以显示十字虚线
            self.update()
            return
        
        # 拖动背景图
        if self.is_dragging_background:
            # 计算偏移量
            delta = mouse_pos - self.drag_start
            self.background_offset += delta
            self.drag_start = mouse_pos
            self.update()
            return
        
        # 拖动检测框
        if self.is_dragging_box and self.selected_box is not None and 0 <= self.selected_box < len(self.parent.detection_boxes):
            # 计算偏移量
            delta = mouse_pos - self.box_drag_start
            
            # 获取背景图信息
            background_rect = self.get_background_rect()
            if background_rect is not None:
                # 转换偏移量到背景图坐标
                delta_x = delta.x() / self.background_scale
                delta_y = delta.y() / self.background_scale
                
                # 获取当前检测框
                box = self.parent.detection_boxes[self.selected_box]
                
                # 计算新位置
                new_x = box["x"] + delta_x
                new_y = box["y"] + delta_y
                
                # 确保检测框不超出背景图范围
                if self.parent.current_background is not None:
                    bg_width = self.parent.current_background.width()
                    bg_height = self.parent.current_background.height()
                    new_x = max(0, new_x)
                    new_y = max(0, new_y)
                    new_x = min(new_x, bg_width - box["width"])
                    new_y = min(new_y, bg_height - box["height"])
                
                # 更新检测框位置
                box["x"] = new_x
                box["y"] = new_y
                
                # 更新拖动起始位置
                self.box_drag_start = mouse_pos
                
                # 更新检测框字典中的数据
                if self.parent.current_background_index in self.parent.detection_boxes_dict:
                    self.parent.detection_boxes_dict[self.parent.current_background_index][self.selected_box] = box.copy()
                
                # 同步更新到原始json文件
                if self.parent.current_background and self.parent.current_background_index >= 0:
                    # 获取当前背景图的路径
                    background_path = self.parent.background_images[self.parent.current_background_index]
                    # 获取背景图的文件名
                    background_name = os.path.basename(background_path)
                    # 调用save_json方法保存检测框信息，传入空的canvas_items确保不包含贴图信息
                    self.parent.save_json(background_path, background_name, "", canvas_items=[])
                
                self.update()
            return
        
        # 调整检测框大小
        if self.is_resizing_box and self.selected_box is not None and 0 <= self.selected_box < len(self.parent.detection_boxes):
            # 计算偏移量
            delta = mouse_pos - self.box_resize_start
            
            # 获取背景图信息
            background_rect = self.get_background_rect()
            if background_rect is not None:
                # 转换偏移量到背景图坐标
                delta_x = delta.x() / self.background_scale
                delta_y = delta.y() / self.background_scale
                
                # 获取当前检测框
                box = self.parent.detection_boxes[self.selected_box]
                
                # 计算检测框的四个角坐标
                box_x = box["x"]
                box_y = box["y"]
                box_width = box["width"]
                box_height = box["height"]
                
                # 计算四个角的原始位置
                tl_x, tl_y = box_x, box_y  # 左上角
                tr_x, tr_y = box_x + box_width, box_y  # 右上角
                bl_x, bl_y = box_x, box_y + box_height  # 左下角
                br_x, br_y = box_x + box_width, box_y + box_height  # 右下角
                
                # 新的坐标
                new_box_x = box_x
                new_box_y = box_y
                new_box_width = box_width
                new_box_height = box_height
                
                if self.resize_handle == "br":
                    # 右下角调整：只移动右下角，其他三个角固定
                    # 计算新的右下角位置
                    new_br_x = br_x + delta_x
                    new_br_y = br_y + delta_y
                    
                    # 确保检测框不超出背景图范围
                    if self.parent.current_background is not None:
                        bg_width = self.parent.current_background.width()
                        bg_height = self.parent.current_background.height()
                        new_br_x = max(tl_x + 10, new_br_x)  # 最小宽度10
                        new_br_y = max(tl_y + 10, new_br_y)  # 最小高度10
                        new_br_x = min(new_br_x, bg_width)
                        new_br_y = min(new_br_y, bg_height)
                    else:
                        new_br_x = max(tl_x + 10, new_br_x)  # 最小宽度10
                        new_br_y = max(tl_y + 10, new_br_y)  # 最小高度10
                    
                    # 计算新的检测框参数
                    new_box_width = new_br_x - tl_x
                    new_box_height = new_br_y - tl_y
                    
                elif self.resize_handle == "tl":
                    # 左上角调整：只移动左上角，其他三个角固定
                    # 计算新的左上角位置
                    new_tl_x = tl_x + delta_x
                    new_tl_y = tl_y + delta_y
                    
                    # 确保检测框不超出背景图范围
                    if self.parent.current_background is not None:
                        bg_width = self.parent.current_background.width()
                        bg_height = self.parent.current_background.height()
                        new_tl_x = max(0, new_tl_x)
                        new_tl_y = max(0, new_tl_y)
                        new_tl_x = min(new_tl_x, br_x - 10)  # 最小宽度10
                        new_tl_y = min(new_tl_y, br_y - 10)  # 最小高度10
                    else:
                        new_tl_x = max(0, new_tl_x)
                        new_tl_y = max(0, new_tl_y)
                        new_tl_x = min(new_tl_x, br_x - 10)  # 最小宽度10
                        new_tl_y = min(new_tl_y, br_y - 10)  # 最小高度10
                    
                    # 计算新的检测框参数
                    new_box_x = new_tl_x
                    new_box_y = new_tl_y
                    new_box_width = br_x - new_tl_x
                    new_box_height = br_y - new_tl_y
                    
                elif self.resize_handle == "tr":
                    # 右上角调整：只移动右上角，其他三个角固定
                    # 计算新的右上角位置
                    new_tr_x = tr_x + delta_x
                    new_tr_y = tr_y + delta_y
                    
                    # 确保检测框不超出背景图范围
                    if self.parent.current_background is not None:
                        bg_width = self.parent.current_background.width()
                        bg_height = self.parent.current_background.height()
                        new_tr_x = max(bl_x + 10, new_tr_x)  # 最小宽度10
                        new_tr_y = max(0, new_tr_y)
                        new_tr_x = min(new_tr_x, bg_width)
                        new_tr_y = min(new_tr_y, bl_y - 10)  # 最小高度10
                    else:
                        new_tr_x = max(bl_x + 10, new_tr_x)  # 最小宽度10
                        new_tr_y = max(0, new_tr_y)
                        new_tr_y = min(new_tr_y, bl_y - 10)  # 最小高度10
                    
                    # 计算新的检测框参数
                    new_box_y = new_tr_y
                    new_box_width = new_tr_x - bl_x
                    new_box_height = bl_y - new_tr_y
                    
                elif self.resize_handle == "bl":
                    # 左下角调整：只移动左下角，其他三个角固定
                    # 计算新的左下角位置
                    new_bl_x = bl_x + delta_x
                    new_bl_y = bl_y + delta_y
                    
                    # 确保检测框不超出背景图范围
                    if self.parent.current_background is not None:
                        bg_width = self.parent.current_background.width()
                        bg_height = self.parent.current_background.height()
                        new_bl_x = max(0, new_bl_x)
                        new_bl_y = max(tr_y + 10, new_bl_y)  # 最小高度10
                        new_bl_x = min(new_bl_x, tr_x - 10)  # 最小宽度10
                        new_bl_y = min(new_bl_y, bg_height)
                    else:
                        new_bl_x = max(0, new_bl_x)
                        new_bl_y = max(tr_y + 10, new_bl_y)  # 最小高度10
                        new_bl_x = min(new_bl_x, tr_x - 10)  # 最小宽度10
                    
                    # 计算新的检测框参数
                    new_box_x = new_bl_x
                    new_box_width = tr_x - new_bl_x
                    new_box_height = new_bl_y - tr_y
                
                # 更新检测框
                box["x"] = new_box_x
                box["y"] = new_box_y
                box["width"] = new_box_width
                box["height"] = new_box_height
                
                # 更新拖动起始位置
                self.box_resize_start = mouse_pos
                
                # 更新检测框字典中的数据
                if self.parent.current_background_index in self.parent.detection_boxes_dict:
                    self.parent.detection_boxes_dict[self.parent.current_background_index][self.selected_box] = box.copy()
                
                # 同步更新到原始json文件
                if self.parent.current_background and self.parent.current_background_index >= 0:
                    # 获取当前背景图的路径（从元组中提取）
                    background_path = self.parent.background_images[self.parent.current_background_index][0]
                    # 获取背景图的文件名
                    background_name = os.path.basename(background_path)
                    # 调用save_json方法保存检测框信息，传入空的canvas_items确保不包含贴图信息
                    self.parent.save_json(background_path, background_name, "", canvas_items=[])
                
                self.update()
            return
        
        # 检查鼠标是否在贴图上，如果是，退出检测框编辑状态
        if self.selected_box is not None:
            item_index = self.find_item_at_position(mouse_pos)
            if item_index is not None:
                # 鼠标在贴图上，退出检测框编辑状态
                self.selected_box = None
                self.update()
        
        # 检测鼠标是否在新的贴图上（无论是否已有选中贴图）
        if not self.is_dragging_item and not self.resize_handle:
            # 检测鼠标位置是否有贴图
            item_at_pos = self.find_item_at_position(mouse_pos)
            
            # 如果鼠标在贴图上，自动选中
            if item_at_pos is not None:
                if self.parent.selected_item != item_at_pos:
                    self.parent.selected_item = item_at_pos
                    # 更新选中贴图的大小
                    _, rect, _ = self.parent.canvas_items[item_at_pos]
                    self.selected_item_size = (rect.width(), rect.height())
                    self.update()
            else:
                # 如果鼠标不在任何贴图上，取消选中
                if self.parent.selected_item is not None:
                    self.parent.selected_item = None
                    self.selected_item_size = None
                    self.update()
        
        # 处理拖拽或缩放操作
        if self.parent.selected_item is not None:
            # 拖拽或缩放贴图片
            if self.is_dragging_item and not self.resize_handle:
                # 拖拽操作
                pixmap, rect, label = self.parent.canvas_items[self.parent.selected_item]
                
                # 计算背景图的实际绘制区域
                background_rect = self.get_background_rect()
                if background_rect is not None:
                    # 计算新的位置（画布坐标）
                    new_pos_canvas = mouse_pos - self.drag_start
                    # 转换为相对背景图的坐标
                    new_pos_x = (new_pos_canvas.x() - background_rect.left()) / self.background_scale
                    new_pos_y = (new_pos_canvas.y() - background_rect.top()) / self.background_scale
                    
                    # 确保贴图在背景图范围内
                    new_pos_x = max(0, new_pos_x)
                    new_pos_y = max(0, new_pos_y)
                    
                    # 确保贴图不超出背景图的右边和下边
                    if self.parent.current_background is not None:
                        bg_width = self.parent.current_background.width()
                        bg_height = self.parent.current_background.height()
                        new_pos_x = min(new_pos_x, bg_width - rect.width())
                        new_pos_y = min(new_pos_y, bg_height - rect.height())
                    
                    new_rect = QRectF(new_pos_x, new_pos_y, rect.width(), rect.height())
                    self.parent.canvas_items[self.parent.selected_item] = (pixmap, new_rect, label)
                
                self.update()
            elif self.resize_handle:
                # 缩放操作
                pixmap, rect, label = self.parent.canvas_items[self.parent.selected_item]
                new_rect = QRectF(rect)
                
                # 计算缩放比例，保持等比缩放
                aspect_ratio = pixmap.width() / pixmap.height()
                
                # 计算当前贴图在画布上的位置
                background_rect = self.get_background_rect()
                if background_rect is not None:
                    # 将鼠标位置转换为相对于贴图左上角的位置（画布坐标）
                    item_x = (rect.x() * self.background_scale) + background_rect.left()
                    item_y = (rect.y() * self.background_scale) + background_rect.top()
                    item_width_canvas = rect.width() * self.background_scale
                    item_height_canvas = rect.height() * self.background_scale
                    
                    if self.resize_handle == 'br':
                        # 右下角：同时调整宽度和高度，保持比例
                        new_width_canvas = max(15, mouse_pos.x() - item_x)
                        new_height_canvas = max(15, mouse_pos.y() - item_y)
                        
                        # 计算宽度和高度的变化比例
                        width_ratio = new_width_canvas / item_width_canvas
                        height_ratio = new_height_canvas / item_height_canvas
                        
                        # 选择较小的比例进行缩放，保持等比
                        scale_ratio = min(width_ratio, height_ratio)
                        
                        new_width = rect.width() * scale_ratio
                        new_height = rect.height() * scale_ratio
                        
                        # 确保最小边不小于15
                        if min(new_width, new_height) < 15:
                            if new_width < new_height:
                                new_width = 15
                                new_height = new_width / aspect_ratio
                            else:
                                new_height = 15
                                new_width = new_height * aspect_ratio
                        
                        # 确保贴图不超过背景图大小
                        if self.parent.current_background is not None:
                            bg_width = self.parent.current_background.width()
                            bg_height = self.parent.current_background.height()
                            
                            # 限制贴图最大尺寸为背景图大小
                            new_width = min(new_width, bg_width - rect.x())
                            new_height = min(new_height, bg_height - rect.y())
                        
                        # 更新贴图尺寸
                        new_rect.setWidth(new_width)
                        new_rect.setHeight(new_height)
                
                self.parent.canvas_items[self.parent.selected_item] = (pixmap, new_rect, label)
                # 更新选中贴图的大小
                self.selected_item_size = (new_rect.width(), new_rect.height())
            
            self.update()
        
        # 只更新鼠标位置显示
        self.update()
    
    def get_background_rect(self):
        """获取背景图在画布上的实际绘制矩形"""
        if self.parent.current_background is None:
            return None
        
        # 计算绘制尺寸
        scaled_width = self.parent.current_background.width() * self.background_scale
        scaled_height = self.parent.current_background.height() * self.background_scale
        
        # 计算居中位置（考虑偏移量）
        x = (self.width() - scaled_width) // 2 + self.background_offset.x()
        y = (self.height() - scaled_height) // 2 + self.background_offset.y()
        
        return QRectF(x, y, scaled_width, scaled_height)
    
    def change_item_label(self, item_index, new_label):
        """更改贴图的标签"""
        if 0 <= item_index < len(self.parent.canvas_items):
            pixmap, rect, _ = self.parent.canvas_items[item_index]
            self.parent.canvas_items[item_index] = (pixmap, rect, new_label)
            self.update()
    
    def add_new_label(self, item_index):
        """添加新标签并应用到贴图"""
        from PyQt5.QtWidgets import QInputDialog
        new_label, ok = QInputDialog.getText(self, "添加新标签", "请输入新标签名称：")
        if ok and new_label.strip():
            # 添加新标签到贴图标签列表
            self.parent.paste_label_list.addItem(new_label.strip())
            # 应用新标签到贴图
            if 0 <= item_index < len(self.parent.canvas_items):
                pixmap, rect, _ = self.parent.canvas_items[item_index]
                self.parent.canvas_items[item_index] = (pixmap, rect, new_label.strip())
                self.update()
    
    def update_status_label(self):
        """更新状态栏显示"""
        # 只有当背景图片加载且鼠标在画布内时才显示坐标
        if self.parent.current_background is not None and self.mouse_inside:
            # 计算相对于背景图左上角的坐标（原图坐标）
            background_rect = self.get_background_rect()
            if background_rect is not None:
                # 将鼠标的画布坐标转换为相对于背景图左上角的坐标
                rel_x = self.mouse_pos.x() - background_rect.left()
                rel_y = self.mouse_pos.y() - background_rect.top()
                # 转换为原图坐标（除以缩放比例）
                orig_x = rel_x / self.background_scale
                orig_y = rel_y / self.background_scale
            else:
                orig_x = self.mouse_pos.x()
                orig_y = self.mouse_pos.y()
            
            # 构建状态文本
            status_text = f"X: {int(orig_x)}, Y: {int(orig_y)}"
            
            # 如果有选中的贴图，显示其大小
            if self.selected_item_size is not None:
                width, height = self.selected_item_size
                status_text += f" | W: {int(width)}, H: {int(height)}"
            # 如果有选中的检测框，显示其大小
            elif self.selected_box is not None and 0 <= self.selected_box < len(self.parent.detection_boxes):
                box = self.parent.detection_boxes[self.selected_box]
                width = box["width"]
                height = box["height"]
                status_text += f" | W: {int(width)}, H: {int(height)}"
            # 如果正在绘制检测框，显示临时绘制框的大小
            elif self.is_drawing_box and self.temp_draw_box is not None:
                # 计算临时绘制框的宽度和高度（转换为原图坐标）
                width = self.temp_draw_box.width() / self.background_scale
                height = self.temp_draw_box.height() / self.background_scale
                status_text += f" | W: {int(width)}, H: {int(height)}"
            
            # 更新状态栏
            self.parent.status_label.setText(status_text)
        else:
            # 当没有背景图片或鼠标不在画布内时，清空状态栏
            self.parent.status_label.setText("")
    
    def enterEvent(self, event):
        """鼠标进入画布时的处理"""
        self.mouse_inside = True
        self.update_status_label()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开画布时的处理"""
        self.mouse_inside = False
        self.update_status_label()
        super().leaveEvent(event)
    
    def find_item_at_position(self, pos):
        """查找指定位置是否有贴图，返回贴图索引"""
        if self.parent.current_background is None:
            return None
        
        background_rect = self.get_background_rect()
        if background_rect is None:
            return None
        
        # 从后往前遍历（后添加的贴图在上层）
        for i in range(len(self.parent.canvas_items) - 1, -1, -1):
            pixmap, rect, label = self.parent.canvas_items[i]
            
            # 计算贴图在画布上的位置
            item_x = (rect.x() * self.background_scale) + background_rect.left()
            item_y = (rect.y() * self.background_scale) + background_rect.top()
            item_width = rect.width() * self.background_scale
            item_height = rect.height() * self.background_scale
            
            # 检查鼠标是否在贴图范围内
            if (item_x <= pos.x() <= item_x + item_width and
                item_y <= pos.y() <= item_y + item_height):
                return i
        
        return None
    
    def wheelEvent(self, event):
        """处理鼠标滚轮事件，实现背景图缩放"""
        if self.parent.current_background is None:
            return
        
        # 获取滚轮角度
        delta = event.angleDelta().y()
        # 定义缩放因子
        scale_factor = 1.1 if delta > 0 else 0.9
        
        # 更新背景图缩放比例
        self.background_scale *= scale_factor
        
        # 限制缩放范围，防止过大或过小
        self.background_scale = max(0.5, min(self.background_scale, 3.0))
        
        # 标记为手动缩放，禁用自动适配
        self.is_manual_scale = True
        
        # 刷新画布
        self.update()
    
    def keyPressEvent(self, event):
        """处理键盘事件：Delete键或E键删除选中的贴图，Ctrl+F重置背景图缩放，Q键退出绘制模式"""
        if event.key() == Qt.Key_Delete or event.key() == Qt.Key_E:
            if self.parent.selected_item is not None and self.parent.selected_item < len(self.parent.canvas_items):
                # 删除选中的贴图
                del self.parent.canvas_items[self.parent.selected_item]
                self.parent.selected_item = None
                self.selected_item_size = None
                self.update_status_label()
                self.update()
        elif event.key() == Qt.Key_F and event.modifiers() & Qt.ControlModifier:
            # Ctrl+F 重置背景图缩放
            self.background_scale = 1.0
            self.background_offset = QPoint(0, 0)
            self.is_manual_scale = False  # 重置为自动适配模式
            self.update()
        elif event.key() == Qt.Key_Q:
            # 按Q键退出绘制模式
            if self.is_dragging_box:
                self.is_dragging_box = False
            if self.is_resizing_box:
                self.is_resizing_box = False
            if self.is_drawing_box:
                self.is_drawing_box = False
                self.draw_start_pos = None
                self.temp_draw_box = None
                # 恢复箭头光标
                self.setCursor(Qt.ArrowCursor)
                # 更新按钮文本
                if hasattr(self.parent, 'draw_box_btn'):
                    self.parent.draw_box_btn.setText("绘制BOX(W)")
                self.update()
        super().keyPressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """处理鼠标释放事件"""
        # 取消所有拖动状态
        self.is_dragging_item = False
        self.is_dragging_background = False
        self.is_dragging_box = False
        self.is_resizing_box = False
        self.resize_handle = None
        self.update()
    
    def contextMenuEvent(self, event):
        """处理右键菜单事件，用于修改检测框标签"""
        mouse_pos = event.pos()
        
        # 检查是否点击了检测框
        if self.parent.show_labels_checkbox.isChecked() and self.parent.current_background is not None:
            background_rect = self.get_background_rect()
            if background_rect is not None:
                for i, box in enumerate(self.parent.detection_boxes):
                    # 计算检测框在画布上的位置
                    box_x = (box["x"] * self.background_scale) + background_rect.left()
                    box_y = (box["y"] * self.background_scale) + background_rect.top()
                    box_width = box["width"] * self.background_scale
                    box_height = box["height"] * self.background_scale
                    box_rect = QRectF(box_x, box_y, box_width, box_height)
                    
                    if box_rect.contains(mouse_pos):
                        # 点击了检测框，显示标签选择菜单
                        self.selected_box = i
                        self.show_label_context_menu(event.globalPos())
                        return
    
    def show_label_context_menu(self, pos):
        """显示标签选择右键菜单"""
        menu = QMenu()
        
        # 添加标签列表选项
        for i in range(self.parent.label_list.count()):
            # 从标签文本中提取纯标签名称，去除"(count)"部分
            label_text = self.parent.label_list.item(i).text()
            if " (" in label_text:
                pure_label = label_text.split(" (")[0]
            else:
                pure_label = label_text
            action = menu.addAction(pure_label)
            action.triggered.connect(lambda checked, l=pure_label: self.change_box_label(l))
        
        # 添加分隔线
        menu.addSeparator()
        
        # 添加"添加新标签"选项
        new_label_action = QAction("添加新标签", self)
        new_label_action.triggered.connect(self.add_new_label_for_box)
        menu.addAction(new_label_action)
        
        # 显示菜单
        menu.exec_(pos)
    
    def add_new_label_for_box(self):
        """添加新标签并应用到检测框"""
        from PyQt5.QtWidgets import QInputDialog
        new_label, ok = QInputDialog.getText(self, "添加新标签", "请输入新标签名称：")
        if ok and new_label.strip():
            # 应用新标签到检测框
            if self.selected_box is not None and 0 <= self.selected_box < len(self.parent.detection_boxes):
                # 更新检测框标签
                self.parent.detection_boxes[self.selected_box]["label"] = new_label.strip()
                
                # 更新detection_boxes_dict中对应背景图的检测框
                if self.parent.current_background_index >= 0:
                    self.parent.detection_boxes_dict[self.parent.current_background_index] = self.parent.detection_boxes.copy()
                
                # 更新标签列表，确保数目显示正确
                self.parent.update_label_list()
                
                # 更新画布
                self.update()
    
    def change_box_label(self, new_label):
        """修改检测框的标签"""
        if self.selected_box is not None and 0 <= self.selected_box < len(self.parent.detection_boxes):
            # 更新检测框标签
            self.parent.detection_boxes[self.selected_box]["label"] = new_label
            
            # 更新detection_boxes_dict中对应背景图的检测框
            if self.parent.current_background_index >= 0:
                self.parent.detection_boxes_dict[self.parent.current_background_index] = self.parent.detection_boxes.copy()
                
                # 保存修改到JSON文件
                if self.parent.current_background and self.parent.current_background_index >= 0:
                    background_path = self.parent.background_images[self.parent.current_background_index]
                    background_name = os.path.basename(background_path)
                    # 调用save_json方法保存检测框信息，传入空的canvas_items确保不包含贴图信息
                    self.parent.save_json(background_path, background_name, "", canvas_items=[])
            
            # 更新标签列表，确保数目显示正确
            self.parent.update_label_list()
            
            # 更新画布
            self.update()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = ImageEditor()
    editor.show()
    sys.exit(app.exec_())
