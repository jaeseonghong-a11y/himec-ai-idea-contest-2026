"""시연 시나리오 문서에 넣을 그림을 만든다: 편집기 화면(Edge), 도면 전후 비교, AutoCAD 출력.

먼저 tools/setup_from_drawings.sh, tools/check_all.sh, 그리고 python tools/rehearse.py 를 돌려 out/ 을 채운 뒤 실행한다.
도면 전후 그림은 마지막으로 반영한 결과(리허설 1부)에서, AutoCAD 출력 그림은
  python tools/verify_generated_autocad.py NEW1 out/rehearsal/expected_NEW1.json
이 만든 out/real/NEW1_autocad.pdf 에서 가져온다. 리허설 단계별 화면은 scenario/rehearsal/ 로 복사한다.
"""
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
DST = ROOT / "scenario"
DST.mkdir(exist_ok=True)
EDGE = next((p for p in (Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"), Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")) if p.exists()), None)
SHOTS = [("a1_editor_original", "relation_editor_A12M.html"), ("a2_editor_edited", "relation_editor_A12M.html#demo"), ("b1_editor_empty", "relation_editor_NEW1.html"),
         ("b2_editor_plan", "relation_editor_NEW1.html#demo"), ("b3_editor_showcase", "relation_editor_NEW1.html#showcase")]
for name, page in SHOTS:
    if EDGE is None:
        print("Edge를 찾지 못해 화면 그림은 건너뜀")
        break
    url = (ROOT / "out" / "editor" / page.split("#")[0]).as_uri() + ("#" + page.split("#")[1] if "#" in page else "")
    out = DST / f"{name}.png"
    subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1700,1050", "--virtual-time-budget=9000", f"--screenshot={out}", url], capture_output=True, timeout=120)
    print(name, out.stat().st_size // 1024 if out.exists() else "실패", "KB")
COPY = [("a3_drawing_before", "A12M_edit_before.png"), ("a4_drawing_after", "A12M_edit_after.png"), ("a5_window_before", "A12M_edit_before_W1.png"), ("a6_window_after", "A12M_edit_after_W1.png"),
        ("a7_door_before", "A12M_edit_before_D8.png"), ("a8_door_after", "A12M_edit_after_D8.png"), ("a9_graph_reread", "A12M_edited_graph.png")]
for name, src in COPY:
    p = ROOT / "out" / "real" / src
    if p.exists():
        shutil.copyfile(p, DST / f"{name}.png")
        print(name, p.stat().st_size // 1024, "KB")
    else:
        print(name, "없음:", src)
REH = ROOT / "out" / "rehearsal"
(DST / "rehearsal").mkdir(exist_ok=True)
n = 0
for src in sorted(REH.glob("*_step*.png")):
    shutil.copyfile(src, DST / "rehearsal" / src.name.replace("A12M_", "a_").replace("NEW1_", "b_")); n += 1
print(f"리허설 화면 {n}장" if n else "리허설 화면 없음: python tools/rehearse.py 를 먼저 실행")
pdf = next((q for q in (ROOT / "out" / "real" / "NEW1_autocad.pdf", ROOT / "out" / "real" / "NEW1T_autocad.pdf") if q.exists()), ROOT / "out" / "real" / "NEW1_autocad.pdf")
if pdf.exists():
    import pymupdf
    pg = pymupdf.open(pdf)[0]
    r = pg.rect
    pg.get_pixmap(dpi=110).save(str(DST / "b4_sheet.png"))
    pg.get_pixmap(dpi=200, clip=pymupdf.Rect(r.width * 0.05, r.height * 0.2, r.width * 0.58, r.height * 0.8)).save(str(DST / "b5_plan.png"))
    pg.get_pixmap(dpi=380, clip=pymupdf.Rect(r.width * 0.13, r.height * 0.30, r.width * 0.29, r.height * 0.52)).save(str(DST / "b6_walls.png"))
    pg.get_pixmap(dpi=300, clip=pymupdf.Rect(r.width * 0.20, r.height * 0.42, r.width * 0.50, r.height * 0.64)).save(str(DST / "b7_lineweights.png"))
    pg.get_pixmap(dpi=170, clip=pymupdf.Rect(r.width * 0.58, r.height * 0.2, r.width * 0.97, r.height * 0.6)).save(str(DST / "b8_schedules.png"))
    pg.get_pixmap(dpi=300, clip=pymupdf.Rect(r.width * 0.31, r.height * 0.45, r.width * 0.50, r.height * 0.67)).save(str(DST / "b9_diagonal.png"))
    print("AutoCAD 출력 그림 6장")
else:
    print("AutoCAD 출력(NEW1_autocad.pdf)이 없어 건너뜀. python tools/verify_generated_autocad.py NEW1 out/rehearsal/expected_NEW1.json 을 먼저 실행")
