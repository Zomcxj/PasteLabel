"""
配置文件 - 定义常量配置
"""

# 支持的图片扩展名
SUPPORTED_IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.bmp', '.gif']

# 缩略图配置
THUMBNAIL_CONFIG = {
    'grid_width': 56,  # 网格宽度（像素）
    'grid_height': 60,  # 网格高度（像素）
    'spacing': 2,  # 网格间距（像素）
}

# 贴图参数默认值
PASTE_PARAMS = {
    'default_count': 1,  # 默认贴图个数
    'min_count': 1,  # 最小贴图个数
    'max_count': 20,  # 最大贴图个数
    'default_min_size': 30,  # 默认最小尺寸
    'min_size_range': (15, 100),  # 最小尺寸范围
    'default_max_size': 60,  # 默认最大尺寸
    'max_size_range': (30, 200),  # 最大尺寸范围
}

# 背景图缩放配置
BACKGROUND_SCALE_CONFIG = {
    'default_scale': 1.0,  # 默认缩放比例
    'min_scale': 0.5,  # 最小缩放比例
    'max_scale': 3.0,  # 最大缩放比例
    'scale_factor': 1.1,  # 滚轮缩放因子
}

# 检测框配置
DETECTION_BOX_CONFIG = {
    'min_width': 3,  # 最小宽度
    'min_height': 3,  # 最小高度
    'resize_handle_size': 8,  # 调整手柄大小
    'border_color_selected': (0, 255, 128),  # 选中边框颜色 (RGB)
    'border_color_normal': (0, 255, 128),  # 普通边框颜色 (RGB)
    'fill_color_selected': (0, 255, 128, 50),  # 选中填充颜色 (RGBA)
}

# 贴图配置
PASTE_ITEM_CONFIG = {
    'border_color': (135, 206, 250),  # 天蓝色边框 (RGB)
    'border_width_selected': 3,  # 选中时边框宽度
    'border_width_normal': 1,  # 正常时边框宽度
    'handle_size': 8,  # 缩放手柄大小
    'min_size': 15,  # 最小尺寸
    'base_scale_factor': 0.5,  # 基础缩放因子
}

# 窗口配置
WINDOW_CONFIG = {
    'default_width': 1600,  # 默认窗口宽度
    'default_height': 1000,  # 默认窗口高度
    'canvas_min_width': 800,  # 画布最小宽度
    'canvas_min_height': 600,  # 画布最小高度
    'control_panel_width': 300,  # 控制面板宽度
}

# Labelme JSON 版本
LABELME_VERSION = "5.0.1"

# 输出目录后缀
OUTPUT_DIR_SUFFIX = "_paste_output"

# 默认前缀
DEFAULT_PREFIX = "paste"

# 随机贴图参数
RANDOM_POSITION_CONFIG = {
    'margin_left': 50,       # 左侧边距
    'margin_top': 200,       # 顶部边距
    'margin_right': 100,     # 右侧安全边距
    'max_retries': 1000,     # 最大重试次数
    'overlap_iou_detection': 0.02,  # 与检测框的 IoU 阈值
    'overlap_iou_pasted': 0.1,      # 与已贴图的 IoU 阈值
    'min_edge_size': 35,     # 手动添加贴图最小边
}

# 自动保存配置
AUTO_SAVE_CONFIG = {
    'enabled': False,  # 默认不启用自动保存
}
