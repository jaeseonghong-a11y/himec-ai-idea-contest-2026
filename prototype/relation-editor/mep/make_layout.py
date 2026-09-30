"""1층 평면도 위에 가상 설비·전기·소방 배치를 얹은 도면을 만든다.

입력: real_dxf/A12.dxf (원본은 건드리지 않음)
출력: real_dxf/A12M.dxf  (A12 + 가상 설비·전기·소방. 'M'이 붙은 도면은 시연용으로 생성한 것)
기구는 이름표가 달린 블록으로 넣고, 건축과의 관계(어느 벽, 어느 구획의 몇 분의 몇)를 블록 속성 HOST에 심는다.
"""
import sys
from pathlib import Path

import ezdxf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "graph"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_graph_real as bgr  # noqa: E402
import mep_schedule as ms  # noqa: E402

WALL_OFFSET = 150   # 벽 부착 기구를 그리드에서 실내 쪽으로 띄우는 거리


def main(src_sheet="A12", dst_sheet="A12M"):
    src = ROOT / "real_dxf" / f"{src_sheet}.dxf"
    g = bgr.build(src, src_sheet)
    doc = ezdxf.readfile(src)
    ms.ensure_blocks(doc)
    msp = doc.modelspace()
    G, N, E = g["grids"], {n["id"]: n for n in g["nodes"]}, {e["id"]: e for e in g["edges"]}
    count = {}

    def tag(prefix):
        count[prefix] = count.get(prefix, 0) + 1
        return f"{prefix}-{count[prefix]}"

    def put(tid, xy, host, rotation=0.0):
        t = ms.BY_ID[tid]
        ref = msp.add_blockref(t["block"], xy, dxfattribs={"layer": t["layer"], "rotation": rotation})
        ref.add_auto_attribs({"TAG": tag(tid[:2]), "TYPE": tid, "HOST": host})
        return ref

    def on_wall(tid, edge_id, frac, side):
        """벽 구간의 frac 지점, side(+1/-1) 쪽 면에 붙인다."""
        e = E.get(edge_id)
        if not e or not e["wall"]:
            return None
        if not e.get("along"):
            return None                              # 사선 벽에는 붙이지 않는다
        a, b = N[e["from"]]["xy"], N[e["to"]]["xy"]
        horiz = G[e["along"]]["axis"] == "y"
        if horiz:
            x, y = a[0] + frac * (b[0] - a[0]), a[1] + side * WALL_OFFSET
            rot = 0 if side > 0 else 180
        else:
            x, y = a[0] + side * WALL_OFFSET, a[1] + frac * (b[1] - a[1])
            rot = -90 if side > 0 else 90
        return put(tid, (round(x), round(y)), f"wall|{edge_id}|{side}", rot)

    def in_bay(tid, gx, gy, fx, fy):
        x = G[gx[0]]["coord"] + fx * (G[gx[1]]["coord"] - G[gx[0]]["coord"])
        y = G[gy[0]]["coord"] + fy * (G[gy[1]]["coord"] - G[gy[0]]["coord"])
        return put(tid, (round(x), round(y)), f"bay|{gx[0]},{gx[1]},{gy[0]},{gy[1]}|{fx:.4f}|{fy:.4f}")

    # 구획: 코어 벽(X5)~기둥열(X6)~외곽 기둥열(X8), 홀의 아래 벽(Y4)~위 벽(Y9)
    bays = [(("X5", "X6"), ("Y4", "Y9")), (("X6", "X8"), ("Y4", "Y9"))]
    for gx, gy in bays:
        for fx in (0.25, 0.75):
            for fy in (1 / 6, 3 / 6, 5 / 6):
                in_bay("EL1", gx, gy, fx, fy)          # 조명 2x3
                in_bay("FS1", gx, gy, fx, fy + 0.07)    # 헤드 2x3 (조명과 겹치지 않게 조금 위)
        for fy in (1 / 3, 2 / 3):
            in_bay("MD1", gx, gy, 0.5, fy)              # 디퓨저 1x2
        in_bay("FD1", gx, gy, 0.5, 0.5)                 # 감지기

    # 벽 부착 기구
    on_wall("EO1", "J@X5-Y4~J@X5-Y6", 0.35, +1)
    on_wall("EO1", "J@X5-Y6~J@X5-Y8", 0.50, +1)
    on_wall("EP1", "J@X5-Y8~J@X5-Y9", 0.50, +1)
    on_wall("EO1", "C@X8-Y4~C@X8-Y7", 0.40, -1)
    on_wall("EO1", "J@X2-Y1~J@X5-Y1", 0.50, +1)          # 화장실 아래 벽 가운데
    on_wall("ES1", "J@X5-Y1~J@X5-Y2", 0.12, -1)          # 화장실 문 옆 스위치
    on_wall("EO1", "J@X1-Y5~J@X1-Y6", 0.50, +1)
    on_wall("ES1", "J@X5-Y4~C@X6-Y4", 0.04, +1)          # 홀 출입 쪽 스위치

    # 덕트: 코어에서 X5 벽을 관통해 홀로 들어와 동쪽으로 가다가, 기둥열 X6 옆에서 아래로 분기
    y_main = 16500
    x0, x1 = G["X5"]["coord"] - 900, G["X8"]["coord"] - 700
    xb = G["X6"]["coord"] + 865
    t = ms.BY_ID["MR1"]
    msp.add_lwpolyline([(x0, y_main), (x1, y_main)], dxfattribs={"layer": t["layer"], "const_width": t["size"]})
    msp.add_lwpolyline([(xb, y_main), (xb, G["Y4"]["coord"] + 350)], dxfattribs={"layer": t["layer"], "const_width": t["size"]})

    dst = ROOT / "real_dxf" / f"{dst_sheet}.dxf"
    doc.saveas(dst)
    return dst, count


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    dst, count = main()
    print("saved", dst, "| 기구", dict(count), "| 덕트 2구간")
