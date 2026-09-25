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


def test_worker_signals_and_run_source():
    import inspect
    from pastelabel.engine import dataset_health
    assert hasattr(dataset_health, 'DatasetHealthWorker')
    src = inspect.getsource(dataset_health.DatasetHealthWorker)
    assert 'health_ready' in src
    assert 'collect_shape_geometry' in src
    assert 'health_advice' in src


def test_health_bar_chart_api_and_paint():
    from pastelabel.ui.widgets.health_charts import HealthBarChart
    chart = HealthBarChart()
    chart.set_data([{'label': 'a', 'value': 3}, {'label': 'b', 'value': 1}])
    chart.paintEvent(None)
    chart.set_data([{'label': 'a', 'value': 3}], horizontal=False,
                   highlight_extremes=True)
    chart.paintEvent(None)
    chart.set_histogram([0.0, 0.5, 1.0], [4, 6])
    chart.paintEvent(None)
    chart.set_placeholder("暂无数据")
    # paintEvent 必须可调用（conftest mock QPainter）
    chart.paintEvent(None)


def test_i18n_health_terms():
    from pastelabel.ui.i18n import _strings
    for key in ("数据集健康", "正在分析", "暂无贴图数据", "请先加载数据集",
                "类别分布", "尺寸分布", "长宽比分布", "IoU 重叠分布",
                "贴图 vs 标注", "建议", "未发现明显失衡"):
        assert key in _strings["zh"], key
        assert key in _strings["en"], key


def test_stats_mixin_exposes_health_section_source():
    import inspect
    from pastelabel.ui.mixins.stats import StatsMixin
    src = inspect.getsource(StatsMixin)
    assert "_build_health_section" in src
    assert "DatasetHealthWorker" in src
    assert "HealthBarChart" in src
    assert "_close_health_worker" in src
    assert "worker.finished.connect(worker.deleteLater)" in src
    assert "requestInterruption" in src
    assert "worker.wait(" in src


class _FakeSignal:
    def __init__(self):
        self._fns = []
    def connect(self, fn):
        self._fns.append(fn)
    def emit(self, payload):
        for fn in self._fns:
            fn(payload)


def _run_health_worker(image_paths=(), memory_boxes=None, canvas_items=None):
    from pastelabel.engine.dataset_health import DatasetHealthWorker
    w = DatasetHealthWorker(tuple(image_paths), memory_boxes or {},
                            canvas_items or {})
    w.health_ready = _FakeSignal()
    w.isInterruptionRequested = lambda: False
    captured = {}
    w.health_ready.connect(lambda p: captured.update(p))
    w.run()
    return captured


def test_collect_paste_geometry_carries_image_index():
    from pastelabel.engine.dataset_health import collect_paste_geometry

    class Rect:
        def __init__(self, w, h, x=0, y=0):
            self._w, self._h, self._x, self._y = w, h, x, y
        def width(self): return self._w
        def height(self): return self._h
        def x(self): return self._x
        def y(self): return self._y

    items = {3: [(None, Rect(10, 10), "a")], 7: [(None, Rect(20, 20), "b")]}
    out = collect_paste_geometry(items)
    assert sorted(b['image_index'] for b in out) == [3, 7]


def test_worker_payload_has_annot_and_paste_sections():
    captured = _run_health_worker()
    assert 'annot' in captured
    assert 'paste' in captured
    assert 'stats' in captured['annot']
    assert 'advice' in captured['annot']
    assert 'stats' in captured['paste']
    assert 'advice' in captured['paste']
    assert captured['images_scanned'] == 0


def test_worker_paste_section_empty_without_paste():
    captured = _run_health_worker()
    assert captured['paste']['stats'] == {}
    assert captured['paste']['advice'] == []


def test_fmt_num_formats_thousands_and_millions():
    from pastelabel.ui.widgets.health_charts import _fmt_num
    assert _fmt_num(0) == '0'
    assert _fmt_num(999) == '999'
    assert _fmt_num(1200) == '1.2k'
    assert _fmt_num(2500000) == '2.5M'


