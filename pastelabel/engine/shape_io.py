"""LabelMe shape <-> internal box conversion."""


def box_from_labelme_shape(shape):
    if not isinstance(shape, dict):
        return None
    points = shape.get("points") or []
    shape_type = shape.get("shape_type") or "rectangle"
    if shape_type == "point":
        if len(points) != 1:
            return None
        x, y = points[0][0], points[0][1]
        return {
            "x": x, "y": y, "width": 0, "height": 0,
            "label": shape.get("label") or "",
            "shape_type": shape_type,
            "group_id": shape.get("group_id"),
            "points": [list(points[0])],
        }
    if len(points) < 2:
        return None
    label = shape.get("label") or ""
    x_coords = [point[0] for point in points]
    y_coords = [point[1] for point in points]
    x = min(x_coords)
    y = min(y_coords)
    box = {
        "x": x,
        "y": y,
        "width": max(x_coords) - x,
        "height": max(y_coords) - y,
        "label": label,
        "shape_type": shape_type,
        "group_id": shape.get("group_id"),
    }
    if shape_type != "rectangle":
        box["points"] = [list(p) for p in points]
    if "visible" in shape:
        box["visible"] = shape["visible"]
    return box


def labelme_shape_from_box(box):
    shape_type = box.get("shape_type") or "rectangle"
    if shape_type == "rectangle":
        x, y, w, h = box["x"], box["y"], box["width"], box["height"]
        points = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]
    else:
        points = [list(p) for p in (box.get("points") or [])]
    shape = {
        "label": box.get("label", ""),
        "points": points,
        "group_id": box.get("group_id"),
        "description": "",
        "shape_type": shape_type,
        "flags": {},
    }
    if "visible" in box:
        shape["visible"] = box["visible"]
    return shape


def format_label_display(label, group_id=None):
    if group_id is not None:
        return f"{label} [{group_id}]"
    return label


def point_warning(point_box, all_boxes):
    """关键点校验：优先无同组框 → '无同组框'，否则不在框内 → '不在框内'，正常为 None。"""
    gid = point_box.get("group_id")
    if gid is None:
        return "无同组框"
    candidates = [
        box for box in (all_boxes or [])
        if (box.get("shape_type") or "rectangle") != "point"
        and box.get("group_id") == gid
    ]
    if not candidates:
        return "无同组框"
    points = point_box.get("points") or []
    px = points[0][0] if points else point_box.get("x", 0)
    py = points[0][1] if points else point_box.get("y", 0)
    for box in candidates:
        if point_in_box(px, py, box):
            return None
    return "不在框内"


def point_in_box(x, y, box):
    """(x, y) 是否落在框内。矩形用 bbox，多边形/旋转框有 points 时用多边形判定。"""
    if not isinstance(box, dict):
        return False
    points = box.get("points")
    if points and (box.get("shape_type") or "rectangle") != "rectangle":
        return point_in_polygon(x, y, points)
    bx, by = box.get("x", 0), box.get("y", 0)
    bw, bh = box.get("width", 0), box.get("height", 0)
    return bx <= x <= bx + bw and by <= y <= by + bh


def point_in_polygon(x, y, points):
    """Ray-casting; True if (x, y) is inside the polygon."""
    if len(points) < 3:
        return False
    inside = False
    j = len(points) - 1
    for i, (xi, yi) in enumerate(points):
        xj, yj = points[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def point_line_distance(point, line):
    """Distance from point (x, y) to segment line[(x1,y1),(x2,y2)]."""
    (x1, y1), (x2, y2) = line
    px, py = point
    dx, dy = x2 - x1, y2 - y1
    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq == 0:
        return ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5
    t = ((px - x1) * dx + (py - y1) * dy) / seg_len_sq
    t = max(0.0, min(1.0, t))
    cx, cy = x1 + t * dx, y1 + t * dy
    return ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5


def nearest_polygon_edge(point, points, epsilon):
    """Insertion index of the nearest edge within epsilon, else None.

    Index i means: insert between points[i-1] and points[i].
    """
    best_i = None
    min_dist = float("inf")
    for i in range(len(points)):
        line = (points[i - 1], points[i])
        dist = point_line_distance(point, line)
        if dist <= epsilon and dist < min_dist:
            min_dist = dist
            best_i = i
    return best_i


def yolo_pose_line(class_id, bbox, keypoints, image_width, image_height):
    """`cls cx cy w h x1 y1 v1 ...`; visibility fixed 2 (visible)."""
    if not image_width or not image_height:
        return None
    x, y, w, h = bbox
    parts = [str(class_id),
             f"{(x + w / 2) / image_width:.6f}",
             f"{(y + h / 2) / image_height:.6f}",
             f"{w / image_width:.6f}",
             f"{h / image_height:.6f}"]
    for kx, ky in keypoints:
        parts.append(f"{kx / image_width:.6f}")
        parts.append(f"{ky / image_height:.6f}")
        parts.append("2")
    return " ".join(parts)


def yolo_seg_line(box, class_id, image_width, image_height):
    points = box.get("points") or []
    if len(points) < 3 or not image_width or not image_height:
        return None
    parts = [str(class_id)]
    for x, y in points:
        parts.append(f"{x / image_width:.6f}")
        parts.append(f"{y / image_height:.6f}")
    return " ".join(parts)
