"""벽을 면으로 합쳐 외곽선만 그린다.

벽을 한 구간씩 두 줄로 그으면 기둥 속으로 벽선이 지나가고 모서리에서 벽끼리 어긋난다.
여기서는 벽(건물 벽, 코어 벽)을 모두 사각형 면으로 모아 합친 다음, 기둥 자리를 빼고, 남은 면의 바깥선만 그린다.
- 기둥과 만나는 곳: 벽선이 기둥 면에서 멈춘다.
- 벽끼리 만나는 곳(ㄱ, ㅜ, +): 안쪽 선은 열리고 바깥 선은 이어진다.
- 코어 벽이 건물 벽에 붙는 곳: 한 덩어리로 이어진다.
모든 벽이 가로·세로라는 전제(사선·곡선 벽은 아직 없음).
"""
from bisect import bisect_left


def column_rects(doc, layer="COL"):
    out = []
    for e in doc.modelspace().query(f'LWPOLYLINE[layer=="{layer}"]'):
        pts = [(p[0], p[1]) for p in e.get_points("xy")]
        if e.closed and len(pts) == 4:
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            out.append((min(xs), min(ys), max(xs), max(ys)))
    return out


def wall_rect(p, layer, owner=None, lw=None):
    (x1, y1), (x2, y2) = p["from_xy"], p["to_xy"]
    t = p.get("thick", 200) / 2
    horiz = abs(y1 - y2) < 1
    r = [min(x1, x2), y1 - t, max(x1, x2), y1 + t] if horiz else [x1 - t, min(y1, y2), x1 + t, max(y1, y2)]
    return {"box": r, "horiz": horiz, "t": t, "ends": [(min(x1, x2), y1), (max(x1, x2), y1)] if horiz else [(x1, min(y1, y2)), (x1, max(y1, y2))], "layer": layer, "owner": owner, "lw": lw}


def extend_at_corners(walls):
    """벽이 다른 방향의 벽과 만나는 끝은 그 벽의 두께 절반만큼 늘려 모서리를 채운다."""
    n = 0
    for w in walls:
        for k, (px, py) in enumerate(w["ends"]):
            m = 0
            for o in walls:
                if o is w or o["horiz"] == w["horiz"]:
                    continue
                b = o["box"]
                if b[0] - 1 <= px <= b[2] + 1 and b[1] - 1 <= py <= b[3] + 1:
                    m = max(m, o["t"])
            if m:
                i = (0 if k == 0 else 2) if w["horiz"] else (1 if k == 0 else 3)
                w["box"][i] += -m if k == 0 else m
                n += 1
    return n


def outline(walls, columns):
    """합친 면의 바깥선. 돌려주는 값: [(x1, y1, x2, y2, layer, owner, 선 굵기)]"""
    xs = sorted({v for w in walls for v in (w["box"][0], w["box"][2])} | {v for c in columns for v in (c[0], c[2])})
    ys = sorted({v for w in walls for v in (w["box"][1], w["box"][3])} | {v for c in columns for v in (c[1], c[3])})
    nx, ny = len(xs) - 1, len(ys) - 1
    cell = [[None] * ny for _ in range(nx)]

    def fill(box, val, keep=None):
        for i in range(bisect_left(xs, box[0]), bisect_left(xs, box[2])):
            for j in range(bisect_left(ys, box[1]), bisect_left(ys, box[3])):
                if keep is None or cell[i][j] is None or keep(cell[i][j]):
                    cell[i][j] = val

    for w in sorted(walls, key=lambda w: w["owner"] is None):        # 코어 벽 먼저, 건물 벽이 그 위를 덮는다
        fill(w["box"], (w["layer"], w["owner"], w.get("lw")))
    for c in columns:
        fill(c, "COLUMN")

    def at(i, j):
        return cell[i][j] if 0 <= i < nx and 0 <= j < ny else None

    raw = {}
    for i in range(nx):
        for j in range(ny):
            v = cell[i][j]
            if v is None or v == "COLUMN":
                continue
            for di, dj, key, a, b in ((-1, 0, ("v", xs[i]), ys[j], ys[j + 1]), (1, 0, ("v", xs[i + 1]), ys[j], ys[j + 1]),
                                      (0, -1, ("h", ys[j]), xs[i], xs[i + 1]), (0, 1, ("h", ys[j + 1]), xs[i], xs[i + 1])):
                if at(i + di, j + dj) is None:                      # 빈 곳과 닿은 변만 선이 된다. 기둥과 닿은 변은 기둥 외곽선이 대신한다
                    raw.setdefault((key, v), []).append((a, b))
    out = []
    for ((o, q), (layer, owner, lw)), spans in raw.items():
        spans.sort()
        a, b = spans[0]
        for s, e in spans[1:] + [(None, None)]:
            if s is not None and abs(s - b) < 1e-6:
                b = e
                continue
            out.append((a, q, b, q, layer, owner, lw) if o == "h" else (q, a, q, b, layer, owner, lw))
            a, b = s, e
    return out


def trim_by_columns(s, e, q, horiz, columns, pad=0):
    """선분(s~e, 직각 방향 좌표 q)에서 기둥 속에 든 구간을 뺀 나머지."""
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


def draw(doc, walls, columns):
    msp = doc.modelspace()
    corners = extend_at_corners(walls)
    lines, by_owner = outline(walls, columns), {}
    for x1, y1, x2, y2, layer, owner, lw in lines:
        if layer not in doc.layers:
            doc.layers.add(layer)
        ln = msp.add_line((x1, y1), (x2, y2), dxfattribs={"layer": layer, **({"lineweight": lw} if lw else {})})      # 벽 두께에 따른 선 굵기
        by_owner.setdefault(owner, []).append(ln)
    return {"lines": len(lines), "corners": corners, "walls": len(walls), "columns": len(columns), "by_owner": by_owner}
