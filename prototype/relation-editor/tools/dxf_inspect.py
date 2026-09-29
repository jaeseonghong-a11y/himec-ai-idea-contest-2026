import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import ezdxf
from collections import Counter
from ezdxf import bbox
path = sys.argv[1]
doc = ezdxf.readfile(path)
msp = doc.modelspace()
print("dxfversion", doc.dxfversion, "| insunits", doc.header.get("$INSUNITS"), "| layouts", [l.name for l in doc.layouts])
types = Counter(e.dxftype() for e in msp)
print("entity types:", dict(types.most_common()))
layers = Counter((e.dxf.layer, e.dxftype()) for e in msp)
by_layer = {}
for (l,t),n in layers.items(): by_layer.setdefault(l, {})[t]=n
print("\nlayers (%d):" % len(by_layer))
for l in sorted(by_layer, key=lambda k:-sum(by_layer[k].values()))[:40]:
    print(f"  {l:28s} {sum(by_layer[l].values()):5d}  {by_layer[l]}")
blocks = Counter(e.dxf.name for e in msp if e.dxftype()=="INSERT")
print("\nblock inserts (%d kinds):" % len(blocks))
for b,n in blocks.most_common(25): print(f"  {b:30s} {n}")
dims = [e for e in msp if e.dxftype()=="DIMENSION"]
print("\nDIMENSION:", len(dims), "| dimtypes", Counter(d.dimtype for d in dims), "| dimstyles", Counter(d.dxf.dimstyle for d in dims).most_common(5))
if dims:
    d=dims[0]; print("  sample: defpoint", d.dxf.defpoint, "defpoint2", d.dxf.defpoint2, "defpoint3", d.dxf.defpoint3, "text", repr(d.dxf.text), "measurement", d.get_measurement())
texts = [(e.dxf.layer, (e.dxf.text if e.dxftype()=="TEXT" else e.plain_text())) for e in msp if e.dxftype() in ("TEXT","MTEXT")]
print("\nTEXT/MTEXT:", len(texts))
pat = re.compile(r"^(C\d+|[XY]\d+|[A-Z]\d{0,2}|\d{1,2}|[가-힣]{1,4})$")
short = Counter(t.strip() for l,t in texts if len(t.strip())<=6)
print("  short labels:", short.most_common(40))
for kw in ("기둥","C1","400","일람","창호","W1","콘센트","X1","Y1"):
    hits=[(l,t) for l,t in texts if kw in t][:4]
    if hits: print(f"  '{kw}':", hits)
ext = bbox.extents(msp, fast=True)
print("\nextents", ext.extmin, ext.extmax)
