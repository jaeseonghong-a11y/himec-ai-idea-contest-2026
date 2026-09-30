"""벽을 면으로 합쳐 외곽선만 그린다. 가로·세로 벽과 사선 벽을 함께 다룬다.

벽을 한 구간씩 두 줄로 그으면 기둥 속으로 벽선이 지나가고 모서리에서 벽끼리 어긋난다.
여기서는 벽(건물 벽, 코어 벽)을 중심선과 두께로 받아 면으로 만들고, 만나는 곳을 채우고, 기둥 자리를 뺀 뒤,
남은 면의 바깥선만 그린다(shapely).
- 기둥과 만나는 곳: 벽선이 기둥 면에서 멈춘다.
- 벽끼리 만나는 곳(ㄱ, ㅜ, +, 사선): 두 벽의 띠가 겹치는 자리(마름모)를 채워 어떤 각도에서도 모서리가 맞물린다.
- 코어 벽이 건물 벽에 붙는 곳: 한 덩어리로 이어진다.
곡선 벽은 아직 없다.
"""
import math

from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

FAR = 1e6


def column_rects(doc, layer="COL"):
    out = []
    for e in doc.modelspace().query(f'LWPOLYLINE[layer=="{layer}"]'):
        pts = [(p[0], p[1]) for p in e.get_points("xy")]
        if e.closed and len(pts) == 4:
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            out.append((min(xs), min(ys), max(xs), max(ys)))
    return out


def wall_seg(a, b, thick, layer, owner=None, lw=None):
    """중심선 a→b, 두께 thick 인 벽."""
    return {"a": (float(a[0]), float(a[1])), "b": (float(b[0]), float(b[1])), "t": thick / 2, "layer": layer, "owner": owner, "lw": lw}


def wall_rect(p, layer, owner=None, lw=None):
    """편집기의 add_wall 변경(from_xy, to_xy, thick)에서."""
    return wall_seg(p["from_xy"], p["to_xy"], p.get("thick", 200), layer, owner, lw)


def wall_from_box(x0, y0, x1, y1, layer, owner=None, lw=None):
    """코어 벽처럼 사각형으로 주어진 벽. 긴 방향이 중심선이다."""
    if x1 - x0 >= y1 - y0:
        cy = (y0 + y1) / 2
        return wall_seg((x0, cy), (x1, cy), y1 - y0, layer, owner, lw)
    cx = (x0 + x1) / 2
    return wall_seg((cx, y0), (cx, y1), x1 - x0, layer, owner, lw)


def _unit(w):
    dx, dy = w["b"][0] - w["a"][0], w["b"][1] - w["a"][1]
    L = math.hypot(dx, dy) or 1.0
    return dx / L, dy / L, L


def _poly(w):
    return LineString([w["a"], w["b"]]).buffer(w["t"], cap_style="flat", join_style="mitre")


def _strip(w, reach=FAR):
    """벽의 띠. reach 만큼 양쪽으로 늘인 중심선을 두께로 두껍게 한 것 (기본은 무한히 긴 띠, 모서리 채움용)."""
    ux, uy, _ = _unit(w)
    a = (w["a"][0] - ux * reach, w["a"][1] - uy * reach)
    b = (w["b"][0] + ux * reach, w["b"][1] + uy * reach)
    return LineString([a, b]).buffer(w["t"], cap_style="flat", join_style="mitre")


def joint_patches(walls, tol=1.0):
    """끝점을 같이 쓰는, 나란하지 않은 두 벽마다 두 띠가 겹치는 마름모를 만든다. 어떤 각도의 모서리도 이것으로 채워진다."""
    ends = {}
    for i, w in enumerate(walls):
        for p in (w["a"], w["b"]):
            ends.setdefault((round(p[0] / tol), round(p[1] / tol)), []).append(i)
    patches, seen = [], set()
    for key, idx in ends.items():
        if len(idx) < 2:
            continue
        for i in idx:
            for j in idx:
                if i >= j or (i, j) in seen:
                    continue
                seen.add((i, j))
                ui, uj = _unit(walls[i]), _unit(walls[j])
                if abs(ui[0] * uj[1] - ui[1] * uj[0]) < 0.05:      # 나란한(이어지는) 벽은 마름모가 무한히 길어지므로 뺀다
                    continue
                P = Point(key[0] * tol, key[1] * tol)
                inter = _strip(walls[i]).intersection(_strip(walls[j]))
                near = inter.buffer(0).intersection(P.buffer(max(walls[i]["t"], walls[j]["t"]) * 4))      # 교점 둘레만
                if not near.is_empty:
                    patches.append(near)
    return patches


