# 현재 브랜치 배정

## Round 02 — 설계 변경 피드백 루프 (2026-09-29)

기준: `docs/PROJECT_BRIEF.md`, `prototype/CONTRACT.md`. 아래 `r02` 브랜치는 팀장이 2026-09-29 `main`의 `14f199e`에서 생성했고 원격 존재를 확인했다. 기존 `r01` 브랜치를 새 과제용으로 재사용하거나 팀원이 직접 새 브랜치를 만들지 않는다. 새 라운드 시작 요청문은 `prompts/ROUND_02_START.md`에 있다.

| 담당 | 지정 브랜치 | 새 이슈 | 담당 파일 |
|---|---|---|---|
| `kijun-0108` | `work/kijun-0108/r02` (생성됨) | [#17 합성 도면·대본·사이드카](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/issues/17) | `prototype/samples/`, `prototype/sidecar/` |
| `archuni` | `work/archuni/r02` (생성됨) | [#18 변경지시 추출·PDF 주석·승인](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/issues/18) | `prototype/extract/`, `prototype/annotate/` |
| `ehgudwns18` | `work/ehgudwns18/r02` (생성됨) | [#20 경량 관계 그래프](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/issues/20) | `prototype/graph/` |
| `jaeseonghong-a11y` | 팀장 전용 작업 브랜치 | [#19 승인된 DXF 변경 전파·검사](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/issues/19) | `prototype/propagate/`, 통합·제출 문서 |

Round 01의 조사 결과와 브랜치는 삭제하지 않는다. 아이디어 확정 전 후보 평가(`#7`, `#8`, PR `#14`)는 새 방향으로 대체되어 2026-09-29 이유를 남기고 종료했다. #9/PR #13의 구현 경로 조사는 이미 `main`에 반영했다.

팀원과 AI는 이 표의 브랜치를 임의로 바꾸거나 새로 만들지 않는다. 팀장 AI만 라운드를 갱신한다.

## 팀원별 활성 배정 — 초기 Round 01

- 초기 기준선: 첫 `r01` 원격 브랜치들은 생성 당시 같은 `main`에서 출발했다. 이후 PR과 `main`이 진행됐으므로 현재 SHA는 같지 않을 수 있다.
- 현재 상태는 아래 표와 GitHub PR·이슈의 실제 상태를 함께 확인한다.

| GitHub 사용자 | 할당 브랜치 | 담당 이슈 | 상태 |
|---|---|---|---|
| `archuni` | `work/archuni/r01` | [#7 현장 문제 후보와 사용자 시나리오](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/issues/7), `docs/candidates/field-problems.md` | [PR #14 수정 요청](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/pull/14) |
| `ehgudwns18` | `work/ehgudwns18/r01` | [#8 아이디어 비교와 평가 적합성](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/issues/8), `docs/candidates/idea-comparison.md` | 브랜치 준비 |
| `kijun-0108` | `work/kijun-0108/r01` | [#9 최소 데모 구현 경로](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/issues/9), `docs/candidates/prototype-feasibility.md` | [PR #13 병합 완료](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/pull/13), 다음 배정 대기 |

## 상태 규칙

- `브랜치 준비`: 원격 브랜치는 준비됐지만 담당 이슈 확인이 필요
- `작업 중`: 팀원 AI가 작업 중
- `PR 열림`: 팀장 AI 검토 대기
- `병합 완료`: 해당 라운드 종료
- `보류`: 충돌 또는 결정 대기

담당 이슈가 없으면 팀원 AI는 임의로 작업을 만들지 않고 팀장에게 배정을 요청한다.

팀원별 라운드 번호는 서로 다를 수 있다. 병합을 마친 팀원에게 새 일을 줄 때 팀장 AI는 그 팀원의 새 `rNN` 브랜치와 이슈를 최신 `main`에서 배정하고, 다른 팀원의 활성 브랜치는 그대로 둔다. 팀원 AI는 fetch 후 `origin/main`의 이 표를 읽어 현재 배정을 확인한다.
