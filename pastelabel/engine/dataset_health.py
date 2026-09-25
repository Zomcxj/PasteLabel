"""数据集健康诊断：纯逻辑，无 Qt 控件依赖。

扫描标注 sidecar 采集逐框几何，计算类别/尺寸/长宽比/IoU 分布并生成建议。
只读：不写盘、不改标注、不持久化结果。
"""
import json
import math
import os
import concurrent.futures

from .quality_lint import _bbox
from ..core.utils import calculate_iou
from ..core.config import QUALITY_LINT_CONFIG


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


def _bucket_count(n):
    if n <= 0:
        return 5
    return max(5, min(20, int(round(math.sqrt(n)))))


def _histogram(values, buckets):
    if not values:
        return {'edges': [0.0, 1.0], 'counts': [0]}
    lo, hi = min(values), max(values)
    if hi <= lo:
        hi = lo + 1.0
    width = (hi - lo) / buckets
    edges = [lo + i * width for i in range(buckets + 1)]
    counts = [0] * buckets
    for v in values:
        idx = int((v - lo) / width)
        if idx >= buckets:
            idx = buckets - 1
        counts[idx] += 1
    return {'edges': edges, 'counts': counts}


def _quantiles(values):
    if not values:
        return [0.0, 0.0, 0.0, 0.0]
    ordered = sorted(values)
    n = len(ordered)

    def _at(p):
        pos = (n - 1) * p
        lo = int(math.floor(pos))
        hi = int(math.ceil(pos))
        if lo == hi:
            return float(ordered[lo])
        return float(ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo))

    return [_at(0.0), _at(0.25), _at(0.5), _at(0.75)]


def _iou_counts(boxes):
    max_pairwise = QUALITY_LINT_CONFIG['max_boxes_pairwise']
    per_image = {}
    for b in boxes:
        idx = b.get('image_index')
        if idx is None:
            continue
        per_image.setdefault(idx, []).append(b)
    counts = [0] * 10
    skipped = 0
    for _idx, group in per_image.items():
        if len(group) > max_pairwise:
            skipped += 1
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if a['label'] != b['label']:
                    continue
                ax1 = a.get('x', 0.0)
                ay1 = a.get('y', 0.0)
                ax2 = ax1 + a['width']
                ay2 = ay1 + a['height']
                bx1 = b.get('x', 0.0)
                by1 = b.get('y', 0.0)
                bx2 = bx1 + b['width']
                by2 = by1 + b['height']
                iou = calculate_iou((ax1, ay1, ax2, ay2), (bx1, by1, bx2, by2))
                idx_bucket = min(9, int(float(iou) * 10))
                counts[idx_bucket] += 1
    edges = [i / 10 for i in range(11)]
    return {'edges': edges, 'counts': counts, 'skipped_images': skipped}


def compute_health(boxes, paste_boxes=None):
    boxes = [b for b in (boxes or []) if isinstance(b, dict)]
    paste_boxes = [b for b in (paste_boxes or []) if isinstance(b, dict)]

    counts = {}
    for b in boxes:
        label = str(b.get('label', '') or '')
        counts[label] = counts.get(label, 0) + 1
    class_dist = [{'label': k, 'count': v}
                  for k, v in sorted(counts.items(), key=lambda x: (-x[1], x[0]))]

    areas = [float(b.get('area', 0) or 0) for b in boxes]
    aspects = [float(b.get('aspect', 0) or 0) for b in boxes]
    paste_areas = [float(b.get('area', 0) or 0) for b in paste_boxes]

    return {
        'class_dist': class_dist,
        'size_hist': _histogram(areas, _bucket_count(len(areas))),
        'aspect_hist': _histogram(aspects, _bucket_count(len(aspects))),
        'iou_hist': _iou_counts(boxes),
        'paste_vs_annot': {
            'annot_quantiles': _quantiles(areas),
            'paste_quantiles': _quantiles(paste_areas),
            'has_paste': bool(paste_boxes),
        },
        'summary': {
            'total_boxes': len(boxes),
            'class_count': len(class_dist),
            'images_scanned': len({b.get('image_index') for b in boxes
                                   if b.get('image_index') is not None}),
        },
    }


def health_advice(stats):
    advice = []
    class_dist = stats.get('class_dist') or []
    total = stats.get('summary', {}).get('total_boxes', 0) or 0
    if class_dist and total:
        for entry in class_dist:
            share = entry['count'] / total
            if entry['count'] >= 20 and share < 0.05:
                advice.append(
                    f"类别 {entry['label']} 样本偏少（{entry['count']} 个，"
                    f"占比 {share * 100:.0f}%），建议多合成")
        if len(class_dist) >= 2:
            top, bottom = class_dist[0]['count'], class_dist[-1]['count']
            if bottom > 0 and top / bottom >= 10:
                advice.append(
                    f"类别分布失衡（{class_dist[0]['label']}:"
                    f"{class_dist[-1]['label']} = {top}:{bottom}）")

    aspect = stats.get('aspect_hist') or {}
    counts = aspect.get('counts') or []
    if counts and sum(counts) > 0:
        peak = max(counts) / sum(counts)
        if peak > 0.8:
            edges = aspect.get('edges') or []
            i = counts.index(max(counts))
            rng = f"{edges[i]:.2f}~{edges[i + 1]:.2f}" if len(edges) > i + 1 else "?"
            advice.append(f"长宽比单一（集中于 {rng}），多样性不足")

    iou = stats.get('iou_hist') or {}
    iou_counts = iou.get('counts') or []
    if iou_counts and sum(iou_counts) > 0:
        high = sum(iou_counts[-2:]) / sum(iou_counts)
        if high >= 0.2:
            advice.append(f"重复/高度重叠框偏多（{high * 100:.0f}%）")

    return advice or ["未发现明显失衡"]
