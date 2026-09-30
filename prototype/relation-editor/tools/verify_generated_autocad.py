"""생성(또는 수정)한 DXF를 AutoCAD로 열어 확인한다.

1. 열리는지, 객체 수
2. 치수: AutoCAD가 다시 계산한 값과 정의점 거리, 기대값(편집기 자동 치수) 비교
3. AutoCAD의 도면 검사(AUDIT) 결과
4. AutoCAD가 직접 출력한 PDF → 그림 (실제로 어떻게 보이는지)
사용: python tools/verify_generated_autocad.py NEW1
"""
import json
import os
import shutil
import sys
import time
from pathlib import Path

import pythoncom
import pywintypes
import win32com.client

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sheet = sys.argv[1] if len(sys.argv) > 1 else "NEW1"
src = ROOT / "out" / "real" / f"{sheet}_edited.dxf"
tmp = Path("C:/himec_tmp"); tmp.mkdir(exist_ok=True)
work = tmp / f"{sheet}_check.dxf"
shutil.copyfile(src, work)


def retry(fn, n=40, w=2):
    last = None
    for _ in range(n):
        try:
            return fn()
        except (pywintypes.com_error, AttributeError) as e:
            last = e; time.sleep(w)
    raise last


pythoncom.CoInitialize()
acad = win32com.client.Dispatch("AutoCAD.Application")
def vis():
    acad.Visible = True
retry(vis)
d0 = retry(lambda: acad.Documents.Add())
for var, val in (("PROXYNOTICE", 0), ("FILEDIA", 0), ("CMDDIA", 0), ("BACKGROUNDPLOT", 0)):
    try: retry(lambda: d0.SetVariable(var, val), n=5)
    except Exception: pass

doc = retry(lambda: acad.Documents.Open(str(work), False))
time.sleep(3)
ms = retry(lambda: doc.ModelSpace)
print(f"AutoCAD {acad.Version} 에서 열림: {src.name} | 모델 공간 객체 {retry(lambda: ms.Count)}개")

# 치수 재계산
res = tmp / "dims.txt"
if res.exists(): res.unlink()
lisp = ('(progn (setq f (open "C:/himec_tmp/dims.txt" "w")) (setq ss (ssget "_X" (list (cons 0 "DIMENSION")))) '
        '(if ss (progn (setq i 0) (repeat (sslength ss) (setq e (ssname ss i)) (entmod (entget e)) (entupd e) (setq d (entget e)) '
        '(princ (strcat (cdr (assoc 5 d)) " " (rtos (cdr (assoc 42 d)) 2 1) " " (rtos (distance (cdr (assoc 13 d)) (cdr (assoc 14 d))) 2 1) " [" (cdr (assoc 1 d)) "] " (cdr (assoc 8 d)) "\\n") f) (setq i (1+ i))))) '
        '(close f) (princ))\n')
retry(lambda: doc.SendCommand(lisp))
for _ in range(30):
    if res.exists() and res.stat().st_size > 0: break
    time.sleep(1)
got = []
if res.exists():
    for line in res.read_text(encoding="utf-8", errors="replace").splitlines():
        p = line.split()
        if len(p) >= 3:
            got.append((p[0], float(p[1]), float(p[2]), line[line.find("["):]))
exp_path = ROOT / "out" / "editor" / {"NEW1": "expected_new.json", "NEW1T": "expected_new_thick.json"}.get(sheet, f"expected_{sheet.lower()}.json")
exp = sorted(d["value"] for d in json.loads(exp_path.read_text(encoding="utf-8")).get("auto_dims", [])) if exp_path.exists() and sheet.startswith("NEW") else None
print(f"\n치수 {len(got)}개 (AutoCAD가 다시 계산한 값 / 정의점 사이 거리)")
for h, m, dist, rest in got:
    print(f"  {h:>5s}  {m:8.1f} / {dist:8.1f}  {'OK' if abs(m - dist) < 0.5 else '불일치'}  {rest}")
if exp is not None:
    vals = sorted(round(g[1]) for g in got)
    print("기대값:", exp)
    print("AutoCAD:", vals, "→", "모두 일치" if vals == exp else "불일치")

# 도면 검사
retry(lambda: doc.SendCommand('(progn (setvar "AUDITCTL" 1) (command "_.AUDIT" "_N") (princ))\n'))
time.sleep(4)
adt = work.with_suffix(".adt")
if adt.exists():
    txt = adt.read_text(encoding="cp949", errors="replace")
    tail = [l.strip() for l in txt.splitlines() if l.strip()][-6:]
    print("\nAUDIT 결과(끝부분):")
    for l in tail: print("  ", l)
else:
    print("\nAUDIT 기록 파일이 만들어지지 않음")

# PDF 출력
pdf = ROOT / "out" / "real" / f"{sheet}_autocad.pdf"
if pdf.exists(): pdf.unlink()
try:
    retry(lambda: doc.SetVariable("TILEMODE", 1)); retry(lambda: doc.SetVariable("BACKGROUNDPLOT", 0))
    lay = retry(lambda: doc.ActiveLayout)
    def cfg(): lay.ConfigName = "DWG To PDF.pc3"
    retry(cfg); retry(lambda: lay.RefreshPlotDeviceInfo())
    names = list(retry(lambda: lay.GetCanonicalMediaNames()))
    media = next((m for m in names if "A2" in m and "full_bleed" in m and "594.00_x_420.00" in m), names[0])
    def setup():
        lay.CanonicalMediaName = media; lay.PlotType = 1; lay.UseStandardScale = True; lay.StandardScale = 0; lay.CenterPlot = True; lay.PlotRotation = 0
        try:
            lay.PlotWithLineweights = True; lay.ScaleLineweights = False   # 레이어 선 굵기 그대로
        except Exception:
            pass
        try:
            lay.PlotWithPlotStyles = True; lay.StyleSheet = "monochrome.ctb"   # 흑백 출력
        except Exception:
            pass
    retry(setup)
    ok = retry(lambda: doc.Plot.PlotToFile(str(pdf)))
    for _ in range(30):
        if pdf.exists() and pdf.stat().st_size > 0: break
        time.sleep(1)
    print(f"\nAutoCAD PDF 출력: {ok}, {pdf.stat().st_size // 1024 if pdf.exists() else 0} KB")
except Exception as e:
    print("\nPDF 출력 실패:", str(e)[:120])
retry(lambda: doc.Close(False))
try:
    retry(lambda: d0.Close(False), n=3)
except Exception: pass
try:
    acad.Quit()
except Exception: pass
if pdf.exists():
    import pymupdf
    pg = pymupdf.open(pdf)[0]
    pg.get_pixmap(dpi=110).save(str(pdf.with_suffix(".png")))
    words = [w[4] for w in pg.get_text("words")]
    print("PDF 안의 글자:", len(words), "개 |", [w for w in words if w.replace(",", "").isdigit()][:12], "|", [w for w in words if not w.replace(",", "").isdigit()][:10])
    print("saved", pdf.with_suffix(".png"))
