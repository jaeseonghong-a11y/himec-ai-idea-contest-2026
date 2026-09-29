"""편집기에서 내려받은 변경 파일을 찾아 도면에 반영하고 결과를 열어 준다.

python tools/try_apply.py                # 다운로드 폴더에서 가장 최근의 changes_*.json 을 찾음
python tools/try_apply.py <변경 파일>
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")


def newest_changes():
    cands = []
    for folder in (Path.home() / "Downloads", Path.home() / "다운로드", ROOT):
        if folder.exists():
            cands += [p for p in folder.glob("changes_*.json")]
    return max(cands, key=lambda p: p.stat().st_mtime) if cands else None


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else newest_changes()
    if not path or not path.exists():
        print("변경 파일을 찾지 못했습니다.")
        print("편집기에서 [변경 내보내기] 버튼을 눌러 changes_<도면>.json 을 내려받은 뒤 다시 실행하세요.")
        return 1
    changes = json.loads(path.read_text(encoding="utf-8"))
    if not changes:
        print("변경 파일이 비어 있습니다.")
        return 1
    sheet = changes[0]["sheet"]
    print(f"변경 파일: {path}")
    print(f"도면: {sheet}   변경 {len(changes)}건   검토자: {changes[0].get('reviewer')}")
    print()
    for c in changes:
        print(f'  {c["id"]}  {c["source"]["text"]}')
    warns = changes[-1].get("warnings") or []
    if warns:
        print(f"\n편집기가 낸 경고 {len(warns)}건")
        for w in warns:
            print("  -", w)
    print("\n도면에 반영하는 중입니다. 1분쯤 걸립니다...\n")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, str(ROOT / "propagate" / "apply_edits.py"), sheet, str(path), "--quick"], cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    for line in r.stdout.splitlines():
        if line.strip().startswith(("CR-", "saved")) or "오류" in line:
            print(line)
    if r.returncode != 0:
        print("\n반영 중 오류가 났습니다.\n", r.stderr[-1500:])
        return 1
    out = ROOT / "out" / "real"
    print("\n결과 파일")
    print("  수정된 도면 :", out / f"{sheet}_edited.dxf")
    print("  변경 전 그림:", out / f"{sheet}_edit_before.png", "(새 도면이면 없음)")
    print("  변경 후 그림:", out / f"{sheet}_edit_after.png")
    print("  다시 읽은 관계도:", out / f"{sheet}_edited_graph.png")
    print("\n원본 도면은 바뀌지 않았습니다. 그림을 엽니다.")
    (ROOT / "out" / "last_edited.txt").write_text(str(out / f"{sheet}_edited.dxf"), encoding="utf-8")
    is_new = not (ROOT / "real_dxf" / f"{sheet}.dxf").exists()
    for name in ((f"{sheet}_edit_after.png", f"{sheet}_edited_graph.png") if is_new else (f"{sheet}_edit_before.png", f"{sheet}_edit_after.png", f"{sheet}_edited_graph.png")):
        f = out / name
        if f.exists():
            os.startfile(f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
