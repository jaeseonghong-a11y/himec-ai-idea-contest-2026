"""합성 평면도 A-101.dxf 생성 (묶음 A 최소 조각).

실제 프로젝트 도면이 아니라 데모용 합성 데이터다. 단위 mm.
- 기둥: 블록 COL, 속성 TAG(C1~C6), SIZE(400x400)
- 보: 레이어 S-BEAM의 LINE, 기둥 중심 사이
- 벽: 레이어 A-WALL의 LINE, 외주부 기둥 사이
- 창호: 블록 WIN, 속성 TAG(W1~), SIZE, 벽 위에 삽입
- 콘센트: 블록 OUTLET, 속성 TAG, 레이어 E-POWER
- 기둥 일람표: 레이어 A-SCHED의 TEXT ("C1 400x400")
"""
from pathlib import Path
import ezdxf

OUT = Path(__file__).resolve().parents[1] / "samples" / "A-101.dxf"

GRID_X = [0, 7500, 15000]
GRID_Y = [0, 6000]


def make_block(doc, name, layer, draw, attribs):
    blk = doc.blocks.new(name=name)
    draw(blk)
    for i, (tag, prompt) in enumerate(attribs):
        blk.add_attdef(tag, (0, -300 - 250 * i), dxfattribs={"height": 150, "layer": layer, "prompt": prompt})
    return blk


def main():
    doc = ezdxf.new("R2018", setup=True)
    doc.header["$INSUNITS"] = 4  # mm
    for name, color in [("S-COL", 1), ("S-BEAM", 3), ("A-WALL", 7), ("A-WIN", 4), ("E-POWER", 6), ("A-SCHED", 2), ("A-GRID", 8)]:
        doc.layers.add(name, color=color)

    make_block(doc, "COL", "S-COL", lambda b: b.add_lwpolyline([(-200, -200), (200, -200), (200, 200), (-200, 200)], close=True, dxfattribs={"layer": "S-COL"}), [("TAG", "기둥 번호"), ("SIZE", "단면 (mm)")])
    make_block(doc, "WIN", "A-WIN", lambda b: b.add_lwpolyline([(-900, -60), (900, -60), (900, 60), (-900, 60)], close=True, dxfattribs={"layer": "A-WIN"}), [("TAG", "창호 번호"), ("SIZE", "창호 크기")])
    make_block(doc, "OUTLET", "E-POWER", lambda b: b.add_circle((0, 0), 80, dxfattribs={"layer": "E-POWER"}), [("TAG", "콘센트 번호")])

    msp = doc.modelspace()

    # 그리드 선
    for i, x in enumerate(GRID_X):
        msp.add_line((x, -1500), (x, 7500), dxfattribs={"layer": "A-GRID", "linetype": "CENTER"})
        msp.add_text(f"X{i+1}", dxfattribs={"layer": "A-GRID", "height": 250}).set_placement((x - 100, 7700))
    for j, y in enumerate(GRID_Y):
        msp.add_line((-1500, y), (16500, y), dxfattribs={"layer": "A-GRID", "linetype": "CENTER"})
        msp.add_text(f"Y{j+1}", dxfattribs={"layer": "A-GRID", "height": 250}).set_placement((-1900, y - 100))

    # 기둥
    cols = {}
    n = 1
    for y in GRID_Y:
        for x in GRID_X:
            tag = f"C{n}"
            ref = msp.add_blockref("COL", (x, y), dxfattribs={"layer": "S-COL"})
            ref.add_auto_attribs({"TAG": tag, "SIZE": "400x400"})
            cols[tag] = (x, y)
            n += 1

    # 보 (가로 4개 + 세로 3개)
    beams = [("C1", "C2"), ("C2", "C3"), ("C4", "C5"), ("C5", "C6"), ("C1", "C4"), ("C2", "C5"), ("C3", "C6")]
    for i, (a, b) in enumerate(beams, 1):
        ln = msp.add_line(cols[a], cols[b], dxfattribs={"layer": "S-BEAM"})
        mx, my = (cols[a][0] + cols[b][0]) / 2, (cols[a][1] + cols[b][1]) / 2
        msp.add_text(f"B{i:02d}", dxfattribs={"layer": "S-BEAM", "height": 180}).set_placement((mx - 200, my + 150))

    # 외벽 (외주부 기둥 사이)
    walls = [("C1", "C2"), ("C2", "C3"), ("C4", "C5"), ("C5", "C6"), ("C1", "C4"), ("C3", "C6")]
    for a, b in walls:
        msp.add_line(cols[a], cols[b], dxfattribs={"layer": "A-WALL", "lineweight": 50})

    # 창호: C4-C5 벽, C5-C6 벽 위
    w1 = msp.add_blockref("WIN", (3750, 6000), dxfattribs={"layer": "A-WIN"})
    w1.add_auto_attribs({"TAG": "W1", "SIZE": "1800x1500"})
    w2 = msp.add_blockref("WIN", (11250, 6000), dxfattribs={"layer": "A-WIN"})
    w2.add_auto_attribs({"TAG": "W2", "SIZE": "1800x1500"})

    # 콘센트: C1-C2 벽 위
    for i, x in enumerate([2500, 5000], 1):
        o = msp.add_blockref("OUTLET", (x, 150), dxfattribs={"layer": "E-POWER"})
        o.add_auto_attribs({"TAG": f"R-101-{i}"})

    # 기둥 일람표
    msp.add_text("기둥 일람표", dxfattribs={"layer": "A-SCHED", "height": 300}).set_placement((18000, 6000))
    for i, tag in enumerate(cols):
        msp.add_text(f"{tag} 400x400", dxfattribs={"layer": "A-SCHED", "height": 220}).set_placement((18000, 5400 - 400 * i))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(OUT)
    print(f"saved {OUT} | columns {len(cols)} beams {len(beams)} walls {len(walls)}")


if __name__ == "__main__":
    main()
