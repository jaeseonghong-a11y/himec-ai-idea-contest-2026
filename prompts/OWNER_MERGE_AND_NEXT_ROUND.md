# 팀장 AI PR 병합 및 다음 작업 요청문

아래 코드블록 내부를 수정하지 말고 팀장이 사용하는 AI에 그대로 붙여넣는다.

```text
HIMEC 공모전 저장소에서 팀원이 병합을 요청한 PR을 검토해 안전하면 순서대로 main에 통합하고, 병합된 팀원에게 확정된 다음 일이 있다면 새 브랜치까지 준비해줘. 이 요청은 검증을 통과한 팀원 PR의 squash merge를 승인하지만 배포나 공모전 제출은 승인하지 않는다.

AGENTS.md, START_HERE.md, BRANCH_ASSIGNMENTS.md, CURRENT_STATE.md, docs/TEAM_WORKFLOW.md와 git status/diff/log를 읽고 GitHub의 열린 PR·댓글·리뷰·checks·최신 head SHA를 확인해.

규칙:
1. 저장소 소유자 jaeseonghong-a11y만 main 통합 담당이다. 다른 팀원의 기존 브랜치와 미커밋 작업을 삭제하거나 덮어쓰지 마.
2. 병합 요청이 온 PR부터 검토해. 여러 PR을 한꺼번에 병합하지 말고 의존성과 파일 겹침을 분석해 안전한 순서를 정해.
3. 각 PR의 작성자, base/main, head 브랜치와 최신 SHA, diff, 예상치 못한 삭제, 비밀값·개인정보, 출처, 실제 검증 결과를 확인해.
4. 더러운 작업 트리는 reset이나 stash로 없애지 말고 별도 worktree에서 검토해.
5. 최신 main과의 Git 충돌뿐 아니라 내용상 충돌도 검사해. 제품 결정이 필요하거나 한쪽 의도를 확신할 수 없으면 해당 PR은 보류하고 내게 질문해.
6. 검토한 SHA와 현재 PR SHA가 같은지 다시 확인한 후 안전한 PR만 squash merge해. 이 Ruleset은 팀장 계정의 일반 병합도 막으므로 GitHub CLI에서 필요하면 `gh pr merge <번호> --squash --admin`으로 관리자 권한을 사용해. 직접 push나 force push는 하지 마.
7. 한 PR을 병합할 때마다 main을 fast-forward로 최신화하고 통합 검증 후 다음 PR을 검토해. 병합하지 못한 PR과 브랜치는 그대로 두고 이유와 필요한 수정 사항을 남겨.
8. 병합된 팀원에게 다음 작업이 확정됐으면 그 팀원만 새 rNN 브랜치를 받을 수 있다. 다른 팀원의 열린 PR은 새 배정을 막지 않는다. 다만 해당 팀원의 열린 PR이나 미완료 작업이 남아 있으면 새 브랜치를 만들지 마.
9. 새 배정이 필요하면 담당 이슈와 파일 경계를 정하고 BRANCH_ASSIGNMENTS.md·CURRENT_STATE.md를 팀장 전용 PR로 먼저 최신 main에 통합해. 그 최종 origin/main SHA에서 아직 쓰지 않은 팀원별 새 원격 브랜치를 만들고 SHA 일치를 확인해. 브랜치 이름 재사용·삭제·force push는 금지한다.
10. 다음 일이 불명확하거나 제품 결정을 요구하면 임의로 발명하지 말고 후보와 필요한 결정만 나에게 알려줘. 병합 자체는 안전한 PR부터 계속 처리해.

마지막에는 병합한 PR·merge SHA, 보류한 PR·이유, 실행한 검증, 최신 main SHA, 새로 만든 팀원별 브랜치·이슈, 사용자가 결정할 항목을 보고해.
```
