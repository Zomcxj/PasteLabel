import os
import random
from typing import Callable, Dict, List, Optional


class YoloExporter:

    def __init__(self, output_dir: str, on_progress: Callable = None,
                 is_interrupted: Callable = None):
        self.output_dir = output_dir
        self.on_progress = on_progress
        self.is_interrupted = is_interrupted or (lambda: False)

    def run(
        self,
        background_images: List[str],
        detection_boxes_dict: Dict[int, List[dict]],
        selected_labels: List[str],
        skip_empty: bool = False,
        input_data: Optional[List[dict]] = None,
    ):
        if input_data is not None:
            items = []
            self._ensure_dirs()
            for idx, item in enumerate(input_data):
                if self.is_interrupted():
                    break
                boxes = [b for b in item["boxes"] if b["label"] in selected_labels]
                if skip_empty and not boxes:
                    continue
                items.append({
                    "stem": item["stem"],
                    "boxes": boxes,
                    "width": item["width"],
                    "height": item["height"],
                    "image": item["image"],
                    "img_path": item.get("img_path", ""),
                })
            self._write_files(items)
            return
        total = len(background_images)
        items = []
        self._ensure_dirs()
        for idx in range(total):
            if self.is_interrupted():
                break
            img_path = background_images[idx]
            base = os.path.splitext(os.path.basename(img_path))[0]
            boxes = detection_boxes_dict.get(idx, [])
            boxes = [b for b in boxes if b["label"] in selected_labels]
            if skip_empty and not boxes:
                continue
            try:
                from PyQt5.QtGui import QImage as _QImage
                img = _QImage(img_path)
                w, h = img.width(), img.height()
            except Exception:
                w, h = 0, 0
                img = None
            items.append({
                "stem": base,
                "boxes": boxes,
                "width": w,
                "height": h,
                "img_path": img_path,
                "image": img
            })
        self._write_files(items)

    def _ensure_dirs(self):
        os.makedirs(os.path.join(self.output_dir, "images"), exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, "labels"), exist_ok=True)

    def _write_files(self, items: List[dict]):
        classes_set = set()
        for item in items:
            for b in item["boxes"]:
                classes_set.add(b["label"])
        classes = sorted(classes_set)
        total = len(items)
        for idx, item in enumerate(items):
            self._write_one(item, classes)
            if self.on_progress:
                self.on_progress(idx + 1, total)
        self._write_classes_file(classes)

    def _write_one(self, item: dict, classes: List[str]):
        stem = item["stem"]
        boxes = item["boxes"]
        iw = item.get("width", 0)
        ih = item.get("height", 0)
        if iw == 0 or ih == 0:
            return
        txt_path = os.path.join(self.output_dir, "labels", f"{stem}.txt")
        with open(txt_path, 'w') as f:
            for b in boxes:
                class_id = classes.index(b["label"])
                x_c = (b["x"] + b["width"] / 2) / iw
                y_c = (b["y"] + b["height"] / 2) / ih
                w_n = b["width"] / iw
                h_n = b["height"] / ih
                f.write(f"{class_id} {x_c:.6f} {y_c:.6f} {w_n:.6f} {h_n:.6f}\n")
        img = item.get("image")
        if img is not None and not img.isNull():
            ext = ".jpg"
            img_path = os.path.join(self.output_dir, "images", f"{stem}{ext}")
            tmp = img_path + ".tmp"
            img.save(tmp)
            img = None
            if os.path.exists(img_path):
                os.remove(img_path)
            os.rename(tmp, img_path)
        elif "img_path" in item:
            ext = os.path.splitext(item["img_path"])[1]
            import shutil
            dst = os.path.join(self.output_dir, "images", f"{stem}{ext}")
            src = os.path.normpath(item["img_path"])
            dst_n = os.path.normpath(dst)
            if src != dst_n:
                if os.path.exists(dst_n):
                    os.remove(dst_n)
                shutil.copy2(src, dst_n)
            json_src = os.path.splitext(item["img_path"])[0] + ".json"
            if os.path.exists(json_src):
                json_dst = os.path.join(self.output_dir, "images", f"{stem}.json")
                if os.path.normpath(json_src) != os.path.normpath(json_dst):
                    if os.path.exists(json_dst):
                        os.remove(json_dst)
                    shutil.copy2(json_src, json_dst)

    def _write_classes_file(self, classes: List[str]):
        path = os.path.join(self.output_dir, "classes.txt")
        with open(path, 'w') as f:
            for c in classes:
                f.write(c + "\n")
