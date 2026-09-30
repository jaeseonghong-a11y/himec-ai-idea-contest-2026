"""시연용: 플러그인이 낸 '설계 변경 지시 일람표' PDF로 도면을 고치고, 전후 비교 그림을 만들어 연다.

python tools/show_pdf_apply.py [지시 PDF] [대상 DXF] [--no-open]
  기본 PDF: samples/instructions/ 의 가장 최근 것
  기본 DXF: out/real/pdf_test6.dxf (PDF 그림과 같은 6기둥 시험 도면. 없으면 만든다)

하는 일
 1. PDF 표를 읽어 확정 지시를 DXF에 반영 (tools/pdf_instructions.py 와 같은 코드)
 2. 전/후를 나란히 그린 그림 out/real/pdf_apply_before_after.png — 옮긴 기둥에 표시
 3. 편집기용 JSON 두 개
    - out/real/instructions_<pdf 이름>.json : PDF 그대로 (실제 도면 A12M 에는 핸들 #8E 가 없어 사람이 대상을 찍는 경로)
    - out/real/instructions_A12M_handle_demo.json : 같은 지시를 A12M 의 실제 기둥 핸들로 바꾼 시험용 파일
      (플러그인이 A12M 도면에서 냈다면 나올 형식. 핸들이 맞으면 편집기가 바로 적용하는 것을 보이기 위한 것)
"""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from pdf_instructions import apply, export_json  # noqa: E402


def render_pair(before, after, items, out_png):
    import ezdxf
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from ezdxf.addons.drawing import RenderContext, Frontend
    from ezdxf.addons.drawing.config import Configuration, ColorPolicy
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

    plt.rcParams["font.family"] = ["Malgun Gothic", "NanumGothic", "DejaVu Sans"]
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    moved = [it for it in items if it.get("from_xy")]
    for ax, path, title in ((axes[0], before, "반영 전"), (axes[1], after, "반영 후")):
        doc = ezdxf.readfile(path); msp = doc.modelspace()
        ctx = RenderContext(doc); ctx.set_current_layout(msp)
        Frontend(ctx, MatplotlibBackend(ax), config=Configuration(color_policy=ColorPolicy.BLACK)).draw_layout(msp, finalize=False)
        ax.set_aspect("equal"); ax.set_axis_off(); ax.set_title(title, fontsize=14)
        for it in moved:
            x, y = it["from_xy"] if title == "반영 전" else it["to_xy"]
            ax.add_patch(plt.Circle((x, y), 700, fill=False, color="crimson" if title == "반영 전" else "green", lw=2))
            if title == "반영 후":
                fx, fy = it["from_xy"]
                ax.annotate("", xy=(x, y), xytext=(fx, fy), arrowprops=dict(arrowstyle="->", color="green", lw=2))
                ax.text(x + 900, y, f'[{it["no"]}] {it["target"]} {it["change"]}', color="green", fontsize=11, va="center")
    from ezdxf import bbox
    ext = [bbox.extents(ezdxf.readfile(p).modelspace()) for p in (before, after)]
    x0, y0 = min(e.extmin.x for e in ext), min(e.extmin.y for e in ext); x1, y1 = max(e.extmax.x for e in ext), max(e.extmax.y for e in ext)
    for ax in axes:
        ax.set_xlim(x0 - 800, x1 + 800); ax.set_ylim(y0 - 800, y1 + 800)
    lines = [f'[{it["no"]}] {it["target"]} {it["change"]} {it.get("floor", "")} / {it["status_text"]} → {it["result"]}' for it in items]
    fig.suptitle("설계 변경 지시 일람표(PDF) → 도면 반영", fontsize=15)
    fig.text(0.01, 0.02, "\n".join(l[:150] for l in lines), fontsize=9, va="bottom", family="Malgun Gothic")
    fig.subplots_adjust(left=0.02, right=0.98, top=0.9, bottom=0.12, wspace=0.05)
    fig.savefig(out_png, dpi=110, facecolor="white"); plt.close(fig)


def handle_demo(items):
    """PDF 의 지시를 A12M 실제 기둥 핸들로 바꾼 시험용 JSON."""
    gp = ROOT / "out" / "real" / "graph_real.json"
    if not gp.exists():
        return None
    g = json.loads(gp.read_text(encoding="utf-8"))
    col = next((n for n in g["nodes"] if n.get("type") == "column" and n.get("handle") and n["grid"][0] == "X6" and n["grid"][1] == "Y2"), None) or next(n for n in g["nodes"] if n.get("type") == "column" and n.get("handle"))
    demo = []
    for it in items:
        d = dict(it)
        if it.get("handle"):
            d["target"] = f'{it["tag"]} #{col["handle"]}'; d["handle"] = col["handle"]
        demo.append(d)
    out = ROOT / "out" / "real" / "instructions_A12M_handle_demo.json"
    out.write_text(json.dumps({"source_pdf": "시험용: 플러그인이 A12M 도면에서 냈다면 나올 형식 (핸들만 A12M 기둥 " + "-".join(col["grid"]) + " 의 것으로 바꿈)",
                               "items": demo, "notes": []}, ensure_ascii=False, indent=1), encoding="utf-8")
    return out, col


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    pdfs = sorted((ROOT / "samples" / "instructions").glob("*.pdf"), key=lambda p: p.stat().st_mtime)
    pdf = Path(args[0]) if args else (pdfs[-1] if pdfs else None)
    if not pdf or not pdf.exists():
        sys.exit("지시 PDF가 없습니다. samples/instructions/ 에 넣거나 경로를 주세요.")
    dxf = Path(args[1]) if len(args) > 1 else ROOT / "out" / "real" / "pdf_test6.dxf"
    if not dxf.exists() and dxf.name == "pdf_test6.dxf":
        subprocess.run([sys.executable, str(ROOT / "tools" / "make_pdf_test_dxf.py")], check=True)
    print(f"지시 PDF: {pdf.name}\n대상 도면: {dxf}")
    rep = apply(pdf, dxf)
    print(f'PDF 의 도면 이름: {rep.get("source_drawing")} ({"같은 도면" if rep.get("same_drawing") else "파일 이름이 다름"})')
    for it in rep["items"]:
        print(f'  [{it["no"]}] {it["target"]} {it["change"]} {it["floor"]} / {it["status_text"]}\n      → {it["result"]}')
    for n in rep["notes"]:
        print("  주기:", n)
    png = ROOT / "out" / "real" / "pdf_apply_before_after.png"
    if rep.get("output"):
        render_pair(dxf, Path(rep["output"]), rep["items"], png)
        print("saved", rep["output"]); print("saved", png)
    else:
        print("반영된 지시가 없어 그림을 만들지 않음")
    jout, items = export_json(pdf)
    print("편집기용 JSON:", jout)
    hd = handle_demo(items)
    if hd:
        print(f"핸들 시험용 JSON: {hd[0]}  (기둥 {'-'.join(hd[1]['grid'])}, 핸들 {hd[1]['handle']})")
    if "--no-open" not in sys.argv and rep.get("output"):
        os.startfile(png)


if __name__ == "__main__":
    main()
