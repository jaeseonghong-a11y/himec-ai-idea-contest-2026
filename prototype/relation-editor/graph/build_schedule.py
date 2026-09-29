"""건물 전체 문·창호 일람표.

여러 층 평면도에서 문·창호를 읽어 타입으로 묶는다.
- 타입 기준: 종류, 문 띠 여부, 짝 수, 호칭 치수(벽체가 끊긴 폭), 기호 구성(객체 수)
- 각 타입은 그 기호가 그려진 곳(도면·객체·위치)을 기억한다. 다른 도면에 넣을 때 그 기호를 복사해 온다
- 도면에 없는 표준 크기는 '가상' 타입으로 채운다(복사할 기호가 없어 기본 기호로 그려짐)
사용: python graph/build_schedule.py [A12,A13,A14,A15]
출력: out/real/schedule.json, out/real/schedule.png
"""
import json
import sys
from pathlib import Path

import ezdxf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_graph_real as bgr  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out" / "real"
SHEET_NAMES = {"A12": "1층", "A13": "2층", "A14": "3층", "A15": "4층", "A16": "다락"}
# 도면에 없을 때 채울 표준 크기 (가상)
VIRTUAL = [("window", 1, 1500), ("window", 1, 1800), ("window", 1, 2400), ("door", 1, 1000), ("door", 2, 1500)]


def collect(sheets):
    items = []
    for sheet in sheets:
        path = ROOT / "real_dxf" / f"{sheet}.dxf"
        if not path.exists():
            continue
        g = bgr.build(path, sheet)
        for o in g["openings"]:
            items.append({"sheet": sheet, "id": o["id"], "kind": o["type"], "band": bool(o.get("band")), "leaves": o.get("leaves", 1) if o["type"] == "door" else 1,
                          "nominal": o["nominal"], "nominal_src": o["nominal_src"], "symbol": o["width"], "n": len(o["handles"]),
                          "handles": o["handles"], "xy": o["xy"], "horiz": o["horiz"]})
    return items


def build(sheets):
    items = collect(sheets)
    # 같은 종류·짝 수·호칭 치수 안에서, 기호 구성(객체 수)이 3개 이하로 차이 나면 같은 타입으로 본다
    sized = {}
    for it in items:
        if it["band"]:
            continue   # 문 띠(접이문·쇼윈도)는 벽 길이에 맞춘 것이라 타입으로 재사용하지 않는다
        sized.setdefault((it["kind"], it["leaves"], it["nominal"]), []).append(it)
    groups = {}
    for (kind, leaves, nominal), lst in sized.items():
        lst.sort(key=lambda x: x["n"])
        base = None
        for it in lst:
            if base is None or it["n"] - base > 3:
                base = it["n"]
            groups.setdefault((kind, leaves, nominal, base), []).append(it)
    order = sorted(groups, key=lambda k: (0 if k[0] == "window" else 1, k[1], k[2], k[3]))
    types, nw, nd = [], 0, 0
    seen_size = {}
    for key in order:
        kind, leaves, nominal, n = key
        grp = groups[key]
        if kind == "window":
            nw += 1; tid = f"WT{nw}"
        else:
            nd += 1; tid = f"DT{nd}"
        measured = [g for g in grp if g["nominal_src"] != "추정"]
        donor = (measured or grp)[0]
        variant = seen_size.get((kind, leaves, nominal), 0) + 1
        seen_size[(kind, leaves, nominal)] = variant
        by_sheet = {}
        for g in grp:
            by_sheet[g["sheet"]] = by_sheet.get(g["sheet"], 0) + 1
        types.append({"id": tid, "kind": kind, "leaves": leaves, "band": False, "width": nominal, "symbol_width": donor["symbol"], "objects": n, "variant": variant,
                      "nominal_src": "벽체 개구부" if measured else "추정", "check": not measured, "count": len(grp), "by_sheet": by_sheet, "virtual": False,
                      "donor": {"sheet": donor["sheet"], "id": donor["id"], "handles": donor["handles"], "xy": donor["xy"], "horiz": donor["horiz"]},
                      "instances": [{"sheet": g["sheet"], "id": g["id"]} for g in grp]})
    for kind, leaves, width in VIRTUAL:
        if any(t["kind"] == kind and t["leaves"] == leaves and abs(t["width"] - width) < 50 for t in types):
            continue
        if kind == "window":
            nw += 1; tid = f"WT{nw}"
        else:
            nd += 1; tid = f"DT{nd}"
        types.append({"id": tid, "kind": kind, "leaves": leaves, "band": False, "width": width, "symbol_width": width, "objects": 0, "variant": 1,
                      "nominal_src": "가상", "check": False, "count": 0, "by_sheet": {}, "virtual": True, "donor": None, "instances": []})
    return {"sheets": sheets, "types": types, "bands": [{"sheet": i["sheet"], "id": i["id"], "width": i["nominal"]} for i in items if i["band"]]}


