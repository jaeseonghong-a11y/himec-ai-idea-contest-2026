# 팀원 AI에 그대로 붙여넣기 — AutoCAD 플러그인 설치

아래 문장을 자신의 AI에게 그대로 보내세요. API 키는 AI 대화에 입력하지 말고 AutoCAD 팔레트에 직접 넣으세요.

> 우리 팀 저장소는 `https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026`입니다. `docs/AUTOCAD_PLUGIN_TEAM_INSTALL.md`와 `AGENTS.md`를 읽고, 내 Windows PC에 AutoCAD 2026용 HIMEC 플러그인 **v0.2.1-preview**를 설치해 주세요. GitHub Release의 ZIP을 내려받아 문서에 적힌 SHA-256과 실제 파일을 대조하고, 압축 안에 `Himec.ChangeLoop.bundle/PackageContents.xml`과 필요한 DLL들이 있는지도 확인하세요. 기존 저장소가 있으면 내 미커밋 변경과 지정 작업 브랜치를 보존하세요. 없다면 clone해 설치 스크립트만 사용하세요. 작업 중 도면 저장 여부를 확인하고 AutoCAD를 완전히 종료한 뒤 `autocad-plugin/install-user.ps1`로 사용자별 설치를 진행하세요. 설치 후 AutoCAD 2026을 다시 열어 `HIMEC` 팔레트가 뜨는지 확인하고, 가능하면 합성 시험 도면 사본에서만 점검하세요. 보안 설정을 낮추거나 실제 업무 도면을 수정하지 마세요. 키가 필요하면 값을 요구하지 말고 제가 팔레트의 가림 입력창에 직접 넣도록 안내하세요. 성공 여부·설치 버전·검증 경계·추가로 제가 해야 할 일을 짧게 보고해 주세요. 내 `main`/작업 브랜치를 임의로 수정·병합·push하지 마세요.

새 Release가 나오면 같은 요청문에서 버전과 해시를 최신 `docs/AUTOCAD_PLUGIN_TEAM_INSTALL.md` 기준으로 확인하게 하세요. `git pull`만으로 이미 설치된 플러그인이 갱신되는 것은 아닙니다.
