from typing import List, Tuple

from PyQt5.QtGui import QImage

from .base import BaseTransform, register_transform


@register_transform
class HorizontalFlip(BaseTransform):
    name = "fliph"

    def apply(
        self, image: QImage, boxes: List[dict],
        image_width: int, image_height: int
    ) -> Tuple[QImage, List[dict]]:
        flipped = image.mirrored(True, False)
        new_boxes = []
        for b in boxes:
            new_boxes.append({
                "x": image_width - b["x"] - b["width"],
                "y": b["y"],
                "width": b["width"],
                "height": b["height"],
                "label": b["label"]
            })
        return flipped, new_boxes


@register_transform
class VerticalFlip(BaseTransform):
    name = "flipv"

    def apply(
        self, image: QImage, boxes: List[dict],
        image_width: int, image_height: int
    ) -> Tuple[QImage, List[dict]]:
        flipped = image.mirrored(False, True)
        new_boxes = []
        for b in boxes:
            new_boxes.append({
                "x": b["x"],
                "y": image_height - b["y"] - b["height"],
                "width": b["width"],
                "height": b["height"],
                "label": b["label"]
            })
        return flipped, new_boxes
