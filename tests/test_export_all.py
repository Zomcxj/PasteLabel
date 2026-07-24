"""
导出窗口全功能测试
测试: YoloExporter 引擎 + 导出面板逻辑
"""
import os
import sys
import shutil
import tempfile
import json
import importlib.util
import pytest

TEST_IMAGES = r"D:\VsPro\PasteLabel\images"
EXPORTS_DIR = os.path.join(os.path.dirname(TEST_IMAGES), "exports")


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_base = os.path.join(os.path.dirname(__file__), '..')
YoloExporter = _load_module('yolo_exporter', os.path.join(_base, 'pastelabel', 'engine', 'yolo_exporter.py')).YoloExporter


def _collect_source_data():
    exts = ('.jpg', '.jpeg', '.png', '.bmp')
    img_files = sorted([
        f for f in os.listdir(TEST_IMAGES)
        if os.path.splitext(f)[1].lower() in exts
    ])
    images = [os.path.join(TEST_IMAGES, f) for f in img_files]
    boxes_dict = {}
    for idx, img_path in enumerate(images):
        json_path = os.path.splitext(img_path)[0] + ".json"
        if not os.path.exists(json_path):
            boxes_dict[idx] = []
            continue
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            boxes = []
            for sh in data.get("shapes", []):
                pts = sh.get("points", [])
                if len(pts) >= 2:
                    x = min(p[0] for p in pts)
                    y = min(p[1] for p in pts)
                    w = max(p[0] for p in pts) - x
                    h = max(p[1] for p in pts) - y
                    boxes.append({"x": x, "y": y, "width": w, "height": h, "label": sh.get("label", "")})
            boxes_dict[idx] = boxes
        except Exception:
            boxes_dict[idx] = []
    return images, boxes_dict


def _build_input_data(images, boxes_dict, width=1920, height=1080):
    input_data = []
    for idx in range(len(images)):
        input_data.append({
            "image": None,
            "boxes": boxes_dict.get(idx, []),
            "width": width, "height": height,
            "stem": os.path.splitext(os.path.basename(images[idx]))[0],
            "img_path": images[idx],
        })
    return input_data


