## 목표

사람이 승인한 C1 이동 한 건만 합성 DXF 2장에 반영하고 검사 보고서를 만든다. 담당: `jaeseonghong-a11y`/팀장 AI.

## 담당 파일

`prototype/propagate/`, `prototype/run_demo.py`, `prototype/README.md`. 계약: `prototype/CONTRACT.md`.

## 완료 기준

- 승인 로그 없는 변경, 모호·기각 변경, 예상 밖 action은 파일 수정 없이 거절하고 이유를 보고한다.
- A-101과 A-301에 C1이 정확히 하나씩 있을 때만 두 DXF를 새 `out/modified_*.dxf`로 작성한다. 원본은 덮어쓰지 않는다.
- 변경 전후 좌표와 단순 규칙 검사, E-201 재검토 필요성을 `out/report.md`에 남긴다. 구조 안전성·설비 간섭 해결은 주장하지 않는다.
- A/B의 실제 출력 없이도 계약 예시로 단위 테스트를 먼저 작성하고, 병합 뒤 합성 샘플로 통합 재검증한다.
- PR을 통한 통합, 실제 검증 명령과 결과, 남은 위험을 `CURRENT_STATE.md`에 기록한다.
