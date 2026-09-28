# 팀장 AI PR 병합 및 다음 라운드 요청문

아래 코드블록 내부를 수정하지 말고 팀장이 사용하는 AI에 그대로 붙여넣는다.

```text
이 저장소의 열린 팀원 Pull Request를 안전하게 검토·통합하고, 가능한 경우 다음 작업 라운드까지 준비해줘. 이 요청은 검증을 통과한 팀원 PR의 squash merge를 승인하지만 배포나 공모전 제출은 승인하지 않는다.

AGENTS.md, START_HERE.md, BRANCH_ASSIGNMENTS.md, CURRENT_STATE.md, docs/TEAM_WORKFLOW.md와 현재 git status/diff/log를 읽고, GitHub의 열린 PR·리뷰·checks·최신 head SHA를 확인해.

규칙:
1. 저장소 소유자 jaeseonghong-a11y만 main 통합 담당이다.
2. 팀원 PR을 한꺼번에 병합하지 말고, 의존성과 변경 파일 겹침을 분석해 안전한 순서를 정한 뒤 하나씩 처리해.
3. 각 PR의 작성자, base/main, head 브랜치, 최신 SHA, diff, 예상치 못한 삭제, 비밀값·개인정보, 출처, 테스트를 확인해.
4. 더러운 작업 트리는 reset이나 stash로 없애지 말고 별도 worktree에서 검토해.
5. 최신 main과 충돌 및 의미상의 충돌을 검사하고 통합 검증을 실행해. 충돌 해결에 제품 결정이 필요하거나 한쪽 의도를 확신할 수 없으면 해당 PR은 병합하지 말고 나에게 질문해.
6. 검토한 SHA와 현재 PR SHA가 같은지 다시 확인한 후 안전한 PR만 squash merge해. 이 Ruleset은 팀장 계정의 일반 병합도 막으므로 GitHub CLI에서 필요하면 `gh pr merge <번호> --squash --admin`으로 관리자 권한을 사용해. 이 권한은 검토를 끝낸 PR 병합에만 사용하고 직접 push나 force push는 하지 마.
7. 한 PR을 병합할 때마다 main을 fast-forward로 최신화하고 통합 검증 후 다음 PR을 검토해.
8. 병합하지 못한 PR은 이유와 필요한 수정 사항을 남기고 유지해. 팀원 브랜치를 임의로 삭제하지 마.
9. 안전한 PR 처리가 모두 끝나고 열린 팀원 PR이 없을 때만 다음 라운드를 준비해.
10. 다음 라운드는 최신 origin/main에서 사용하지 않은 새 rNN 브랜치를 팀원별로 만들고, 기존 라운드 이름을 재사용하지 마.
11. BRANCH_ASSIGNMENTS.md와 CURRENT_STATE.md를 다음 라운드 상태로 갱신하고 팀장 전용 PR로 main에 통합한 다음, 새 팀원 브랜치가 최종 main SHA에서 출발하는지 검증해.

마지막에는 병합한 PR과 merge SHA, 보류한 PR과 이유, 실행한 검증, 최신 main SHA, 다음 라운드의 팀원별 브랜치·이슈, 사용자 결정이 필요한 항목을 보고해.
```