def test_bar_label_formats_value_and_percent():
    from pastelabel.ui.widgets.health_charts import _bar_label
    assert _bar_label(3, 4) == '3 (75%)'
    assert _bar_label(1200, 2400) == '1.2k (50%)'
    assert _bar_label(0, 0) == '0 (0%)'


def test_chart_accepts_colors_and_axis_labels():
    from pastelabel.ui.widgets.health_charts import HealthBarChart
    chart = HealthBarChart()
    chart.set_data([{'label': 'a', 'value': 3, 'color': '#FF0000'},
                    {'label': 'b', 'value': 1}])
    chart.paintEvent(None)
    chart.set_histogram([0.0, 0.5, 1.0], [4, 6],
                        xlabel='面积', ylabel='框数')
    chart.paintEvent(None)


def test_chart_paint_offscreen_real_qt(tmp_path):
    import os
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    script = '''
from PyQt5.QtWidgets import QApplication
from pastelabel.ui.widgets.health_charts import HealthBarChart, _fmt_num
app = QApplication.instance() or QApplication([])
assert _fmt_num(1200) == "1.2k"
c = HealthBarChart()
c.resize(400, 140)
c.set_data([{"label": "cat", "value": 30, "color": "#FF0000"},
            {"label": "dog", "value": 10}])
c.paintEvent(None)
c.set_histogram([0.0, 0.5, 1.0], [4, 6], xlabel="面积", ylabel="框数")
c.paintEvent(None)
c.set_placeholder("暂无数据")
c.paintEvent(None)
from PyQt5.QtGui import QImage
from PyQt5.QtCore import Qt

img = QImage(200, 60, QImage.Format_ARGB32)
img.fill(Qt.white)
c2 = HealthBarChart()
c2.resize(200, 60)
c2.set_data([{'label': 'a', 'value': 10, 'color': '#FF0000'}])
c2.render(img)
pix = img.pixelColor(90, 20)
assert pix.red() > 200 and pix.green() < 80, (pix.red(), pix.green(), pix.blue())

img2 = QImage(200, 140, QImage.Format_ARGB32)
img2.fill(Qt.white)
c3 = HealthBarChart()
c3.resize(200, 140)
c3.set_histogram([0.0, 1.0], [5, 1])
c3.render(img2)
dark = any(img2.pixelColor(x, y).lightness() < 128
           for x in range(0, 200, 4) for y in range(0, 16, 2))
assert dark, "peak bar count label missing in top band"

img3 = QImage(200, 140, QImage.Format_ARGB32)
img3.fill(Qt.white)
c4 = HealthBarChart()
c4.resize(200, 140)
c4.set_data([{"label": "a", "value": 10, "color": "#FF0000"},
             {"label": "b", "value": 5, "color": "#00FF00"}], horizontal=False)
c4.render(img3)
v1 = img3.pixelColor(50, 130)
v2 = img3.pixelColor(150, 130)
assert v1.red() > 200 and v1.green() < 80, v1.getRgb()
assert v2.green() > 200 and v2.red() < 80, v2.getRgb()
print("OK")
'''
    env = os.environ | {"QT_QPA_PLATFORM": "offscreen", "PYTHONPATH": str(root)}
    font_dir = next((p for p in (r"C:\Windows\Fonts", "/usr/share/fonts",
                                 "/System/Library/Fonts") if Path(p).is_dir()), None)
    if font_dir:
        env["QT_QPA_FONTDIR"] = font_dir
    result = subprocess.run([sys.executable, "-c", script], cwd=root, env=env,
                            text=True, capture_output=True, timeout=120)
    assert result.returncode == 0, result.stderr


def test_collect_shape_geometry_empty_memory_slot_falls_back_to_disk(tmp_path):
    """已加载但内存为空的图（应用里每张图都有空槽）必须回读磁盘。"""
    from pastelabel.engine.dataset_health import collect_shape_geometry
    img = _write(tmp_path, "mem_empty", [_box("cat", w=100, h=50)])
    out = collect_shape_geometry([img], memory_boxes={0: []})
    assert [b["label"] for b in out["boxes"]] == ["cat"]
    assert out["images_scanned"] == 1