class TestExportBasic:
    """基础导出功能"""

    def test_export_creates_dirs(self):
        """导出创建 images/ labels/ 目录"""
        images, boxes_dict = _collect_source_data()
        input_data = _build_input_data(images, boxes_dict)

        tmp_out = os.path.join(tempfile.mkdtemp(), "test_dirs")
        exporter = YoloExporter(tmp_out)
        exporter.run(images, boxes_dict, ["Person"], input_data=input_data)

        assert os.path.isdir(os.path.join(tmp_out, "images"))
        assert os.path.isdir(os.path.join(tmp_out, "labels"))
        shutil.rmtree(tmp_out)

    def test_export_creates_classes_txt(self):
        """导出生成 classes.txt"""
        images, boxes_dict = _collect_source_data()
        all_labels = set()
        for boxes in boxes_dict.values():
            for b in boxes:
                all_labels.add(b["label"])
        if not all_labels:
            pytest.skip("无标注")

        input_data = _build_input_data(images, boxes_dict)
        tmp_out = os.path.join(tempfile.mkdtemp(), "test_classes")
        exporter = YoloExporter(tmp_out)
        exporter.run(images, boxes_dict, list(all_labels), input_data=input_data)

        classes_file = os.path.join(tmp_out, "classes.txt")
        assert os.path.exists(classes_file)
        with open(classes_file, 'r') as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        assert set(lines) == all_labels
        assert lines == sorted(lines), "classes.txt 应按字母排序"
        shutil.rmtree(tmp_out)

    def test_export_yolo_format(self):
        """导出 YOLO 格式正确: class_id xc yc w h"""
        images, boxes_dict = _collect_source_data()
        all_labels = set()
        for boxes in boxes_dict.values():
            for b in boxes:
                all_labels.add(b["label"])
        if not all_labels:
            pytest.skip("无标注")

        input_data = _build_input_data(images, boxes_dict)
        tmp_out = os.path.join(tempfile.mkdtemp(), "test_format")
        exporter = YoloExporter(tmp_out)
        exporter.run(images, boxes_dict, list(all_labels), input_data=input_data)

        labels_dir = os.path.join(tmp_out, "labels")
        for txt in os.listdir(labels_dir):
            if not txt.endswith('.txt'):
                continue
            with open(os.path.join(labels_dir, txt), 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    assert len(parts) == 5, f"格式错误: {line.strip()}"
                    cls_id = int(parts[0])
                    assert cls_id >= 0, f"class_id 负数: {cls_id}"
                    xc, yc, w_n, h_n = map(float, parts[1:])
                    assert w_n > 0, f"宽度 <= 0: {w_n}"
                    assert h_n > 0, f"高度 <= 0: {h_n}"
        shutil.rmtree(tmp_out)

    def test_export_label_count(self):
        """每个图片的标注行数 == 原始 box 数"""
        images, boxes_dict = _collect_source_data()
        all_labels = set()
        for boxes in boxes_dict.values():
            for b in boxes:
                all_labels.add(b["label"])
        if not all_labels:
            pytest.skip("无标注")

        input_data = _build_input_data(images, boxes_dict)
        tmp_out = os.path.join(tempfile.mkdtemp(), "test_count")
        exporter = YoloExporter(tmp_out)
        exporter.run(images, boxes_dict, list(all_labels), input_data=input_data)

        labels_dir = os.path.join(tmp_out, "labels")
        for idx in range(len(images)):
            stem = os.path.splitext(os.path.basename(images[idx]))[0]
            txt_path = os.path.join(labels_dir, stem + ".txt")
            if not os.path.exists(txt_path):
                continue
            with open(txt_path, 'r') as f:
                line_count = len([l for l in f.readlines() if l.strip()])
            expected = len(boxes_dict.get(idx, []))
            assert line_count == expected, f"{stem}: 期望 {expected} 行, 实际 {line_count}"
        shutil.rmtree(tmp_out)


class TestExportSkipEmpty:
    """skip_empty 功能"""

    def test_skip_empty_true(self):
        """skip_empty=True 跳过无标注图片"""
        images, boxes_dict = _collect_source_data()
        all_labels = set()
        for boxes in boxes_dict.values():
            for b in boxes:
                all_labels.add(b["label"])
        if not all_labels:
            pytest.skip("无标注")

        input_data = _build_input_data(images, boxes_dict)
        tmp_out = os.path.join(tempfile.mkdtemp(), "test_skip")
        exporter = YoloExporter(tmp_out)
        exporter.run(images, boxes_dict, list(all_labels), skip_empty=True, input_data=input_data)

        labels_dir = os.path.join(tmp_out, "labels")
        txt_files = [f for f in os.listdir(labels_dir) if f.endswith('.txt')]
        empty_count = sum(1 for idx in range(len(images)) if not boxes_dict.get(idx, []))
        assert len(txt_files) == len(images) - empty_count
        shutil.rmtree(tmp_out)

    def test_skip_empty_false(self):
        """skip_empty=False 不跳过"""
        images, boxes_dict = _collect_source_data()
        all_labels = set()
        for boxes in boxes_dict.values():
            for b in boxes:
                all_labels.add(b["label"])
        if not all_labels:
            pytest.skip("无标注")

        input_data = _build_input_data(images, boxes_dict)
        tmp_out = os.path.join(tempfile.mkdtemp(), "test_noskip")
        exporter = YoloExporter(tmp_out)
        exporter.run(images, boxes_dict, list(all_labels), skip_empty=False, input_data=input_data)

        labels_dir = os.path.join(tmp_out, "labels")
        txt_files = [f for f in os.listdir(labels_dir) if f.endswith('.txt')]
        assert len(txt_files) == len(images)
        shutil.rmtree(tmp_out)


class TestExportLabelFilter:
    """标签过滤"""

    def test_filter_labels(self):
        """只导出 selected_labels 中的标签"""
        images, boxes_dict = _collect_source_data()
        all_labels = set()
        for boxes in boxes_dict.values():
            for b in boxes:
                all_labels.add(b["label"])
        if len(all_labels) < 2:
            pytest.skip("标签不足 2 个")

        subset = list(all_labels)[:1]
        input_data = _build_input_data(images, boxes_dict)
        tmp_out = os.path.join(tempfile.mkdtemp(), "test_filter")
        exporter = YoloExporter(tmp_out)
        exporter.run(images, boxes_dict, subset, input_data=input_data)

        labels_dir = os.path.join(tmp_out, "labels")
        for txt in os.listdir(labels_dir):
            if not txt.endswith('.txt'):
                continue
            with open(os.path.join(labels_dir, txt), 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) == 5:
                        assert int(parts[0]) == 0, f"应只有 class 0"
        shutil.rmtree(tmp_out)

    def test_filter_empty_labels(self):
        """selected_labels 为空 + skip_empty=False 时仍写空文件"""
        images, boxes_dict = _collect_source_data()
        input_data = _build_input_data(images, boxes_dict)
        tmp_out = os.path.join(tempfile.mkdtemp(), "test_empty_lbl")
        exporter = YoloExporter(tmp_out)
        exporter.run(images, boxes_dict, [], skip_empty=False, input_data=input_data)

        labels_dir = os.path.join(tmp_out, "labels")
        txt_files = [f for f in os.listdir(labels_dir) if f.endswith('.txt')]
        assert len(txt_files) == len(images), "skip_empty=False 应写所有文件"
        for txt in txt_files:
            with open(os.path.join(labels_dir, txt), 'r') as f:
                assert len(f.readlines()) == 0, "空 labels 应写 0 行"
        shutil.rmtree(tmp_out)

    def test_filter_empty_labels_skip_empty(self):
        """selected_labels 为空 + skip_empty=True 时无输出"""
        images, boxes_dict = _collect_source_data()
        input_data = _build_input_data(images, boxes_dict)
        tmp_out = os.path.join(tempfile.mkdtemp(), "test_empty_lbl_skip")
        exporter = YoloExporter(tmp_out)
        exporter.run(images, boxes_dict, [], skip_empty=True, input_data=input_data)

        labels_dir = os.path.join(tmp_out, "labels")
        txt_files = [f for f in os.listdir(labels_dir) if f.endswith('.txt')]
        assert len(txt_files) == 0
        shutil.rmtree(tmp_out)


class TestExportImageCopy:
    """图片复制"""

    def test_image_copied(self):
        """导出复制图片到 images/"""
        images, boxes_dict = _collect_source_data()
        all_labels = set()
        for boxes in boxes_dict.values():
            for b in boxes:
                all_labels.add(b["label"])
        if not all_labels:
            pytest.skip("无标注")

        input_data = _build_input_data(images, boxes_dict)
        tmp_out = os.path.join(tempfile.mkdtemp(), "test_imgcopy")
        exporter = YoloExporter(tmp_out)
        exporter.run(images, boxes_dict, list(all_labels), input_data=input_data)

        images_dir = os.path.join(tmp_out, "images")
        img_files = [f for f in os.listdir(images_dir)
                     if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        assert len(img_files) == len(images)
        shutil.rmtree(tmp_out)

    def test_json_copied(self):
        """导出同时复制 JSON"""
        images, boxes_dict = _collect_source_data()
        all_labels = set()
        for boxes in boxes_dict.values():
            for b in boxes:
                all_labels.add(b["label"])
        if not all_labels:
            pytest.skip("无标注")

        input_data = _build_input_data(images, boxes_dict)
        tmp_out = os.path.join(tempfile.mkdtemp(), "test_jsoncopy")
        exporter = YoloExporter(tmp_out)
        exporter.run(images, boxes_dict, list(all_labels), input_data=input_data)

        images_dir = os.path.join(tmp_out, "images")
        json_files = [f for f in os.listdir(images_dir) if f.endswith('.json')]
        assert len(json_files) == len(images)
        shutil.rmtree(tmp_out)


class TestExportEdgeCases:
    """边界情况"""

    def test_width_zero_skips(self):
        """width=0 时跳过写入"""
        images, boxes_dict = _collect_source_data()
        all_labels = set()
        for boxes in boxes_dict.values():
            for b in boxes:
                all_labels.add(b["label"])
        if not all_labels:
            pytest.skip("无标注")

        input_data = [{
            "image": None,
            "boxes": boxes_dict.get(0, []),
            "width": 0, "height": 0,
            "stem": os.path.splitext(os.path.basename(images[0]))[0],
            "img_path": images[0],
        }]
        tmp_out = os.path.join(tempfile.mkdtemp(), "test_zero")
        exporter = YoloExporter(tmp_out)
        exporter.run(images, boxes_dict, list(all_labels), input_data=input_data)

        labels_dir = os.path.join(tmp_out, "labels")
        txt_files = [f for f in os.listdir(labels_dir) if f.endswith('.txt')]
        assert len(txt_files) == 0
        shutil.rmtree(tmp_out)

    def test_empty_input_data(self):
        """空 input_data 无输出"""
        images, boxes_dict = _collect_source_data()
        tmp_out = os.path.join(tempfile.mkdtemp(), "test_empty")
        exporter = YoloExporter(tmp_out)
        exporter.run(images, boxes_dict, ["Person"], input_data=[])

        labels_dir = os.path.join(tmp_out, "labels")
        txt_files = [f for f in os.listdir(labels_dir) if f.endswith('.txt')]
        assert len(txt_files) == 0
        shutil.rmtree(tmp_out)

    def test_progress_callback(self):
        """进度回调被调用"""
        images, boxes_dict = _collect_source_data()
        all_labels = set()
        for boxes in boxes_dict.values():
            for b in boxes:
                all_labels.add(b["label"])
        if not all_labels:
            pytest.skip("无标注")

        progress_calls = []
        input_data = _build_input_data(images, boxes_dict)
        tmp_out = os.path.join(tempfile.mkdtemp(), "test_progress")
        exporter = YoloExporter(tmp_out, on_progress=lambda c, t: progress_calls.append((c, t)))
        exporter.run(images, boxes_dict, list(all_labels), input_data=input_data)

        assert len(progress_calls) == len(images)
        assert progress_calls[-1] == (len(images), len(images))
        shutil.rmtree(tmp_out)

    def test_interrupt(self):
        """中断后不继续"""
        images, boxes_dict = _collect_source_data()
        all_labels = set()
        for boxes in boxes_dict.values():
            for b in boxes:
                all_labels.add(b["label"])
        if not all_labels:
            pytest.skip("无标注")

        call_count = [0]
        def interrupt_after_2():
            call_count[0] += 1
            return call_count[0] >= 2

        input_data = _build_input_data(images, boxes_dict)
        tmp_out = os.path.join(tempfile.mkdtemp(), "test_interrupt")
        exporter = YoloExporter(tmp_out, is_interrupted=interrupt_after_2)
        exporter.run(images, boxes_dict, list(all_labels), input_data=input_data)

        labels_dir = os.path.join(tmp_out, "labels")
        txt_files = [f for f in os.listdir(labels_dir) if f.endswith('.txt')]
        assert len(txt_files) < len(images)
        shutil.rmtree(tmp_out)


class TestExportOnRealData:
    """使用真实 exports 数据"""

    def test_aug_image_json_count_match(self):
        """增广图和 JSON 数量一致"""
        aug_dir = os.path.join(EXPORTS_DIR, "images")
        if not os.path.isdir(aug_dir):
            pytest.skip("exports/images 不存在")

        img_files = [f for f in os.listdir(aug_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        json_files = [f for f in os.listdir(aug_dir) if f.endswith('.json')]
        assert len(img_files) == len(json_files), f"图片 {len(img_files)} != JSON {len(json_files)}"

        img_bases = {os.path.splitext(f)[0] for f in img_files}
        json_bases = {os.path.splitext(f)[0] for f in json_files}
        assert img_bases == json_bases, f"不匹配: {img_bases - json_bases}"

    def test_labels_count_matches_images(self):
        """labels txt 数量 == images jpg 数量"""
        aug_dir = os.path.join(EXPORTS_DIR, "images")
        labels_dir = os.path.join(EXPORTS_DIR, "labels")
        if not os.path.isdir(aug_dir) or not os.path.isdir(labels_dir):
            pytest.skip("exports 不存在")

        img_count = len([f for f in os.listdir(aug_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
        txt_count = len([f for f in os.listdir(labels_dir) if f.endswith('.txt')])
        assert img_count == txt_count, f"图片 {img_count} != 标签 {txt_count}"

    def test_labels_format_valid(self):
        """所有导出标签格式正确"""
        labels_dir = os.path.join(EXPORTS_DIR, "labels")
        if not os.path.isdir(labels_dir):
            pytest.skip("exports/labels 不存在")

        classes_file = os.path.join(EXPORTS_DIR, "classes.txt")
        assert os.path.exists(classes_file), "classes.txt 不存在"
        with open(classes_file, 'r') as f:
            classes = [l.strip() for l in f.readlines() if l.strip()]

        txt_files = [f for f in os.listdir(labels_dir) if f.endswith('.txt')]
        assert len(txt_files) > 0, "无 txt 文件"

        for txt in txt_files[:5]:
            with open(os.path.join(labels_dir, txt), 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    assert len(parts) == 5, f"{txt} 格式错误: {line.strip()}"
                    cls_id = int(parts[0])
                    assert 0 <= cls_id < len(classes), f"{txt} class_id {cls_id} 越界 (共 {len(classes)} 类)"
                    for v in map(float, parts[1:]):
                        assert v > 0, f"{txt} 值 <= 0: {v}"

    def test_image_json_label_stem_match(self):
        """图片、JSON、标签文件 stem 一致"""
        aug_dir = os.path.join(EXPORTS_DIR, "images")
        labels_dir = os.path.join(EXPORTS_DIR, "labels")
        if not os.path.isdir(aug_dir) or not os.path.isdir(labels_dir):
            pytest.skip("exports 不存在")

        img_stems = {os.path.splitext(f)[0] for f in os.listdir(aug_dir)
                     if f.lower().endswith(('.jpg', '.jpeg', '.png'))}
        json_stems = {os.path.splitext(f)[0] for f in os.listdir(aug_dir) if f.endswith('.json')}
        txt_stems = {os.path.splitext(f)[0] for f in os.listdir(labels_dir) if f.endswith('.txt')}

        assert img_stems == json_stems, f"图片 vs JSON 不匹配"
        assert img_stems == txt_stems, f"图片 vs 标签不匹配"

    def test_classes_txt_content(self):
        """classes.txt 内容与标签一致"""
        labels_dir = os.path.join(EXPORTS_DIR, "labels")
        classes_file = os.path.join(EXPORTS_DIR, "classes.txt")
        if not os.path.isdir(labels_dir) or not os.path.exists(classes_file):
            pytest.skip("exports 不存在")

        with open(classes_file, 'r') as f:
            classes = [l.strip() for l in f.readlines() if l.strip()]

        found_labels = set()
        for txt in os.listdir(labels_dir):
            if not txt.endswith('.txt'):
                continue
            with open(os.path.join(labels_dir, txt), 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) == 5:
                        found_labels.add(classes[int(parts[0])])

        assert found_labels == set(classes), f"classes.txt 中有未使用的类: {set(classes) - found_labels}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
