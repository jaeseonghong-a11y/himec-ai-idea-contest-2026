# 팀장 통합형 GitHub 작업 절차

## 역할

- 팀장·저장소 소유자: `jaeseonghong-a11y`
- 팀원: `archuni`, `ehgudwns18`, `kijun-0108`
- `main` 통합 권한: 팀장 또는 팀장이 명시적으로 실행시킨 AI만 사용
- 팀원 AI: 지정 브랜치 작업, push, PR 생성까지만 수행

## 팀원별 작업 순환

1. 팀장 AI가 최신 `origin/main`에서 팀원별 `work/<사용자명>/rNN` 브랜치를 만든다.
2. 팀장 AI가 `BRANCH_ASSIGNMENTS.md`에 사용자별 활성 브랜치·이슈·담당 경로를 기록한다.
3. 팀원은 각자 AI에 `prompts/TEAM_FIRST_START.md` 또는 `prompts/TEAM_NEXT_ROUND.md`를 그대로 붙여넣는다.
4. 팀원 AI는 자신의 GitHub 계정을 감지하고 할당된 브랜치만 checkout한다.
5. 팀원 AI는 해당 브랜치를 `origin`에서 최신화한 뒤 작업·검증·commit·push한다.
6. 팀원 AI는 `main` 대상 PR을 만들고 멈춘다. 병합·브랜치 삭제·다음 브랜치 생성은 하지 않는다.
7. 팀원은 병합을 원할 때 `prompts/TEAM_REQUEST_MERGE.md`를 AI에 붙여넣어 PR 상태와 병합 요청을 남긴다.
8. 팀장은 `prompts/OWNER_MERGE_AND_NEXT_ROUND.md`를 AI에 붙여넣고 병합 요청이 온 PR을 순차 검토한다.
9. 안전한 PR만 squash merge하고 `main` 통합 검증을 실행한다.
10. 병합이 끝난 팀원은 다른 팀원의 PR이 열려 있어도 다음 작업을 받을 수 있다. 팀장 AI가 그 팀원에게만 최신 `main` 기반 새 `rNN` 브랜치와 이슈를 배정한다. 미병합 팀원은 기존 브랜치를 유지한다.

각 팀원의 라운드 번호가 서로 달라도 정상이다. `rNN`은 사용자별로 증가한다. `BRANCH_ASSIGNMENTS.md`는 현재 팀원별 활성 배정을 나타내며, 과거 브랜치와 PR은 GitHub 이력으로 추적한다. 팀원 AI는 로컬 문서가 오래됐을 수 있으므로 fetch 후 `origin/main`의 배정표를 확인한다.

## pull과 push의 의미

- `pull`: GitHub에 있는 브랜치의 최신 변경을 팀원 PC로 가져온다.
- `push`: 팀원 PC의 commit을 GitHub 작업 브랜치로 올린다.
- `merge`: 작업 브랜치의 변경을 `main`에 통합한다. 이 프로젝트에서는 팀장 AI만 수행한다.

팀원은 병합된 이전 브랜치를 억지로 최신화하지 않는다. 팀장 AI가 최신 `main`에서 새 브랜치를 만들면 팀원 AI가 fetch·checkout해 작업한다. 기존 브랜치를 삭제 후 같은 이름으로 재사용하지 않는다.

## 충돌 처리

- 팀장 AI는 PR을 한 번에 합치지 않고 하나씩 검토·병합한다.
- 먼저 병합된 PR 때문에 다음 PR이 충돌하면 별도 worktree에서 양쪽 의도를 비교한다.
- 자동 해결이 확실하지 않거나 제품 결정이 필요한 충돌은 병합하지 않고 팀장에게 질문한다.
- `ours` 또는 `theirs`로 전체 파일을 근거 없이 덮지 않는다.
- 병합 후 다음 PR을 검토하기 전에 `main` 통합 검증을 다시 실행한다.

## 현재 GitHub 보호 설정

2026-09-29 저장소를 공개로 전환하고 `main` 대상 Ruleset [`Protect main - owner merges`](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/rules/24130976)을 활성화했다. GitHub API에서 적용 규칙 5개와 권한을 확인했다.

- 적용 대상: `refs/heads/main`만. 팀원별 `work/<사용자명>/rNN` 브랜치에는 적용되지 않는다.
- `Restrict updates`: 관리자 역할만 우회하여 `main`을 갱신할 수 있다. 현재 관리자 계정은 `jaeseonghong-a11y`이고 세 팀원은 Write 권한이다.
- `Restrict deletions`, `Block force pushes`, `Require linear history`, `Require a pull request before merging` 적용. 병합 방법은 squash만 허용한다.
- 관리자 우회 방식은 `Always allow`다. 실제 PR #10에서 일반 squash 병합은 차단되고 팀장 계정의 `--admin` 병합으로 성공했다. 팀장 AI는 검토를 끝낸 PR에만 관리자 병합 권한을 사용한다. 직접 push는 프로젝트 규칙상 금지다.
- 팀원은 지정 브랜치에 push하고 PR을 만든 뒤 멈춘다. Ruleset 변경 권한은 관리자에게만 있다.

공개 저장소이므로 코드와 이력이 누구에게나 보인다. 개인정보가 기입된 신청서, 서명, 연락처, 토큰, 고객 자료는 `submission-private/` 또는 저장소 밖에 둔다.

## 마감일 운영

- 공통 파일(`PROJECT_BRIEF`, 발표 본문, 데이터 계약, 빌드 설정)은 동시에 편집하지 않고 한 명이 통합한다.
- 긴 기능보다 제출에 직접 기여하는 작은 PR을 우선한다.
- 최종 제출 후보 커밋을 태그하고, 제출 파일의 해시와 제출 여부를 별도로 기록한다.
- GitHub에 병합된 것과 실제 공모전 제출 완료는 구분한다. 계정 로그인, 동의, 최종 제출 버튼은 담당자가 직접 확인한다.
