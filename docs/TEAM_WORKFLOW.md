# 팀 협업 실행 절차

## 공통 원칙

각 팀원은 자신의 PC에 저장소를 clone하고, 자신의 브랜치와 AI 세션을 사용한다. 공통 기억은 대화창이 아니라 `AGENTS.md`, `CURRENT_STATE.md`, 이슈, PR, Git 이력이다.

## 작업 시작

```powershell
git switch main
git pull --ff-only origin main
git status --short
git switch -c feat/<짧은-작업명>
```

AI 도구에는 다음을 먼저 지시한다.

```text
AGENTS.md, CURRENT_STATE.md, docs/PROJECT_BRIEF.md와 현재 git 상태를 먼저 읽어.
다른 팀원의 변경을 보존하고, 이번 브랜치의 담당 범위와 완료 기준만 수행해.
실제로 검증한 결과와 미검증 사항을 CURRENT_STATE.md에 기록해.
```

## 작업 종료와 PR

```powershell
git status --short
git diff
git add <본인이 변경한 경로>
git diff --cached
git commit -m "feat: 작업 요약"
git push -u origin HEAD
```

GitHub에서 `main`을 대상으로 PR을 열고 템플릿을 채운다. push만으로는 `main`에 반영되지 않는다.

## 병합 기준

- PR 설명과 변경 범위가 일치한다.
- 비밀값, 개인정보, 출처 불명 자료가 없다.
- 합의한 검증이 통과했거나 미검증 사유가 명시돼 있다.
- 최소 1명의 다른 팀원이 검토한다.
- 최신 `main`과 충돌 및 의미상의 충돌이 없다.
- 기본 병합 방식은 squash merge이며 병합 후 작업 브랜치를 삭제한다.

## 현재 GitHub 제한

2026-09-29 확인 결과, 개인 GitHub Free 계정의 비공개 저장소에서는 `main` branch protection 적용이 거부되었다. 저장소 공개 또는 GitHub Pro 전환 전까지 다음을 수동으로 지킨다.

- 누구도 `main`에 직접 push하지 않는다.
- 모든 변경은 PR을 만들고 최소 1명의 다른 팀원이 승인한다.
- 병합 직전 PR의 최신 커밋과 검토한 커밋이 같은지 확인한다.
- force push와 `main` 삭제를 하지 않는다.

공개 전환은 제안 내용과 Git 이력의 공개를 뜻하므로 팀 대표 승인 없이 실행하지 않는다.

## 마감일 운영

- 공통 파일(`PROJECT_BRIEF`, 발표 본문, 데이터 계약, 빌드 설정)은 동시에 편집하지 않고 한 명이 통합한다.
- 긴 기능보다 제출에 직접 기여하는 작은 PR을 우선한다.
- 최종 제출 후보 커밋을 태그하고, 제출 파일의 해시와 제출 여부를 별도로 기록한다.
- GitHub에 병합된 것과 실제 공모전 제출 완료는 구분한다. 계정 로그인, 동의, 최종 제출 버튼은 담당자가 직접 확인한다.
