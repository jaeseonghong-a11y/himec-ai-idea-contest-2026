# 현재 브랜치 배정

2026-09-30 기준: 김기준 팀원의 `r03` 작업은 [PR #57](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/pull/57)로 보완·병합됐다. 원본 [PR #56](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/pull/56)은 같은 내용을 포함한 통합 PR의 중복이므로 닫았다. #17 합성 입력 산출물은 아직 없으므로 다음 `work/kijun-0108/r04`에서 계속한다. `archuni`의 서로 다른 과제 PR #34·#50은 그대로 열려 있다.

## AutoCAD 2024 호환 작업 — archuni 별도 과제 (2026-09-29)

| 담당 | 지정 브랜치 | 이슈 | 담당 파일 |
|---|---|---|---|
| `archuni` | `work/archuni/r03` (팀장 생성) | [#35 AutoCAD 2024 전용 플러그인](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/issues/35) | `autocad-plugin/`의 2024 전용 프로젝트·번들·설치/시험 문서. 공유 코어 변경 시 2026 회귀 검사 필수 |

기존 `work/archuni/r02`의 [PR #34](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/pull/34)는 별도로 열려 있다. 두 과제는 서로 다른 clone/worktree에서 작업하고, r02 변경을 r03에 복사하거나 r02 브랜치를 새 과제에 재사용하지 않는다. 2024용 배포는 2026용과 공존하게 만든다. 시작 요청문은 `prompts/TEAM_AUTOCAD_2024_START.md`다.

## Round 02 — 설계 변경 피드백 루프 (2026-09-29)

기준: `docs/PROJECT_BRIEF.md`, `prototype/CONTRACT.md`. `r02` 브랜치들은 2026-09-29 `main`의 `14f199e`에서 출발했으나, 병합된 김기준 브랜치는 2026-09-30 정리됐다. 아래에서 실제 원격 존재 여부를 확인하고, 옛 `r01` 브랜치를 재사용하거나 팀원이 직접 새 브랜치를 만들지 않는다. 시작 요청문은 `prompts/ROUND_02_START.md`에 있다.

| 담당 | 지정 브랜치 | 새 이슈 | 담당 파일 |
|---|---|---|---|
| `kijun-0108` | `work/kijun-0108/r04` (이 문서 병합 후 최신 `main`에서 생성) | [#17 합성 도면·대본·사이드카](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/issues/17)는 PR #57의 관계도 기능과 별개 | `prototype/samples/`, `prototype/sidecar/`의 합성 산출물만 담당. `prototype/relation-editor/`는 이번 작업에서 변경하지 않음 |
| `archuni` | `work/archuni/r02` — [PR #34 열림](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/pull/34) | [#18 변경지시 추출·PDF 주석·승인](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/issues/18) | `prototype/extract/`, `prototype/annotate/` |
| `ehgudwns18` | `work/ehgudwns18/r02` — 원격 존재, 아직 작업 커밋 없음 | [#20 경량 관계 그래프](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/issues/20) | `prototype/graph/` |
| `jaeseonghong-a11y` | 팀장 전용 작업 브랜치 | [#19 합성 DXF 전파·검사](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/issues/19), [#25 AutoCAD 플러그인 v0](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/issues/25) | `prototype/propagate/`, `autocad-plugin/`, 통합·제출 문서 |

Round 01 조사 결과 중 병합된 것은 `main`과 PR 기록에 남아 있다. 닫혔지만 병합되지 않은 PR #14의 고유 내용은 `archive/archuni-r01-20260930` 태그로 보존하고 옛 브랜치를 삭제했다. 아이디어 확정 전 후보 평가(`#7`, `#8`, PR `#14`)는 새 방향으로 대체되어 2026-09-29 이유를 남기고 종료했다. #9/PR #13의 구현 경로 조사는 이미 `main`에 반영했다.

팀원과 AI는 이 표의 브랜치를 임의로 바꾸거나 새로 만들지 않는다. 팀장 AI만 라운드를 갱신한다.

## 옛 브랜치 정리 기록

2026-09-30 병합 완료 PR의 브랜치 31개, 내용이 `main`에 이미 있는 `ehgudwns18/r01`, 태그로 보존한 `archuni/r01`을 삭제했다. 브랜치 삭제는 병합된 `main` 커밋·PR 기록·Release·보존 태그를 삭제하지 않는다. 열린 PR #34·#50의 브랜치와 현재 배정된 `ehgudwns18/r02`는 유지한다. 김기준 `r03`은 PR #57에 통합돼 종료됐고 원격 이력은 보존한다. `r04`는 #17 작업을 위해 최신 `main`에서 새로 만든다.

## 상태 규칙

- `브랜치 준비`: 원격 브랜치는 준비됐지만 담당 이슈 확인이 필요
- `작업 중`: 팀원 AI가 작업 중
- `PR 열림`: 팀장 AI 검토 대기
- `병합 완료`: 해당 라운드 종료
- `보류`: 충돌 또는 결정 대기

담당 이슈가 없으면 팀원 AI는 임의로 작업을 만들지 않고 팀장에게 배정을 요청한다.

팀원별 라운드 번호는 서로 다를 수 있다. 병합을 마친 팀원에게 새 일을 줄 때 팀장 AI는 그 팀원의 새 `rNN` 브랜치와 이슈를 최신 `main`에서 배정하고, 다른 팀원의 활성 브랜치는 그대로 둔다. 팀원 AI는 fetch 후 `origin/main`의 이 표를 읽어 현재 배정을 확인한다.
