"""실제 도면 관계도 데모 한 번에 실행.

전제: real_dxf/<sheet>.dxf 가 있어야 한다 (DWG는 AutoCAD COM으로 변환: tools/dwg2dxf.py).
python run_real_demo.py                       # A12, "X6 move 500"
python run_real_demo.py A12 "X6 move 500;C@X8-Y2 resize 700x400"
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable
sheet = sys.argv[1] if len(sys.argv) > 1 else "A12"
cmds = sys.argv[2] if len(sys.argv) > 2 else "X6 move 500"

out = ROOT / "out" / "real"
out.mkdir(parents=True, exist_ok=True)
for f in ("changes.json", "graph_real.json", "graph_real_after.json", "propagate_report.json"):
    (out / f).unlink(missing_ok=True)

steps = [
    ("3-a 실도면 관계도 읽기 (그리드·기둥·스팬·치수)", [PY, "graph/build_graph_real.py", sheet]),
    ("3-b 관계도에서 변경 적용", [PY, "graph/apply_change_real.py", cmds]),
    ("2   DXF 반영 + 치수 재렌더 + 정합성 검사", [PY, "propagate/apply_to_dxf.py", sheet]),
]
for name, cmd in steps:
    print(f"\n=== {name} ===", flush=True)
    r = subprocess.run(cmd, cwd=ROOT, text=True, encoding="utf-8")
    if r.returncode != 0:
        print(f"실패: {name}")
        sys.exit(r.returncode)
print("\n완료. out/real/ 의 graph_real_before.png, graph_real_after.png, A12_before.png, A12_after.png, A12_modified.dxf, propagate_report.json 확인")
