#!/usr/bin/env bash
# 받은 뒤 한 번 실행: real_dxf/ 의 1~4층 평면도에서 일람표, 설비 가상 배치(A12M), 관계도, 편집기를 만든다
cd "$(dirname "$0")/.." || exit 1
set -e
python graph/build_schedule.py | tail -2          # 1~4층 평면도 → 건물 전체 문·창호 일람표
python mep/make_layout.py | tail -1               # A12 + 설비·전기·소방 가상 배치 → real_dxf/A12M.dxf
python graph/build_graph_real.py A12M | tail -2   # 관계도 읽기
python editor/build_editor.py real | tail -1      # 기존 도면 편집기
python editor/build_editor.py blank | tail -1     # 새 프로젝트 편집기
echo "준비 끝. 확인은 bash tools/check_all.sh"
