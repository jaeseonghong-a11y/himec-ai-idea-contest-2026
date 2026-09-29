"""그린 도면의 레이어별 선 굵기를 센다. 사용: python tools/lw_report.py NEW1T"""
import sys
from collections import Counter
from pathlib import Path

import ezdxf

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sheet = sys.argv[1] if len(sys.argv) > 1 else "NEW1"
doc = ezdxf.readfile(ROOT / "out" / "real" / f"{sheet}_edited.dxf")
c = Counter()
for e in doc.modelspace():
    if e.dxftype() == "LINE" and e.dxf.layer in ("WAL", "HID", "CORE-WAL"):
        lw = e.dxf.get("lineweight", -1)
        c[(e.dxf.layer, lw if lw > 0 else doc.layers.get(e.dxf.layer).dxf.lineweight, "객체" if lw > 0 else "레이어 값")] += 1
for (layer, lw, src), n in sorted(c.items()):
    print(f"  {layer:9s} {lw / 100:.2f} mm  {n:3d}개  ({src})")
