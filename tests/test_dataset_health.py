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
