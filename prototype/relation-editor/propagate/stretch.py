"""영역 STRETCH.

AutoCAD의 STRETCH처럼, 지정한 영역 안에 있는 정점만 (dx, dy)만큼 옮긴다.
- stretch_region: 임의 영역(판정 함수)
- stretch_band:   그리드 좌표 ± half_width 띠 (그리드 이동)
- 치수는 영역 안의 정의점을 옮기고 ezdxf로 그래픽을 재생성
- 해치는 폴리선 경계·직선 경계만 처리하고 곡선 경계는 표시만 한다
"""
import ezdxf
from ezdxf.entities import BoundaryPathType, EdgeType


def rerender_dim(doc, d):
    old_blk = d.dxf.geometry
    try:
        d.render()
        ok = True
    except Exception:
        d.dxf.geometry = ""
        ok = False
    if old_blk and old_blk in doc.blocks and d.dxf.geometry != old_blk:
        try:
            doc.blocks.delete_block(old_blk, safe=False)
        except Exception:
            pass
    return ok


def stretch_region(doc, inside, dx: float, dy: float, exclude_handles=(), only_handles=None, exclude_layers=(), only_layers=None, rigid_cross=False):
    """inside(x, y) -> bool 인 정점을 (dx, dy) 이동.
    rigid_cross=True 이면 이동 방향과 나란한 선분만 늘이거나 줄이고, 나란하지 않은 선분은 한쪽 끝이 영역 안에 있으면
    통째로 옮긴다. 벽과 직각인 선의 한쪽 끝만 움직여 비스듬해지는 것을 막는다."""
    msp = doc.modelspace()
    exclude_handles = set(exclude_handles)
    only = set(only_handles) if only_handles is not None else None
    stats, moved, dims, flagged = {}, [], [], []

    def bump(e):
        k = f"{e.dxf.layer}:{e.dxftype()}"
        stats[k] = stats.get(k, 0) + 1
        moved.append(e.dxf.handle)

    def sp(p):
        return (p[0] + dx, p[1] + dy, p[2] if len(p) > 2 else 0.0)

    def hit(p):
        return inside(p[0], p[1])

    def parallel(a, b):
        """선분 a-b가 이동 방향과 나란한가"""
        vx, vy = b[0] - a[0], b[1] - a[1]
        return abs(vx * dy - vy * dx) <= 1e-6 * max(1.0, abs(vx) + abs(vy)) * max(1.0, abs(dx) + abs(dy))

    for e in list(msp):
        h = e.dxf.handle
        if h in exclude_handles or (only is not None and h not in only) or e.dxf.layer in exclude_layers:
            continue
        if only_layers is not None and e.dxf.layer not in only_layers:
            continue
        t = e.dxftype()
        try:
            if t == "LINE":
                hs_, he_ = hit(e.dxf.start), hit(e.dxf.end)
                if rigid_cross and (hs_ or he_) and not parallel(e.dxf.start, e.dxf.end):
                    hs_ = he_ = True
                n = 0
                if hs_:
                    e.dxf.start = sp(e.dxf.start); n += 1
                if he_:
                    e.dxf.end = sp(e.dxf.end); n += 1
                if n:
                    bump(e)
            elif t == "LWPOLYLINE":
                pts = [list(p) for p in e.get_points()]
                mark = [hit(p) for p in pts]
                if rigid_cross and any(mark):
                    segs = list(zip(range(len(pts)), range(1, len(pts)))) + ([(len(pts) - 1, 0)] if e.closed and len(pts) > 2 else [])
                    changed = True
                    while changed:
                        changed = False
                        for i, j in segs:
                            if mark[i] != mark[j] and not parallel(pts[i], pts[j]):
                                mark[i] = mark[j] = True; changed = True
                n = 0
                for p, mk in zip(pts, mark):
                    if mk:
                        p[0] += dx; p[1] += dy; n += 1
                if n:
                    e.set_points([tuple(p) for p in pts]); bump(e)
            elif t == "POLYLINE":
                n = 0
                for v in e.vertices:
                    loc = v.dxf.location
                    if hit(loc):
                        v.dxf.location = sp(loc); n += 1
                if n:
                    bump(e)
            elif t == "INSERT":
                if hit(e.dxf.insert):
                    e.translate(dx, dy, 0); bump(e)     # 블록 속성(이름표)도 함께 이동
            elif t in ("TEXT", "MTEXT", "ATTDEF", "POINT"):
                name = "location" if t == "POINT" else "insert"
                p = getattr(e.dxf, name)
                if hit(p):
                    setattr(e.dxf, name, sp(p)); bump(e)
            elif t in ("CIRCLE", "ARC", "ELLIPSE"):
                if hit(e.dxf.center):
                    e.dxf.center = sp(e.dxf.center); bump(e)
            elif t in ("SOLID", "TRACE", "3DFACE"):
                n = 0
                for name in ("vtx0", "vtx1", "vtx2", "vtx3"):
                    p = getattr(e.dxf, name)
                    if hit(p):
                        setattr(e.dxf, name, sp(p)); n += 1
                if n:
                    bump(e)
            elif t == "HATCH":
                n, other = 0, False
                for path in e.paths:
                    if path.type == BoundaryPathType.POLYLINE:
                        new = []
                        for v in path.vertices:
                            v = list(v)
                            if hit(v):
                                v[0] += dx; v[1] += dy; n += 1
                            new.append(tuple(v))
                        path.vertices = new
                    else:
                        for edge in path.edges:
                            if edge.type == EdgeType.LINE:
                                if hit(edge.start):
                                    edge.start = (edge.start[0] + dx, edge.start[1] + dy); n += 1
                                if hit(edge.end):
                                    edge.end = (edge.end[0] + dx, edge.end[1] + dy); n += 1
                            else:
                                other = True
                if n:
                    bump(e)
                if other and n:
                    flagged.append({"handle": h, "layer": e.dxf.layer, "issue": "HATCH 곡선 경계는 이동하지 않음"})
            elif t == "DIMENSION":
                old_m = round(e.get_measurement()) if e.dimtype in (0, 1) else None
                mv = []
                for name in ("defpoint", "defpoint2", "defpoint3", "defpoint4", "defpoint5", "text_midpoint"):
                    if e.dxf.hasattr(name):
                        p = getattr(e.dxf, name)
                        if hit(p):
                            setattr(e.dxf, name, sp(p)); mv.append(name)
                if mv:
                    new_m = round(e.get_measurement()) if e.dimtype in (0, 1) else None
                    ok = rerender_dim(doc, e)
                    bump(e)
                    dims.append({"handle": h, "moved": mv, "old": old_m, "new": new_m, "rerender": ok})
        except Exception as ex:
            flagged.append({"handle": h, "layer": e.dxf.layer, "issue": f"{t} 처리 오류: {str(ex)[:60]}"})

    return {"dx": dx, "dy": dy, "moved_count": len(moved), "by_layer": dict(sorted(stats.items(), key=lambda kv: -kv[1])),
            "moved_handles": moved, "dims": dims, "flagged": flagged}


