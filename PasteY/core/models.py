"""
数据模型模块 - 定义数据结构
"""
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from PyQt5.QtCore import QRectF


@dataclass
class DetectionBox:
    """检测框数据模型"""
    x: float
    y: float
    width: float
    height: float
    label: str
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "label": self.label
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'DetectionBox':
        """从字典创建"""
        return DetectionBox(
            x=data.get("x", 0),
            y=data.get("y", 0),
            width=data.get("width", 0),
            height=data.get("height", 0),
            label=data.get("label", "")
        )
    
    def is_valid(self, min_width: float = 3, min_height: float = 3) -> bool:
        """检测框是否有效"""
        return (self.width > min_width and 
                self.height > min_height and
                not (self.x <= 0 and self.y <= 0))
    
    def get_points(self) -> List[List[float]]:
        """获取四个角点坐标"""
        return [
            [self.x, self.y],
            [self.x + self.width, self.y],
            [self.x + self.width, self.y + self.height],
            [self.x, self.y + self.height]
        ]


@dataclass
class PasteItem:
    """贴图数据模型"""
    pixmap_path: str  # 图片路径
    rect: QRectF  # 位置和大小（相对于背景图）
    label: str  # 标签名称
    
    def to_tuple(self):
        """转换为元组格式 (用于兼容旧代码)"""
        from PyQt5.QtGui import QPixmap
        pixmap = QPixmap(self.pixmap_path)
        return (pixmap, self.rect, self.label)


@dataclass
class BackgroundImage:
    """背景图数据模型"""
    file_path: str
    index: int
    detection_boxes: List[DetectionBox] = field(default_factory=list)
    paste_items: List[PasteItem] = field(default_factory=list)
    
    def get_json_path(self) -> str:
        """获取对应的 JSON 文件路径"""
        import os
        base_name = os.path.splitext(self.file_path)[0]
        return f"{base_name}.json"


@dataclass
class SaveInfo:
    """保存信息数据模型"""
    file_path: str
    base_name: str
    prefix: str
    output_dir: str


@dataclass
class LabelMeShape:
    """Labelme 格式的 Shape 数据"""
    label: str
    points: List[List[float]]
    group_id: Optional[str] = None
    description: str = ""
    shape_type: str = "rectangle"
    flags: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "label": self.label,
            "points": self.points,
            "group_id": self.group_id,
            "description": self.description,
            "shape_type": self.shape_type,
            "flags": self.flags
        }


@dataclass
class LabelMeData:
    """Labelme 格式的完整数据"""
    version: str = "5.0.1"
    flags: dict = field(default_factory=dict)
    shapes: List[LabelMeShape] = field(default_factory=list)
    imagePath: str = ""
    imageData: Optional[str] = None
    imageHeight: int = 0
    imageWidth: int = 0
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "version": self.version,
            "flags": self.flags,
            "shapes": [shape.to_dict() for shape in self.shapes],
            "imagePath": self.imagePath,
            "imageData": self.imageData,
            "imageHeight": self.imageHeight,
            "imageWidth": self.imageWidth
        }
