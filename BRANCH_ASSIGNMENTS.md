# 현재 브랜치 배정

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
