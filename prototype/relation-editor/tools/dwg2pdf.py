"""AutoCAD COM으로 DWG → PDF 출력 (DWG To PDF.pc3, 모델 공간 범위, 용지에 맞춤).
python tools/dwg2pdf.py A12        # 코드로 시작하는 도면 하나
python tools/dwg2pdf.py            # 전체
"""
import sys, io, time
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import win32com.client, pythoncom, pywintypes

ROOT = Path(__file__).resolve().parents[1]
SRC, DST = ROOT / "real sample", ROOT / "real_pdf"
DST.mkdir(exist_ok=True)
want = sys.argv[1:] 

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
doc0 = retry(lambda: acad.Documents.Add())
for var, val in (("PROXYNOTICE", 0), ("FILEDIA", 0), ("CMDDIA", 0), ("BACKGROUNDPLOT", 0)):
    try: retry(lambda: doc0.SetVariable(var, val), n=5)
    except Exception as e: print("sysvar", var, "fail", str(e)[:60])

for dwg in sorted(SRC.glob("*.dwg")):
    code = dwg.name.split(".")[0]
    if want and code not in want:
        continue
    out = DST / f"{code}.pdf"
    try:
        doc = retry(lambda: acad.Documents.Open(str(dwg), True))
        time.sleep(3)
        retry(lambda: doc.SetVariable("TILEMODE", 1))
        retry(lambda: doc.SetVariable("BACKGROUNDPLOT", 0))
        lay = retry(lambda: doc.ActiveLayout)
        def cfg():
            lay.ConfigName = "DWG To PDF.pc3"
        retry(cfg)
        retry(lambda: lay.RefreshPlotDeviceInfo())
        names = list(retry(lambda: lay.GetCanonicalMediaNames()))
        media = next((m for m in names if "A3" in m and "full_bleed" in m and "420.00_x_297.00" in m), None) or next((m for m in names if "A3" in m), names[0])
        def setup():
            lay.CanonicalMediaName = media
            lay.PlotType = 1          # acExtents
            lay.UseStandardScale = True
            lay.StandardScale = 0     # acScaleToFit
            lay.CenterPlot = True
            lay.PlotRotation = 0
        retry(setup)
        ok = retry(lambda: doc.Plot.PlotToFile(str(out)))
        for _ in range(30):
            if out.exists() and out.stat().st_size > 0: break
            time.sleep(1)
        print(f"{code}: plot={ok} media={media} size={out.stat().st_size//1024 if out.exists() else 0}KB", flush=True)
        retry(lambda: doc.Close(False))
    except Exception as e:
        print(f"{code}: FAIL {str(e)[:160]}", flush=True)
