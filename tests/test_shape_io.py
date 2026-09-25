"""LabelMe shape <-> internal box conversion (polygon / group_id / compat)."""
from pastelabel.engine.shape_io import (
    box_from_labelme_shape,
    format_label_display,
    labelme_shape_from_box,
    yolo_seg_line,
)


def test_old_json_without_shape_type_loads_as_rectangle():
    box = box_from_labelme_shape({
        "label": "cat",
        "points": [[10, 20], [110, 20], [110, 80], [10, 80]],
    })
    assert box["shape_type"] == "rectangle"
    assert box["x"] == 10
    assert box["y"] == 20
    assert box["width"] == 100
    assert box["height"] == 60
    assert box["label"] == "cat"
    assert box.get("group_id") is None


def test_polygon_shape_keeps_points_and_bbox():
    pts = [[10, 10], [50, 10], [40, 40]]
    box = box_from_labelme_shape({
        "label": "person",
        "shape_type": "polygon",
        "points": pts,
        "group_id": 2,
    })
    assert box["shape_type"] == "polygon"
    assert box["points"] == pts
    assert box["x"] == 10
    assert box["y"] == 10
    assert box["width"] == 40
    assert box["height"] == 30
    assert box["group_id"] == 2


def test_labelme_roundtrip_polygon_preserves_points_and_group():
    box = {
        "label": "dog",
        "shape_type": "polygon",
        "points": [[1, 2], [3, 4], [5, 1]],
        "x": 1, "y": 1, "width": 4, "height": 3,
        "group_id": 3,
    }
    shape = labelme_shape_from_box(box)
    assert shape["shape_type"] == "polygon"
    assert shape["points"] == box["points"]
    assert shape["group_id"] == 3
    assert shape["label"] == "dog"


def test_labelme_roundtrip_rectangle_still_four_corner_points():
    box = {"label": "cat", "x": 10, "y": 20, "width": 30, "height": 40}
    shape = labelme_shape_from_box(box)
    assert shape["shape_type"] == "rectangle"
    assert shape["points"] == [[10, 20], [40, 20], [40, 60], [10, 60]]
    assert shape["group_id"] is None


def test_format_label_display_shows_group_brackets():
    assert format_label_display("nose") == "nose"
    assert format_label_display("nose", None) == "nose"
    assert format_label_display("nose", 1) == "nose [1]"


def test_yolo_seg_line_normalizes_polygon_points():
    box = {
        "label": "person",
        "shape_type": "polygon",
        "points": [[50, 25], [150, 25], [100, 75]],
    }
    line = yolo_seg_line(box, class_id=0, image_width=200, image_height=100)
    assert line.startswith("0 ")
    parts = line.split()
    assert parts[0] == "0"
    assert len(parts) == 1 + 6
    assert parts[1:3] == ["0.250000", "0.250000"]


def test_point_in_polygon_inside_and_outside():
    from pastelabel.engine.shape_io import point_in_polygon
    pts = [[10, 10], [40, 10], [40, 40]]
    assert point_in_polygon(30, 20, pts) is True
    assert point_in_polygon(11, 39, pts) is False


def test_point_line_distance_perpendicular_and_clamped():
    from pastelabel.engine.shape_io import point_line_distance
    assert point_line_distance((15, 20), ((10, 10), (40, 10))) == 10.0
    assert point_line_distance((0, 0), ((10, 10), (40, 10))) == 200 ** 0.5


def test_nearest_polygon_edge_insert_index():
    from pastelabel.engine.shape_io import nearest_polygon_edge
    pts = [[10, 10], [40, 10], [40, 40], [10, 40]]
    assert nearest_polygon_edge((25, 10), pts, 3.0) == 1
    assert nearest_polygon_edge((40, 25), pts, 3.0) == 2
    assert nearest_polygon_edge((25, 40), pts, 3.0) == 3
    assert nearest_polygon_edge((10, 25), pts, 3.0) == 0
    assert nearest_polygon_edge((70, 25), pts, 3.0) is None


def test_point_shape_roundtrips_through_labelme():
    shape = {"label": "nose", "points": [[12.5, 30.0]],
             "group_id": 2, "shape_type": "point", "flags": {}}
    box = box_from_labelme_shape(shape)
    assert box is not None
    assert box["shape_type"] == "point"
    assert box["points"] == [[12.5, 30.0]]
    assert box["x"] == 12.5 and box["y"] == 30.0

    back = labelme_shape_from_box(box)
    assert back["shape_type"] == "point"
    assert back["points"] == [[12.5, 30.0]]


def test_yolo_seg_line_skips_fewer_than_three_points():
    box = {"shape_type": "polygon", "points": [[1, 1], [2, 2]]}
    assert yolo_seg_line(box, 0, 100, 100) is None


def test_paste_flag_round_trip():
    from pastelabel.engine.shape_io import labelme_shape_from_box, box_from_labelme_shape
    box = {"label": "logo", "x": 1, "y": 2, "width": 3, "height": 4}
    shape = labelme_shape_from_box(box)
    assert shape["flags"] == {}
    assert box_from_labelme_shape(shape)["is_paste"] is False
    shape["flags"] = {"paste": True}
    assert box_from_labelme_shape(shape)["is_paste"] is True


def test_labelme_shape_from_box_preserves_flags():
    from pastelabel.engine.shape_io import labelme_shape_from_box
    shape = labelme_shape_from_box(
        {"label": "logo", "x": 0, "y": 0, "width": 1, "height": 1,
         "flags": {"paste": True}})
    assert shape["flags"] == {"paste": True}
