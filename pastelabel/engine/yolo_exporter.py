import os
from typing import Callable, Dict, List, Optional

from .base_exporter import BaseExporter


class YoloExporter(BaseExporter):

    def _ensure_dirs(self):
        super()._ensure_dirs()

    def _write_files(self, items: List[dict], selected_labels: List[str] = None):
        classes = self._get_classes(items, selected_labels)
        self._write_classes_file(classes)
        total = len(items)
        for idx, item in enumerate(items):
            self._write_one(item, classes)
            if self.on_progress:
                self.on_progress(idx + 1, total)

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
                x1 = max(0, b["x"])
                y1 = max(0, b["y"])
                x2 = min(iw, b["x"] + b["width"])
                y2 = min(ih, b["y"] + b["height"])
                if x2 - x1 < 1 or y2 - y1 < 1:
                    continue
                x_c = (x1 + x2) / 2 / iw
                y_c = (y1 + y2) / 2 / ih
                w_n = (x2 - x1) / iw
                h_n = (y2 - y1) / ih
                x_c = max(0.0, min(1.0, x_c))
                y_c = max(0.0, min(1.0, y_c))
                w_n = max(0.0, min(1.0, w_n))
                h_n = max(0.0, min(1.0, h_n))
                if w_n < 1e-6 or h_n < 1e-6:
                    continue
                f.write(f"{class_id} {x_c:.6f} {y_c:.6f} {w_n:.6f} {h_n:.6f}\n")
        self._copy_image(item)

    def _write_classes_file(self, classes: List[str]):
        path = os.path.join(self.output_dir, "classes.txt")
        with open(path, 'w') as f:
            for c in classes:
                f.write(c + "\n")
