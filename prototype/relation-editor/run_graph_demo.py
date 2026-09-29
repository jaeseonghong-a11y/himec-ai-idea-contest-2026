"""관계도 데모 한 번에 실행.

python run_graph_demo.py                       # 기본: C1 move -500 0 ; C5 resize 600x400
python run_graph_demo.py "C1 move 0 500"       # 변경 지정 (; 로 여러 개)
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable
cmds = sys.argv[1] if len(sys.argv) > 1 else "C1 move -500 0;C5 resize 600x400"

out = ROOT / "out"
out.mkdir(exist_ok=True)
for f in ("changes.json", "graph.json", "graph_after.json", "graph_before.png", "graph_after.png"):
    (out / f).unlink(missing_ok=True)

steps = [
    ("0-a 합성 도면 생성", [PY, "sidecar/make_sample.py"]),
    ("0-b 사이드카 JSON", [PY, "sidecar/build_sidecar.py", "A-101"]),
    ("3-a 관계도 읽기", [PY, "graph/build_graph.py", "A-101"]),
    ("3-b 관계도 수정", [PY, "graph/apply_change.py", cmds]),
]
for name, cmd in steps:
    print(f"\n=== {name} ===")
    r = subprocess.run(cmd, cwd=ROOT, text=True, encoding="utf-8")
    if r.returncode != 0:
        print(f"실패: {name}")
        sys.exit(r.returncode)
print("\n완료. out/ 폴더의 graph_before.png, graph_after.png, changes.json 확인")
