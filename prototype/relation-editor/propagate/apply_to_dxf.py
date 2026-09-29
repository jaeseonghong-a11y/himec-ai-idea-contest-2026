"""changes.json(confirmed) → 실제 DXF 반영 (묶음 C, 한 도면).

- 그리드 이동: 띠 STRETCH (stretch.py). 그리드선·기둥·벽·마감·치수가 함께 움직이고, 띠 밖으로 뻗은 선은 끝점만 따라온다
- 기둥 단면 변경: COL 폴리선을 중심 기준으로 재작성
- 정합성 검사: 이동한 기둥에 접한 벽선이 따라왔는지
원본은 건드리지 않고 out/real/<sheet>_modified.dxf 로 저장. 변경 전후 확대 이미지를 함께 저장.
"""
import json
import sys
from pathlib import Path

import ezdxf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stretch import grid_move_with_checks  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out" / "real"


def resize_poly(e, spec):
    w, h = map(float, spec.lower().split("x"))
    pts = [(p[0], p[1]) for p in e.get_points()]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    e.set_points([(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2), (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)])
    e.closed = True


def apply(sheet: str, changes_path: Path = None):
    changes = json.loads((changes_path or (OUT / "changes.json")).read_text(encoding="utf-8"))
    graph = json.loads((OUT / "graph_real.json").read_text(encoding="utf-8"))
    src = ROOT / "real_dxf" / f"{sheet}.dxf"
    doc = ezdxf.readfile(src)
    db = doc.entitydb
    log, results = [], []
    for ch in changes:
        if ch["status"] != "confirmed" or ch["sheet"] != sheet:
            continue
        if ch["action"] == "move" and ch["target"] in graph["grids"]:
            g = graph["grids"][ch["target"]]
            res = grid_move_with_checks(doc, g["axis"], g["coord"], ch["params"]["delta"])
            res["change"] = ch["id"]
            results.append(res)
            log.append(f'{ch["id"]} 그리드 {ch["target"]} {g["axis"]}={g["coord"]} → {g["coord"] + ch["params"]["delta"]:.0f}: 객체 {res["moved_count"]}개 이동')
            for k, v in list(res["by_layer"].items())[:12]:
                log.append(f"     {k}: {v}")
            for d in res["dims"]:
                log.append(f'     치수 {d["handle"]} {d["old"]} → {d["new"]} (재렌더 {"성공" if d["rerender"] else "실패"})')
            for c in res["column_checks"]:
                log.append(f'     기둥 {c["column"]} 접한 벽선 {c["walls_before"]} → {c["walls_after"]} {"OK" if c["ok"] else "미이동 " + str(c["lost"])}')
            for f in res["flagged"][:6]:
                log.append(f'     주의 {f["layer"]} {f["handle"]}: {f["issue"]}')
        elif ch["action"] == "resize":
            for imp in ch["impacts"]:
                if imp["kind"] == "column" and "new_spec" in imp:
                    resize_poly(db[imp["handle"]], imp["new_spec"])
                    log.append(f'{ch["id"]} 기둥 {imp["element"]} 단면 {imp["old_spec"]} → {imp["new_spec"]}')
        else:
            log.append(f'{ch["id"]} {ch["target"]} {ch["action"]}: 도면 반영 미지원(관계도에만 기록)')
    dst = OUT / f"{sheet}_modified.dxf"
    doc.saveas(dst)
    report = {"sheet": sheet, "source": src.name, "output": dst.name, "log": log,
              "results": [{k: v for k, v in r.items() if k != "moved_handles"} for r in results]}
    (OUT / "propagate_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    return dst, log, results


def render_window(dxf_path: Path, out_png: Path, window, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from ezdxf.addons.drawing import RenderContext, Frontend
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

    plt.rcParams["font.family"] = ["Malgun Gothic", "AppleSDGothicNeoR00", "NanumGothic", "DejaVu Sans"]
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_axes([0, 0, 1, 0.95])
    ax.set_axis_off()
    ctx = RenderContext(doc)
    ctx.set_current_layout(msp)
    Frontend(ctx, MatplotlibBackend(ax)).draw_layout(msp, finalize=False)
    ax.set_xlim(window[0], window[2])
    ax.set_ylim(window[1], window[3])
    ax.set_aspect("equal")
    fig.suptitle(title, color="white", backgroundcolor="black", fontsize=11)
    fig.savefig(out_png, dpi=120, facecolor="black")
    plt.close(fig)


if __name__ == "__main__":
    sheet = sys.argv[1] if len(sys.argv) > 1 else "A12"
    cpath = Path(sys.argv[2]) if len(sys.argv) > 2 else None   # 편집기가 내보낸 changes_<sheet>.json 경로
    dst, log, results = apply(sheet, cpath)
    for l in log:
        print("  " + l)
    print("saved", dst, "| propagate_report.json")
    win = (10500, 8500, 35500, 28500)
    render_window(ROOT / "real_dxf" / f"{sheet}.dxf", OUT / f"{sheet}_before.png", win, f"{sheet} 변경 전")
    render_window(dst, OUT / f"{sheet}_after.png", win, f"{sheet} 변경 후")
    print("saved", OUT / f"{sheet}_before.png", OUT / f"{sheet}_after.png")
