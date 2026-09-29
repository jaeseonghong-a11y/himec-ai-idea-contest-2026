"""도면에서 사무소·대지·사람을 알 수 있는 정보가 어디에 있는지 조사한다 (가리기 전 확인용).

사용: python tools/mask_survey.py A12 [폴더]
"""
import re
import sys
from pathlib import Path

import ezdxf

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sheet = sys.argv[1] if len(sys.argv) > 1 else "A12"
folder = sys.argv[2] if len(sys.argv) > 2 else "real_dxf"
path = ROOT / folder / f"{sheet}.dxf"
d = ezdxf.readfile(path)
msp = d.modelspace()


def text_of(e):
    return (e.text if e.dxftype() == "MTEXT" else e.dxf.text).strip()


tb = next((b for b in d.blocks if any("TEL" in text_of(x) for x in b.query("TEXT MTEXT"))), None)
if tb is None:
    print("표제란 블록(TEL 문자가 든 블록)이 없음")
else:
    lab = [(e.dxf.insert.x, e.dxf.insert.y, text_of(e)) for e in tb.query("TEXT")]
    xs, ys = [v[0] for v in lab], [v[1] for v in lab]
    ins = [i for i in msp.query("INSERT") if i.dxf.name == tb.name]
    print(f"표제란 블록 {tb.name}: 글자 범위 x {min(xs):.0f}~{max(xs):.0f}, y {min(ys):.0f}~{max(ys):.0f}, 삽입 {[(round(i.dxf.insert.x), round(i.dxf.insert.y)) for i in ins]}")
    x0, ox = min(xs) - 500, (ins[0].dxf.insert.x if ins else 0)
    near = []
    for e in msp.query("TEXT MTEXT ATTRIB"):
        p = e.dxf.insert
        if p.x >= x0 + ox:
            near.append((round(p.x), round(p.y), e.dxf.layer, e.dxf.handle, text_of(e)[:60]))
    print(f"표제란 띠 안의 모델 공간 문자 {len(near)}개")
    for t in sorted(near, key=lambda v: -v[1]):
        print("   ", t)
print("문서 속성:", {k: d.header.get(k) for k in ("$LASTSAVEDBY", "$PROJECTNAME", "$HYPERLINKBASE", "$STYLESHEET", "$MENU") if k in d.header})
print("외부 참조:", [b.name for b in d.blocks if b.block is not None and b.block.dxf.get("xref_path")], "| 이미지·밑바탕:", [e.dxftype() for e in d.objects if e.dxftype() in ("IMAGEDEF", "UNDERLAYDEFINITION", "PDFDEFINITION", "DGNDEFINITION")])
raw = path.read_text(encoding="utf-8", errors="replace")
for m in sorted(set(re.findall(r"[A-Za-z]:\\[^\r\n]{3,90}", raw)))[:20]:
    print("   파일 안의 경로:", m)