def test_collect_shape_geometry_routes_paste_shapes(tmp_path):
    """磁盘 flags.paste 的 shape 进 paste_boxes，不进 boxes。"""
    from pastelabel.engine.dataset_health import collect_shape_geometry
    img = _write(tmp_path, "flagged", [
        _box("cat", w=100, h=50),
        dict(_box("logo", w=10, h=10), flags={"paste": True}),
    ])
    out = collect_shape_geometry([img])
    assert [b["label"] for b in out["boxes"]] == ["cat"]
    assert [b["label"] for b in out["paste_boxes"]] == ["logo"]
    assert out["paste_boxes"][0]["image_index"] == 0


def test_collect_shape_geometry_memory_paste_boxes_routed(tmp_path):
    """内存框带 is_paste（新会话从磁盘载入的贴图）也要进 paste_boxes。"""
    from pastelabel.engine.dataset_health import collect_shape_geometry
    img = _write(tmp_path, "mem_paste", [_box("cat", w=100, h=50)])
    memory = {0: [
        {"label": "cat", "x": 0, "y": 0, "width": 100, "height": 50},
        {"label": "logo", "x": 5, "y": 5, "width": 10, "height": 10,
         "is_paste": True},
    ]}
    out = collect_shape_geometry([img], memory_boxes=memory)
    assert [b["label"] for b in out["boxes"]] == ["cat"]
    assert [b["label"] for b in out["paste_boxes"]] == ["logo"]


def test_merge_paste_geometry_prefers_memory_and_dedupes():
    from pastelabel.engine.dataset_health import merge_paste_geometry
    disk = [{"label": "old", "x": 1.0, "y": 2.0, "width": 10.0, "height": 10.0,
             "area": 100.0, "aspect": 1.0, "image_index": 0}]
    memory = [{"label": "new", "x": 1.0, "y": 2.0, "width": 10.0, "height": 10.0,
               "area": 100.0, "aspect": 1.0, "image_index": 0},
              {"label": "extra", "x": 50.0, "y": 50.0, "width": 5.0, "height": 5.0,
               "area": 25.0, "aspect": 1.0, "image_index": 1}]
    merged = merge_paste_geometry(disk, memory)
    assert sorted(b["label"] for b in merged) == ["extra", "new"]


def test_worker_paste_section_includes_disk_paste(tmp_path):
    img = _write(tmp_path, "disk_paste", [
        _box("cat", w=100, h=50),
        dict(_box("logo", w=10, h=10), flags={"paste": True}),
    ])
    captured = _run_health_worker(image_paths=[img])
    assert captured["paste"]["stats"]["class_dist"] == [
        {"label": "logo", "count": 1}]
    assert captured["annot"]["stats"]["class_dist"] == [
        {"label": "cat", "count": 1}]


def test_worker_paste_section_computed_with_paste():
    class Rect:
        def __init__(self, w, h, x=0, y=0):
            self._w, self._h, self._x, self._y = w, h, x, y
        def width(self): return self._w
        def height(self): return self._h
        def x(self): return self._x
        def y(self): return self._y

    captured = _run_health_worker(
        canvas_items={0: [(None, Rect(30, 20), "a"), (None, Rect(30, 20, 40, 0), "a")]})
    paste_stats = captured['paste']['stats']
    assert paste_stats['class_dist'] == [{'label': 'a', 'count': 2}]
    assert paste_stats['summary']['total_boxes'] == 2
    assert isinstance(captured['paste']['advice'], list)
    # annot 侧仍带对比数据
    assert captured['annot']['stats']['paste_vs_annot']['has_paste'] is True


def test_i18n_stats_redesign_terms():
    from pastelabel.ui.i18n import _strings
    for key in ("数据源：背景图标签（切换标签页）",
                "数据源：贴图标签（切换标签页）",
                "各类别占比应接近均衡；长尾类别建议多合成",
                "框尺寸应覆盖多种尺度，避免集中于单一范围",
                "长宽比多样化更贴近真实场景",
                "高 IoU 区间框多说明重复标注偏多",
                "贴图尺寸中位数与标注接近时合成更自然",
                "面积", "长宽比", "框数",
                "背景图标签", "贴图标签"):
        assert key in _strings["zh"], key
        assert key in _strings["en"], key


