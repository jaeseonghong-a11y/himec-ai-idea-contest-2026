# AGENTS.md — 하이멕 AI 활용 아이디어 공모전 공통 작업 지침

이 파일은 Codex, Claude Code 등 팀원이 사용하는 모든 AI 도구의 공통 기준이다. 확인되지 않은 프로젝트 사실은 추정하지 않고 `미정`으로 남긴다.

## 시작할 때 읽을 순서

1. `AGENTS.md`
2. `START_HERE.md`
3. `BRANCH_ASSIGNMENTS.md`
4. `CURRENT_STATE.md`
5. `docs/PROJECT_BRIEF.md`
6. `sources/SOURCE_INDEX.md`
7. 필요한 경우 `docs/DECISION_LOG.md`, `docs/TEAM_WORKFLOW.md`, `docs/SUBMISSION_CHECKLIST.md`
8. `git status --short`, `git diff`, `git log --oneline -5`
9. 현재 작업에 필요한 실제 자료와 코드

문서와 결과물이 다르면 실제 파일을 확인하고 문서를 갱신한다. 다른 팀원이나 AI가 만든 미커밋 변경은 삭제·reset·stash하지 않는다.

## 프로젝트

- 프로젝트명: 하이멕 AI 활용 아이디어 공모전
- 마감 목표: 2026-09-30까지 제출 가능 상태 완성
- 목표: 제1회 HIMEC AI 활용 아이디어 공모전 출품
- 한 줄 정의: 회의 설계 변경 지시를 구조화·주석화하고 사람이 승인한 일부 변경만 합성 CAD 도면에 반영하는 피드백 루프 — `docs/PROJECT_BRIEF.md`
- 공모 분야: 설계·엔지니어링
- 데모 구성: AutoCAD 2026 플러그인 v0(녹음·전사 선택 호출·검토·수동 대상 지정·승인 후 블록 이동)과 기존 합성 텍스트·PDF·DXF 경로를 구분한다. 실제 검증 결과만 확정한다.
- AutoCAD 플러그인: 사용자 요청으로 우선 구현 중. 2024 호환, 실제 DWG/PDF 매핑, AutoCAD 내부 로드·녹음·편집 검증은 별도 완료 전까지 미검증
- 제출 규격과 평가 기준: `sources/SRC-001_OFFICIAL_CONTEST.md` 기준

## 작업 방식

- 한 브랜치에는 한 가지 산출물 또는 검증 가능한 작은 작업만 담는다.
- 작업 시작 전에 완료 기준과 담당 파일을 이슈 또는 팀 채널에 기록한다.
- 자료 조사 결과는 출처 URL, 확인 날짜, 근거와 해석을 구분해 남긴다.
- 새 근거를 추가할 때 `sources/SOURCE_INDEX.md`에 식별자, 원본 위치, 확인일, 검증 상태를 먼저 등록한다.
- 공식 원본은 `sources/official/`에 변형 없이 보존하고, 해석은 별도 Markdown 파일에 작성한다.
- 외부 SDK/API, 공모전 규정, 호환성은 공식 자료나 실제 실행으로 확인한다.
- 생성형 AI 결과는 사실 검증과 팀 검토 없이 최종 근거로 사용하지 않는다.
- 개인정보, 고객 자료, API 키, 토큰을 코드·문서·로그·커밋에 넣지 않는다.
- 서명·생년월일·전화번호 등이 적힌 참가 서류는 절대 Git에 올리지 않고 `submission-private/` 또는 저장소 밖에서 관리한다.
- C 단계 합성 DXF 단위 검증: `python -m unittest discover -s prototype/tests -v` (`ezdxf` 설치 필요). A/B/D와 연결한 전체 통합 검증 명령은 아직 미정이다.
- 플러그인 파서 검증: `dotnet run --project autocad-plugin/Himec.ChangeCore.Tests/Himec.ChangeCore.Tests.csproj`; 호스트 빌드: `dotnet build autocad-plugin/Himec.AutoCad2026/Himec.AutoCad2026.csproj -c Release`. 실제 AutoCAD 로드·실행은 별도 스모크 테스트가 필요하다.
- 커밋 메시지는 `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:` 중 알맞은 말머리를 사용한다.

## GitHub 팀 규칙

- 저장소 소유자이자 유일한 통합 담당자는 `jaeseonghong-a11y`다.
- `main`은 최종 기준선이다. 팀원과 팀원 AI는 `main`을 수정·commit·push·merge·rebase·reset하지 않는다.
- 팀원과 팀원 AI는 브랜치를 임의로 생성하지 않는다. `BRANCH_ASSIGNMENTS.md`에 지정된 `work/<github-user>/rNN` 브랜치만 사용한다.
- 팀원은 작업 브랜치에만 commit·push하고 `main` 대상 Pull Request(PR)를 연 뒤 멈춘다. PR을 직접 병합하거나 닫거나 브랜치를 삭제하지 않는다.
- `main` 병합, 충돌 해결, 병합 순서 결정, 다음 라운드 브랜치 생성은 `jaeseonghong-a11y` 또는 그 사용자가 명시적으로 실행시킨 AI만 수행한다.
- 통합 담당 AI는 PR별 최신 SHA·diff·검증·충돌을 확인하고 안전한 PR만 순차적으로 squash merge한다. 제품 판단이 필요한 충돌은 사용자에게 묻는다.
- 본인이 담당한 파일만 stage한다. 다른 팀원의 변경을 `git add -A`로 섞지 않는다.
- 공통 문서, 데이터 계약, 빌드 설정을 동시에 바꿀 때는 담당자 한 명을 정한다.
- 병행 작업은 각자 clone 또는 별도 worktree에서 수행한다. 같은 작업 트리를 여러 AI가 동시에 편집하지 않는다.
- 충돌은 양쪽 의도를 확인해 통합한다. 관리자 권한을 이용한 직접 push, 강제 push, 공유 `main` 재작성은 금지한다.
- 공개 저장소의 `main`에는 활성 Ruleset `Protect main - owner merges`가 적용된다. 관리자 역할만 우회할 수 있고 팀원 Write 역할은 `main` 갱신·삭제·강제 push가 차단된다. 저장소 소유자도 모든 통합을 PR과 squash merge로 기록한다.

## 작업 종료

팀원은 PR 설명과 담당 이슈에, 팀장 AI는 `CURRENT_STATE.md`에 아래를 기록한다. 팀원별 브랜치에서 공통 `CURRENT_STATE.md`를 동시에 수정하지 않는다.

- 수행한 일과 변경 파일
- 실제로 실행한 검증과 결과
- 미검증 사항과 남은 위험
- 다른 브랜치와 겹치는 영역
- 다음 담당자가 바로 실행할 `Recommended Next Step`

최신 체크포인트 3개만 유지하고 이전 내용은 `docs/archive/`에 보관한다.
