import random
from typing import List, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPainter

from .base import BaseTransform, register_transform


@register_transform
class RandomScale(BaseTransform):
    name = "scale"

    def __init__(self, min: float = 0.8, max: float = 1.2):
        self.min = min
        self.max = max

    def apply(
        self, image: QImage, boxes: List[dict],
        image_width: int, image_height: int
    ) -> Tuple[QImage, List[dict]]:
        scale = random.uniform(self.min, self.max)
        new_w = max(1, int(image_width * scale))
        new_h = max(1, int(image_height * scale))
        scaled = image.scaled(new_w, new_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        if scale >= 1.0:
            result = scaled
        else:
            result = QImage(image_width, image_height, QImage.Format_ARGB32)
            result.fill(Qt.black)
            painter = QPainter(result)
            ox = (image_width - new_w) // 2
            oy = (image_height - new_h) // 2
            painter.drawImage(ox, oy, scaled)
            painter.end()
        new_boxes = []
        for b in boxes:
            bx = b["x"] * scale
            by = b["y"] * scale
            bw = b["width"] * scale
            bh = b["height"] * scale
            if scale < 1.0:
                bx += (image_width - new_w) // 2
                by += (image_height - new_h) // 2
            new_boxes.append({
                "x": bx, "y": by,
                "width": bw, "height": bh,
                "label": b["label"]
            })
        return result, new_boxes
