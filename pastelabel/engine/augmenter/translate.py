import random
from typing import List, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPainter

from .base import BaseTransform, register_transform


@register_transform
class RandomTranslate(BaseTransform):
    name = "trans"

    def __init__(self, max_dx: int = 20, max_dy: int = 20):
        self.max_dx = max(0, min(100, max_dx))
        self.max_dy = max(0, min(100, max_dy))

    def apply(
        self, image: QImage, boxes: List[dict],
        image_width: int, image_height: int
    ) -> Tuple[QImage, List[dict]]:
        dx = random.randint(-self.max_dx, self.max_dx)
        dy = random.randint(-self.max_dy, self.max_dy)
        result = QImage(image.width(), image.height(), QImage.Format_ARGB32)
        result.fill(Qt.black)
        painter = QPainter(result)
        painter.drawImage(dx, dy, image)
        painter.end()
        new_boxes = []
        w = image_width
        h = image_height
        for b in boxes:
            x1 = max(0, b["x"] + dx)
            y1 = max(0, b["y"] + dy)
            x2 = min(w, b["x"] + b["width"] + dx)
            y2 = min(h, b["y"] + b["height"] + dy)
            new_w = x2 - x1
            new_h = y2 - y1
            if new_w < 1 or new_h < 1:
                continue
            new_boxes.append({
                "x": x1,
                "y": y1,
                "width": new_w,
                "height": new_h,
                "label": b["label"]
            })
        return result, new_boxes