def test_stats_health_section_supports_source_switch():
    import inspect
    from pastelabel.ui.mixins.stats import StatsMixin
    src = inspect.getsource(StatsMixin)
    assert "_set_health_source" in src
    assert "'annot'" in src and "'paste'" in src
    assert "currentChanged" in src
    assert "_health_source" in src
    assert "_health_payload" in src
    assert "QDockWidget" in src


def test_health_source_switch_routes_payload_real_qt(tmp_path):
    import os
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    script = '''
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout
from pastelabel.ui.mixins.stats import StatsMixin

app = QApplication.instance() or QApplication([])


class FakeEditor(StatsMixin, QObject):
    def __init__(self):
        super().__init__()
        self.background_images = ["x.png"]
        self.detection_boxes_dict = {}
        self.canvas_items_dict = {}
        self.canvas_items = []
        self.current_background_index = -1
        self._health_worker = None

    def get_label_color(self, label):
        return "#123456"


editor = FakeEditor()
dialog = QDialog()
layout = QVBoxLayout(dialog)
editor._build_health_section(dialog, layout)
# 无事件循环，queued signal 不会投递；先停掉 worker，再同步注入 payload
editor._close_health_worker()

payload = {
    "annot": {
        "stats": {
            "class_dist": [{"label": "annot_cls", "count": 9}],
            "size_hist": {"edges": [0, 1], "counts": [9]},
            "aspect_hist": {"edges": [0, 1], "counts": [9]},
            "iou_hist": {"edges": [0.0, 1.0], "counts": [9]},
            "paste_vs_annot": {"has_paste": True,
                               "annot_quantiles": [0, 0, 111, 0],
                               "paste_quantiles": [0, 0, 222, 0]},
        },
        "advice": ["annot advice"],
    },
    "paste": {
        "stats": {
            "class_dist": [{"label": "paste_cls", "count": 4}],
            "size_hist": {"edges": [0, 1], "counts": [4]},
            "aspect_hist": {"edges": [0, 1], "counts": [4]},
            "iou_hist": {"edges": [0.0, 1.0], "counts": [4]},
            # 面板 5 必须固定读 annot：此处放不同的值以捕获路由回退
            "paste_vs_annot": {"has_paste": True,
                               "annot_quantiles": [0, 0, 333, 0],
                               "paste_quantiles": [0, 0, 444, 0]},
        },
        "advice": ["paste advice"],
    },
    "images_scanned": 1,
}
charts = dialog._health_charts

dialog._health_payload = payload
dialog._set_health_source("annot")
assert charts["class"]._items[0]["label"] == "annot_cls", charts["class"]._items
assert charts["class"]._items[0]["color"] == "#123456"
assert charts["size"]._xlabel != ""
assert charts["size"]._counts == [9], charts["size"]._counts

dialog._set_health_source("paste")
assert charts["class"]._items[0]["label"] == "paste_cls", charts["class"]._items
assert charts["class"]._items[0]["color"] == "#123456"
assert charts["size"]._counts == [4], charts["size"]._counts
assert dialog._health_source == "paste"
# 面板 5 固定 annot 对比：贴图模式仍显示 annot 的 111/222
assert charts["paste"]._mode == "bars", charts["paste"]._mode
assert charts["paste"]._items[0]["value"] == 111, charts["paste"]._items
assert charts["paste"]._items[1]["value"] == 222, charts["paste"]._items

# paste 空 → 1-4 显示占位符
empty = dict(payload)
empty["paste"] = {"stats": {}, "advice": []}
dialog._health_payload = empty
dialog._set_health_source("paste")
assert charts["class"]._mode == "empty", charts["class"]._mode
assert charts["class"]._placeholder == "暂无贴图数据", charts["class"]._placeholder

# error → 全部分析失败
dialog._health_payload = {"error": True}
dialog._set_health_source("annot")
assert charts["class"]._placeholder == "分析失败", charts["class"]._placeholder
assert charts["paste"]._placeholder == "分析失败", charts["paste"]._placeholder

editor._close_health_worker()
print("OK")
'''
    env = os.environ | {"QT_QPA_PLATFORM": "offscreen", "PYTHONPATH": str(root)}
    result = subprocess.run([sys.executable, "-c", script], cwd=root, env=env,
                            text=True, capture_output=True, timeout=120)
    assert result.returncode == 0, result.stderr


