import time
from pathlib import Path
import win32com.client, pythoncom, pywintypes
SRC = Path(r"C:\Users\김기준\Desktop\하이맥_프로토타입\real sample")
DST = Path(r"C:\Users\김기준\Desktop\하이맥_프로토타입\real_dxf")
pythoncom.CoInitialize()
acad = win32com.client.Dispatch("AutoCAD.Application")

def retry(fn, tries=30, wait=3):
    last = None
    for _ in range(tries):
        try:
            return fn()
        except pywintypes.com_error as e:
            last = e; time.sleep(wait)
    raise last

def _vis():
    acad.Visible = True
for _ in range(40):
    try: _vis(); break
    except Exception: time.sleep(3)
doc0 = retry(lambda: acad.Documents.Add())
for var, val in (("PROXYNOTICE", 0), ("FILEDIA", 0), ("CMDDIA", 0)):
    try: retry(lambda: doc0.SetVariable(var, val)); print("sysvar", var, "=", val, flush=True)
    except Exception as e: print("sysvar", var, "fail", str(e)[:80], flush=True)

ok = fail = 0
for dwg in sorted(SRC.glob("*.dwg")):
    code = dwg.name.split(".")[0]
    out = DST / f"{code}.dxf"
    if out.exists():
        ok += 1; continue
    try:
        doc = retry(lambda: acad.Documents.Open(str(dwg), True))
        time.sleep(3)
        retry(lambda: doc.SaveAs(str(out), 61))
        retry(lambda: doc.Close(False))
        print("ok  ", code, out.stat().st_size // 1024, "KB", flush=True); ok += 1
    except Exception as e:
        print("FAIL", code, str(e)[:200], flush=True); fail += 1
        try: acad.ActiveDocument.Close(False)
        except Exception: pass
print(f"done ok={ok} fail={fail}", flush=True)
