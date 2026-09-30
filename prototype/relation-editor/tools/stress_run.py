"""한계 찾기 2단계: editor/test_stress.js 가 만든 계획안들을 도면으로 그리고 다시 읽어 대조한다.

python tools/stress_run.py            # out/editor/stress/changes_*.json 전부
python tools/stress_run.py S1 S3      # 일부만
"""
import json
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
SD = ROOT / "out" / "editor" / "stress"
names = sys.argv[1:] or sorted(p.stem[8:] for p in SD.glob("changes_*.json"))
rows = []
for name in names:
    ch, ex = SD / f"changes_{name}.json", SD / f"expected_{name}.json"
    t0 = time.time()
    sheet = json.loads(ch.read_text(encoding="utf-8"))[0]["sheet"] if ch.stat().st_size > 2 else name      # 기존 도면 시험은 changes 의 sheet(A12M)를 쓴다
    r = subprocess.run([sys.executable, str(ROOT / "propagate" / "apply_edits.py"), sheet, str(ch), str(ex), "--quick"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT)
    out = r.stdout
    errs = [l.strip() for l in out.splitlines() if "오류" in l]
    fails = [l.strip() for l in out.splitlines() if l.strip().startswith("FAIL")]
    tot = next((l.strip() for l in out.splitlines() if "일치" in l and "/" in l), "")
    crash = r.returncode != 0
    rows.append((name, tot, len(errs), len(fails), crash, round(time.time() - t0, 1)))
    print(f"== {name}: {tot or '왕복 검증 없음'} | 반영 오류 {len(errs)} | {round(time.time() - t0, 1)}초" + (" | 실행 실패" if crash else ""))
    for l in errs[:6]:
        print("   ", l[:200])
    for l in fails[:8]:
        print("   ", l[:200])
    if crash:
        print("   ", r.stderr.strip().splitlines()[-1][:200] if r.stderr.strip() else "(stderr 없음)")
print("\n요약")
for n, tot, ne, nf, crash, sec in rows:
    print(f"  {n:4s} {tot:14s} 오류 {ne} 불일치 {nf} {'실패' if crash else ''} {sec}초")
