"""실제 도면(DXF) → 관계 그래프 (그리드 기반) + 약속한 표기법 렌더링.

표기: ○ 기둥(단면 크기에 비례) · 실선 벽 · 점선 보 · □ 창호 · △ 문 · 녹색 치수 · 회색 그리드 · 우측 일람표

읽는 단서
- 그리드: CEN 레이어 수직/수평선 → X1.., Y1.. (도면의 실제 명칭은 모델 공간에 없어 좌표순 자동 명명)
- 기둥: COL 레이어 사각 폴리선 중 그리드 교점 위 → 노드 C@Xi-Yj
- 벽: 그리드 구간과 나란한 WAL 레이어 선분이 구간 길이의 일정 비율 이상을 덮으면 벽
- 보: 양 끝이 기둥인 구간(구조 추정) 또는 HID(은선) 레이어가 나란히 있는 구간
- 창호: WID/WID-S 레이어 요소를 군집화해 가장 가까운 벽 구간에 붙임
- 문: DOOR/RXDOOR/DOOR-S 레이어의 호(문 궤적)를 군집화해 가장 가까운 벽 구간에 붙임
- 치수: DIMENSION 정의점이 그리드 좌표와 일치하면 그 그리드에 연결
출력: out/real/graph_real.json, out/real/graph_real_before.png
"""
import json
import math
import sys
from pathlib import Path

import ezdxf

ROOT = Path(__file__).resolve().parents[1]
GRID_TOL = 5
COL_TOL = 450
WALL_OFF = 450      # 벽 중심선이 그리드에서 벗어날 수 있는 거리
WALL_MIN_COVER = 0.25
HID_MIN_COVER = 0.25
OPEN_ATTACH = 600   # 창호·문 중심에서 벽 구간까지 허용 거리
CLUSTER_GAP = 150

WALL_LAYERS = ("WAL", "마감선", "단열재", "COL")   # 이 도면은 콘크리트 벽체를 COL 레이어에 그린다
DOOR_BAND_MIN = 0.4   # 벽 구간 위를 DOOR 레이어 선이 이 비율 이상 덮으면 문 띠(접이문·쇼윈도)
HID_LAYERS = ("HID",)
WIN_LAYERS = ("WID", "WID-S")
DOOR_LAYERS = ("DOOR", "RXDOOR", "DOOR-S")


# ---------- 기본 유틸 ----------
def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def segments_of(msp, layers, types=("LINE", "LWPOLYLINE")):
    """레이어의 선분 목록 [(x1,y1,x2,y2,handle)]"""
    out = []
    for e in msp:
        if e.dxf.layer not in layers or e.dxftype() not in types:
            continue
        if e.dxftype() == "LINE":
            out.append((e.dxf.start.x, e.dxf.start.y, e.dxf.end.x, e.dxf.end.y, e.dxf.handle))
        else:
            pts = [(p[0], p[1]) for p in e.get_points()]
            if e.closed and len(pts) > 2:
                pts.append(pts[0])
            for a, b in zip(pts, pts[1:]):
                out.append((a[0], a[1], b[0], b[1], e.dxf.handle))
    return out


def coverage(seg_a, seg_b, axis_h, segs, off_tol, rivals=()):
    """그리드 구간 a-b(수평이면 axis_h=True)와 나란한 선분들이 덮는 비율.
    rivals: 같은 방향의 다른 그리드 좌표들. 선분이 다른 그리드에 더 가까우면 그쪽 벽으로 보고 제외한다."""
    lo, hi = (min(seg_a[0], seg_b[0]), max(seg_a[0], seg_b[0])) if axis_h else (min(seg_a[1], seg_b[1]), max(seg_a[1], seg_b[1]))
    line_c = seg_a[1] if axis_h else seg_a[0]
    L = hi - lo
    if L <= 0:
        return 0.0, []
    ivs, handles = [], set()
    for x1, y1, x2, y2, h in segs:
        if axis_h:
            if abs(y1 - y2) > 1 or abs(y1 - line_c) > off_tol:
                continue
            if any(abs(y1 - r) < abs(y1 - line_c) - 1 for r in rivals):
                continue
            a, b = min(x1, x2), max(x1, x2)
        else:
            if abs(x1 - x2) > 1 or abs(x1 - line_c) > off_tol:
                continue
            if any(abs(x1 - r) < abs(x1 - line_c) - 1 for r in rivals):
                continue
            a, b = min(y1, y2), max(y1, y2)
        a, b = max(a, lo), min(b, hi)
        if b > a:
            ivs.append((a, b)); handles.add(h)
    ivs.sort()
    total, cur = 0.0, None
    for a, b in ivs:
        if cur is None or a > cur[1]:
            if cur:
                total += cur[1] - cur[0]
            cur = [a, b]
        else:
            cur[1] = max(cur[1], b)
    if cur:
        total += cur[1] - cur[0]
    merged = []
    cur = None
    for a, b in ivs:
        if cur is None or a > cur[1]:
            if cur:
                merged.append(tuple(cur))
            cur = [a, b]
        else:
            cur[1] = max(cur[1], b)
    if cur:
        merged.append(tuple(cur))
    return total / L, sorted(handles), merged, (lo, hi)


