"""数据集健康诊断：纯逻辑，无 Qt 控件依赖。

扫描标注 sidecar 采集逐框几何，计算类别/尺寸/长宽比/IoU 分布并生成建议。
只读：不写盘、不改标注、不持久化结果。
"""
import json
import os
import concurrent.futures

from .quality_lint import _bbox


def _geometry_of(label, rect):
    x1, y1, x2, y2 = rect
    w = float(x2 - x1)
    h = float(y2 - y1)
    if w <= 0 or h <= 0:
        return None
    return {
        'label': str(label or ''),
        'x': float(x1), 'y': float(y1),
        'width': w, 'height': h,
        'area': w * h, 'aspect': w / h,
    }


def _read_json_shapes(json_path):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    shapes = data.get('shapes')
    if not isinstance(shapes, list):
        return None
    return shapes


def collect_shape_geometry(image_paths, memory_boxes=None, is_interrupted=None):
    """采集逐框几何。已加载图以内存框为准；缺 sidecar 跳过。"""
    image_paths = list(image_paths or [])
    memory_boxes = memory_boxes or {}
    boxes = []
    images_scanned = 0

    def _one(index, path):
        json_path = f"{os.path.splitext(path)[0]}.json"
        loaded = index in memory_boxes
        if loaded:
            shapes = list(memory_boxes.get(index) or [])
            exists = os.path.exists(json_path)
            if not shapes and not exists:
                return index, None
            return index, shapes
        return index, _read_json_shapes(json_path)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(_one, i, p) for i, p in enumerate(image_paths)]
        for future in concurrent.futures.as_completed(futures):
            if is_interrupted and is_interrupted():
                break
            index, shapes = future.result()
            if shapes is None:
                continue
            images_scanned += 1
            for shape in shapes:
                if not isinstance(shape, dict):
                    continue
                if (shape.get('shape_type') or 'rectangle') == 'point':
                    continue
                rect = _bbox(shape)
                if rect is None:
                    continue
                geo = _geometry_of(shape.get('label', ''), rect)
                if geo is None:
                    continue
                geo['image_index'] = index
                boxes.append(geo)
    return {'boxes': boxes, 'images_scanned': images_scanned}


def collect_paste_geometry(canvas_items_dict):
    """从 {index: [(pixmap, rect, label), ...]} 提取贴图几何。"""
    boxes = []
    for _index, items in (canvas_items_dict or {}).items():
        for entry in items or []:
            if not entry or len(entry) < 3:
                continue
            _pixmap, rect, label = entry[0], entry[1], entry[2]
            try:
                x = float(rect.x())
                y = float(rect.y())
                w = float(rect.width())
                h = float(rect.height())
            except Exception:
                continue
            if w <= 0 or h <= 0:
                continue
            boxes.append({
                'label': str(label or ''),
                'x': x, 'y': y, 'width': w, 'height': h,
                'area': w * h, 'aspect': w / h,
            })
    return boxes
