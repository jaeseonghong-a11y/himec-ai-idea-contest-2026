# 범용 팀 개발 워크플로우 킷

새 프로젝트에서 여러 팀원이 브랜치로 작업하고, AI 코딩 도구가 맥락을 이어받아 PR을 검토·병합하도록 돕는 템플릿입니다. 성균관대 시간표 서비스의 코드·데이터·Upstage·Vercel 설정은 옮기지 않았습니다. AutoCAD 플러그인 프로젝트를 염두에 두되 구현 언어와 배포 방식은 아직 결정하지 않았습니다.

## 파일 지도

| 파일 | 용도 |
|---|---|
| `01_시작하기.md` | 새 저장소 생성과 템플릿 적용 |
| `02_팀_GitHub_브랜치_PR_병합.md` | 브랜치, push, PR, AI 검토, 충돌 해결, 병합 |
| `03_개발_품질_인수인계.md` | 일일 개발 루프, 검증, AI 도구 전환 |
| `04_AutoCAD_프로젝트_결정사항.md` | 플러그인 프로젝트에서 먼저 정할 것 |
| `05_복붙_프롬프트.md` | 프로젝트 시작부터 병합까지 바로 쓰는 프롬프트 |
| `templates/` | 새 저장소에 복사할 프로젝트 문서와 PR·CI 예시 |

## 5분 시작

1. ZIP을 풀고 `01_시작하기.md`를 읽습니다.
2. 새 GitHub 저장소를 만든 뒤 `templates/`의 문서를 프로젝트 루트에 복사합니다.
3. `[[...]]` 자리표시자를 채웁니다. 모르는 것은 `미정`으로 표시합니다.
4. `05_복붙_프롬프트.md`의 **0. 프로젝트 초기화**를 AI 도구에 붙여넣습니다.
5. 실제 기술 스택과 검증 명령이 정해지면 CI를 구성하고 `main` 보호 규칙을 켭니다.

```text
팀원: main 최신화 → 작업 브랜치 → 작은 변경·검증 → push → Pull Request
담당자/AI: PR 확인 → diff·CI·충돌 검토 → 통합 검증 → 병합
모두: main 최신화 → CURRENT_STATE.md 갱신 → 다음 작업
```

**push는 브랜치를 GitHub에 올리는 것**입니다. main에 반영하려면 PR을 병합해야 합니다. Git 충돌을 항상 없앨 수는 없지만, 작은 PR과 분리된 작업 공간, 수동 검증으로 안전하게 해결할 수 있습니다.

## 원본에서 가져온 것과 바꾼 것

원본 SKKU-DULE 저장소의 `AGENTS.md`, `CURRENT_STATE.md`, `WORKFLOW.md`, `PROMPTS.md`, 기존 `vibe-coding-kit/`, CI 및 병합 이력을 참고했습니다. 실제 원본에는 원격 브랜치를 직접 병합한 기록이 있습니다. 이 킷은 새 프로젝트에 맞게 **PR 검토와 main 보호를 기본값**으로 제안합니다. 원본이 처음부터 PR로 운영되었다는 뜻은 아닙니다.

## 공식 참고 자료

- GitHub 보호 브랜치: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- GitHub CLI PR 병합: https://cli.github.com/manual/gh_pr_merge
- 충돌 해결: https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/resolving-a-merge-conflict-using-the-command-line
- Autodesk 호환성: https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-Customization/files/GUID-D54B0935-1638-4F97-8B37-1EC3635A1E71.htm

이 킷은 안내서와 템플릿입니다. GitHub 저장소·보호 규칙·CI·AutoCAD 개발 환경을 자동으로 만들거나 PR을 자동 병합하지는 않습니다.
