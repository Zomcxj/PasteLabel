"""
models.py 单元测试 - 纯 Python dataclass 测试
PyQt5 由 conftest.py mock
"""
import sys
import os
import importlib.util


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_models_path = os.path.join(os.path.dirname(__file__), '..', 'core', 'models.py')
_models = _load_module('PasteY.core.models', os.path.abspath(_models_path))

DetectionBox = _models.DetectionBox
SaveInfo = _models.SaveInfo
LabelMeShape = _models.LabelMeShape
LabelMeData = _models.LabelMeData


class TestDetectionBox:
    """DetectionBox 测试"""

    def test_to_dict(self):
        box = DetectionBox(x=10, y=20, width=100, height=50, label="cat")
        d = box.to_dict()
        assert d == {"x": 10, "y": 20, "width": 100, "height": 50, "label": "cat"}

    def test_from_dict(self):
        d = {"x": 10, "y": 20, "width": 100, "height": 50, "label": "cat"}
        box = DetectionBox.from_dict(d)
        assert box.x == 10
        assert box.y == 20
        assert box.width == 100
        assert box.height == 50
        assert box.label == "cat"

    def test_from_dict_missing_fields(self):
        d = {"x": 5}
        box = DetectionBox.from_dict(d)
        assert box.x == 5
        assert box.y == 0
        assert box.width == 0
        assert box.height == 0
        assert box.label == ""

    def test_is_valid_normal(self):
        box = DetectionBox(10, 10, 10, 10, "x")
        assert box.is_valid() is True

    def test_is_valid_at_origin(self):
        box = DetectionBox(0, 0, 10, 10, "x")
        assert box.is_valid() is False

    def test_is_valid_too_small(self):
        box = DetectionBox(10, 10, 1, 1, "x")
        assert box.is_valid() is False

    def test_is_valid_custom_min(self):
        box = DetectionBox(10, 10, 5, 5, "x")
        assert box.is_valid(min_width=10, min_height=10) is False
        assert box.is_valid(min_width=3, min_height=3) is True

    def test_get_points(self):
        box = DetectionBox(10, 20, 100, 50, "x")
        points = box.get_points()
        assert points == [
            [10, 20],
            [110, 20],
            [110, 70],
            [10, 70]
        ]

    def test_roundtrip(self):
        original = DetectionBox(10, 20, 100, 50, "cat")
        restored = DetectionBox.from_dict(original.to_dict())
        assert original.x == restored.x
        assert original.y == restored.y
        assert original.width == restored.width
        assert original.height == restored.height
        assert original.label == restored.label


class TestSaveInfo:
    """SaveInfo 测试"""

    def test_creation(self):
        info = SaveInfo(
            file_path="/tmp/output.png",
            base_name="prefix_image.png",
            prefix="prefix",
            output_dir="/tmp/output"
        )
        assert info.file_path == "/tmp/output.png"
        assert info.base_name == "prefix_image.png"
        assert info.prefix == "prefix"
        assert info.output_dir == "/tmp/output"


class TestLabelMeShape:
    """LabelMeShape 测试"""

    def test_to_dict(self):
        shape = LabelMeShape(
            label="cat",
            points=[[10, 20], [110, 20], [110, 70], [10, 70]]
        )
        d = shape.to_dict()
        assert d["label"] == "cat"
        assert len(d["points"]) == 4
        assert d["shape_type"] == "rectangle"
        assert d["flags"] == {}

    def test_defaults(self):
        shape = LabelMeShape(label="dog", points=[[0, 0], [10, 10]])
        assert shape.group_id is None
        assert shape.description == ""
        assert shape.shape_type == "rectangle"


class TestLabelMeData:
    """LabelMeData 测试"""

    def test_to_dict(self):
        data = LabelMeData()
        data.shapes.append(LabelMeShape(
            label="cat",
            points=[[0, 0], [10, 0], [10, 10], [0, 10]]
        ))
        data.imagePath = "test.png"
        data.imageWidth = 100
        data.imageHeight = 100

        d = data.to_dict()
        assert d["version"] == "5.0.1"
        assert len(d["shapes"]) == 1
        assert d["imagePath"] == "test.png"
        assert d["imageWidth"] == 100
        assert d["imageHeight"] == 100
        assert d["imageData"] is None

    def test_empty(self):
        data = LabelMeData()
        d = data.to_dict()
        assert d["shapes"] == []
        assert d["flags"] == {}