def cluster_boxes(boxes, gap):
    """[(xmin,ymin,xmax,ymax,handle)] → 가까운 것끼리 병합한 군집"""
    clusters = []
    for b in boxes:
        merged = None
        for c in clusters:
            if b[0] <= c["xmax"] + gap and b[2] >= c["xmin"] - gap and b[1] <= c["ymax"] + gap and b[3] >= c["ymin"] - gap:
                c["xmin"], c["ymin"] = min(c["xmin"], b[0]), min(c["ymin"], b[1])
                c["xmax"], c["ymax"] = max(c["xmax"], b[2]), max(c["ymax"], b[3])
                c["handles"].append(b[4]); merged = c
                break
        if merged is None:
            clusters.append({"xmin": b[0], "ymin": b[1], "xmax": b[2], "ymax": b[3], "handles": [b[4]]})
    # 병합으로 겹치게 된 군집 재병합 (한 번 더)
    changed = True
    while changed:
        changed = False
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                a, c = clusters[i], clusters[j]
                if a["xmin"] <= c["xmax"] + gap and a["xmax"] >= c["xmin"] - gap and a["ymin"] <= c["ymax"] + gap and a["ymax"] >= c["ymin"] - gap:
                    a["xmin"], a["ymin"] = min(a["xmin"], c["xmin"]), min(a["ymin"], c["ymin"])
                    a["xmax"], a["ymax"] = max(a["xmax"], c["xmax"]), max(a["ymax"], c["ymax"])
                    a["handles"] += c["handles"]; clusters.pop(j); changed = True
                    break
            if changed:
                break
    return clusters


