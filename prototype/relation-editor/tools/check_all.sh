#!/usr/bin/env bash
# 편집기와 도면 그리기를 한 번에 확인한다 (AutoCAD 확인은 따로: tools/verify_generated_autocad.py)
cd "$(dirname "$0")/.." || exit 1
python editor/build_editor.py blank | tail -1 >/dev/null
python editor/build_editor.py >/dev/null
echo "== 편집기 로직 (새 프로젝트 / 기존 도면)"
node editor/test_new.js NEW1 2>&1 | grep -E "FAIL|passed|Error|^\s+at " | head -12
node editor/test_core.js A12M 2>&1 | grep -E "FAIL|passed"
echo "== 도면 그리기와 왕복 검증 (NEW1 / NEW1T)"
for s in "NEW1 changes_new expected_new" "NEW1T changes_new_thick expected_new_thick"; do
  set -- $s
  python propagate/apply_edits.py "$1" "out/editor/$2.json" "out/editor/$3.json" --quick 2>&1 | grep -E "오류|일치|FAIL|Trace|Error|겹침 피하기: .*줄을" | cut -c1-220
done
echo "== 화면 조작 (NEW1 / A12M)"
EDGE="/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
for sh in NEW1 A12M; do
  "$EDGE" --headless=new --disable-gpu --virtual-time-budget=20000 --dump-dom "file:///$(pwd -W)/out/editor/relation_editor_$sh.html#selftest" 2>/dev/null | grep -oE "[0-9]+ passed, [0-9]+ failed|FAIL  [^<]{0,200}" | grep -v '시험 중 오류: "' | head -8
done
echo "== 선 굵기 (NEW1T)"
python tools/lw_report.py NEW1T
