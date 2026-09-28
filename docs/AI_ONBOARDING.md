# AI 작업 시작 프롬프트

팀원이 사용하는 AI 도구에 아래 프롬프트를 전달한다.

```text
이 저장소는 제1회 HIMEC AI 활용 아이디어 공모전 출품 프로젝트다.
먼저 AGENTS.md, CURRENT_STATE.md, docs/PROJECT_BRIEF.md,
sources/SOURCE_INDEX.md와 현재 git status/diff/log를 읽어.

공식 사실은 SRC-001~004에 근거하고, 팀 분석·가정과 구분해.
확인되지 않은 하이멕 내부 업무·데이터·성과 수치는 만들지 마.
작성된 참가서류, 연락처, 생년월일, 서명 등 개인정보는 Git에 올리지 마.

이번 작업은 [작업명], 담당 경로는 [경로], 완료 기준은 [기준]이다.
본인 브랜치에서 작은 변경으로 수행하고 실제 검증 결과와 미검증을
CURRENT_STATE.md에 기록해. 커밋·push·PR은 AGENTS.md 규칙을 따라.
```

## 역할별 첫 브랜치 예시

- `research/problem-evidence`: 문제·현장 근거와 출처
- `feat/prototype`: 최소 사용자 경로 프로토타입
- `docs/proposal`: 붙임 4 제안서 초안
- `docs/presentation`: 발표/설명 자료
- `chore/submission-qa`: 출처·권리·제출 패키지 점검

실제 담당자가 정해지면 동시에 같은 파일을 고치지 않도록 이슈에 담당 경로를 적는다.
