"""한 변경(예: X6 그리드 500 이동)을 도면 세트 전체에 전파.

1. 각 도면의 CEN 그리드선 좌표(수직/수평)를 1층 평면도 X·Y 그리드 집합과 간격 패턴으로 정렬해 (축, 오프셋)을 찾는다.
   평면도는 오프셋 0으로 정렬되고, 단면도는 절단 방향에 따라 X 또는 Y 그리드에 오프셋을 두고 정렬된다.
2. 변경 대상 그리드가 그 도면에 대응되면 매핑된 좌표에서 띠 STRETCH를 수행한다(치수 재렌더 포함).
3. 도면별 수정 DXF, 변경 전후 확대 이미지, 종합 보고서를 만든다.
"""
import json
import sys
from pathlib import Path

import ezdxf

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "graph"))
from stretch import grid_move_with_checks  # noqa: E402
from build_graph_real import grid_lines  # noqa: E402
from apply_to_dxf import render_window  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out" / "real" / "multi"
TOL = 6
MIN_MATCH = 3


def align(sheet_coords, ref_coords):
    """sheet_coords 를 ref_coords 에 가장 많이 겹치게 하는 오프셋. (count, offset)"""
    best = (0, None)
    for s in sheet_coords:
        for r in ref_coords:
            off = s - r
            cnt = sum(1 for rr in ref_coords if any(abs(rr + off - ss) <= TOL for ss in sheet_coords))
            if cnt > best[0] or (cnt == best[0] and best[1] is not None and abs(off) < abs(best[1])):
                best = (cnt, off)
    return best


def dim_support(msp, orient, ref_coords, offset):
    """정렬된 그리드 좌표 두 개를 양 끝으로 갖는 치수의 수. 우연한 정렬을 걸러내는 근거."""
    mapped = [r + offset for r in ref_coords]
    n = 0
    for d in msp.query("DIMENSION"):
        p2, p3 = d.dxf.defpoint2, d.dxf.defpoint3
        horizontal = abs(p2.y - p3.y) < 1
        if (orient == "v") != horizontal:
            continue
        a, b = (p2.x, p3.x) if horizontal else (p2.y, p3.y)
        if any(abs(a - m) <= TOL for m in mapped) and any(abs(b - m) <= TOL for m in mapped) and abs(a - b) > 1:
            n += 1
    return n


def sheet_alignment(msp, ref):
    g = grid_lines(msp)
    sv = sorted(v["coord"] for v in g.values() if v["axis"] == "x")  # 도면의 수직선
    sh = sorted(v["coord"] for v in g.values() if v["axis"] == "y")  # 도면의 수평선
    # 허용 조합: 도면 수직선 → 평면 X(평면·정배면도) 또는 평면 Y(X방향 절단 단면·측면도), 도면 수평선 → 평면 Y(평면도)만.
    # 도면 수평선이 평면 X와 맞는 경우는 물리적으로 없으므로(층 레벨선과의 우연 일치) 제외한다.
    allowed = {"v": ("x", "y"), "h": ("y",)}
    out = {}
    for orient, coords in (("v", sv), ("h", sh)):
        best = None
        for plan_axis in allowed[orient]:
            cnt, off = align(coords, ref[plan_axis])
            if cnt < MIN_MATCH:
                continue
            sup = dim_support(msp, orient, ref[plan_axis], off)
            if cnt < 4 and sup < 1:  # 3개 일치는 그 그리드를 잇는 치수가 있어야 인정
                continue
            score = cnt + 2 * sup
            cand = {"orient": orient, "plan_axis": plan_axis, "offset": off, "count": cnt, "of": len(ref[plan_axis]),
                    "dim_support": sup, "score": score, "confidence": "high" if (cnt >= 5 or sup >= 2) else "low"}
            if best is None or score > best["score"]:
                best = cand
        # 한 방향의 선들은 평면의 한 축에만 대응한다
        if best and (best["plan_axis"] not in out or best["score"] > out[best["plan_axis"]]["score"]):
            out[best["plan_axis"]] = best
    return out, {"v": sv, "h": sh}


