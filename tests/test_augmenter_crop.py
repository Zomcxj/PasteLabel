"""滑窗裁剪测试：网格公式 + 标注过滤（纯逻辑，conftest mock 下可直接跑）。"""
from pastelabel.engine.augmenter.crop import crop_boxes, size_for_count, window_starts


# ---------- 网格公式 ----------

def test_window_starts_exact_fit():
    assert window_starts(100, 50, 0) == [0, 50]


def test_window_starts_covers_axis():
    assert window_starts(100, 100, 0) == [0]


def test_window_starts_last_flush_and_overlap_ge_requested():
    # c=60, ov=10: step=50 → n=2, 均摊后 [0,40]，末窗贴边且实际重叠 20 ≥ 请求 10
    starts = window_starts(100, 60, 10)
    assert starts == [0, 40]
    assert starts[-1] + 60 == 100


def test_window_starts_slack_spread_three():
    # c=35, ov=10: step=25 → n=4, span=65 → [0,22,43,65]
    assert window_starts(100, 35, 10) == [0, 22, 43, 65]


def test_window_starts_step_floor_one_when_overlap_too_big():
    # ov ≥ c 时 step 兜底为 1（调用方另有 ov 钳制，这里保证不产生非法步长）
    assert window_starts(10, 3, 50) == list(range(8))


def test_size_for_count_exact_fit():
    assert size_for_count(100, 3, 20) == 47   # (100+2*20)/3 = 46.67 → 47
    assert size_for_count(100, 1, 20) == 100


def test_size_for_count_clamps():
    assert size_for_count(50, 99, 10) == 11   # 10.4 → 钳到 ov+1


# ---------- 标注过滤 ----------

def _rect(x, y, w, h, **kw):
    b = {"label": "cat", "shape_type": "rectangle", "x": x, "y": y, "width": w, "height": h}
    b.update(kw)
    return b


def test_crop_rect_clips_and_translates():
    # 窗口 (10,10,20,20)，框 (5,5,20,20)：交集 15×15，比例 0.5625 ≥ 0.3 → 保留
    out = crop_boxes([_rect(5, 5, 20, 20)], 10, 10, 20, 20, 0.3)
    assert len(out) == 1
    assert (out[0]["x"], out[0]["y"], out[0]["width"], out[0]["height"]) == (0, 0, 15, 15)
    assert out[0]["label"] == "cat"


def test_crop_rect_boundary_ratio_kept():
    # 交集 3×100=300，面积 1000，比例恰为 0.3 → 保留（>= 阈值）
    out = crop_boxes([_rect(0, 0, 10, 100)], 0, 0, 3, 100, 0.3)
    assert len(out) == 1


def test_crop_rect_below_threshold_dropped():
    out = crop_boxes([_rect(0, 0, 10, 100)], 0, 0, 2, 100, 0.3)
    assert out == []


def test_crop_polygon_translates_without_point_clipping():
    poly = {"label": "car", "shape_type": "polygon",
            "points": [[0, 0], [30, 0], [30, 30], [0, 30]],
            "x": 0, "y": 0, "width": 30, "height": 30}
    out = crop_boxes([poly], 10, 10, 20, 20, 0.3)  # bbox 交比例 400/900 ≈ 0.44
    assert len(out) == 1
    assert out[0]["points"][0] == [-10, -10]       # 越界顶点不裁剪（与 RandomTranslate 一致）
    assert (out[0]["x"], out[0]["y"]) == (-10, -10)


def test_crop_polygon_low_ratio_dropped():
    poly = {"label": "car", "shape_type": "polygon",
            "points": [[0, 0], [30, 0], [30, 30], [0, 30]],
            "x": 0, "y": 0, "width": 30, "height": 30}
    assert crop_boxes([poly], 25, 25, 20, 20, 0.3) == []  # 25/900 < 0.3


def test_crop_point_inside_kept_outside_dropped():
    pt = lambda x, y: {"label": "nose", "shape_type": "point", "points": [[x, y]], "x": x, "y": y, "width": 0, "height": 0}
    out = crop_boxes([pt(15, 15)], 10, 10, 20, 20, 0.3)
    assert len(out) == 1 and out[0]["points"] == [[5, 5]]
    assert crop_boxes([pt(5, 15)], 10, 10, 20, 20, 0.3) == []


def test_crop_degenerate_box_treated_as_point():
    out = crop_boxes([_rect(15, 15, 0, 0)], 10, 10, 20, 20, 0.3)
    assert len(out) == 1 and (out[0]["x"], out[0]["y"]) == (5, 5)
    assert crop_boxes([_rect(5, 5, 0, 0)], 10, 10, 20, 20, 0.3) == []


def test_crop_preserves_metadata():
    b = _rect(5, 5, 20, 20, group_id=3, flags={"paste": True})
    out = crop_boxes([b], 0, 0, 100, 100, 0.3)
    assert out[0]["group_id"] == 3


