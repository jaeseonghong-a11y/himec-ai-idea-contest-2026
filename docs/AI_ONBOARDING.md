# AI 작업 요청 위치

편집 없이 그대로 붙여넣는 요청문은 `prompts/README.md`에서 상황별로 찾는다.

- 팀원 최초 시작: `prompts/TEAM_FIRST_START.md`
- 팀원 병합 요청: `prompts/TEAM_REQUEST_MERGE.md`
- 팀원 병합 후 새 작업: `prompts/TEAM_AFTER_MERGE.md`
- 팀원 열린 PR 수정: `prompts/TEAM_REVISE_OPEN_PR.md`
- 팀원 작업 중 막힘: `prompts/TEAM_BLOCKED.md`
- 팀원 다음 라운드: `prompts/TEAM_NEXT_ROUND.md`
- 팀장 새 작업 배정: `prompts/OWNER_OPEN_ROUND.md`
- 팀장 PR 병합과 병합된 팀원 후속 배정: `prompts/OWNER_MERGE_AND_NEXT_ROUND.md`

팀원에게 Git 명령을 따로 설명하지 않는다. 팀원은 GitHub 초대 수락과 로그인만 직접 하고, 나머지는 자신의 AI가 저장소 문서에 따라 처리하게 한다.

모든 프롬프트는 현재 로그인된 GitHub 사용자명, `BRANCH_ASSIGNMENTS.md`, 열린 이슈와 PR을 AI가 직접 확인하도록 작성되어 있다. 팀원이 브랜치명이나 작업명을 직접 편집해 넣지 않는다.

팀원이 병합 요청 프롬프트를 쓰면 AI는 PR에 팀장 검토 요청을 남긴다. 실제 병합은 팀장 AI가 담당한다. 한 팀원의 PR이 병합되면 다른 팀원의 PR 진행 여부와 관계없이 그 팀원에게 다음 브랜치를 배정할 수 있다.
