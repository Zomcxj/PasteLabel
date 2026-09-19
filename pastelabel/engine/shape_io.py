"""LabelMe shape <-> internal box conversion."""


def box_from_labelme_shape(shape):
    if not isinstance(shape, dict):
        return None
    points = shape.get("points") or []
    if len(points) < 2:
        return None
    label = shape.get("label") or ""
    shape_type = shape.get("shape_type") or "rectangle"
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


def yolo_seg_line(box, class_id, image_width, image_height):
    points = box.get("points") or []
    if len(points) < 3 or not image_width or not image_height:
        return None
    parts = [str(class_id)]
    for x, y in points:
        parts.append(f"{x / image_width:.6f}")
        parts.append(f"{y / image_height:.6f}")
    return " ".join(parts)