def attach_to_edge(pt, edges, nodes, max_d):
    best = None
    for e in edges:
        a, b = nodes[e["from"]]["xy"], nodes[e["to"]]["xy"]
        L2 = (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2
        if L2 == 0:
            continue
        t = ((pt[0] - a[0]) * (b[0] - a[0]) + (pt[1] - a[1]) * (b[1] - a[1])) / L2
        if t < -0.02 or t > 1.02:
            continue
        t = min(max(t, 0.0), 1.0)
        c = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
        d = dist(pt, c)
        if d <= max_d and (best is None or d < best[0]):
            best = (d, e["id"], round(t, 3))
    return best


def wall_gap(msp, horiz, wall_c, center, zone=450):
    """개구부 중심을 끼고 벽선이 끊긴 구간의 폭을 레이어 계열별로 잰다. {계열: 폭}"""
    res = {}
    for layers in (("COL",), ("WAL",), ("마감선", "단열재")):
        by_q = {}
        for x1, y1, x2, y2, _h in segments_of(msp, layers):
            (a1, q1), (a2, q2) = ((x1, y1), (x2, y2)) if horiz else ((y1, x1), (y2, x2))
            if abs(q1 - q2) < 1 and abs(q1 - wall_c) <= zone and abs(a1 - a2) > 1:
                by_q.setdefault(round(q1 - wall_c), []).append((min(a1, a2), max(a1, a2)))
        found = []
        for q, ivs in by_q.items():
            if any(lo < center - 1 and hi > center + 1 for lo, hi in ivs):
                continue   # 개구부를 가로질러 이어진 선
            left = [hi for lo, hi in ivs if hi <= center + 1]
            right = [lo for lo, hi in ivs if lo >= center - 1]
            if left and right:
                found.append(round(min(right) - max(left)))
        if found:
            best = {}
            for f in found:
                best[f] = best.get(f, 0) + 1
            res[layers[0]] = max(best.items(), key=lambda kv: kv[1])[0]
    return res


def nominal_width(msp, o, horiz, wall_c):
    """호칭 치수: 벽체(COL) → 벽 마감(WAL) → 마감선 순으로 끊긴 폭을 쓰고, 못 재면 기호 폭에서 추정."""
    c = o["xy"][0] if horiz else o["xy"][1]
    gap = wall_gap(msp, horiz, wall_c, c)
    for k, label in (("COL", "벽체 개구부"), ("WAL", "벽 마감 개구부")):
        g = gap.get(k)
        if g and o["width"] - 30 <= g <= o["width"] + 300:
            return int(round(g / 10) * 10), label
    if o["type"] == "window":
        return int(round((o["width"] + 20) / 100) * 100), "추정"
    return int(round((o["width"] + 110) / 50) * 50), "추정"


# ---------- 그리드 ----------
def grid_lines(msp):
    raw = []
    for e in msp.query('LINE[layer=="CEN"]'):
        raw.append((e.dxf.start.x, e.dxf.start.y, e.dxf.end.x, e.dxf.end.y, e.dxf.handle))
    for e in msp.query('LWPOLYLINE[layer=="CEN"]'):
        pts = list(e.get_points())
        if len(pts) == 2:
            raw.append((pts[0][0], pts[0][1], pts[1][0], pts[1][1], e.dxf.handle))
    xs, ys = {}, {}
    for x1, y1, x2, y2, h in raw:
        if abs(x1 - x2) < 1:
            k = round(x1)
            g = xs.setdefault(k, {"coord": k, "lo": min(y1, y2), "hi": max(y1, y2), "handles": []})
            g["lo"], g["hi"] = min(g["lo"], y1, y2), max(g["hi"], y1, y2); g["handles"].append(h)
        elif abs(y1 - y2) < 1:
            k = round(y1)
            g = ys.setdefault(k, {"coord": k, "lo": min(x1, x2), "hi": max(x1, x2), "handles": []})
            g["lo"], g["hi"] = min(g["lo"], x1, x2), max(g["hi"], x1, x2); g["handles"].append(h)
    grids = {}
    for i, k in enumerate(sorted(xs), 1):
        grids[f"X{i}"] = {"id": f"X{i}", "axis": "x", **xs[k]}
    for j, k in enumerate(sorted(ys), 1):
        grids[f"Y{j}"] = {"id": f"Y{j}", "axis": "y", **ys[k]}
    return grids


def rect_polys(msp, layer):
    out = []
    for e in msp.query(f'LWPOLYLINE[layer=="{layer}"]'):
        pts = [(p[0], p[1]) for p in e.get_points()]
        if len(pts) < 4:
            continue
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        if 250 <= w <= 1200 and 250 <= h <= 1200:
            out.append({"handle": e.dxf.handle, "cx": (max(xs) + min(xs)) / 2, "cy": (max(ys) + min(ys)) / 2, "w": round(w, -1), "h": round(h, -1)})
    return out


# ---------- 설비·전기·소방 ----------
def read_mep(msp, grids, nodes, edges):
    """이름표 블록으로 그려진 기구와 M-DUCT 레이어의 덕트를 읽는다. 관계(HOST 속성)가 심겨 있으면 그대로 쓰고, 없으면 위치로 추정한다."""
    sys.path.insert(0, str(ROOT / "mep"))
    try:
        import mep_schedule as ms
    except Exception:
        return None
    N = {n["id"]: n for n in nodes}
    E = {e["id"]: e for e in edges}
    devices = []
    for ins in msp.query("INSERT"):
        t = ms.BY_BLOCK.get(ins.dxf.name)
        if not t:
            continue
        attrs = {a.dxf.tag: a.dxf.text for a in ins.attribs}
        xy = [round(ins.dxf.insert.x), round(ins.dxf.insert.y)]
        parts = (attrs.get("HOST") or "").split("|")
        host = None
        if parts[0] == "wall" and len(parts) >= 3:
            host = {"kind": "wall", "edge": parts[1], "side": int(parts[2])}
        elif parts[0] == "bay" and len(parts) >= 4:
            g4 = parts[1].split(",")
            if all(k in grids for k in g4):
                host = {"kind": "bay", "gx": g4[:2], "gy": g4[2:], "fx": float(parts[2]), "fy": float(parts[3])}
        if host is None and t["host"] == "wall":   # 관계가 심겨 있지 않으면 가장 가까운 벽으로 추정
            att = attach_to_edge(xy, [e for e in edges if e["wall"]], N, 500)
            if att:
                e = E[att[1]]
                horiz = grids[e["along"]]["axis"] == "y"
                c = grids[e["along"]]["coord"]
                host = {"kind": "wall", "edge": att[1], "side": 1 if (xy[1] if horiz else xy[0]) >= c else -1, "inferred": True}
        if host and host["kind"] == "wall":
            e = E.get(host["edge"])
            if e and e["wall"]:
                horiz = grids[e["along"]]["axis"] == "y"
                host["a"] = xy[0] if horiz else xy[1]
                host["offset"] = abs((xy[1] if horiz else xy[0]) - grids[e["along"]]["coord"])
            else:
                host["orphan"] = True     # 붙어 있던 벽이 없음
        devices.append({"id": attrs.get("TAG") or f'{t["id"][:2]}-{len(devices) + 1}', "type": t["id"], "disc": t["disc"], "host": host, "xy": xy,
                        "rotation": round(ins.dxf.get("rotation", 0)), "handle": ins.dxf.handle})
    routes = []
    for pl in msp.query('LWPOLYLINE[layer=="M-DUCT"]'):
        pts = [[round(q[0]), round(q[1])] for q in pl.get_points()]
        w = round(pl.dxf.get("const_width", 0)) or 400
        routes.append({"id": f"MR-{len(routes) + 1}", "type": "MR1", "disc": "M", "width": w, "pts": pts, "handle": pl.dxf.handle})
    if not devices and not routes:
        return None
    return {"devices": devices, "routes": routes, "types": ms.TYPES, "rules": ms.RULES, "disciplines": ms.DISC, "virtual": True}


# ---------- 코어, 대지 ----------
CORE_APP = "HIMEC_CORE"


def read_cores(msp, grids):
    """코어 외곽선에 심어 둔 정보를 읽는다. 위치는 도면의 외곽선에서, 기준 교점은 지금의 그리드에서 다시 찾는다."""
    import json
    cores, fh = [], None
    for e in msp:
        if e.dxftype() != "LWPOLYLINE" or not e.has_xdata(CORE_APP):
            continue
        tags = [t.value for t in e.get_xdata(CORE_APP) if t.code == 1000]
        if len(tags) < 2:
            continue
        info = json.loads("".join(tags[1:]))
        pts = [(p[0], p[1]) for p in e.get_points("xy")]
        x0, y0, x1, y1 = min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)
        # 기준 교점: 외곽선의 네 모서리 가운데 그리드 교점에 놓인 것. 방향과 옆으로 어느 모서리인지 정해진다
        sd, d = info.get("side") or 1, info["dir"]
        ax = (x0 if sd > 0 else x1) if d in ("N", "S") else (x0 if d == "E" else x1)
        ay = (y0 if d == "N" else y1) if d in ("N", "S") else (y0 if sd > 0 else y1)
        def nearest(axis, v, tol=450):      # 코어는 기둥 면이나 벽 면에서 시작하므로 교점에서 조금 떨어져 있다
            c = [g for g in grids.values() if g["axis"] == axis and abs(g["coord"] - v) <= tol]
            return min(c, key=lambda g: abs(g["coord"] - v))["id"] if c else None
        gx, gy = nearest("x", ax), nearest("y", ay)
        c = {"id": info["id"], "type": info["type"], "kind": info["kind"], "anchor": [gx, gy], "anchor_xy": [grids[gx]["coord"] if gx else None, grids[gy]["coord"] if gy else None], "dir": d, "side": sd, "entry": info.get("entry"), "travel": info.get("travel"),
             "walls": info.get("walls"), "wall_thick": info.get("wt"), "rect": [round(x0), round(y0), round(x1), round(y1)], "handle": e.dxf.handle, "anchored": bool(gx and gy)}
        cores.append(c)
        fh = info.get("fh") or fh
    return sorted(cores, key=lambda c: c["id"]), fh


