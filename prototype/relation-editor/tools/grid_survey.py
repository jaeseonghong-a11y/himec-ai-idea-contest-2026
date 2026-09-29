"""각 도면의 CEN 그리드선 좌표와 치수 수를 조사해 1층 평면도와 좌표계가 같은지 본다."""
import sys, io; sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import ezdxf
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "graph"))
from build_graph_real import grid_lines
ROOT = Path(__file__).resolve().parents[1]
sheets = sys.argv[1:] or ["A12","A13","A14","A15","A16","A17","A21","A22","A23","A04","A05"]
ref = None
for s in sheets:
    doc = ezdxf.readfile(ROOT/"real_dxf"/f"{s}.dxf"); msp = doc.modelspace()
    g = grid_lines(msp)
    xs = sorted(v["coord"] for v in g.values() if v["axis"]=="x"); ys = sorted(v["coord"] for v in g.values() if v["axis"]=="y")
    nd = len(msp.query("DIMENSION")); ncol = len(msp.query('LWPOLYLINE[layer=="COL"]'))
    if ref is None: ref = (set(xs), set(ys))
    mx = len(set(xs)&ref[0]); my = len(set(ys)&ref[1])
    print(f"{s}: X{len(xs)} {xs}\n     Y{len(ys)} {ys}\n     dims={nd} col_polys={ncol} | 1층과 같은 좌표: X {mx}/{len(xs)}, Y {my}/{len(ys)}")