def stretch_band(doc, axis: str, coord: float, delta: float, half_width: float = 700, exclude_layers=()):
    ai = 0 if axis == "x" else 1
    dx, dy = (delta, 0.0) if axis == "x" else (0.0, delta)
    res = stretch_region(doc, lambda x, y: abs((x, y)[ai] - coord) <= half_width, dx, dy, exclude_layers=exclude_layers)
    res.update({"axis": axis, "coord": coord, "delta": delta, "half_width": half_width})
    return res


def columns_in_band(msp, axis, coord, hw=700):
    ai = 0 if axis == "x" else 1
    out = []
    for e in msp.query('LWPOLYLINE[layer=="COL"]'):
        pts = [(p[0], p[1]) for p in e.get_points()]
        if len(pts) < 4:
            continue
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        c = ((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2)
        if 250 <= w <= 1200 and 250 <= h <= 1200 and abs(c[ai] - coord) <= hw:
            out.append(e)
    return out


def touching(msp, target, layers=("WAL", "FIN", "마감선", "단열재"), tol=60):
    from ezdxf import bbox as bb
    tb = bb.extents([target])
    hits = set()
    if not tb.has_data:
        return hits
    for e in msp:
        if e.dxf.layer not in layers or e.dxftype() not in ("LINE", "LWPOLYLINE"):
            continue
        eb = bb.extents([e])
        if eb.has_data and (eb.extmin.x <= tb.extmax.x + tol and eb.extmax.x >= tb.extmin.x - tol and
                            eb.extmin.y <= tb.extmax.y + tol and eb.extmax.y >= tb.extmin.y - tol):
            hits.add(e.dxf.handle)
    return hits


def grid_move_with_checks(doc, axis, coord, delta, half_width=700):
    """띠 STRETCH 실행 + 기둥에 접한 벽선이 따라왔는지 검사."""
    msp = doc.modelspace()
    cols = columns_in_band(msp, axis, coord, half_width)
    before = {c.dxf.handle: touching(msp, c) for c in cols}
    res = stretch_band(doc, axis, coord, delta, half_width)
    checks = []
    for c in cols:
        after = touching(msp, c)
        lost = before[c.dxf.handle] - after
        checks.append({"column": c.dxf.handle, "walls_before": len(before[c.dxf.handle]), "walls_after": len(after),
                       "lost": sorted(lost), "ok": not lost})
    res["column_checks"] = checks
    return res