def main(target: str, delta: float, sheets):
    graph = json.loads((ROOT / "out" / "real" / "graph_real.json").read_text(encoding="utf-8"))
    ref = {"x": [g["coord"] for g in graph["grids"].values() if g["axis"] == "x"],
           "y": [g["coord"] for g in graph["grids"].values() if g["axis"] == "y"]}
    tg = graph["grids"][target]
    plan_axis, plan_coord = tg["axis"], tg["coord"]
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"change": f"{target} move {delta}", "plan_axis": plan_axis, "plan_coord": plan_coord, "sheets": []}

    for sheet in sheets:
        src = ROOT / "real_dxf" / f"{sheet}.dxf"
        if not src.exists():
            continue
        doc = ezdxf.readfile(src)
        msp = doc.modelspace()
        al, coords = sheet_alignment(msp, ref)
        entry = {"sheet": sheet, "alignment": al}
        if plan_axis not in al:
            other = [f'{k}축 {v["count"]}/{v["of"]}' for k, v in al.items()]
            entry["status"] = ("영향 없음(이 도면은 " + ", ".join(other) + " 그리드만 표시)") if other else "정렬 불가(그리드 패턴이 1층 평면과 맞지 않음)"
            report["sheets"].append(entry)
            print(f"{sheet}: {entry['status']}")
            continue
        a = al[plan_axis]
        coord = plan_coord + a["offset"]
        sheet_axis = "x" if a["orient"] == "v" else "y"
        has_grid = any(abs(c - coord) <= TOL for c in coords[a["orient"]])
        res = grid_move_with_checks(doc, sheet_axis, coord, delta)
        entry.update({"sheet_axis": sheet_axis, "sheet_coord": coord, "grid_line_present": has_grid,
                      "moved_count": res["moved_count"], "by_layer": res["by_layer"], "dims": res["dims"],
                      "column_checks": res["column_checks"], "flagged": res["flagged"]})
        if res["moved_count"] == 0:
            entry["status"] = "영향 없음(해당 좌표에 객체 없음)"
            report["sheets"].append(entry)
            print(f"{sheet}: {entry['status']} (매핑 {sheet_axis}={coord:.0f}, 정렬 {a['count']}/{a['of']} off={a['offset']:.0f})")
            continue
        dst = OUT / f"{sheet}_modified.dxf"
        doc.saveas(dst)
        entry["status"] = "반영"
        entry["output"] = dst.name
        # 변경 영역 확대 이미지
        from ezdxf import bbox as bb
        ents = [doc.entitydb[h] for h in res["moved_handles"] if h in doc.entitydb]
        ext = bb.extents(ents, fast=True)
        if ext.has_data:
            pad = 2500
            if sheet_axis == "x":
                win = (coord - 6000, ext.extmin.y - pad, coord + 6500, ext.extmax.y + pad)
            else:
                win = (ext.extmin.x - pad, coord - 6000, ext.extmax.x + pad, coord + 6500)
            render_window(src, OUT / f"{sheet}_before.png", win, f"{sheet} 변경 전 ({target} → {sheet_axis}={coord:.0f})")
            render_window(dst, OUT / f"{sheet}_after.png", win, f"{sheet} 변경 후 ({target} {delta:+.0f})")
        report["sheets"].append(entry)
        dims_txt = ", ".join(f'{d["old"]}→{d["new"]}' for d in res["dims"] if d["old"] is not None)
        cols = res["column_checks"]
        print(f'{sheet}: 반영({a["confidence"]}) | {sheet_axis}={coord:.0f} (정렬 {a["count"]}/{a["of"]}+치수{a["dim_support"]}, off={a["offset"]:.0f}, 그리드선 {"있음" if has_grid else "없음"}) | 객체 {res["moved_count"]} | 치수 {len(res["dims"])}개 [{dims_txt}] | 기둥 {len(cols)}개 벽선 {"OK" if all(c["ok"] for c in cols) else "미이동 있음"} | 주의 {len(res["flagged"])}')

    (OUT / "multi_sheet_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f'# 다중 도면 전파 보고: {report["change"]}', "", "| 도면 | 상태 | 매핑 좌표 | 이동 객체 | 치수 갱신 | 기둥/벽선 | 주의 |", "|---|---|---|---|---|---|---|"]
    for e in report["sheets"]:
        if e["status"] != "반영":
            lines.append(f'| {e["sheet"]} | {e["status"]} | {e.get("sheet_axis", "")}={e.get("sheet_coord", "")} | | | | |')
        else:
            dims_txt = "; ".join(f'{d["old"]}→{d["new"]}' for d in e["dims"] if d["old"] is not None)
            cols = e["column_checks"]
            conf = e["alignment"][report["plan_axis"]]["confidence"]
            lines.append(f'| {e["sheet"]} | 반영{"" if conf == "high" else " (정렬 신뢰도 낮음, 확인 필요)"} | {e["sheet_axis"]}={e["sheet_coord"]:.0f}{"" if e["grid_line_present"] else " (그리드선 없음)"} | {e["moved_count"]} | {len(e["dims"])} ({dims_txt}) | {len(cols)}개 {"OK" if all(c["ok"] for c in cols) else "확인"} | {len(e["flagged"])} |')
    (OUT / "multi_sheet_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("saved", OUT / "multi_sheet_report.md")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "X6"
    delta = float(sys.argv[2]) if len(sys.argv) > 2 else 500
    sheets = sys.argv[3].split(",") if len(sys.argv) > 3 else [f"A{n:02d}" for n in range(1, 24)]
    main(target, delta, sheets)