# ---------- Augmenter 集成（真实 Qt 子进程） ----------

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run_real_qt(script):
    env = os.environ | {"QT_QPA_PLATFORM": "offscreen", "PYTHONPATH": str(ROOT)}
    r = subprocess.run([sys.executable, "-c", script], cwd=ROOT, env=env,
                       text=True, capture_output=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_augmenter_crop_all_mode_outputs_and_sidecar(tmp_path):
    script = f'''
import json, os
from PyQt5.QtGui import QImage
from pastelabel.engine.augmenter import Augmenter

out = r"{(tmp_path / "out").as_posix()}"
src = os.path.join(out, "img.png")
os.makedirs(out, exist_ok=True)
QImage(100, 100, QImage.Format_RGB888).save(src)
boxes = [{{"label": "cat", "shape_type": "rectangle", "x": 10, "y": 10, "width": 40, "height": 40}}]
res = Augmenter(os.path.join(out, "exports")).run(
    [src], {{0: boxes}}, [], mode="all",
    crop_spec={{"w": 60, "h": 60, "overlap": 10, "min_visible": 0.3}})
stems = sorted(r["stem"] for r in res)
assert stems == ["img_crop_r1c1"], stems  # 其余三窗可见比例 ≤0.25 < 0.3
d = os.path.join(out, "exports", "images")
assert os.path.exists(os.path.join(d, "img_crop_r1c1.png"))
data = json.load(open(os.path.join(d, "img_crop_r1c1.json"), encoding="utf-8"))
assert (data["imageWidth"], data["imageHeight"]) == (60, 60)
assert data["shapes"][0]["points"] == [[10, 10], [50, 10], [50, 50], [10, 50]]
print("OK_ALL")
'''
    assert "OK_ALL" in _run_real_qt(script)


def test_augmenter_crop_image_smaller_than_window(tmp_path):
    script = f'''
import os
from PyQt5.QtGui import QImage
from pastelabel.engine.augmenter import Augmenter

out = r"{(tmp_path / "out").as_posix()}"
src = os.path.join(out, "s.png")
os.makedirs(out, exist_ok=True)
QImage(40, 40, QImage.Format_RGB888).save(src)
boxes = [{{"label": "a", "shape_type": "rectangle", "x": 1, "y": 1, "width": 10, "height": 10}}]
res = Augmenter(os.path.join(out, "exports")).run(
    [src], {{0: boxes}}, [], mode="all",
    crop_spec={{"w": 60, "h": 60, "overlap": 10, "min_visible": 0.3}})
assert len(res) == 1 and res[0]["width"] == 40 and res[0]["height"] == 40
assert res[0]["stem"] == "s_crop_r1c1"
print("OK_SMALL")
'''
    assert "OK_SMALL" in _run_real_qt(script)


def test_augmenter_crop_empty_source_writes_nothing(tmp_path):
    script = f'''
import os
from PyQt5.QtGui import QImage
from pastelabel.engine.augmenter import Augmenter

out = r"{(tmp_path / "out").as_posix()}"
src = os.path.join(out, "e.png")
os.makedirs(out, exist_ok=True)
QImage(50, 50, QImage.Format_RGB888).save(src)
res = Augmenter(os.path.join(out, "exports")).run(
    [src], {{0: []}}, [], mode="all", skip_empty=False,
    crop_spec={{"w": 30, "h": 30, "overlap": 5, "min_visible": 0.3}})
assert res == []
assert not os.path.exists(os.path.join(out, "exports", "images")) or \
       not os.listdir(os.path.join(out, "exports", "images"))
print("OK_EMPTY")
'''
    assert "OK_EMPTY" in _run_real_qt(script)


def test_augmenter_crop_random_mode_pool(tmp_path):
    script = f'''
import os
from PyQt5.QtGui import QImage
from pastelabel.engine.augmenter import Augmenter
from pastelabel.engine.augmenter.color import Brightness

out = r"{(tmp_path / "out").as_posix()}"
src = os.path.join(out, "r.png")
os.makedirs(out, exist_ok=True)
QImage(60, 60, QImage.Format_RGB888).save(src)
boxes = [{{"label": "a", "shape_type": "rectangle", "x": 5, "y": 5, "width": 20, "height": 20}}]
res = Augmenter(os.path.join(out, "exports"), seed=3).run(
    [src], {{0: boxes}}, [(Brightness, {{"delta": (10, 20)}})], mode="random",
    crop_spec={{"w": 30, "h": 30, "overlap": 5, "min_visible": 0.3}})
assert res, "random 模式应有产出（亮度或裁剪）"
print("OK_RANDOM")
'''
    assert "OK_RANDOM" in _run_real_qt(script)


def test_panel_crop_row_and_default_spec(tmp_path):
    script = f'''
import os
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
from pastelabel.ui.processing_panel import ProcessingPanel

QImage(100, 80, QImage.Format_RGB888).save(os.path.join(r"{tmp_path.as_posix()}", "p.png"))
editor = type("E", (), {{"background_images": []}})()
panel = ProcessingPanel(editor)

# 回归：未加载数据集就点勾选（_run_images 未经过 _ensure_boxes_loaded）不得崩溃
panel._crop_check.setChecked(True)
spec = panel._get_crop_spec()
assert spec == {{"w": 640, "h": 640, "overlap": 54, "min_visible": 0.3, "square": True}}, spec

panel._path_edit.setText(r"{tmp_path.as_posix()}")
panel._ensure_boxes_loaded()
panel._crop_spec = None  # 重新按首图派生
spec = panel._get_crop_spec()
assert spec == {{"w": 640, "h": 640, "overlap": 8, "min_visible": 0.3, "square": True}}, spec
assert "640×640" in panel._crop_summary_lbl.text()
panel._crop_check.setChecked(False)
assert panel._get_crop_spec() is None
assert panel._crop_summary_lbl.text() != ""  # 未配置 提示
print("OK_PANEL")
'''
    assert "OK_PANEL" in _run_real_qt(script)


def test_crop_dialog_linkage_and_preview(tmp_path):
    script = f'''
import os
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
from pastelabel.ui.crop_dialog import CropConfigDialog
from pastelabel.engine.augmenter.crop import size_for_count, window_starts

d = r"{tmp_path.as_posix()}"
src = os.path.join(d, "d.png")
QImage(200, 100, QImage.Format_RGB888).save(src)
boxes = [{{"label": "a", "shape_type": "rectangle", "x": 10, "y": 10, "width": 40, "height": 40}}]
dlg = CropConfigDialog([src], {{0: boxes}},
                       {{"w": 100, "h": 50, "overlap": 10, "min_visible": 0.3}})
assert (dlg._rows.value(), dlg._cols.value()) == (3, 3)  # 初始化即联动（brief 笔误：(3,2)，实际 window_starts(200,100,10)=3）

dlg._w.setValue(150)  # 尺寸 → 数量
assert dlg._cols.value() == len(window_starts(200, 150, 10))

dlg._cols.setValue(5)  # 数量 → 尺寸
assert dlg._w.value() == size_for_count(200, 5, 10)

dlg._square.setChecked(True)  # 正方形镜像
assert dlg._w.value() == dlg._h.value()

dlg._refresh()
assert dlg._preview._rects and dlg._est.text()
s = dlg.spec()
assert s["min_visible"] == 0.3 and s["w"] == dlg._w.value() and s["square"] is True
print("OK_DIALOG")
'''
    assert "OK_DIALOG" in _run_real_qt(script)


def test_augmenter_crop_random_mode_deterministic_crop_path(tmp_path):
    # 池=[("__crop__",spec)] → 必选；ratio 门 1.0 必过 → 裁剪路径确定性执行
    # 窗口起点两轴 [0,40]；框(10,10,40,40) 面积1600：r1c1 全含=1.0，
    # r1c2/r2c1=400/1600=0.25、r2c2=100/1600=0.0625，均 <0.3 丢弃
    script = f'''
import os
from PyQt5.QtGui import QImage
from pastelabel.engine.augmenter import Augmenter

out = r"{(tmp_path / "out").as_posix()}"
src = os.path.join(out, "x.png")
os.makedirs(out, exist_ok=True)
QImage(100, 100, QImage.Format_RGB888).save(src)
boxes = [{{"label": "a", "shape_type": "rectangle", "x": 10, "y": 10, "width": 40, "height": 40}}]
res = Augmenter(os.path.join(out, "exports"), seed=1).run(
    [src], {{0: boxes}}, [], mode="random",
    crop_spec={{"w": 60, "h": 60, "overlap": 10, "min_visible": 0.3}})
stems = sorted(r["stem"] for r in res)
assert stems == ["x_crop_r1c1"], stems
d = os.path.join(out, "exports", "images")
assert not os.path.exists(os.path.join(d, "x.png"))  # 裁剪已产出 → 原图兜底不得触发
print("OK_RANDOM_CROP")
'''
    assert "OK_RANDOM_CROP" in _run_real_qt(script)


def test_augmenter_crop_random_mode_zero_windows_fallback(tmp_path):
    # 框(30,30,60,60) 面积3600，min_visible=0.9：四窗交比 0.25 / 0.417 / 0.417 / 0.694
    # 全部 <0.9 → 0 窗产出 → _apply_crop 返回 0 → 走 _save_original 兜底
    script = f'''
import os
from PyQt5.QtGui import QImage
from pastelabel.engine.augmenter import Augmenter

out = r"{(tmp_path / "out").as_posix()}"
src = os.path.join(out, "z.png")
os.makedirs(out, exist_ok=True)
QImage(100, 100, QImage.Format_RGB888).save(src)
boxes = [{{"label": "a", "shape_type": "rectangle", "x": 30, "y": 30, "width": 60, "height": 60}}]
res = Augmenter(os.path.join(out, "exports"), seed=1).run(
    [src], {{0: boxes}}, [], mode="random",
    crop_spec={{"w": 60, "h": 60, "overlap": 10, "min_visible": 0.9}})
assert len(res) == 1, res
stem = res[0]["stem"]
assert "_crop_" not in stem, stem
d = os.path.join(out, "exports", "images")
assert os.path.exists(os.path.join(d, "z.png"))
assert os.path.exists(os.path.join(d, "z.json"))
print("OK_RANDOM_FALLBACK")
'''
    assert "OK_RANDOM_FALLBACK" in _run_real_qt(script)