def read_site(msp):
    best = None
    for e in msp.query('LWPOLYLINE[layer=="SITE"]'):
        pts = [[round(p[0]), round(p[1])] for p in e.get_points("xy")]
        if e.closed and len(pts) >= 3:
            a = abs(sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))) / 2
            if not best or a > best[0]:
                best = (a, pts)
    return {"pts": best[1], "area_m2": round(best[0] / 1e6, 1)} if best else None


# ---------- 그래프 ----------
def build(dxf_path: Path, sheet: str):
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    grids = grid_lines(msp)
    gx = {g["id"]: g for g in grids.values() if g["axis"] == "x"}
    gy = {g["id"]: g for g in grids.values() if g["axis"] == "y"}

    # 교점 노드(joint) 후보: 두 그리드선의 범위 안에 있는 교점
    joints = {}
    for xi, gxv in gx.items():
        for yj, gyv in gy.items():
            x, y = gxv["coord"], gyv["coord"]
            if gxv["lo"] - 1 <= y <= gxv["hi"] + 1 and gyv["lo"] - 1 <= x <= gyv["hi"] + 1:
                joints[(xi, yj)] = {"id": f"J@{xi}-{yj}", "type": "joint", "grid": [xi, yj], "xy": [x, y]}

    # 기둥
    columns = {}
    for c in rect_polys(msp, "COL"):
        xi = next((g["id"] for g in gx.values() if abs(g["coord"] - c["cx"]) <= COL_TOL), None)
        yj = next((g["id"] for g in gy.values() if abs(g["coord"] - c["cy"]) <= COL_TOL), None)
        if xi and yj and (xi, yj) not in columns:
            columns[(xi, yj)] = {"id": f"C@{xi}-{yj}", "type": "column", "grid": [xi, yj], "xy": [gx[xi]["coord"], gy[yj]["coord"]],
                                 "spec": f'{int(c["w"])}x{int(c["h"])}', "handle": c["handle"], "layer": "COL"}

    wall_segs = segments_of(msp, WALL_LAYERS)
    wal_only = segments_of(msp, ("WAL",))

    def measure_thick(a, b, axis_h, rivals):
        """벽 두께: 이 구간과 나란한 벽선 가운데 가장 바깥 두 줄 사이의 거리. 구간 길이의 절반 이상을 덮는 줄만 센다."""
        c0 = a[1] if axis_h else a[0]
        lo, hi = (min(a[0], b[0]), max(a[0], b[0])) if axis_h else (min(a[1], b[1]), max(a[1], b[1]))
        cover = {}
        for s in wal_only:
            if (abs(s[1] - s[3]) > 1) if axis_h else (abs(s[0] - s[2]) > 1):
                continue
            q = s[1] if axis_h else s[0]
            if abs(q - c0) > WALL_OFF or any(abs(q - r) < abs(q - c0) for r in rivals):
                continue
            u0, u1 = sorted((s[0], s[2]) if axis_h else (s[1], s[3]))
            ov = min(u1, hi) - max(u0, lo)
            if ov > 0:
                cover[round(q)] = cover.get(round(q), 0) + ov
        qs = [q for q, v in cover.items() if v >= (hi - lo) * 0.3]
        return round(max(qs) - min(qs)) if len(qs) >= 2 else None
    hid_segs = segments_of(msp, HID_LAYERS)

    # 구간(edge): 같은 그리드선 위 인접 교점 사이
    edges = []
    def key_of(k):
        return columns[k]["id"] if k in columns else joints[k]["id"]
    for axis, gmap in (("x", gx), ("y", gy)):
        for gid in gmap:
            ks = [k for k in joints if k[0 if axis == "x" else 1] == gid]
            ks.sort(key=lambda k: joints[k]["xy"][1 if axis == "x" else 0])
            for ka, kb in zip(ks, ks[1:]):
                a, b = joints[ka]["xy"], joints[kb]["xy"]
                axis_h = axis == "y"
                rivals = [g2["coord"] for g2 in gmap.values() if g2["id"] != gid]
                wc, wh, _, _ = coverage(a, b, axis_h, wall_segs, WALL_OFF, rivals)
                hc, hh, _, _ = coverage(a, b, axis_h, hid_segs, WALL_OFF, rivals)
                both_col = ka in columns and kb in columns
                is_wall = wc >= WALL_MIN_COVER
                is_beam = both_col or hc >= HID_MIN_COVER
                if not (is_wall or is_beam):
                    continue
                edges.append({"id": f"{key_of(ka)}~{key_of(kb)}", "from": key_of(ka), "to": key_of(kb), "along": gid,
                              "length": round(dist(a, b)), "wall": is_wall, "wall_cover": round(wc, 2), "wall_handles": wh, "thick_measured": measure_thick(a, b, axis_h, rivals) if is_wall else None,
                              "beam": is_beam, "beam_evidence": "columns" if both_col else ("hidden-line" if hc >= HID_MIN_COVER else None)})

    used = {e["from"] for e in edges} | {e["to"] for e in edges}
    nodes = list(columns.values()) + [j for j in joints.values() if j["id"] in used]
    byid = {n["id"]: n for n in nodes}
    wall_edges = [e for e in edges if e["wall"]]

    # 창호
    from ezdxf import bbox as bb
    def boxes(layers, types):
        out = []
        for e in msp:
            if e.dxf.layer in layers and e.dxftype() in types:
                b = bb.extents([e], fast=True)
                if b.has_data:
                    out.append((b.extmin.x, b.extmin.y, b.extmax.x, b.extmax.y, e.dxf.handle))
        return out
    openings = []
    wn = 0
    for c in sorted(cluster_boxes(boxes(WIN_LAYERS, ("LINE", "LWPOLYLINE")), CLUSTER_GAP), key=lambda c: (c["ymin"], c["xmin"])):
        w, h = c["xmax"] - c["xmin"], c["ymax"] - c["ymin"]
        if max(w, h) < 300:
            continue
        ctr = ((c["xmin"] + c["xmax"]) / 2, (c["ymin"] + c["ymax"]) / 2)
        att = attach_to_edge(ctr, wall_edges, byid, OPEN_ATTACH)
        if not att:
            continue
        wn += 1
        openings.append({"id": f"W{wn}", "type": "window", "xy": [round(ctr[0]), round(ctr[1])], "width": int(round(max(w, h), -1)),
                         "on_edge": att[1], "t": att[2], "handles": c["handles"]})
    dn = 0
    door_boxes = []
    for e in msp:
        if e.dxf.layer in DOOR_LAYERS and e.dxftype() == "ARC":
            r = e.dxf.radius
            if 500 <= r <= 2000:
                b = bb.extents([e], fast=False)   # 호가 실제로 차지하는 범위(경첩~문 끝)
                if b.has_data:
                    door_boxes.append((b.extmin.x, b.extmin.y, b.extmax.x, b.extmax.y, e.dxf.handle, r))
    for c in sorted(cluster_boxes([b[:5] for b in door_boxes], 50), key=lambda c: (c["ymin"], c["xmin"])):
        rs = [b[5] for b in door_boxes if b[4] in c["handles"]]
        # 호 범위 안에 든 문짝 선·문틀 등 문 레이어 객체도 같은 문으로 묶는다
        for e in msp:
            if e.dxf.layer in DOOR_LAYERS and e.dxftype() in ("LINE", "LWPOLYLINE") and e.dxf.handle not in c["handles"]:
                b = bb.extents([e], fast=True)
                if b.has_data and b.extmin.x >= c["xmin"] - 300 and b.extmax.x <= c["xmax"] + 300 and b.extmin.y >= c["ymin"] - 300 and b.extmax.y <= c["ymax"] + 300:
                    c["handles"].append(e.dxf.handle)
        # 문 위치 = 호들이 차지한 범위의 중심을 벽 위로 내린 점(개구부 중심). 문 궤적이 벽에서 멀리 뻗으므로 허용 거리는 반지름만큼 넓힌다
        ctr = ((c["xmin"] + c["xmax"]) / 2, (c["ymin"] + c["ymax"]) / 2)
        att = attach_to_edge(ctr, wall_edges, byid, OPEN_ATTACH + max(rs))
        if not att:
            continue
        ed = next(x for x in wall_edges if x["id"] == att[1])
        a, b2 = byid[ed["from"]]["xy"], byid[ed["to"]]["xy"]
        ctr = (a[0] + att[2] * (b2[0] - a[0]), a[1] + att[2] * (b2[1] - a[1]))
        dn += 1
        openings.append({"id": f"D{dn}", "type": "door", "xy": [round(ctr[0]), round(ctr[1])], "width": int(round(sum(rs), -1)),
                         "leaves": len(rs), "on_edge": att[1], "t": att[2], "handles": c["handles"]})

    # 문 띠(접이문·쇼윈도): 벽 구간 위를 DOOR 레이어 선이 길게 덮는 경우
    door_segs = segments_of(msp, DOOR_LAYERS, ("LINE", "LWPOLYLINE"))
    for e in wall_edges:
        a, b = byid[e["from"]]["xy"], byid[e["to"]]["xy"]
        axis_h = abs(a[1] - b[1]) < 1
        rivals = [g2["coord"] for g2 in grids.values() if g2["axis"] == grids[e["along"]]["axis"] and g2["id"] != e["along"]]
        dc, dh, ivs, (lo, hi) = coverage(a, b, axis_h, door_segs, WALL_OFF, rivals)
        if dc < DOOR_BAND_MIN or not ivs:
            continue
        big = max(ivs, key=lambda iv: iv[1] - iv[0])
        if big[1] - big[0] < 1500:
            continue
        # 이미 이 구간에 붙은 문(호)이 띠 안에 있으면 띠로 대체
        openings[:] = [o for o in openings if not (o["type"] == "door" and o["on_edge"] == e["id"])]
        dn += 1
        cpos = (big[0] + big[1]) / 2
        t = (cpos - lo) / (hi - lo) if (a[0] if axis_h else a[1]) == lo else 1 - (cpos - lo) / (hi - lo)
        ctr = (cpos, a[1]) if axis_h else (a[0], cpos)
        openings.append({"id": f"D{dn}", "type": "door", "band": True, "xy": [round(ctr[0]), round(ctr[1])], "width": int(round(big[1] - big[0], -1)),
                         "leaves": 0, "on_edge": e["id"], "t": round(t, 3), "handles": dh})
        e["opening_band"] = True

    # 호칭 치수
    eid = {e["id"]: e for e in edges}
    for o in openings:
        e = eid[o["on_edge"]]
        horiz = grids[e["along"]]["axis"] == "y"
        o["horiz"] = horiz
        if o.get("band"):
            o["nominal"], o["nominal_src"] = o["width"], "문 띠 길이"
        else:
            o["nominal"], o["nominal_src"] = nominal_width(msp, o, horiz, grids[e["along"]]["coord"])

    # 치수
    dims = []
    for d in msp.query("DIMENSION"):
        p2, p3, pl = d.dxf.defpoint2, d.dxf.defpoint3, d.dxf.defpoint
        horizontal = abs(p2.y - p3.y) < 1
        gm = gx if horizontal else gy
        val = (lambda p: p.x) if horizontal else (lambda p: p.y)
        g_from = next((g["id"] for g in gm.values() if abs(g["coord"] - val(p2)) <= GRID_TOL), None)
        g_to = next((g["id"] for g in gm.values() if abs(g["coord"] - val(p3)) <= GRID_TOL), None)
        dims.append({"handle": d.dxf.handle, "orient": "H" if horizontal else "V", "from_grid": g_from, "to_grid": g_to,
                     "p2": [round(p2.x), round(p2.y)], "p3": [round(p3.x), round(p3.y)], "line": [round(pl.x), round(pl.y)],
                     "measurement": round(d.get_measurement()), "text": d.dxf.text, "style": d.dxf.dimstyle, "attached": bool(g_from and g_to)})

    schedule = {"columns": [{"id": n["id"], "spec": n["spec"]} for n in nodes if n["type"] == "column"],
                "windows": [{"id": o["id"], "width": o["nominal"], "on": o["on_edge"]} for o in openings if o["type"] == "window"],
                "doors": [{"id": o["id"], "width": o["nominal"], "leaves": o.get("leaves", 1), "on": o["on_edge"]} for o in openings if o["type"] == "door"]}
    out = {"sheet": sheet, "dwg": dxf_path.name, "units": "mm", "naming": "그리드 명칭은 좌표순 자동 명명(도면 실제 명칭 미확인)",
           "grids": grids, "nodes": nodes, "edges": edges, "openings": openings, "dims": dims, "schedule": schedule}
    mep = read_mep(msp, grids, nodes, edges)
    if mep:
        out["mep"] = mep
    cores, fh = read_cores(msp, grids)
    if cores:
        out["cores"] = [c for c in cores if c["anchored"]]
        out["cores_unanchored"] = [c["id"] for c in cores if not c["anchored"]]
        if fh:
            out["project"] = {"floor_height": fh}
    site = read_site(msp)
    if site:
        out["site"] = site
    return out


