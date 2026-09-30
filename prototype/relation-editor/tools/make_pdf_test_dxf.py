"""플러그인의 두 번째 지시 PDF(pdf-test.dxf-변경일람-*.pdf)에 그려진 것과 같은 시험 도면을 만든다.

X1~X3(0, 5000, 10000), Y1~Y2(0, 5000) 그리드 위에 같은 COLUMN 블록 6개, 'COLUMN n' 글자, 그리드 치수.
실제 설계 자료가 아니다. 플러그인 표본(autocad-plugin/tests/make_smoke_dxf.py)과 같은 순서로 만들어
첫 기둥의 핸들이 8E가 되게 한다(PDF의 대상 'C1 #8E'와 맞추기 위해).

python tools/make_pdf_test_dxf.py   → out/real/pdf_test6.dxf
"""
import sys
from pathlib import Path

import ezdxf
from ezdxf import units

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out" / "real" / "pdf_test6.dxf"

XS, YS = (0, 5000, 10000), (5000, 0)          # Y2 가 위, Y1 이 아래 (PDF 그림과 같은 배치: COLUMN 1~3 이 윗줄)


def main():
    d = ezdxf.new("R2018", setup=True)
    d.units = units.MM; d.header["$INSUNITS"] = units.MM
    blk = d.blocks.new(name="COLUMN")
    blk.add_lwpolyline([(-150, -150), (150, -150), (150, 150), (-150, 150)], close=True)
    msp = d.modelspace()
    n = 0
    for y in YS:                                   # 기둥 블록을 먼저 넣어 첫 블록이 8E 가 되게 한다
        for x in XS:
            n += 1
            msp.add_blockref("COLUMN", (x, y), dxfattribs={"layer": "0"})
            msp.add_text(f"COLUMN {n}", dxfattribs={"height": 120, "insert": (x - 150, y - 400)})
    for i, x in enumerate(XS, start=1):            # 그리드선과 기호
        msp.add_line((x, -1500), (x, 8000), dxfattribs={"layer": "GRID", "linetype": "CENTER"})
        msp.add_circle((x, 8000 + 400), 400, dxfattribs={"layer": "GRID"})
        msp.add_text(f"X{i}", dxfattribs={"height": 300, "insert": (x - 200, 8000 + 250), "layer": "GRID"})
    for j, y in enumerate(sorted(YS), start=1):
        msp.add_line((-2500, y), (11500, y), dxfattribs={"layer": "GRID", "linetype": "CENTER"})
        msp.add_circle((-2500 - 400, y), 400, dxfattribs={"layer": "GRID"})
        msp.add_text(f"Y{j}", dxfattribs={"height": 300, "insert": (-2500 - 600, y - 150), "layer": "GRID"})
    for a, b in zip(XS, XS[1:]):                   # 치수
        msp.add_linear_dim(base=(0, 6500), p1=(a, 5000), p2=(b, 5000), dxfattribs={"layer": "DIM"}).render()
    msp.add_linear_dim(base=(0, 7300), p1=(XS[0], 5000), p2=(XS[-1], 5000), dxfattribs={"layer": "DIM"}).render()
    msp.add_linear_dim(base=(-1200, 0), p1=(0, 0), p2=(0, 5000), angle=90, dxfattribs={"layer": "DIM"}).render()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    d.saveas(OUT)
    r = ezdxf.readfile(OUT)
    ins = list(r.modelspace().query("INSERT"))
    print(OUT, "| 기둥", len(ins), "| 첫 기둥 핸들", ins[0].dxf.handle, tuple(ins[0].dxf.insert)[:2])


if __name__ == "__main__":
    main()
