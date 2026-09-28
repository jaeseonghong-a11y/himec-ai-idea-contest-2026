# 팀장 통합형 AI 협업 시작 안내

이 프로젝트는 팀장 `jaeseonghong-a11y`만 `main`을 통합하고, 다른 팀원은 팀장이 만든 전용 브랜치에서 AI로 작업하는 방식으로 운영한다.

## 팀원이 직접 해야 하는 일

1. GitHub 초대 수락
2. GitHub 로그인 또는 AI가 요청하는 인증 승인
3. 팀원용 프롬프트를 자신의 AI에 그대로 붙여넣기

Git clone, fetch, checkout, pull, commit, push, PR 생성은 팀원 AI가 처리한다. 팀원은 브랜치명을 만들거나 Git 명령을 직접 입력할 필요가 없다.

## 팀원이 AI에 붙여넣을 파일

- 처음 참여할 때: `prompts/TEAM_FIRST_START.md`
- 작업을 끝내고 병합 요청할 때: `prompts/TEAM_REQUEST_MERGE.md`
- 병합된 뒤 새 작업을 원할 때: `prompts/TEAM_AFTER_MERGE.md`
- 새 브랜치가 배정된 뒤 시작할 때: `prompts/TEAM_NEXT_ROUND.md`
- 리뷰 수정 또는 작업 중 막혔을 때: `prompts/README.md`에서 해당 상황을 선택

## 팀장이 AI에 붙여넣을 파일

- 작업 라운드를 열 때: `prompts/OWNER_OPEN_ROUND.md`
- 팀원 PR을 검토·병합하고 후속 작업을 배정할 때: `prompts/OWNER_MERGE_AND_NEXT_ROUND.md`

## 안전 경계

- 팀원 AI는 `main`을 수정하거나 병합하지 않는다.
- 팀원 AI는 지정 브랜치에 push하고 PR을 만든 뒤 멈춘다.
- 팀장 AI는 PR을 하나씩 검토하고 충돌·검증을 확인한 뒤 안전한 것만 병합한다.
- 팀장 AI는 병합된 팀원에게 최신 `main`에서 다음 브랜치를 만든다. 다른 팀원의 열린 PR은 유지한다.
- 작성된 개인정보·서명 문서는 Git에 올리지 않는다.

공개 저장소의 활성 Ruleset이 팀원의 `main` 갱신·삭제·강제 push를 서버에서 차단한다. 각자의 작업 브랜치에서 push하고 PR을 연 뒤 팀장 통합을 기다린다. 작성된 참가 서류와 비밀값은 공개 저장소와 Git 이력에 올리지 않는다.