def render(schedule, out_png):
    """일람표 그림: 타입마다 실제 기호를 그려 넣는다."""
    import math
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from ezdxf import bbox as bb
    from ezdxf.addons.drawing import RenderContext, Frontend
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

    plt.rcParams["font.family"] = ["Malgun Gothic", "AppleSDGothicNeoR00", "NanumGothic", "DejaVu Sans"]
    types = schedule["types"]
    cols = 6
    rows = math.ceil(len(types) / cols)
    fig = plt.figure(figsize=(cols * 3.0, rows * 3.3 + 0.6), facecolor="white")
    fig.suptitle("문·창호 일람표 (건물 전체, 도면에서 읽음)", fontsize=14, y=0.995)
    docs = {}
    for i, t in enumerate(types):
        ax = fig.add_axes([(i % cols) / cols + 0.01, 1 - (i // cols + 1) / rows * 0.96 + 0.075 / rows * 3, 1 / cols - 0.02, 0.62 / rows])
        ax.set_facecolor("black")
        ax.set_xticks([]); ax.set_yticks([])
        if t["donor"]:
            sh = t["donor"]["sheet"]
            if sh not in docs:
                docs[sh] = ezdxf.readfile(ROOT / "real_dxf" / f"{sh}.dxf")
            doc = docs[sh]
            ents = [doc.entitydb[h] for h in t["donor"]["handles"] if h in doc.entitydb]
            ctx = RenderContext(doc)
            ctx.set_current_layout(doc.modelspace())
            Frontend(ctx, MatplotlibBackend(ax)).draw_entities(ents)
            ext = bb.extents(ents, fast=True)
            if ext.has_data:
                cx, cy = (ext.extmin.x + ext.extmax.x) / 2, (ext.extmin.y + ext.extmax.y) / 2
                half = max(ext.size.x, ext.size.y) / 2 * 1.25 + 100
                ax.set_xlim(cx - half, cx + half); ax.set_ylim(cy - half, cy + half)
            ax.set_aspect("equal")
        else:
            ax.text(0.5, 0.5, "가상\n(기본 기호로 그림)", color="#bbbbbb", ha="center", va="center", transform=ax.transAxes, fontsize=10)
        for sp in ax.spines.values():
            sp.set_edgecolor("#888888")
        kind = "창호" if t["kind"] == "window" else f'문 {t["leaves"]}짝'
        src = "가상" if t["virtual"] else ", ".join(f'{SHEET_NAMES.get(k, k)} {v}' for k, v in t["by_sheet"].items())
        note = "" if t["nominal_src"] in ("벽체 개구부", "가상") else " (확인 필요)"
        fig.text((i % cols + 0.5) / cols, 1 - (i // cols + 1) / rows * 0.96 + 0.06 / rows * 3,
                 f'{t["id"]}  {kind}  폭 {t["width"]}{note}' + chr(10) + f'{src}' + (f'  · {t["objects"]}개 객체' if t["objects"] else ""), ha="center", va="top", fontsize=8.5,
                 color="#0a8f3c" if t["virtual"] else "black")
    fig.savefig(out_png, dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sheets = sys.argv[1].split(",") if len(sys.argv) > 1 else ["A12", "A13", "A14", "A15"]
    sc = build(sheets)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "schedule.json").write_text(json.dumps(sc, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)), encoding="utf-8")
    print(f'{"타입":5s} {"종류":8s} {"호칭폭":>6s} {"기호폭":>6s} {"객체":>4s} {"개수":>4s}  출처')
    for t in sc["types"]:
        kind = "창호" if t["kind"] == "window" else f'문 {t["leaves"]}짝'
        src = "가상" if t["virtual"] else ", ".join(f'{SHEET_NAMES.get(k, k)} {v}' for k, v in t["by_sheet"].items()) + ("" if t["nominal_src"] == "벽체 개구부" else "  ※폭 추정")
        print(f'{t["id"]:5s} {kind:8s} {t["width"]:6d} {t["symbol_width"]:6d} {t["objects"]:4d} {t["count"]:4d}  {src}')
    print(f'문 띠(타입 제외): {len(sc["bands"])}개')
    render(sc, OUT / "schedule.png")
    print("saved", OUT / "schedule.json", OUT / "schedule.png")
