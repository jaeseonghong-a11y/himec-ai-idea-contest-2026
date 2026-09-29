# 팀원용 AutoCAD 플러그인 설치·업데이트

기준 배포판: **v0.2.1-preview** (AutoCAD 2026 / Windows 전용). 이 버전은 팀 공동 개발용 시험판이다. 실제 API 전사와 플러그인 승인→도면 이동/UNDO는 나중에 검증한다. [GitHub Release](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/releases/tag/v0.2.1-preview)의 ZIP을 사용한다. 소스와 설치 스크립트는 저장소의 `main`에서 볼 수 있다.

## 처음 설치 / 새 버전으로 교체

1. Windows용 **정식 AutoCAD 2026**이 있는지 확인한다. AutoCAD LT, Mac, 2024는 이 패키지 대상이 아니다. 작업 중인 도면을 저장하고 AutoCAD를 완전히 종료한다.
2. 위 Release에서 `Himec.ChangeLoop-AutoCAD2026-v0.2.1-team.zip`을 내려받는다. SHA-256은 `114AB5A9C77A0A9CC588D110F6858BA8ED2373F08BC8FFA1E9AE2E4ACB493423`이다. 압축을 풀면 `Himec.ChangeLoop.bundle`, `install-user.ps1`, `README_INSTALL_KO.md`가 나온다. ZIP 안의 README가 다운로드부터 사용법·오류 대응까지 설명한다.
3. ZIP 해시를 확인한다. PowerShell: `Get-FileHash -LiteralPath '다운로드한 ZIP 전체 경로' -Algorithm SHA256`. 다르면 설치하지 말고 팀장에게 알린다.
4. 압축을 푼 폴더에서 PowerShell로 `./install-user.ps1 -BundlePath ./Himec.ChangeLoop.bundle`를 실행한다. 저장소 clone이나 팀원 작업 브랜치 변경은 설치에 필요하지 않다. 스크립트는 실행 중인 AutoCAD가 있으면 중단하고, 이전 설치 버전을 사용자별 백업 폴더에 보존한다. 관리자 권한은 필요 없다. 회사 PC 실행 정책이 스크립트를 막으면 보안 설정을 낮추지 말고 ZIP의 README에 적힌 대안을 확인한다.
5. AutoCAD 2026을 다시 열어 명령창에 `HIMEC`을 입력한다. Windows/AutoCAD 보안 안내가 나오면 게시자·경로·버전을 검토하고 승인 여부를 직접 결정한다. `SECURELOAD`를 낮추거나 보안 설정을 끄지 않는다.
6. 우선 **합성 시험 도면의 사본**으로 확인한다. 제공한 `autocad-plugin/tests/three_columns_mm.dxf`는 도면에 통째로 `삽입`하지 말고 AutoCAD에서 **열기**로 연다. 실제 업무 도면에 실행하지 않는다.

새 배포판이 나오면 자동으로 갱신되지 않는다. 위의 다운로드→해시 확인→AutoCAD 종료→설치→재시작을 다시 해야 한다. `git pull`만으로 설치된 DLL은 교체되지 않는다.

## 전사 API 키

현재 플러그인의 전사 버튼은 **OpenAI API**를 호출한다. 각자가 [OpenAI API 키 페이지](https://platform.openai.com/api-keys)에서 키를 만들고, 팔레트의 `전사 API 키 입력`에 직접 붙여넣는다. 이 입력은 현재 AutoCAD 실행 중 메모리에서만 사용한다. OpenAI API 결제는 ChatGPT 구독과 별개일 수 있으니 본인 [API 사용·결제 설정](https://platform.openai.com/settings/organization/billing/overview)을 확인한다. 키를 팀 채팅·AI 대화·화면 공유·Git에 보내지 않는다. 팀장 키를 공유하지 않는다.

녹음은 키 없이도 가능하다. 전사는 사용자가 버튼을 누르고 외부 전송에 동의한 후에만 실행된다. 회의 참가자 동의와 고객 자료 반출 권한이 없는 녹음은 업로드하지 않는다. 다른 제공자(Anthropic·Gemini)의 키는 **현재 플러그인 전사 버튼에 사용할 수 없다**.

## 실패 시 팀장에게 보낼 정보

AutoCAD 버전, Release 버전, ZIP 해시 일치 여부, `HIMEC` 명령의 표시/오류, 재현 단계, 시험 도면 여부를 전달한다. **API 키·개인 녹음·고객 도면은 보내지 않는다.** 전사 실패 메시지에 HTTP 코드가 나오면 코드만 전달한다.

팀원 AI에 바로 붙여넣을 요청문은 [`prompts/TEAM_INSTALL_AUTOCAD_PLUGIN.md`](../prompts/TEAM_INSTALL_AUTOCAD_PLUGIN.md)에 있다.

패키지를 다시 만들 때는 기존 `package.ps1`로 번들을 빌드한 뒤 `./autocad-plugin/package-team.ps1 -Version 0.2.1`을 실행한다. 출력 ZIP에는 README·설치 스크립트·번들 필수 파일을 검증해 포함한다. 기존 ZIP을 덮어쓰지 않으므로 새 배포 버전을 사용한다.
