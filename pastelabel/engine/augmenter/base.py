from abc import ABC, abstractmethod
from typing import Dict, List, Tuple

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

    @abstractmethod
    def apply(
        self, image: QImage, boxes: List[dict],
        image_width: int, image_height: int
    ) -> Tuple[QImage, List[dict]]:
        pass