def test_stats_dialog_min_width_810():
    import inspect
    from pastelabel.ui.main_window import ImageEditor
    src = inspect.getsource(ImageEditor._show_label_stats)
    assert "dialog.setMinimumSize(810, 600)" in src


def test_stats_dialog_table_wiring_and_worker_payload_real_qt(tmp_path):
    import os
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    script = '''
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QApplication, QDialog, QWidget
from pastelabel.ui.mixins.stats import StatsMixin

app = QApplication.instance() or QApplication([])


class FakeLabelManager:
    def rename_detection_label(self, old, new):
        return False

    def rename_paste_label(self, old, new):
        return False


class FakeEditor(StatsMixin, QWidget):
    def __init__(self):
        super().__init__()
        self.background_images = ["x.png"]
        self.detection_boxes_dict = {
            0: [{"label": "bg_cls", "x": 0, "y": 0, "width": 10, "height": 10}]}
        self.canvas_items_dict = {0: [(None, None, "paste_cls")]}
        self.canvas_items = []
        self.current_background_index = 0
        self._health_worker = None
        self._cached_bg_label_stats = None
        self._memory_background_path = "x.png"
        self.label_color_map = {}
        self.global_labels = set()
        self.background_dataset_labels = set()
        self.label_manager = FakeLabelManager()
        self._dataset_stats_dirty = False
        self._background_label_scan_completed = True

    def get_label_color(self, label):
        return "#123456"


editor = FakeEditor()
# 无事件循环：拦截 exec_ 以捕获真实 _StatsDialog
captured = {}


def _capture_exec(self):
    captured["dialog"] = self
    return 0


QDialog.exec_ = _capture_exec
editor._show_label_stats()
dialog = captured["dialog"]
editor._close_health_worker()

bg_table = dialog._bg_table
paste_table = dialog._paste_table
charts = dialog._health_charts

# Gap 1: 真实接线（切换标签页 → 切换数据源）
tabs = dialog._tabs
tabs.setCurrentIndex(0)
assert dialog._health_source == "annot", dialog._health_source
tabs.setCurrentIndex(1)
assert dialog._health_source == "paste", dialog._health_source
tabs.setCurrentIndex(0)
assert dialog._health_source == "annot", dialog._health_source

payload = {
    "annot": {
        "stats": {
            "class_dist": [{"label": "annot_cls", "count": 9}],
            "size_hist": {"edges": [0, 1], "counts": [9]},
            "aspect_hist": {"edges": [0, 1], "counts": [9]},
            "iou_hist": {"edges": [0.0, 1.0], "counts": [9]},
            "paste_vs_annot": {"has_paste": True,
                               "annot_quantiles": [0, 0, 111, 0],
                               "paste_quantiles": [0, 0, 222, 0]},
        },
        "advice": ["annot advice"],
    },
    "paste": {
        "stats": {
            "class_dist": [{"label": "paste_cls", "count": 4}],
            "size_hist": {"edges": [0, 1], "counts": [4]},
            "aspect_hist": {"edges": [0, 1], "counts": [4]},
            "iou_hist": {"edges": [0.0, 1.0], "counts": [4]},
        },
        "advice": ["paste advice"],
    },
    "images_scanned": 1,
}

# Gap 2: worker payload 投递（存储 + 渲染）
payload2 = {
    "annot": payload["annot"],
    "paste": {"stats": {
        "class_dist": [{"label": "from_worker", "count": 7}],
        "size_hist": {"edges": [0, 1], "counts": [7]},
        "aspect_hist": {"edges": [0, 1], "counts": [7]},
        "iou_hist": {"edges": [0.0, 1.0], "counts": [7]},
    }, "advice": ["w"]},
    "images_scanned": 2,
}
dialog._set_health_source("paste")
dialog._on_health_payload(payload2)
assert dialog._health_payload is payload2
assert charts["class"]._items[0]["label"] == "from_worker", charts["class"]._items
assert dialog._health_source == "paste"

# payload 到达前已选 paste：存储的数据源优先
dialog._health_payload = None
dialog._set_health_source("paste")
dialog._on_health_payload(payload)
assert dialog._health_payload is payload
assert charts["class"]._items[0]["label"] == "paste_cls", charts["class"]._items

editor._close_health_worker()
print("OK")
'''
    env = os.environ | {"QT_QPA_PLATFORM": "offscreen", "PYTHONPATH": str(root)}
    result = subprocess.run([sys.executable, "-c", script], cwd=root, env=env,
                            text=True, capture_output=True, timeout=120)
    assert result.returncode == 0, result.stderr


