import math
import random
from typing import List, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPainter

from .base import BaseTransform, register_transform


@register_transform
class RandomRotation(BaseTransform):
    name = "rotate"

    def __init__(self, max_angle: float = 15, bg: str = "black"):
        self.max_angle = max(0, min(45, max_angle))
        self.bg = bg

    def apply(
        self, image: QImage, boxes: List[dict],
        image_width: int, image_height: int
    ) -> Tuple[QImage, List[dict]]:
        angle = random.uniform(-self.max_angle, self.max_angle)
        cx, cy = image_width / 2.0, image_height / 2.0
        theta = math.radians(angle)
        cos_a = math.cos(theta)
        sin_a = math.sin(theta)
        corners = [(-cx, -cy), (image_width - cx, -cy),
                   (image_width - cx, image_height - cy), (-cx, image_height - cy)]
        new_corners = []
        for x, y in corners:
            nx = x * cos_a - y * sin_a
            ny = x * sin_a + y * cos_a
            new_corners.append((nx, ny))
        xs = [p[0] for p in new_corners]
        ys = [p[1] for p in new_corners]
        new_w = int(math.ceil(max(xs) - min(xs)))
        new_h = int(math.ceil(max(ys) - min(ys)))
        offset_x = cx - (min(xs) + max(xs)) / 2.0
        offset_y = cy - (min(ys) + max(ys)) / 2.0
        result = QImage(new_w, new_h, QImage.Format_ARGB32)
        if self.bg == "black":
            result.fill(Qt.black)
        elif self.bg == "white":
            result.fill(Qt.white)
        else:
            result.fill(Qt.transparent)
        painter = QPainter(result)
        painter.translate(new_w / 2.0, new_h / 2.0)
        painter.rotate(angle)
        painter.drawImage(int(-cx), int(-cy), image)
        painter.end()
        new_boxes = []
        for b in boxes:
            cos_a = math.cos(theta)
            sin_a = math.sin(theta)
            bx, by = b["x"], b["y"]
            bw, bh = b["width"], b["height"]
            box_corners = [(bx, by), (bx + bw, by), (bx + bw, by + bh), (bx, by + bh)]
            rotated = []
            for px, py in box_corners:
                rx = (px - cx) * cos_a - (py - cy) * sin_a + new_w / 2.0
                ry = (px - cx) * sin_a + (py - cy) * cos_a + new_h / 2.0
                rotated.append((rx, ry))
            rxs = [p[0] for p in rotated]
            rys = [p[1] for p in rotated]
            new_x = min(rxs)
            new_y = min(rys)
            new_w_box = max(rxs) - new_x
            new_h_box = max(rys) - new_y
            new_boxes.append({
                "x": new_x, "y": new_y,
                "width": new_w_box, "height": new_h_box,
                "label": b["label"]
            })
        return result, new_boxes
