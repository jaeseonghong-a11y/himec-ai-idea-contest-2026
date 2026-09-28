# 팀원 AI 다음 라운드 요청문

아래 코드블록 내부를 수정하지 말고 팀원이 사용하는 AI에 그대로 붙여넣는다.

```text
HIMEC 공모전 저장소에서 내 다음 작업 라운드를 시작해줘.

먼저 현재 저장소 위치와 GitHub 로그인 계정을 확인하고, AGENTS.md, START_HERE.md, CURRENT_STATE.md, docs/TEAM_WORKFLOW.md를 읽어. origin을 fetch한 뒤 `origin/main`의 BRANCH_ASSIGNMENTS.md를 읽어. 로컬 문서보다 원격 main 배정표를 기준으로 삼아.

현재 로그인된 GitHub 사용자명으로 배정표에서 내 활성 브랜치를 자동으로 찾아. 먼저 이전 PR의 MERGED 상태와 새 원격 브랜치가 실제 존재하는지 확인해. 아직 내 새 브랜치나 담당 이슈가 없으면 팀장에게 요청할 내용을 알려주고 멈춰. 배정이 있으면 팀장이 만든 해당 원격 브랜치를 checkout한 뒤 fast-forward 방식으로 최신화해. 이전 라운드 브랜치를 재사용하거나 임의의 브랜치를 만들지 마.

main은 읽기 전용 기준선이다. main을 수정·commit·push·merge·rebase·reset하지 마. 다른 팀원의 브랜치도 수정하지 마.

내게 배정된 열린 GitHub 이슈와 브랜치 담당 범위를 확인하고 작업·검증·기록을 완료해. 담당 이슈가 없거나 공통 파일 충돌 가능성이 있으면 임의로 진행하지 말고 팀장에게 필요한 결정을 알려줘.

완료 후 내 변경만 commit하고 할당 브랜치에 push한 다음 base가 main인 PR을 만들어. PR 설명에 변경 내용, 검증 결과, 미검증 사항, 충돌 가능성을 적어. PR을 직접 merge·close하지 말고 브랜치를 삭제하거나 다음 브랜치를 만들지 말고 멈춰.

마지막에는 사용한 브랜치, 담당 이슈, commit SHA, PR URL, 검증 결과, 팀장 결정이 필요한 항목만 알려줘.
```
