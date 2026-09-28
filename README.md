# HIMEC AI Idea Contest 2026

제1회 HIMEC AI 활용 아이디어 공모전 출품을 위한 공개 팀 협업 저장소입니다. 공식 마감일은 2026년 9월 30일이며, 정확한 마감 시각은 공고에 명시되지 않았습니다.

## 가장 먼저 읽을 파일

1. `START_HERE.md` — 역할과 전체 순환 구조
2. `BRANCH_ASSIGNMENTS.md` — 현재 라운드에서 사용할 정확한 브랜치
3. `prompts/README.md` — 처음 시작, 병합 요청, 새 작업, 리뷰 수정, 막힘 상황별 AI 요청문
4. `AGENTS.md` — 모든 사람과 AI가 따를 공통 규칙
5. `CURRENT_STATE.md` — 지금 상태와 바로 할 다음 작업

## 현재 핵심 상태

- 공식 공고와 제출 양식 원본 확보
- 평가 기준과 제출 체크리스트 정리
- 아이디어·지원 분야·기술 스택은 팀 합의 필요
- 팀원 계정: `archuni`, `ehgudwns18`, `kijun-0108` 협업 권한 확인

## 작업 흐름

```text
팀장 AI: 최신 main에서 팀원별 라운드 브랜치 생성
팀원 AI: 지정 브랜치 최신화 → 작업 → commit → push → PR 생성 후 정지
팀장 AI: PR 순차 검토 → 충돌·통합 검증 → main에 squash merge
팀장 AI: 병합된 팀원에게 최신 main에서 새 브랜치 배정 → 반복
```

`main` 통합은 `jaeseonghong-a11y`와 그 사용자가 실행시킨 AI만 담당합니다. 팀원은 할당된 `work/<사용자명>/rNN` 브랜치에만 push하고 PR을 직접 병합하지 않습니다. 작성된 참가신청서, 개인정보 동의서, 서명, 연락처, 신분증·계좌정보는 Git에 올리지 않습니다.

저장소는 공개이며 `main`에 활성 Ruleset이 적용되어 있습니다. 팀원은 `main`을 갱신·삭제·강제 push할 수 없고, PR을 열어 팀장 통합을 기다립니다. Ruleset은 `main`에만 적용되므로 팀원별 작업 브랜치에는 push할 수 있습니다. [현재 Ruleset](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/rules/24130976)

## 공식 자료

- [하이멕 공식 공고](https://www.himec.co.kr/ko/info/newsroom/?bbsid=33&gbn=viewok&ix=508&scroll=Y)
- 저장된 원본: `sources/official/`
- AI용 근거 요약: `sources/SRC-001_OFFICIAL_CONTEST.md`, `sources/SRC-002_SUBMISSION_FORMS.md`
