"""数据集健康仪表盘纯逻辑测试。"""
import json


def _write(tmp_path, stem, shapes, size=(200, 200)):
    img = tmp_path / f"{stem}.png"
    img.write_bytes(b"x")
    (tmp_path / f"{stem}.json").write_text(
        json.dumps({"shapes": shapes, "imageWidth": size[0], "imageHeight": size[1]}),
        encoding="utf-8")
    return str(img)


def _box(label="cat", x=0, y=0, w=100, h=50, shape_type=None):
    b = {"label": label, "x": x, "y": y, "width": w, "height": h}
    if shape_type:
        b["shape_type"] = shape_type
    return b


def test_collect_shape_geometry_basic(tmp_path):
    from pastelabel.engine.dataset_health import collect_shape_geometry
    img = _write(tmp_path, "a", [
        _box("cat", w=100, h=50),
        _box("dog", w=40, h=80),
    ])
    out = collect_shape_geometry([img])
    assert out["images_scanned"] == 1
    assert len(out["boxes"]) == 2
    cat = next(b for b in out["boxes"] if b["label"] == "cat")
    assert cat["width"] == 100.0 and cat["height"] == 50.0
    assert cat["area"] == 5000.0
    assert cat["aspect"] == 2.0


def test_collect_shape_geometry_skips_points_and_degenerate(tmp_path):
    from pastelabel.engine.dataset_health import collect_shape_geometry
    img = _write(tmp_path, "b", [
        _box("kp", w=0, h=0, shape_type="point"),
        _box("zero", w=0, h=0),
        _box("ok", w=10, h=10),
    ])
    out = collect_shape_geometry([img])
    assert [b["label"] for b in out["boxes"]] == ["ok"]


def test_collect_shape_geometry_skips_missing_sidecar(tmp_path):
    from pastelabel.engine.dataset_health import collect_shape_geometry
    img = tmp_path / "none.png"
    img.write_bytes(b"x")
    out = collect_shape_geometry([str(img)])
    assert out["boxes"] == []
    assert out["images_scanned"] == 0


def test_collect_shape_geometry_memory_overrides_disk(tmp_path):
    from pastelabel.engine.dataset_health import collect_shape_geometry
    img = _write(tmp_path, "c", [_box("cat", w=100, h=50)])
    memory = {0: [_box("cat", w=10, h=10), _box("bird", w=20, h=20)]}
    out = collect_shape_geometry([img], memory_boxes=memory)
    assert sorted(b["label"] for b in out["boxes"]) == ["bird", "cat"]
    assert len(out["boxes"]) == 2


def test_collect_paste_geometry():
    from pastelabel.engine.dataset_health import collect_paste_geometry

    class Rect:
        def __init__(self, w, h, x=0, y=0):
            self._w, self._h, self._x, self._y = w, h, x, y
        def width(self):
            return self._w
        def height(self):
            return self._h
        def x(self):
            return self._x
        def y(self):
            return self._y

    items = {0: [(None, Rect(100, 50), "car"), (None, Rect(20, 20), "car")]}
    out = collect_paste_geometry(items)
    assert len(out) == 2
    assert all(b["label"] == "car" for b in out)
    assert out[0]["area"] == 5000.0


def _geo(label, w, h, x=0.0, y=0.0):
    return {'label': label, 'x': float(x), 'y': float(y),
            'width': float(w), 'height': float(h),
            'area': float(w * h), 'aspect': w / h}


def test_compute_health_class_dist_descending():
    from pastelabel.engine.dataset_health import compute_health
    stats = compute_health([_geo("a", 10, 10), _geo("a", 10, 10),
                            _geo("b", 10, 10)])
    assert stats['class_dist'] == [{'label': 'a', 'count': 2},
                                   {'label': 'b', 'count': 1}]
    assert stats['summary']['total_boxes'] == 3
    assert stats['summary']['class_count'] == 2


def test_compute_health_size_hist_covers_all_boxes():
    from pastelabel.engine.dataset_health import compute_health
    boxes = [_geo("a", i * 10, 10) for i in range(1, 21)]
    stats = compute_health(boxes)
    assert sum(stats['size_hist']['counts']) == len(boxes)
    assert len(stats['size_hist']['edges']) == len(stats['size_hist']['counts']) + 1


def test_compute_health_aspect_hist():
    from pastelabel.engine.dataset_health import compute_health
    boxes = [_geo("a", 10, 10), _geo("a", 20, 10), _geo("a", 40, 10)]
    stats = compute_health(boxes)
    assert sum(stats['aspect_hist']['counts']) == 3


def test_compute_health_iou_hist_same_label_only():
    from pastelabel.engine.dataset_health import compute_health
    # 两个同类框完全重叠 -> IoU 1.0 落最后一桶
    boxes = [_geo("a", 100, 100), _geo("a", 100, 100)]
    for i, b in enumerate(boxes):
        b['image_index'] = 0
    stats = compute_health(boxes)
    assert stats['iou_hist']['counts'][-1] == 1


def test_compute_health_paste_vs_annot_quantiles():
    from pastelabel.engine.dataset_health import compute_health
    annot = [_geo("a", w, 10) for w in (10, 20, 30, 40)]
    paste = [_geo("p", 100, 10)]
    stats = compute_health(annot, paste_boxes=paste)
    assert stats['paste_vs_annot']['has_paste'] is True
    assert stats['paste_vs_annot']['paste_quantiles'][2] == 1000.0  # 面积中位数


def test_health_advice_rare_class():
    from pastelabel.engine.dataset_health import health_advice
    stats = {
        'class_dist': [{'label': 'a', 'count': 1950}, {'label': 'b', 'count': 50}],
        'size_hist': {'edges': [0, 1, 2], 'counts': [1000, 1000]},
        'aspect_hist': {'edges': [0, 1, 2, 3], 'counts': [800, 600, 600]},
        'iou_hist': {'edges': [0.0, 0.5, 1.0], 'counts': [1800, 200],
                     'skipped_images': 0},
        'paste_vs_annot': {'has_paste': False},
        'summary': {'total_boxes': 2000, 'class_count': 2, 'images_scanned': 1},
    }
    advice = health_advice(stats)
    assert any("b" in a for a in advice)


def test_health_advice_no_issue():
    from pastelabel.engine.dataset_health import health_advice
    stats = {
        'class_dist': [{'label': 'a', 'count': 50}, {'label': 'b', 'count': 50}],
        'size_hist': {'edges': [0, 1, 2], 'counts': [50, 50]},
        'aspect_hist': {'edges': [0, 1, 2, 3], 'counts': [40, 30, 30]},
        'iou_hist': {'edges': [i / 10 for i in range(11)],
                     'counts': [90, 0, 0, 0, 0, 0, 0, 0, 0, 10],
                     'skipped_images': 0},
        'paste_vs_annot': {'has_paste': False},
        'summary': {'total_boxes': 100, 'class_count': 2, 'images_scanned': 1},
    }
    assert health_advice(stats) == ["未发现明显失衡"]
