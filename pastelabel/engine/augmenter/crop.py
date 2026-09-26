"""滑窗裁剪：网格计算与标注过滤（纯函数）。

约定：可见比例 = 框 bbox 与窗口交集面积 / 框自身面积，低于 min_visible 丢弃；
rectangle 保留交集矩形；polygon/rotation 整框平移不逐点裁剪（与 RandomTranslate 一致）；
point 与退化框（宽或高为 0）按点处理，窗口内（含边界）才保留；空窗由调用方丢弃。
"""
from typing import List


def window_starts(length: int, size: int, overlap: int) -> List[int]:
    """单轴窗口起点：首窗贴 0，末窗贴边（start+size==length），余量均摊。"""
    if size >= length:
        return [0]
    step = max(1, size - overlap)
    n = 1 + -(-(length - size) // step)  # ceil((length-size)/step)
    span = length - size
    return [round(i * span / (n - 1)) for i in range(n)]


def size_for_count(length: int, count: int, overlap: int) -> int:
    """数量反推尺寸：n*c - (n-1)*ov = A → c=(A+(n-1)*ov)/n，钳制到 [ov+1, A]。"""
    if count <= 1:
        return length
    c = round((length + (count - 1) * overlap) / count)
    return min(max(overlap + 1, c), length)


def normalized_window(iw: int, ih: int, spec: dict) -> tuple:
    """把 spec 钳制到图像尺寸：返回 (cw, ch, ov)，面板/预览/引擎三处共用。"""
    cw = min(int(spec["w"]), iw)
    ch = min(int(spec["h"]), ih)
    ov = max(0, min(int(spec["overlap"]), cw - 1, ch - 1))
    return cw, ch, ov


def crop_boxes(boxes: List[dict], x0: int, y0: int, cw: int, ch: int,
               min_visible: float) -> List[dict]:
    """把标注过滤/平移到窗口 (x0,y0,cw,ch) 坐标系；不修改入参 box。"""
    from .base import map_box_points

    out = []
    wx1, wy1 = x0 + cw, y0 + ch
    for b in boxes:
        st = b.get("shape_type") or "rectangle"
        if st == "point":
            pts = b.get("points")
            px, py = (pts[0][0], pts[0][1]) if pts else (b["x"], b["y"])
            if x0 <= px <= wx1 and y0 <= py <= wy1:
                out.append(map_box_points(b, lambda x, y: (x - x0, y - y0)))
            continue
        pts = b.get("points")
        if pts and st != "rectangle":
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
        else:
            xs = [b["x"], b["x"] + b["width"]]
            ys = [b["y"], b["y"] + b["height"]]
        bx1, by1, bx2, by2 = min(xs), min(ys), max(xs), max(ys)
        bw, bh = bx2 - bx1, by2 - by1
        if bw <= 0 or bh <= 0:  # 退化框按点处理
            cx, cy = (bx1 + bx2) / 2, (by1 + by2) / 2
            if x0 <= cx <= wx1 and y0 <= cy <= wy1:
                out.append(map_box_points(b, lambda x, y: (x - x0, y - y0)))
            continue
        ix1, iy1 = max(bx1, x0), max(by1, y0)
        ix2, iy2 = min(bx2, wx1), min(by2, wy1)
        if ix2 <= ix1 or iy2 <= iy1:  # 零交集无条件丢弃（min_visible=0 也不例外）
            continue
        if (ix2 - ix1) * (iy2 - iy1) / (bw * bh) < min_visible:
            continue
        if st == "rectangle" and not pts:
            nx1, ny1 = max(b["x"], x0), max(b["y"], y0)
            nb = dict(b)
            nb["x"], nb["y"] = nx1 - x0, ny1 - y0
            nb["width"] = min(b["x"] + b["width"], wx1) - nx1
            nb["height"] = min(b["y"] + b["height"], wy1) - ny1
            if nb["width"] >= 1 and nb["height"] >= 1:
                out.append(nb)
        else:
            out.append(map_box_points(b, lambda x, y: (x - x0, y - y0)))
    return out
