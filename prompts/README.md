# 상황별 AI 요청문

이 파일들은 코드블록 내부를 편집하지 않고 각자 AI에 붙여넣는다. AI가 현재 GitHub 계정, 원격 배정표, 이슈와 PR을 직접 확인한다.

| 상황 | 팀원이 붙여넣을 파일 | 팀장이 붙여넣을 파일 |
|---|---|---|
| 저장소 첫 시작 | `TEAM_FIRST_START.md` | — |
| 맡은 작업 완료, 병합 요청 | `TEAM_REQUEST_MERGE.md` | `OWNER_MERGE_AND_NEXT_ROUND.md` |
| 열린 PR에 리뷰·수정 요청 | `TEAM_REVISE_OPEN_PR.md` | `OWNER_MERGE_AND_NEXT_ROUND.md` |
| 내 PR 병합 후 추가 작업 | `TEAM_AFTER_MERGE.md` | `OWNER_OPEN_ROUND.md` |
| 이미 배정된 새 브랜치에서 시작 | `TEAM_NEXT_ROUND.md` | — |
| 인증·권한·충돌·환경 문제 | `TEAM_BLOCKED.md` | 문제 보고를 받은 뒤 해당 PR·이슈 검토 |

팀원은 병합 요청을 할 수 있지만 실제 `main` 병합과 새 원격 브랜치 생성은 팀장 AI만 한다. 한 팀원의 PR이 병합되면 다른 팀원의 PR을 기다리지 않고 그 팀원에게 다음 작업을 배정할 수 있다.
