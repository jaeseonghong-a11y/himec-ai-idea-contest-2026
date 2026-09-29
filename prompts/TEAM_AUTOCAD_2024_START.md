# archuni에게 그대로 보내는 요청문 — AutoCAD 2024 호환판

아래 코드블록 전체를 `archuni`가 AutoCAD 2024가 설치된 PC의 AI에게 **수정 없이** 붙여넣는다.

```text
HIMEC AutoCAD 2024 전용 플러그인을 만들어줘. 저장소는 https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026 이고, 내 GitHub 사용자명은 archuni야.

먼저 AutoCAD 2024가 실제 설치되어 실행되는지와 설치 폴더의 AcMgd.dll, AcDbMgd.dll, AcCoreMgd.dll을 확인해. 내 로컬 저장소가 없으면 새 폴더에 clone하고, 기존 저장소가 있으면 미커밋 작업을 보존해. origin을 fetch한 뒤 최신 origin/main의 AGENTS.md, START_HERE.md, BRANCH_ASSIGNMENTS.md, CURRENT_STATE.md, docs/PROJECT_BRIEF.md와 이슈 #35를 읽어줘. 배정된 work/archuni/r03 원격 브랜치가 존재하는지 확인하고, 그 브랜치에서만 작업해. 계정·브랜치·2024 설치 중 하나라도 맞지 않으면 새 브랜치를 만들거나 2026 DLL을 2024에 로드하지 말고 나에게 알려줘.

현재 내 work/archuni/r02의 PR #34는 다른 과제야. r03는 별도 clone 또는 worktree에서 작업하고 r02의 미커밋 변경을 섞지 마. main이나 다른 브랜치는 commit, push, merge, rebase, reset, 삭제하지 마.

이슈 #35의 완료 기준에 따라 AutoCAD 2024용을 실제로 구현해. Autodesk 공식 문서와 로컬 설치 파일을 확인해 .NET Framework 4.8 및 AutoCAD 2024(R24.3) 참조로 빌드하고, 기존 2026용과 공존하는 별도 DLL·bundle·설치 스크립트/안내를 만들어. 2026용 배포판을 덮어쓰거나 호환된다고 추정하지 마. 공유 코어를 바꿔야 한다면 변경 근거와 2026 회귀 검증을 포함해. 원본 코드 복제 대신 가능한 범위에서 공통 로직을 재사용하되, 호환성 때문에 필요한 차이는 명시해.

합성 도면 복사본만 사용해 AutoCAD 2024에서 HIMEC 팔레트 로드, 녹음 WAV 저장, 수동 전사문, 태그 연결·수정·재열기와 승인 전 도면 불변을 직접 시험해. 실제 전사 API는 본인이 키와 시험용 음성의 외부 전송을 명시적으로 승인하지 않았다면 호출하지 마. API 키·토큰·고객 도면·실제 회의록·개인정보를 코드, 로그, Git, PR에 남기지 마. 승인 후 이동/UNDO 등 검증하지 못한 기능은 완료라고 주장하지 말고 미검증으로 기록해.

2024용 설치·업데이트·제거법, 필요한 파일과 SHA-256, 실행한 빌드·테스트 명령과 실제 결과를 한국어로 남겨. 작업 전후 git status와 diff를 확인하고 담당 파일만 stage해 commit/push한 뒤 main 대상 PR을 열어. PR에는 이슈 #35, 변경 파일, 2024 호스트 시험 결과, 2026 회귀 결과, 미검증 사항, 설치 ZIP 위치와 해시, Recommended Next Step을 적어. PR을 직접 병합하거나 닫거나 브랜치를 삭제하지 마. 마지막에는 PR 링크와 검증 경계를 나에게 간단히 보고해.
```

팀장 AI는 PR의 실제 빌드·호스트 근거와 ZIP 구성을 검토한 뒤에만 병합·Release 배포를 결정한다.
