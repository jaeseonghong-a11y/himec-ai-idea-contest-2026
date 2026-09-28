# 02. 팀 GitHub 브랜치·PR·병합

## 기본 구조

- `main`: 검증을 통과한 공유 기준선. 직접 push·force push는 팀 규칙으로 금지합니다.
- 작업 브랜치: 한 이슈 또는 작은 기능. 예: `feat/drawing-import`, `fix/undo-state`.
- Pull Request(PR): 브랜치를 main에 합쳐 달라는 요청과 리뷰·CI 기록.
- 담당자/AI: 팀장이 “PR #번호를 병합해”라고 요청한 범위에서 검토부터 병합까지 수행합니다.

Git은 같은 줄의 충돌을 자동 해결하지 못할 수 있습니다. **충돌이 없어도** 공유 인터페이스나 설정의 의미가 어긋나면 기능이 깨질 수 있으므로 통합 검증이 필요합니다.

## 팀원: 브랜치 생성부터 PR까지

PowerShell 예시입니다.

```powershell
git status --short
git switch main
git pull --ff-only origin main
git switch -c feat/drawing-import
# 작은 기능 구현 후 프로젝트 검증 명령 실행
git add <내가_바꾼_경로>
git diff --cached
git commit -m "feat: 도면 가져오기 추가"
git push -u origin feat/drawing-import
gh pr create --base main --head feat/drawing-import --fill
```

`git status --short`에 기존 변경이 있으면 소유자를 확인합니다. 다른 사람의 변경을 `git add -A`로 함께 담지 않습니다. `gh`가 없다면 GitHub 웹에서 **Compare & pull request**를 누릅니다. PR에는 변경 이유, 영향받는 CAD 버전, 검증 명령·실기 결과, 스크린샷/샘플 도면, 미검증 사항을 씁니다.

작업 중 main이 바뀌면 `git fetch origin` 후 팀이 정한 방법으로 브랜치를 갱신합니다. 기본은 `git merge origin/main`입니다. 공동 작업 중인 브랜치의 커밋을 `rebase`·force push로 바꾸는 일은 피합니다.

## 담당자/AI: 한 PR 검토·병합

1. PR 번호, 대상 브랜치, 작성자, 최신 커밋 SHA를 확인합니다. `git status --short`로 현재 미커밋 변경을 기록합니다. 더러운 작업 트리를 reset/stash하지 말고 **별도 worktree 또는 clone**에서 검토합니다.
2. `git fetch origin --prune`, `gh pr view <번호>`, `gh pr diff <번호>`, `gh pr checks <번호>`로 변경·리뷰·CI를 확인합니다.
3. 예상치 못한 삭제, 비밀값, 의존성, CAD host API·명령 등록·설치/배포 변경을 검사합니다.
4. 실패한 CI와 리뷰 의견을 해결합니다. CI가 아직 없다면 로컬 검증과 실제 AutoCAD smoke test를 실행하고 검증 범위를 명시합니다.
5. 최신 main과 통합해 충돌과 **의미상의 충돌**을 확인합니다. 두 기능이 함께 동작하는지 시험합니다.
6. 요구된 승인·CI가 모두 끝나면 팀이 정한 전략으로 병합합니다. 기본은 squash merge를 권장합니다. 개별 커밋 기록을 보존해야 하면 merge commit을 선택합니다.
7. 병합 후 main을 최신화하고 커밋 SHA·검증·남은 리스크를 기록합니다.

```powershell
gh pr view 123
gh pr diff 123
gh pr checks 123 --watch
# 승인·검증 완료 후
gh pr merge 123 --squash --delete-branch --match-head-commit <검토한_SHA>
git switch main
git pull --ff-only origin main
```

`--match-head-commit`은 리뷰 후 다른 커밋이 추가된 PR을 실수로 병합하지 않게 합니다. 실제 권한·보호 규칙을 우회하지 않습니다. [GitHub CLI 매뉴얼](https://cli.github.com/manual/gh_pr_merge).

## 충돌 해결

1. PR 브랜치를 **분리된 작업 디렉터리**에서 엽니다. `gh pr checkout <번호> --worktree <새_경로>`를 사용할 수 있습니다.
2. 그 디렉터리에서 `git fetch origin`, `git merge origin/main`을 실행합니다. `git status --short`로 충돌 파일을 확인합니다.
3. `<<<<<<<`, `=======`, `>>>>>>>` 양쪽 변경의 의도를 읽고 통합합니다. `ours`/`theirs` 전체 선택을 근거 없이 사용하지 않습니다.
4. `git diff --check`, 빌드·테스트·AutoCAD 실행·Undo 테스트 후 충돌 해결 커밋을 PR 브랜치에 push합니다. CI와 승인 상태가 다시 바뀌었는지 확인합니다.
5. 팀원 브랜치에 push 권한이 없거나 제품 결정이 필요한 충돌이면 해결안을 PR에 남기고 담당자의 답을 받습니다.

```powershell
gh pr checkout 123 --worktree ..\review-pr-123
Set-Location ..\review-pr-123
git fetch origin
git merge origin/main
git status --short
# 충돌 파일 수정 → git add <해결한_파일> → git commit → git push
```

Worktree 경로는 실제 저장소 밖의 **빈 경로**로 바꿉니다. 정리 전에는 그곳에 사용자 파일이 없는지 확인합니다. [GitHub 충돌 해결 가이드](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/resolving-a-merge-conflict-using-the-command-line).

## 되돌리기

- PR 병합 전: 병합 보류, 브랜치 수정.
- 병합 후: 새 수정 PR 또는 해당 변경을 **새 커밋으로 되돌리는** PR. 공유 main에 `git reset --hard`·force push 금지.
- 배포 후: 정상 릴리스로 롤백하고 코드·배포 이력을 함께 기록.

## 충돌을 줄이는 팀 약속

- 작업 전에 이슈에 담당자와 예상 변경 파일을 적습니다.
- 공통 인터페이스·설정·CAD 명령 등록·설치 프로그램은 담당자를 한 명으로 정합니다.
- 큰 작업은 인터페이스 계약 PR과 구현 PR로 나눕니다.
- PR을 작게 유지하고 자주 main을 동기화합니다.
- AI 도구 두 개가 같은 작업 트리에서 같은 파일을 동시에 편집하지 않게 합니다. 병행 시 별도 worktree를 씁니다.
