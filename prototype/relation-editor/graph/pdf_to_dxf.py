"""PDF(레이어 포함 벡터) → 레이어가 살아 있는 DXF 복원 → 관계도.

AutoCAD 'DWG To PDF'로 출력한 PDF는 레이어(OCG)·벡터 선·문자가 남는다. 잃는 것은 블록·치수 객체·선종류(일점쇄선은 조각남).
복원 규칙
- 축척: 치수 숫자 글자와 그 옆 치수선 길이(pt)의 비율로 추정 (mm/pt)
- 그리드(CEN): 같은 직선 위의 조각들을 이어 붙여 한 줄로
- 기둥(COL): 닫힌 경로의 경계상자 → 사각 폴리선
- 문(DOOR 계열)의 곡선: 베지어 → 원호(중심·반지름)
- 치수(RXDIM): 숫자 글자와 길이가 일치하는 가까운 선 → DIMENSION 객체 재생성
- 나머지 레이어: 선분 그대로
사용: python graph/pdf_to_dxf.py A12
출력: out/pdf/<sheet>_restored.dxf, out/pdf/graph_pdf.json, out/pdf/graph_pdf.png, DXF 기반 관계도와의 비교
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import ezdxf
import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_graph_real as bgr  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out" / "pdf"
DOOR_LAYERS = ("DOOR", "RXDOOR", "DOOR-S")


def circle_from_3pts(a, b, c):
    ax, ay, bx, by, cx, cy = *a, *b, *c
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-9:
        return None
    ux = ((ax**2 + ay**2) * (by - cy) + (bx**2 + by**2) * (cy - ay) + (cx**2 + cy**2) * (ay - by)) / d
    uy = ((ax**2 + ay**2) * (cx - bx) + (bx**2 + by**2) * (ax - cx) + (cx**2 + cy**2) * (bx - ax)) / d
    return (ux, uy), math.hypot(ax - ux, ay - uy)


def bezier_mid(p0, p1, p2, p3):
    return ((p0[0] + 3 * p1[0] + 3 * p2[0] + p3[0]) / 8, (p0[1] + 3 * p1[1] + 3 * p2[1] + p3[1]) / 8)


def estimate_scale(segs_pt, words):
    """치수선(pt)과 숫자 글자 → mm/pt. 가장 많이 나오는 비율."""
    ratios = []
    for w in words:
        txt = w[4].replace(",", "")
        if not txt.isdigit() or int(txt) < 300:
            continue
        v = int(txt)
        cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
        for x1, y1, x2, y2 in segs_pt:
            L = math.hypot(x2 - x1, y2 - y1)
            if L < 3:
                continue
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            if math.hypot(mx - cx, my - cy) <= 18:
                ratios.append(round(v / L, 1))
    if not ratios:
        return None
    best, n = Counter(ratios).most_common(1)[0]
    near = [r for r in ratios if abs(r - best) <= 0.3]
    return sum(near) / len(near), n, len(ratios)


def estimate_scale_by_grid(cen_pt, words):
    """그리드선 사이 거리(pt)와 치수 숫자(mm)를 대조해 mm/pt 추정. 가장 많은 그리드 간격을 설명하는 비율을 고른다."""
    lines, _ = merge_collinear(cen_pt, tol=0.15, min_len=40)
    xs = sorted({round(l[0], 2) for l in lines if abs(l[0] - l[2]) < 0.01})
    ys = sorted({round(l[1], 2) for l in lines if abs(l[1] - l[3]) < 0.01})
    dists = [abs(a - b) for cs in (xs, ys) for i, a in enumerate(cs) for b in cs[i + 1:] if abs(a - b) > 5]
    vals = sorted({int(w[4].replace(",", "")) for w in words if w[4].replace(",", "").isdigit() and int(w[4].replace(",", "")) >= 300})
    if not dists or not vals:
        return None
    best = (0, None, [])
    for v in vals:
        for d in dists:
            k = v / d
            if not 5 <= k <= 500:
                continue
            hits = [(vv, dd) for dd in dists for vv in vals if abs(dd * k - vv) <= max(6, 0.003 * vv)]
            nd = len({dd for _, dd in hits})
            if nd > best[0]:
                best = (nd, k, hits)
    nd, k, hits = best
    k = sum(v for v, _ in hits) / sum(d for _, d in hits)  # 일치 쌍으로 정밀화
    return k, nd, len(dists)


def merge_collinear(segs, tol=4, min_len=1500):
    """일점쇄선 조각 → 한 줄. segs: [(x1,y1,x2,y2)] mm"""
    vert, horiz, other = defaultdict(list), defaultdict(list), []
    for x1, y1, x2, y2 in segs:
        if abs(x1 - x2) <= 1.5:
            vert[round((x1 + x2) / 2 / tol)].append((min(y1, y2), max(y1, y2), (x1 + x2) / 2))
        elif abs(y1 - y2) <= 1.5:
            horiz[round((y1 + y2) / 2 / tol)].append((min(x1, x2), max(x1, x2), (y1 + y2) / 2))
        else:
            other.append((x1, y1, x2, y2))
    out = []
    for grp, is_v in ((vert, True), (horiz, False)):
        for k, parts in grp.items():
            lo, hi = min(p[0] for p in parts), max(p[1] for p in parts)
            c = sum(p[2] for p in parts) / len(parts)
            if hi - lo >= min_len:
                out.append((c, lo, c, hi) if is_v else (lo, c, hi, c))
    return out, other


def restore(pdf_path: Path, sheet: str):
    pdf = pymupdf.open(pdf_path)
    page = pdf[0]
    H = page.rect.height
    drawings = page.get_drawings()
    words = page.get_text("words")

    # 1) 축척
    cen_pt = [(it[1].x, it[1].y, it[2].x, it[2].y) for d in drawings if d.get("layer") == "CEN" for it in d["items"] if it[0] == "l"]
    k, votes, total = estimate_scale_by_grid(cen_pt, words)
    P = lambda p: (p[0] * k, (H - p[1]) * k)  # pt → mm, y 위로

    doc = ezdxf.new("R2013", setup=True)
    doc.header["$INSUNITS"] = 4
    msp = doc.modelspace()
    stats = Counter()
    layer_segs = defaultdict(list)
    layer_rects = defaultdict(list)
    layer_arcs = defaultdict(list)
    for d in drawings:
        layer = d.get("layer") or "0"
        pts_in_path = []
        for it in d["items"]:
            if it[0] == "l":
                a, b = P((it[1].x, it[1].y)), P((it[2].x, it[2].y))
                layer_segs[layer].append((*a, *b)); pts_in_path += [a, b]
            elif it[0] == "re":
                r = it[1]
                a, c = P((r.x0, r.y0)), P((r.x1, r.y1))
                for s in ((a[0], a[1], c[0], a[1]), (c[0], a[1], c[0], c[1]), (c[0], c[1], a[0], c[1]), (a[0], c[1], a[0], a[1])):
                    layer_segs[layer].append(s)
                pts_in_path += [a, c]
            elif it[0] == "qu":
                q = it[1]
                qs = [P((p.x, p.y)) for p in (q.ul, q.ur, q.lr, q.ll)]
                for a, b in zip(qs, qs[1:] + qs[:1]):
                    layer_segs[layer].append((*a, *b))
                pts_in_path += qs
            elif it[0] == "c":
                p0, p1, p2, p3 = (P((p.x, p.y)) for p in it[1:5])
                fit = circle_from_3pts(p0, bezier_mid(p0, p1, p2, p3), p3)
                if fit:
                    layer_arcs[layer].append((fit[0], fit[1], p0, p3))
                pts_in_path += [p0, p3]
        if pts_in_path and (len(d["items"]) >= 3 or any(it[0] in ("re", "qu") for it in d["items"])):
            xs, ys = [p[0] for p in pts_in_path], [p[1] for p in pts_in_path]
            layer_rects[layer].append((min(xs), min(ys), max(xs), max(ys)))

    for name in set(layer_segs) | set(layer_arcs):
        if name not in doc.layers:
            doc.layers.add(name)

    # 2) 그리드: 조각 병합 → 치수 숫자를 그리드 쌍에 연결 → 치수 숫자로 좌표 보정
    grid, rest = merge_collinear(layer_segs.pop("CEN", []))
    vx = sorted([(l[0], l[1], l[3]) for l in grid if abs(l[0] - l[2]) < 0.01])
    hy = sorted([(l[1], l[0], l[2]) for l in grid if abs(l[1] - l[3]) < 0.01])
    gx, gy = [v[0] for v in vx], [v[0] for v in hy]

    def match_pairs(coords, horizontal):
        pairs = []
        for w in words:
            txt = w[4].replace(",", "")
            if not txt.isdigit() or int(txt) < 100:
                continue
            v = int(txt)
            text_horizontal = (w[2] - w[0]) >= (w[3] - w[1])
            if text_horizontal != horizontal:
                continue
            c = P(((w[0] + w[2]) / 2, (w[1] + w[3]) / 2))
            pos = c[0] if horizontal else c[1]
            best = None
            for i in range(len(coords)):
                for j in range(i + 1, len(coords)):
                    if abs((coords[j] - coords[i]) - v) > max(8, 0.004 * v):
                        continue
                    err = abs(pos - (coords[i] + coords[j]) / 2)
                    if err <= 0.25 * v + 300 and (best is None or err < best[0]):
                        best = (err, i, j)
            if best:
                pairs.append({"v": v, "i": best[1], "j": best[2], "c": c})
        return pairs

    def snap(coords, pairs):
        if not coords:
            return []
        new = [round(coords[0])]
        for idx in range(1, len(coords)):
            cand = [q for q in pairs if q["j"] == idx]
            if cand:
                q = max(cand, key=lambda q: q["i"])
                new.append(new[q["i"]] + q["v"])
            else:
                new.append(new[idx - 1] + round(coords[idx] - coords[idx - 1]))
        return new

    px, py = match_pairs(gx, True), match_pairs(gy, False)
    nx, ny = snap(gx, px), snap(gy, py)
    corrections = [round(n - o, 1) for n, o in zip(nx + ny, gx + gy)]
    for (x, lo, hi), n in zip(vx, nx):
        msp.add_line((n, lo), (n, hi), dxfattribs={"layer": "CEN"}); stats["CEN 병합선"] += 1
    for (y, lo, hi), n in zip(hy, ny):
        msp.add_line((lo, n), (hi, n), dxfattribs={"layer": "CEN"}); stats["CEN 병합선"] += 1

    # 3) 기둥: 닫힌 경로 경계상자 → 사각 폴리선
    seen = set()
    for x0, y0, x1, y1 in layer_rects.get("COL", []):
        w, h = x1 - x0, y1 - y0
        key = (round(x0 / 20), round(y0 / 20), round(w / 20), round(h / 20))
        if 250 <= w <= 1200 and 250 <= h <= 1200 and key not in seen:
            seen.add(key)
            msp.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], close=True, dxfattribs={"layer": "COL"}); stats["COL 사각형"] += 1
    layer_segs.pop("COL", None)

    # 4) 문 호
    for layer in DOOR_LAYERS:
        for (c, r, a, b) in layer_arcs.get(layer, []):
            if 500 <= r <= 2000:
                sa = math.degrees(math.atan2(a[1] - c[1], a[0] - c[0])); ea = math.degrees(math.atan2(b[1] - c[1], b[0] - c[0]))
                msp.add_arc(c, r, sa, ea, dxfattribs={"layer": layer}); stats[f"{layer} 호"] += 1

    # 5) 치수 복원: 그리드 쌍에 연결된 치수 숫자 → DIMENSION 객체 재생성
    layer_segs.pop("RXDIM", None)
    ov = {"dimtxt": 250, "dimasz": 150, "dimexe": 100, "dimexo": 50, "dimlfac": 1, "dimdec": 0}
    for q in px:
        yl = q["c"][1] - 150
        dim = msp.add_linear_dim(base=((nx[q["i"]] + nx[q["j"]]) / 2, yl), p1=(nx[q["i"]], yl), p2=(nx[q["j"]], yl), angle=0,
                                 dimstyle="EZDXF", override=ov, dxfattribs={"layer": "RXDIM"})
        dim.render(); stats["RXDIM 치수"] += 1
    for q in py:
        xl = q["c"][0] + 150
        dim = msp.add_linear_dim(base=(xl, (ny[q["i"]] + ny[q["j"]]) / 2), p1=(xl, ny[q["i"]]), p2=(xl, ny[q["j"]]), angle=90,
                                 dimstyle="EZDXF", override=ov, dxfattribs={"layer": "RXDIM"})
        dim.render(); stats["RXDIM 치수"] += 1
    numeric = sum(1 for w in words if w[4].replace(",", "").isdigit() and int(w[4].replace(",", "")) >= 100)

    # 6) 나머지 선분
    for layer, segs in layer_segs.items():
        for x1, y1, x2, y2 in segs:
            if math.hypot(x2 - x1, y2 - y1) < 1:
                continue
            msp.add_line((x1, y1), (x2, y2), dxfattribs={"layer": layer}); stats["기타 선분"] += 1

    OUT.mkdir(parents=True, exist_ok=True)
    dst = OUT / f"{sheet}_restored.dxf"
    doc.saveas(dst)
    return dst, {"scale_mm_per_pt": round(k, 3), "scale_votes": f"{votes}/{total}", "approx_plot_scale": f"1/{round(k / (25.4 / 72))}",
                 "pdf_layers": len(pdf.get_ocgs()), "paths": len(drawings), "words": len(words), "numeric_texts": numeric,
                 "grid_corrections_mm": {"max": max(map(abs, corrections)) if corrections else 0, "values": corrections}, "restored": dict(stats)}


def summarize(g):
    return {"grids_x": sum(1 for v in g["grids"].values() if v["axis"] == "x"), "grids_y": sum(1 for v in g["grids"].values() if v["axis"] == "y"),
            "columns": sum(n["type"] == "column" for n in g["nodes"]), "walls": sum(e["wall"] for e in g["edges"]), "beams": sum(e["beam"] for e in g["edges"]),
            "windows": len(g["schedule"]["windows"]), "doors": len(g["schedule"]["doors"]), "dims": len(g["dims"]), "dims_attached": sum(d["attached"] for d in g["dims"])}


def spacing(g, axis):
    cs = sorted(v["coord"] for v in g["grids"].values() if v["axis"] == axis)
    return [round(b - a) for a, b in zip(cs, cs[1:])]


if __name__ == "__main__":
    sheet = sys.argv[1] if len(sys.argv) > 1 else "A12"
    dst, info = restore(ROOT / "real_pdf" / f"{sheet}.pdf", sheet)
    print("PDF 복원:", json.dumps(info, ensure_ascii=False))
    g = bgr.build(dst, sheet)
    g["source"] = "pdf"
    (OUT / "graph_pdf.json").write_text(json.dumps(g, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)), encoding="utf-8")
    bgr.render(g, OUT / "graph_pdf.png", title=f"관계도 {sheet} — PDF에서 읽음 (캐드 파일 없이)")
    sp = summarize(g)
    ref_path = ROOT / "out" / "real" / "graph_real.json"
    print(f'\n{"항목":14s} {"PDF":>6s} {"DXF(원본)":>10s}')
    if ref_path.exists():
        ref = json.loads(ref_path.read_text(encoding="utf-8"))
        # 원본 그래프가 변경 전 상태인지 확인 필요 없음: graph_real.json 은 항상 변경 전
        sr = summarize(ref)
        for kx in sp:
            print(f"{kx:14s} {sp[kx]:6d} {sr[kx]:10d} {'' if sp[kx] == sr[kx] else '  ← 차이'}")
        print("\n그리드 간격 X  PDF:", spacing(g, "x")); print("그리드 간격 X  DXF:", spacing(ref, "x"))
        print("그리드 간격 Y  PDF:", spacing(g, "y")); print("그리드 간격 Y  DXF:", spacing(ref, "y"))
        cp = sorted(n["spec"] for n in g["nodes"] if n["type"] == "column"); cr = sorted(n["spec"] for n in ref["nodes"] if n["type"] == "column")
        print("기둥 단면 PDF:", cp); print("기둥 단면 DXF:", cr)
    print("saved", OUT / "graph_pdf.png")