def outline(walls, columns):
    """합친 면의 바깥선. 돌려주는 값: [(x1, y1, x2, y2, layer, owner, 선 굵기)]"""
    if not walls:
        return []
    polys = [_poly(w) for w in walls]
    union = unary_union(polys + joint_patches(walls))
    cols = [box(*c) for c in columns]
    if cols:
        union = union.difference(unary_union(cols))
    strips = [_strip(w, reach=w["t"] * 3) for w in walls]      # 선이 어느 벽의 것인지 정할 때는 벽 끝에서 조금만 더 본다(모서리 채움 범위)
    col_bounds = [c.exterior for c in cols]
    out = []
    geoms = list(union.geoms) if hasattr(union, "geoms") else [union]
    for g in geoms:
        if g.is_empty or not isinstance(g, Polygon):
            continue
        for ring in [g.exterior, *g.interiors]:
            pts = list(ring.coords)
            for p, q in zip(pts, pts[1:]):
                if math.hypot(q[0] - p[0], q[1] - p[1]) < 0.5:
                    continue
                m = Point((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
                if any(b.distance(m) < 0.01 for b in col_bounds):      # 기둥과 닿은 변은 기둥 외곽선이 대신한다
                    continue
                k = min(range(len(walls)), key=lambda i: (round(strips[i].exterior.distance(m), 1), walls[i]["owner"] is not None))      # 같은 거리면 건물 벽(코어 벽보다) 우선
                w = walls[k]
                out.append((p[0], p[1], q[0], q[1], w["layer"], w["owner"], w.get("lw")))
    return _merge(out)


def _merge(lines, tol=0.5):
    """같은 직선 위에서 이어지는 선분은 하나로 합친다."""
    out, used = [], [False] * len(lines)
    for i, L in enumerate(lines):
        if used[i]:
            continue
        x1, y1, x2, y2, layer, owner, lw = L
        changed = True
        while changed:
            changed = False
            for j, M in enumerate(lines):
                if used[j] or j == i or M[4:] != (layer, owner, lw):
                    continue
                ux, uy = x2 - x1, y2 - y1
                vx, vy = M[2] - M[0], M[3] - M[1]
                if abs(ux * vy - uy * vx) > tol * max(1.0, math.hypot(ux, uy)):
                    continue
                for (px, py), (qx, qy) in (((M[0], M[1]), (M[2], M[3])), ((M[2], M[3]), (M[0], M[1]))):
                    if math.hypot(px - x2, py - y2) < tol:
                        x2, y2 = qx, qy; used[j] = True; changed = True; break
                    if math.hypot(qx - x1, qy - y1) < tol:
                        x1, y1 = px, py; used[j] = True; changed = True; break
                if changed:
                    break
        used[i] = True
        out.append((x1, y1, x2, y2, layer, owner, lw))
    return out


def trim_by_columns(s, e, q, horiz, columns, pad=0):
    """가로·세로 선분(s~e, 직각 방향 좌표 q)에서 기둥 속에 든 구간을 뺀 나머지 (보 선 등)."""
    cuts = []
    for c in columns:
        lo, hi, a, b = (c[1], c[3], c[0], c[2]) if horiz else (c[0], c[2], c[1], c[3])
        if lo - 1e-6 < q < hi + 1e-6:
            cuts.append((a - pad, b + pad))
    out, cur = [], s
    for a, b in sorted(cuts):
        if b <= cur or a >= e:
            continue
        if a > cur:
            out.append((cur, a))
        cur = max(cur, b)
    if cur < e:
        out.append((cur, e))
    return out


def clip_line(a, b, columns):
    """임의 방향 선분에서 기둥 속에 든 구간을 뺀 나머지 [(p, q)]."""
    ln = LineString([a, b])
    if columns:
        ln = ln.difference(unary_union([box(*c) for c in columns]))
    parts = list(ln.geoms) if hasattr(ln, "geoms") else [ln]
    return [(tuple(p.coords[0]), tuple(p.coords[-1])) for p in parts if not p.is_empty and p.length > 0.5]


def offset_lines(a, b, half):
    """중심선 a→b 양쪽으로 half 만큼 떨어진 두 선."""
    ux, uy, _ = _unit({"a": a, "b": b})
    nx, ny = -uy * half, ux * half
    return [((a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny)), ((a[0] - nx, a[1] - ny), (b[0] - nx, b[1] - ny))]


def draw(doc, walls, columns):
    msp = doc.modelspace()
    lines, by_owner = outline(walls, columns), {}
    for x1, y1, x2, y2, layer, owner, lw in lines:
        if layer not in doc.layers:
            doc.layers.add(layer)
        ln = msp.add_line((x1, y1), (x2, y2), dxfattribs={"layer": layer, **({"lineweight": lw} if lw else {})})      # 벽 두께에 따른 선 굵기
        by_owner.setdefault(owner, []).append(ln)
    joints = len(joint_patches(walls))
    diag = sum(1 for w in walls if abs(w["a"][0] - w["b"][0]) > 1 and abs(w["a"][1] - w["b"][1]) > 1)
    return {"lines": len(lines), "corners": joints, "walls": len(walls), "diagonal": diag, "columns": len(columns), "by_owner": by_owner}
