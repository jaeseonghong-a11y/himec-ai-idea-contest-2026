# 팀장 AI 새 작업 배정 요청문

아래 코드블록 내부를 수정하지 말고 팀장이 사용하는 AI에 그대로 붙여넣는다.

```text
HIMEC 공모전 저장소에서 새 작업을 기다리는 팀원에게만 다음 브랜치와 이슈를 배정해줘. 다른 팀원의 열린 PR이나 작업 브랜치는 유지해.

AGENTS.md, START_HERE.md, BRANCH_ASSIGNMENTS.md, CURRENT_STATE.md, docs/TEAM_WORKFLOW.md와 git status/diff/log를 읽고, 원격 main, 팀원별 활성 브랜치·PR·이슈·권한을 확인해.

각 팀원별로 다음을 판단해:
1. 아직 자신의 PR이 열려 있거나 현재 브랜치 작업 중이면 새 브랜치를 만들지 마.
2. 자신의 이전 PR이 병합됐고 다음 작업이 확정됐으면, 그 사용자에게만 사용하지 않은 다음 rNN 이름을 배정해. 다른 팀원의 rNN과 같을 필요는 없어.
3. 다음 작업은 확정된 프로젝트 범위와 열린 이슈에서 고르고 담당 파일·완료 기준을 명확히 해. 선택이 제품 방향을 바꾸거나 작업이 불명확하면 나에게 필요한 결정만 물어봐.
4. BRANCH_ASSIGNMENTS.md와 CURRENT_STATE.md를 팀장 전용 브랜치에서 갱신하고 PR로 최신 main에 squash 병합해. 관리자 권한은 검토한 PR 병합에만 쓰고 main 직접 push·force push는 하지 마.
5. 그 최종 origin/main SHA에서 해당 팀원의 새 원격 브랜치를 만들어. 기존 브랜치를 삭제·재사용·덮어쓰지 말고 새 브랜치가 main과 같은 SHA인지 검증해.

마지막에는 새로 배정한 팀원별 이슈·브랜치, 그대로 유지한 팀원과 그 이유, main SHA, 사용자가 결정할 사항을 알려줘.
```
