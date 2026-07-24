"""
数据处理流水线测试 - 使用 D:/VsPro/PasteLabel/images 数据集
测试: 导出 -> 划分 完整流程
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
Splitter = _load_module('splitter', os.path.join(_base, 'pastelabel', 'engine', 'splitter.py')).Splitter


def _collect_source_data():
    """收集源图片和 boxes"""
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


class TestYOLOExport:

    def test_export_from_source(self):
        """从源图导出 YOLO 标签 (通过 input_data)"""
        images, boxes_dict = _collect_source_data()
        assert len(images) > 0, "测试数据集无图片"

        all_labels = set()
        for boxes in boxes_dict.values():
            for b in boxes:
                all_labels.add(b["label"])
        if not all_labels:
            pytest.skip("测试数据集无标注")

        input_data = []
        for idx in range(len(images)):
            input_data.append({
                "image": None,
                "boxes": boxes_dict.get(idx, []),
                "width": 1920, "height": 1080,
                "stem": os.path.splitext(os.path.basename(images[idx]))[0],
                "img_path": images[idx],
            })

        tmp_out = os.path.join(tempfile.mkdtemp(), "test_export")
        exporter = YoloExporter(tmp_out)
        exporter.run(images, boxes_dict, list(all_labels), skip_empty=False, input_data=input_data)

        labels_dir = os.path.join(tmp_out, "labels")
        assert os.path.isdir(labels_dir), "labels 目录未创建"
        txt_files = [f for f in os.listdir(labels_dir) if f.endswith('.txt')]
        assert len(txt_files) == len(images), \
            f"txt 文件数 {len(txt_files)} != 图片数 {len(images)}"

        for txt in txt_files:
            txt_path = os.path.join(labels_dir, txt)
            with open(txt_path, 'r') as f:
                lines = f.readlines()
            for line in lines:
                parts = line.strip().split()
                assert len(parts) == 5, f"YOLO 格式错误: {line.strip()}"
                cls_id = int(parts[0])
                assert 0 <= cls_id < len(all_labels), f"class_id {cls_id} 越界"
                for v in map(float, parts[1:]):
                    assert -0.5 <= v <= 1.5, f"归一化值异常: {v}"

        classes_file = os.path.join(tmp_out, "classes.txt")
        assert os.path.exists(classes_file), "classes.txt 未创建"
        shutil.rmtree(tmp_out)

    def test_export_skip_empty(self):
        """测试 skip_empty 选项"""
        images, boxes_dict = _collect_source_data()
        if len(images) < 2:
            pytest.skip("图片不足")

        all_labels = set()
        for boxes in boxes_dict.values():
            for b in boxes:
                all_labels.add(b["label"])
        if not all_labels:
            pytest.skip("无标注")

        input_data = []
        for idx in range(len(images)):
            input_data.append({
                "image": None,
                "boxes": boxes_dict.get(idx, []),
                "width": 640, "height": 480,
                "stem": os.path.splitext(os.path.basename(images[idx]))[0],
                "img_path": images[idx],
            })

        tmp_out = os.path.join(tempfile.mkdtemp(), "test_skip")
        exporter = YoloExporter(tmp_out)
        exporter.run(images, boxes_dict, list(all_labels), skip_empty=True, input_data=input_data)

        labels_dir = os.path.join(tmp_out, "labels")
        txt_files = [f for f in os.listdir(labels_dir) if f.endswith('.txt')]
        empty_count = sum(1 for idx in range(len(images)) if not boxes_dict.get(idx, []))
        assert len(txt_files) == len(images) - empty_count, \
            f"skip_empty 后 txt 数不匹配"
        shutil.rmtree(tmp_out)

    def test_export_with_input_data(self):
        """测试 input_data 模式（来自增广图）"""
        images, boxes_dict = _collect_source_data()
        if not images:
            pytest.skip("无图片")

        all_labels = set()
        for boxes in boxes_dict.values():
            for b in boxes:
                all_labels.add(b["label"])
        if not all_labels:
            pytest.skip("无标注")

        input_data = []
        for idx in range(min(3, len(images))):
            input_data.append({
                "image": None,
                "boxes": boxes_dict.get(idx, []),
                "width": 640, "height": 480,
                "stem": os.path.splitext(os.path.basename(images[idx]))[0],
                "img_path": images[idx],
            })

        tmp_out = os.path.join(tempfile.mkdtemp(), "test_input_data")
        exporter = YoloExporter(tmp_out)
        exporter.run(images, boxes_dict, list(all_labels), skip_empty=False, input_data=input_data)

        labels_dir = os.path.join(tmp_out, "labels")
        txt_files = [f for f in os.listdir(labels_dir) if f.endswith('.txt')]
        assert len(txt_files) == 3, f"input_data 模式应导出 3 个，实际 {len(txt_files)}"
        shutil.rmtree(tmp_out)


class TestSplit:

    def test_split_evenly(self):
        """均匀划分 train/val/test"""
        images, boxes_dict = _collect_source_data()
        if len(images) < 10:
            pytest.skip("图片不足 10 张")

        tmp_out = os.path.join(tempfile.mkdtemp(), "test_split")
        labels_dir = os.path.join(tmp_out, "labels")
        os.makedirs(labels_dir, exist_ok=True)

        for idx, img_path in enumerate(images):
            base = os.path.splitext(os.path.basename(img_path))[0]
            txt_path = os.path.join(labels_dir, base + ".txt")
            with open(txt_path, 'w') as f:
                for b in boxes_dict.get(idx, []):
                    f.write(f"0 0.5 0.5 0.1 0.1\n")

        ratios = {"train": 0.8, "val": 0.1, "test": 0.1}
        splitter = Splitter(tmp_out)
        splitter.run(images, boxes_dict, ratios)

        divide_dir = os.path.join(tmp_out, "divide")
        assert os.path.isdir(os.path.join(divide_dir, "images", "train"))
        assert os.path.isdir(os.path.join(divide_dir, "images", "val"))
        assert os.path.isdir(os.path.join(divide_dir, "images", "test"))
        assert os.path.isdir(os.path.join(divide_dir, "labels", "train"))
        assert os.path.isdir(os.path.join(divide_dir, "labels", "val"))
        assert os.path.isdir(os.path.join(divide_dir, "labels", "test"))

        train_imgs = len(os.listdir(os.path.join(divide_dir, "images", "train")))
        val_imgs = len(os.listdir(os.path.join(divide_dir, "images", "val")))
        test_imgs = len(os.listdir(os.path.join(divide_dir, "images", "test")))
        total = train_imgs + val_imgs + test_imgs
        assert total == len(images), f"总数 {total} != {len(images)}"

        yaml_path = os.path.join(divide_dir, "dataset.yaml")
        assert os.path.exists(yaml_path), "dataset.yaml 未创建"
        shutil.rmtree(tmp_out)

    def test_split_with_augmented(self):
        """增广图划分"""
        images, boxes_dict = _collect_source_data()
        if len(images) < 5:
            pytest.skip("图片不足")

        tmp_out = os.path.join(tempfile.mkdtemp(), "test_split_aug")
        aug_dir = os.path.join(tmp_out, "images")
        labels_dir = os.path.join(tmp_out, "labels")
        os.makedirs(aug_dir, exist_ok=True)
        os.makedirs(labels_dir, exist_ok=True)

        count = min(3, len(images))
        for i in range(count):
            img_path = images[i]
            base = os.path.splitext(os.path.basename(img_path))[0]
            for suffix in ["_fliph", "_flipv"]:
                dst_img = os.path.join(aug_dir, f"{base}{suffix}.jpg")
                shutil.copy2(img_path, dst_img)
                dst_txt = os.path.join(labels_dir, f"{base}{suffix}.txt")
                with open(dst_txt, 'w') as f:
                    for b in boxes_dict.get(i, []):
                        f.write(f"0 0.5 0.5 0.1 0.1\n")

        aug_images = [os.path.join(aug_dir, f) for f in sorted(os.listdir(aug_dir))
                      if f.endswith('.jpg')]
        aug_boxes = {i: boxes_dict.get(i % count, []) for i in range(len(aug_images))}

        ratios = {"train": 0.8, "val": 0.1, "test": 0.1}
        splitter = Splitter(tmp_out)
        splitter.run(aug_images, aug_boxes, ratios)

        divide_dir = os.path.join(tmp_out, "divide")
        assert os.path.isdir(os.path.join(divide_dir, "images", "train"))
        train_imgs = len(os.listdir(os.path.join(divide_dir, "images", "train")))
        val_imgs = len(os.listdir(os.path.join(divide_dir, "images", "val")))
        test_imgs = len(os.listdir(os.path.join(divide_dir, "images", "test")))
        assert train_imgs + val_imgs + test_imgs == len(aug_images)
        shutil.rmtree(tmp_out)


class TestExportsIntegration:
    """直接使用 exports 目录中的真实数据测试"""

    def test_labels_dir_path(self):
        """验证 labels_dir 路径计算"""
        labels_dir = os.path.join(EXPORTS_DIR, "labels")
        images_dir = os.path.join(EXPORTS_DIR, "images")
        if not os.path.isdir(labels_dir) and not os.path.isdir(images_dir):
            pytest.skip("exports 目录不存在")
        if os.path.isdir(labels_dir):
            assert os.path.isdir(images_dir), f"有 labels 但无 images"

    def test_aug_label_image_count_match(self):
        """验证增广图和标签数量一致"""
        aug_dir = os.path.join(EXPORTS_DIR, "images")
        labels_dir = os.path.join(EXPORTS_DIR, "labels")
        if not os.path.isdir(aug_dir) or not os.path.isdir(labels_dir):
            pytest.skip("exports 目录不存在")

        img_files = [f for f in os.listdir(aug_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        txt_files = [f for f in os.listdir(labels_dir) if f.endswith('.txt')]
        assert len(img_files) == len(txt_files), \
            f"增广图 {len(img_files)} != 标签 {len(txt_files)}"

        img_basenames = {os.path.splitext(f)[0] for f in img_files}
        txt_basenames = {os.path.splitext(f)[0] for f in txt_files}
        missing_labels = img_basenames - txt_basenames
        assert not missing_labels, f"缺少标签: {missing_labels}"

    def test_splitter_reads_correct_labels_dir(self):
        """验证 Splitter 读取 labels 的路径"""
        splitter_output = os.path.join(EXPORTS_DIR, "divide")
        yolo_labels_dir = os.path.join(os.path.dirname(splitter_output), "labels")
        if not os.path.isdir(yolo_labels_dir):
            pytest.skip("labels 目录不存在")
        txt_files = [f for f in os.listdir(yolo_labels_dir) if f.endswith('.txt')]
        assert len(txt_files) > 0, "labels 目录无 txt 文件"

    def test_full_pipeline_on_real_data(self):
        """使用真实 exports 数据完整走一遍 Splitter"""
        aug_dir = os.path.join(EXPORTS_DIR, "images")
        labels_dir = os.path.join(EXPORTS_DIR, "labels")
        if not os.path.isdir(aug_dir) or not os.path.isdir(labels_dir):
            pytest.skip("exports 目录不存在")

        img_files = sorted([f for f in os.listdir(aug_dir)
                           if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
        if len(img_files) < 5:
            pytest.skip("增广图不足 5 张")

        aug_images = [os.path.join(aug_dir, f) for f in img_files]
        aug_boxes = {}
        for i, img_path in enumerate(aug_images):
            base = os.path.splitext(os.path.basename(img_path))[0]
            txt_path = os.path.join(labels_dir, base + ".txt")
            if os.path.exists(txt_path):
                boxes = []
                with open(txt_path, 'r') as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) == 5:
                            cls_id, xc, yc, w, h = map(float, parts)
                            boxes.append({"x": (xc - w/2) * 640, "y": (yc - h/2) * 480,
                                          "width": w * 640, "height": h * 480, "label": str(int(cls_id))})
                aug_boxes[i] = boxes
            else:
                aug_boxes[i] = []

        tmp_out = os.path.join(tempfile.mkdtemp(), "test_real_split")
        tmp_labels = os.path.join(tmp_out, "labels")
        os.makedirs(tmp_labels, exist_ok=True)
        for f in os.listdir(labels_dir):
            if f.endswith('.txt'):
                shutil.copy2(os.path.join(labels_dir, f), os.path.join(tmp_labels, f))

        ratios = {"train": 0.8, "val": 0.1, "test": 0.1}
        splitter = Splitter(tmp_out)
        splitter.run(aug_images, aug_boxes, ratios)

        divide_dir = os.path.join(tmp_out, "divide")
        assert os.path.isdir(os.path.join(divide_dir, "images", "train"))
        assert os.path.isdir(os.path.join(divide_dir, "images", "val"))
        assert os.path.isdir(os.path.join(divide_dir, "images", "test"))

        train_imgs = len(os.listdir(os.path.join(divide_dir, "images", "train")))
        val_imgs = len(os.listdir(os.path.join(divide_dir, "images", "val")))
        test_imgs = len(os.listdir(os.path.join(divide_dir, "images", "test")))
        total = train_imgs + val_imgs + test_imgs
        assert total == len(aug_images), f"划分总数 {total} != {len(aug_images)}"

        for split in ("train", "val", "test"):
            lbl_dir = os.path.join(divide_dir, "labels", split)
            img_dir = os.path.join(divide_dir, "images", split)
            lbl_count = len([f for f in os.listdir(lbl_dir) if f.endswith('.txt')])
            img_count = len([f for f in os.listdir(img_dir)
                            if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
            assert lbl_count == img_count, f"{split}: 标签 {lbl_count} != 图片 {img_count}"

        shutil.rmtree(tmp_out)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