# ---------- 렌더링 ----------
def render(graph: dict, out_png: Path, highlight=None, title=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle, Polygon

    plt.rcParams["font.family"] = ["Malgun Gothic", "AppleSDGothicNeoR00", "NanumGothic", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    hl = highlight or {}
    hn, he, hg, hd, ho = (set(hl.get(k, ())) for k in ("nodes", "edges", "grids", "dims", "openings"))
    RED = "#d62728"
    grids, nodes = graph["grids"], {n["id"]: n for n in graph["nodes"]}

    fig = plt.figure(figsize=(16, 9.5))
    ax = fig.add_axes([0.02, 0.02, 0.72, 0.92])
    # 그리드
    for g in grids.values():
        hot = g["id"] in hg
        c = RED if hot else "#c8c8c8"
        if g["axis"] == "x":
            ax.plot([g["coord"]] * 2, [g["lo"], g["hi"]], "-.", color=c, lw=1.6 if hot else 0.7, zorder=1)
            ax.text(g["coord"], g["hi"] + 250, g["id"], ha="center", fontsize=8, color=c)
        else:
            ax.plot([g["lo"], g["hi"]], [g["coord"]] * 2, "-.", color=c, lw=1.6 if hot else 0.7, zorder=1)
            ax.text(g["lo"] - 250, g["coord"], g["id"], ha="right", va="center", fontsize=8, color=c)
    # 구간: 벽 실선, 보 점선(살짝 띄움)
    for e in graph["edges"]:
        a, b = nodes[e["from"]]["xy"], nodes[e["to"]]["xy"]
        hot = e["id"] in he
        horiz = abs(a[1] - b[1]) < 1
        if e["wall"]:
            ax.plot([a[0], b[0]], [a[1], b[1]], "-", color=RED if hot else "#333333", lw=3.2 if not hot else 4.2, zorder=2, solid_capstyle="butt")
        if e["beam"]:
            off = 130 if e["wall"] else 0
            ox, oy = (0, off) if horiz else (off, 0)
            ax.plot([a[0] + ox, b[0] + ox], [a[1] + oy, b[1] + oy], "--", color=RED if hot else "#1f77b4", lw=1.6 if not hot else 2.4, zorder=2)
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        if e["beam"] and e["beam_evidence"] == "columns":
            ax.text(mx + (0 if horiz else 160), my + (200 if horiz else 0), f'{e["length"]}', ha="center" if horiz else "left", va="bottom" if horiz else "center",
                    fontsize=6.5, color=RED if hot else "#1f77b4", rotation=0 if horiz else 90)
    # 창호(□)·문(△)
    for o in graph["openings"]:
        e = next(x for x in graph["edges"] if x["id"] == o["on_edge"])
        a, b = nodes[e["from"]]["xy"], nodes[e["to"]]["xy"]
        horiz = abs(a[1] - b[1]) < 1
        x, y = a[0] + o["t"] * (b[0] - a[0]), a[1] + o["t"] * (b[1] - a[1])
        hot = o["id"] in ho
        half = max(o["width"], 600) / 2
        if o["type"] == "window":
            w, h = (half * 2, 240) if horiz else (240, half * 2)
            ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, fc=RED if hot else "#9edae5", ec="black", lw=0.8, zorder=5))
            ax.text(x + (0 if horiz else 260), y + (300 if horiz else 0), f'{o["id"]} {o.get("nominal", o["width"])}', ha="center" if horiz else "left", va="bottom" if horiz else "center", fontsize=6.5, rotation=0 if horiz else 90)
        else:
            s = 260 if not o.get("band") else max(o["width"] / 2, 400)
            hgt = 1.6 * 260
            tri = [(x - s, y), (x + s, y), (x, y + hgt)] if horiz else [(x, y - s), (x, y + s), (x + hgt, y)]
            ax.add_patch(Polygon(tri, closed=True, fc=RED if hot else "#ff9896", ec="black", lw=0.8, zorder=5))
            ax.text(x + (0 if horiz else 520), y - (330 if horiz else 0), f'{o["id"]} {o.get("nominal", o["width"])}', ha="center" if horiz else "left", va="top" if horiz else "center", fontsize=6.5, rotation=0 if horiz else 90)
    # 노드: 기둥 ○(크기 비례), 교점 ·
    for n in graph["nodes"]:
        x, y = n["xy"]
        hot = n["id"] in hn
        if n["type"] == "column":
            w, h = map(int, n["spec"].split("x"))
            r = 300 * math.sqrt(w * h) / 400
            ax.add_patch(Circle((x, y), r, fc=RED if hot else "white", ec=RED if hot else "black", lw=2.2, zorder=6))
            ax.text(x, y - r - 120, f'{n["id"][2:]}\n{n["spec"]}', ha="center", va="top", fontsize=7, fontweight="bold" if hot else "normal", zorder=7)
        else:
            ax.add_patch(Circle((x, y), 70, fc=RED if hot else "#666666", ec="none", zorder=6))
    # 설비·전기·소방
    mep = graph.get("mep")
    if mep:
        MC = {"E": "#e67e00", "M": "#1565c0", "F": "#c2185b"}
        hm = set(hl.get("mep", ()))
        for r in mep["routes"]:
            xs, ys = [q[0] for q in r["pts"]], [q[1] for q in r["pts"]]
            ax.plot(xs, ys, "-", color=RED if r["id"] in hm else MC["M"], lw=5, alpha=0.35, solid_capstyle="butt", zorder=4)
            ax.plot(xs, ys, "-", color=RED if r["id"] in hm else MC["M"], lw=0.8, zorder=4)
        mk = {"EO1": ("o", 28), "ES1": ("o", 14), "EP1": ("s", 45), "EL1": ("x", 30), "MD1": ("s", 60), "FS1": ("+", 30), "FD1": ("D", 22)}
        for dv in mep["devices"]:
            m, sz = mk.get(dv["type"], ("o", 20))
            c = RED if dv["id"] in hm else MC[dv["disc"]]
            ax.scatter([dv["xy"][0]], [dv["xy"][1]], marker=m, s=sz, c=c if m in ("x", "+") else "none", edgecolors=c, linewidths=1.0, zorder=7)

    # 치수
    for d in graph["dims"]:
        if not d["attached"]:
            continue
        hot = d["handle"] in hd
        c = RED if hot else "#2ca02c"
        if d["orient"] == "H":
            y = d["line"][1]
            ax.plot([d["p2"][0], d["p3"][0]], [y, y], color=c, lw=1.3 if hot else 0.7, zorder=3)
            for xx in (d["p2"][0], d["p3"][0]):
                ax.plot([xx, xx], [y - 90, y + 90], color=c, lw=0.6, zorder=3)
            ax.text((d["p2"][0] + d["p3"][0]) / 2, y + 70, str(d["measurement"]), ha="center", fontsize=6.5, color=c)
        else:
            x = d["line"][0]
            ax.plot([x, x], [d["p2"][1], d["p3"][1]], color=c, lw=1.3 if hot else 0.7, zorder=3)
            for yy in (d["p2"][1], d["p3"][1]):
                ax.plot([x - 90, x + 90], [yy, yy], color=c, lw=0.6, zorder=3)
            ax.text(x - 70, (d["p2"][1] + d["p3"][1]) / 2, str(d["measurement"]), ha="right", va="center", fontsize=6.5, color=c, rotation=90)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title or f'관계도 {graph["sheet"]} — ○ 기둥(단면 비례)  ─ 벽  - - 보  □ 창호  △ 문  녹색 치수  회색 그리드', fontsize=11)

    # 일람표
    sc = graph["schedule"]
    tx = fig.add_axes([0.76, 0.05, 0.23, 0.88])
    tx.axis("off")
    lines = ["기둥 일람표", "─────────────"]
    lines += [f'{c["id"][2:]:12s} {c["spec"]}' for c in sc["columns"]] or ["(없음)"]
    lines += ["", "창호 일람표", "─────────────"]
    lines += [f'{w["id"]:4s} W={w["width"]:5d}  {w["on"]}' for w in sc["windows"]] or ["(없음)"]
    lines += ["", "문 일람표", "─────────────"]
    lines += [f'{d["id"]:4s} W={d["width"]:5d} {"띠 " if d["leaves"] == 0 else str(d["leaves"]) + "짝"} {d["on"]}' for d in sc["doors"]] or ["(없음)"]
    hot_ids = hn | ho
    y0 = 1.0
    for ln in lines:
        key = ln.split()[0] if ln.strip() else ""
        is_hot = key and any(h.endswith(key) or h == key for h in hot_ids)
        tx.text(0, y0, ln, fontsize=7.2, family=["Malgun Gothic", "DejaVu Sans Mono"], va="top", color=RED if is_hot else "black", fontweight="bold" if is_hot else "normal")
        y0 -= 0.026
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    sheet = sys.argv[1] if len(sys.argv) > 1 else "A12"
    g = build(ROOT / "real_dxf" / f"{sheet}.dxf", sheet)
    out = ROOT / "out" / "real"
    out.mkdir(parents=True, exist_ok=True)
    def _default(o):  # numpy 스칼라 등
        if hasattr(o, "item"):
            return o.item()
        raise TypeError(str(type(o)))
    (out / "graph_real.json").write_text(json.dumps(g, ensure_ascii=False, indent=1, default=_default), encoding="utf-8")
    render(g, out / "graph_real_before.png")
    ncol = sum(n["type"] == "column" for n in g["nodes"]); njoint = len(g["nodes"]) - ncol
    nw = sum(e["wall"] for e in g["edges"]); nb = sum(e["beam"] for e in g["edges"])
    if g.get("mep"):
        from collections import Counter
        print("설비·전기·소방(가상):", dict(Counter(d["type"] for d in g["mep"]["devices"])), "| 덕트", len(g["mep"]["routes"]), "| 벽 부착", sum(1 for d in g["mep"]["devices"] if d["host"] and d["host"]["kind"] == "wall"), "구획 배치", sum(1 for d in g["mep"]["devices"] if d["host"] and d["host"]["kind"] == "bay"))
    print(f'grids {len(g["grids"])} | columns {ncol} joints {njoint} | edges {len(g["edges"])} (wall {nw}, beam {nb}) | windows {len(g["schedule"]["windows"])} doors {len(g["schedule"]["doors"])} | dims {len(g["dims"])} attached {sum(d["attached"] for d in g["dims"])}')
    for e in g["edges"]:
        print(f'  {e["id"]:24s} {e["along"]:3s} L={e["length"]:5d} wall={e["wall"]!s:5s}({e["wall_cover"]:.2f}) beam={e["beam"]!s:5s} {e["beam_evidence"] or ""}')
    for o in g["openings"]:
        print(f'  {o["id"]:4s} {o["type"]:6s} 호칭 {o["nominal"]:5d} ({o["nominal_src"]}, 기호 {o["width"]}) on {o["on_edge"]} t={o["t"]}')
