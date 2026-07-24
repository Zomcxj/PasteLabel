import copy
import json
import os
import random
from typing import Callable, Dict, List, Tuple, Type

from PyQt5.QtGui import QImage

from .base import BaseTransform, get_all_transforms, register_transform

from . import flipt, color, noise, translate, rotate, scale


class Augmenter:

    def __init__(self, output_dir: str, on_progress: Callable = None,
                 is_interrupted: Callable = None, on_transform_progress: Callable = None):
        self.output_dir = os.path.join(output_dir, "images")
        self.on_progress = on_progress
        self.is_interrupted = is_interrupted or (lambda: False)
        self.on_transform_progress = on_transform_progress

    def run(
        self,
        background_images: List[str],
        detection_boxes_dict: Dict[int, List[dict]],
        transform_specs: List[Tuple[Type[BaseTransform], Dict[str, Tuple[float, float]]]],
        image_ratio: float = 1.0,
        mode: str = "all",
        include_original: bool = False,
    ) -> List[dict]:
        os.makedirs(self.output_dir, exist_ok=True)
        total = len(background_images)
        results = []

        if include_original:
            for idx in range(total):
                img_path = background_images[idx]
                base = os.path.splitext(os.path.basename(img_path))[0]
                ext = os.path.splitext(img_path)[1].lower()
                if ext not in ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'):
                    ext = '.jpg'
                boxes = detection_boxes_dict.get(idx, [])
                self._save_original(img_path, base, ext, boxes, results)

        if mode == "random":
            results = self._run_random(background_images, detection_boxes_dict,
                                       transform_specs, image_ratio, total, results)
        else:
            results = self._run_all(background_images, detection_boxes_dict,
                                    transform_specs, image_ratio, total, results)
        return results

    def _run_all(self, background_images, detection_boxes_dict,
                 transform_specs, image_ratio, total, results=None):
        if results is None:
            results = []
        for cls, ranges in transform_specs:
            if self.is_interrupted():
                break
            t_name = cls.__name__
            if self.on_transform_progress:
                self.on_transform_progress(t_name, 0, total)
            for idx in range(total):
                if self.is_interrupted():
                    break
                if random.random() >= image_ratio:
                    if self.on_transform_progress:
                        self.on_transform_progress(t_name, idx + 1, total)
                    continue
                img_path = background_images[idx]
                base = os.path.splitext(os.path.basename(img_path))[0]
                ext = os.path.splitext(img_path)[1].lower()
                if ext not in ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'):
                    ext = '.jpg'
                boxes = detection_boxes_dict.get(idx, [])
                original_image = QImage(img_path)
                iw = original_image.width()
                ih = original_image.height()
                kwargs = self._build_kwargs(cls, ranges, "all")
                t = cls(**kwargs)
                img_copy = original_image.copy()
                boxes_copy = copy.deepcopy(boxes)
                img_copy, boxes_copy = t.apply(img_copy, boxes_copy, iw, ih)
                suffix = "_" + t.name
                out_name = base + suffix + ext
                img_copy.save(os.path.join(self.output_dir, out_name))
                self._save_labelme_json(
                    os.path.join(self.output_dir, base + suffix + ".json"),
                    out_name, boxes_copy, img_copy.width(), img_copy.height()
                )
                results.append({
                    "image": img_copy, "boxes": boxes_copy,
                    "width": img_copy.width(), "height": img_copy.height(),
                    "stem": base + suffix
                })
                if self.on_transform_progress:
                    self.on_transform_progress(t_name, idx + 1, total)
        return results

    def _run_random(self, background_images, detection_boxes_dict,
                    transform_specs, image_ratio, total, results=None):
        if results is None:
            results = []
        for idx in range(total):
            if self.is_interrupted():
                break
            img_path = background_images[idx]
            base = os.path.splitext(os.path.basename(img_path))[0]
            ext = os.path.splitext(img_path)[1].lower()
            if ext not in ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'):
                ext = '.jpg'
            boxes = detection_boxes_dict.get(idx, [])
            original_image = QImage(img_path)
            original_boxes = copy.deepcopy(boxes)
            iw = original_image.width()
            ih = original_image.height()
            n = random.randint(1, len(transform_specs))
            active = random.sample(transform_specs, n)
            any_applied = False
            for cls, ranges in active:
                if random.random() >= image_ratio:
                    continue
                any_applied = True
                kwargs = self._build_kwargs(cls, ranges, "random")
                t = cls(**kwargs)
                img_copy = original_image.copy()
                boxes_copy = copy.deepcopy(original_boxes)
                img_copy, boxes_copy = t.apply(img_copy, boxes_copy, iw, ih)
                suffix = "_" + t.name
                out_name = base + suffix + ext
                img_copy.save(os.path.join(self.output_dir, out_name))
                self._save_labelme_json(
                    os.path.join(self.output_dir, base + suffix + ".json"),
                    out_name, boxes_copy, img_copy.width(), img_copy.height()
                )
                results.append({
                    "image": img_copy, "boxes": boxes_copy,
                    "width": img_copy.width(), "height": img_copy.height(),
                    "stem": base + suffix
                })
            if not any_applied:
                self._save_original(img_path, base, ext, boxes, results)
            if self.on_progress:
                self.on_progress(idx + 1, total)
        return results

    def _build_kwargs(self, cls, ranges, mode):
        kwargs = {}
        for pname, (vmin, vmax) in ranges.items():
            kwargs[pname] = random.uniform(vmin, vmax) if mode == "random" else (vmin + vmax) / 2
        if cls.__name__ in ("RandomRotation", "RandomScale"):
            if "angle" in kwargs:
                kwargs["max_angle"] = abs(kwargs.pop("angle"))
            if "scale" in kwargs:
                v = kwargs.pop("scale")
                kwargs["min"] = min(v, 1.0)
                kwargs["max"] = max(v, 1.0)
        if cls.__name__ == "RandomTranslate":
            if "offset" in kwargs:
                v = int(abs(kwargs.pop("offset")))
                kwargs["max_dx"] = v
                kwargs["max_dy"] = v
        if cls.__name__ in ("Brightness", "Hue", "Value") and "delta" in kwargs:
            kwargs["delta"] = int(kwargs["delta"])
        if cls.__name__ == "GaussianNoise" and "sigma" in kwargs:
            kwargs["sigma"] = int(kwargs["sigma"])
        return kwargs

    def _save_original(self, img_path, base, ext, boxes, results):
        data = QImage(img_path)
        out_img = os.path.join(self.output_dir, base + ext)
        if not os.path.exists(out_img):
            data.save(out_img)
        out_json = os.path.join(self.output_dir, base + ".json")
        if not os.path.exists(out_json):
            self._save_labelme_json(out_json, base + ext, boxes, data.width(), data.height())
        results.append({
            "image": data, "boxes": boxes,
            "width": data.width(), "height": data.height(),
            "stem": base
        })

    def _save_labelme_json(self, json_path, image_name, boxes, width, height):
        shapes = []
        for b in boxes:
            x, y, w, h = b["x"], b["y"], b["width"], b["height"]
            shapes.append({
                "label": b["label"],
                "points": [[x, y], [x + w, y], [x + w, y + h], [x, y + h]],
                "group_id": None, "description": "",
                "shape_type": "rectangle", "flags": {}
            })
        data = {
            "version": "5.2.1", "flags": {},
            "shapes": shapes, "imagePath": image_name,
            "imageData": None,
            "imageHeight": height, "imageWidth": width
        }
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
