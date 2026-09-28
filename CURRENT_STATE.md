# CURRENT_STATE.md — 최신 인수인계

> 매 세션 시작·종료 시 갱신한다. 최신 상태와 최근 체크포인트 3개만 남기고 오래된 내용은 `docs/archive/`에 보관한다.

## 현재 상태

- 갱신 일시/도구: 2026-09-29 / Codex
- 브랜치·HEAD: `main` / 최신 커밋은 `git log -1` 참조
- 미커밋 변경과 소유자: 없음
- 열린 PR: 없음
- 빌드·테스트: 기술 스택 및 검증 명령 미정
- 실제 제품 검증: 미검증
- 배포·제출: 미실행
- 한 줄 상태: 공개 GitHub 저장소의 `main` Ruleset 활성화, 세 팀원 Write 권한 확인, Round 01 이슈 #7~#9와 전용 원격 브랜치 준비

## Recommended Next Step

1. 팀원에게 `prompts/TEAM_FIRST_START.md`를 그대로 전달해 #7~#9 조사 PR을 받는다.
2. 결과를 보고 아이디어와 공모 분야를 확정하고 `docs/PROJECT_BRIEF.md`를 채운다.

## 막힌 곳과 필요한 결정

- 팀의 확정 아이디어와 지원 분야
- AutoCAD 플러그인 프로젝트인지 여부와 실제 개발·검증 환경
- 공식 공고의 정확한 마감 시각은 확인되지 않음

## 최근 체크포인트

### 2026-09-29 / Codex / 공개 저장소와 `main` 서버 규칙

- 문제와 해결: 비공개 Free 저장소의 보호 규칙 제한 → 사용자 지시에 따라 공개 전환, `main` 전용 Ruleset 24130976 활성화
- 변경 파일: `AGENTS.md`, `README.md`, `START_HERE.md`, `BRANCH_ASSIGNMENTS.md`, `docs/TEAM_WORKFLOW.md`, `prompts/`
- 실행한 검증: GitHub API로 공개 상태, 팀원 3명의 Write 권한과 관리자 1명, `main`의 다섯 규칙 확인. PR #10 일반 병합 차단과 관리자 squash 병합 성공 확인. 팀원 브랜치 세 개의 시작 SHA 일치 확인
- 결과: 팀원은 지정 브랜치에서 push·PR 가능, `main` 갱신·삭제·강제 push는 관리자 역할로 제한. PR #10 병합 SHA `ab01cab`; Round 01 브랜치 셋의 최초 생성 기준은 이 SHA
- 남은 위험: 관리자 역할은 Ruleset을 우회할 수 있어 팀장 AI도 PR 절차를 따라야 함; 제품 아이디어와 데모 범위 미정

### 2026-09-29 / Codex / 팀원별 병합 요청과 후속 작업 절차

- 문제와 해결: 전체 팀원 PR이 끝나야 새 라운드를 여는 지침 때문에 먼저 끝난 팀원이 대기 → 팀원별 독립 라운드로 변경
- 변경 파일: `prompts/`, `START_HERE.md`, `docs/TEAM_WORKFLOW.md`, `docs/AI_ONBOARDING.md`, `BRANCH_ASSIGNMENTS.md`, `AGENTS.md`
- 검증: 프롬프트 간 역할·브랜치 권한·상태 전이를 대조하고 Git diff 검증
- 결과: 팀원은 PR 병합 요청·리뷰 수정·새 작업 요청을 복붙 프롬프트로 처리; 팀장은 병합된 팀원에게만 다음 브랜치 배정 가능
- 남은 위험: 다음 작업 범위·담당 파일이 미정이면 팀장이 배정 결정을 해야 함

### 2026-09-29 / Codex / 하이멕 DX·AI 전략 학습

- 문제와 해결: 하이멕의 기존 디지털 기반을 모르면 중복 아이디어 위험 → 하이멕 저자 학술논문 원문 4쪽을 확보·검토
- 변경 파일: `sources/official/SRC-004_HIMEC_DX_AI_strategy.pdf`, `sources/SRC-004_HIMEC_DX_AI_STRATEGY.md`, `docs/JUDGING_STRATEGY.md`
- 실행한 명령: 공식 첨부 PDF 다운로드, PDF 정보 확인, 4쪽 PNG 렌더·전수 시각 검토, SHA-256 계산
- 결과: HDP·HDB·HDT 구조와 AI의 설명가능성·책임성·데이터 품질 제약을 아이디어 평가 기준에 반영
- 남은 위험: 내부 플랫폼의 현재 운영 범위·API·데이터 접근권한은 미확인
