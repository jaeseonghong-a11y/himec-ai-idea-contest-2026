"""층별 문·창호를 읽고, 기호 크기와 '벽이 끊긴 폭'을 함께 재서 비교한다."""
import sys, io
from collections import Counter
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "graph"))
import ezdxf
import build_graph_real as bgr

WALLS = ("COL", "WAL", "마감선", "단열재")


def wall_gap(msp, horiz, wall_c, center, zone=450):
    """개구부 중심을 끼고 벽선이 끊긴 구간. 벽체(COL) 선을 우선한다."""
    res = {}
    for layers in (("COL",), ("WAL",), ("마감선", "단열재")):
        gaps = []
        for e in msp:
            if e.dxf.layer not in layers:
                continue
            if e.dxftype() == "LINE":
                segs = [((e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y))]
            elif e.dxftype() == "LWPOLYLINE":
                pts = [(p[0], p[1]) for p in e.get_points()]
                if e.closed and len(pts) > 2:
                    pts.append(pts[0])
                segs = list(zip(pts, pts[1:]))
            else:
                continue
            for (x1, y1), (x2, y2) in segs:
                (a1, q1), (a2, q2) = ((x1, y1), (x2, y2)) if horiz else ((y1, x1), (y2, x2))
                if abs(q1 - q2) < 1 and abs(q1 - wall_c) <= zone and abs(a1 - a2) > 1:
                    gaps.append((min(a1, a2), max(a1, a2), round(q1 - wall_c)))
        by_q = {}
        for lo, hi, q in gaps:
            by_q.setdefault(q, []).append((lo, hi))
        found = []
        for q, ivs in by_q.items():
            left = [hi for lo, hi in ivs if hi <= center + 1]
            right = [lo for lo, hi in ivs if lo >= center - 1]
            if any(lo < center - 1 and hi > center + 1 for lo, hi in ivs):
                continue   # 이 선은 개구부를 가로질러 끊기지 않음
            if left and right:
                found.append(round(min(right) - max(left)))
        if found:
            res[layers[0]] = Counter(found).most_common(1)[0][0]
    return res


for sheet, name in (("A12", "1층"), ("A13", "2층"), ("A14", "3층"), ("A15", "4층")):
    path = ROOT / "real_dxf" / f"{sheet}.dxf"
    g = bgr.build(path, sheet)
    msp = ezdxf.readfile(path).modelspace()
    E = {e["id"]: e for e in g["edges"]}
    print(f"== {sheet} {name}")
    for o in sorted(g["openings"], key=lambda o: (o["type"], o["width"])):
        if o.get("band"):
            continue
        e = E[o["on_edge"]]
        horiz = g["grids"][e["along"]]["axis"] == "y"
        wall_c = o["xy"][1] if horiz else o["xy"][0]
        c = o["xy"][0] if horiz else o["xy"][1]
        gap = wall_gap(msp, horiz, wall_c, c)
        print(f'  {o["id"]:4s} {o["type"]:6s} 기호폭 {o["width"]:5d} {str(o.get("leaves", "")) + "짝" if o["type"] == "door" else "":4s} 객체 {len(o["handles"]):3d}개  벽 끊긴 폭 {gap}  @ {o["xy"]} {"가로벽" if horiz else "세로벽"}')
