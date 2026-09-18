from abc import ABC, abstractmethod
from typing import Dict, List, Tuple
import random

from PyQt5.QtGui import QImage

_registered_transforms: Dict[str, type] = {}


def register_transform(cls):
    if issubclass(cls, BaseTransform) and cls is not BaseTransform:
        name = getattr(cls, 'name', None) or cls.__name__.lower()
        _registered_transforms[name] = cls
    return cls


def get_all_transforms() -> Dict[str, type]:
    return dict(_registered_transforms)


class BaseTransform(ABC):
    name: str

    def __init__(self, rng=None):
        # rng 由 Augmenter 注入，用于让随机变换可复现；不传时用全局 random
        self.rng = rng if rng is not None else random

    @abstractmethod
    def apply(
        self, image: QImage, boxes: List[dict],
        image_width: int, image_height: int
    ) -> Tuple[QImage, List[dict]]:
        pass