def test_stats_dialog_tabs_and_docks_real_qt(tmp_path):
    import os
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    script = '''
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QApplication, QDialog, QDockWidget
from pastelabel.ui.mixins.stats import StatsMixin

app = QApplication.instance() or QApplication([])


class FakeLabelManager:
    def rename_detection_label(self, old, new):
        return False

    def rename_paste_label(self, old, new, rewrite_disk=False):
        return False


class FakeEditor(StatsMixin, QDialog):
    def __init__(self):
        super().__init__()
        self.background_images = ["x.png"]
        self.detection_boxes_dict = {
            0: [{"label": "bg_cls", "x": 0, "y": 0, "width": 10, "height": 10}]}
        self.canvas_items_dict = {0: [(None, None, "paste_cls")]}
        self.canvas_items = []
        self.current_background_index = 0
        self._health_worker = None
        self._cached_bg_label_stats = None
        self._memory_background_path = "x.png"
        self.label_color_map = {}
        self.global_labels = set()
        self.background_dataset_labels = set()
        self.label_manager = FakeLabelManager()
        self._dataset_stats_dirty = False
        self._background_label_scan_completed = True

    def get_label_color(self, label):
        return "#123456"


editor = FakeEditor()
captured = {}


def _capture_exec(self):
    captured["dialog"] = self
    return 0


QDialog.exec_ = _capture_exec
editor._show_label_stats()
dialog = captured["dialog"]
editor._close_health_worker()

# 单表位置：一个 QTabWidget，两个页签
tabs = dialog._tabs
assert tabs.count() == 2, tabs.count()
assert dialog._bg_table is not None
assert dialog._paste_table is not None

# 切换页签 → 健康数据源联动
tabs.setCurrentIndex(1)
assert dialog._health_source == "paste", dialog._health_source
tabs.setCurrentIndex(0)
assert dialog._health_source == "annot", dialog._health_source

# 5 个统计面板为可拖拽 dock
docks = dialog._health_docks
assert sorted(docks) == ["aspect", "class", "iou", "paste", "size"], sorted(docks)
for dock in docks.values():
    assert isinstance(dock, QDockWidget)
    assert dock.features() & QDockWidget.DockWidgetMovable
    assert not (dock.features() & QDockWidget.DockWidgetFloatable)

# 整库贴图：payload 到达后贴图表重建（磁盘贴图统计进表）
payload = {
    "annot": {"stats": {"class_dist": [{"label": "bg_cls", "count": 9}]},
              "advice": ["a"]},
    "paste": {"stats": {"class_dist": [{"label": "disk_logo", "count": 7}]},
              "advice": ["p"]},
    "images_scanned": 1,
}
dialog._on_health_payload(payload)
rows = dialog._paste_table.rowCount()
assert rows == 1, rows
assert dialog._paste_table.item(0, 0).text() == "disk_logo"
assert dialog._paste_table.item(0, 1).text() == "7"

editor._close_health_worker()
print("OK")
'''
    env = os.environ | {"QT_QPA_PLATFORM": "offscreen", "PYTHONPATH": str(root)}
    result = subprocess.run([sys.executable, "-c", script], cwd=root, env=env,
                            text=True, capture_output=True, timeout=120)
    assert result.returncode == 0, result.stderr
