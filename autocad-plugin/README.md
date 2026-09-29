# HIMEC AutoCAD 플러그인 v0

AutoCAD 내부 `HIMEC` 명령으로 열리는 팔레트의 첫 구현이다. 현재 PC의 AutoCAD 2026(.NET 8 호스트)용으로 빌드했다. 2024용 DLL은 **별도로** .NET Framework 4.8 대상 빌드·검증해야 한다. AutoCAD LT와 Mac은 대상이 아니다.

## 현재 가능한 것

1. `● 녹음 시작` / `■ 녹음 중지`: 마이크 WAV를 `%LOCALAPPDATA%\Himec\Recordings`에 저장한다. 이전에 녹음한 WAV도 `이미 녹음한 WAV 선택`으로 가져올 수 있다.
2. `녹음 전사`: 사용자의 확인 후에만 OpenAI 전사 API로 WAV를 전송한다. API 키는 팔레트에서 **이번 실행에만** 입력하거나 로컬 `OPENAI_API_KEY` 환경변수로 설정한다. 키는 플러그인 파일·Git에 저장하지 않는다. 키가 없으면 녹음은 되지만 API 전사는 안 되며 전사문을 직접 입력할 수 있다. 허가받지 않은 회의·고객 자료는 외부 전송하지 않는다.
3. `전사문에서 이동 지시 찾기`: **로컬 규칙**으로 `위로 30cm` 등을 mm 이동량으로 읽는다. AI가 도면 객체를 찾아냈다고 주장하지 않는다. 문장이 여러 개면 현재는 첫 번째 인식 가능한 이동 지시 하나만 처리한다.
4. `후보 찾기`: “왼쪽에서 세 번째”라고 했고, 같은 줄에 있는 기둥 블록을 식별할 수 있을 때만 X좌표 기준 세 번째를 **추천**한다. 여러 줄·겹친 X좌표·후보 부족은 모호하다고 알린다. 추천만으로 대상은 확정되지 않는다.
5. `도면에서 대상 직접 선택`: AutoCAD에서 기둥 블록 하나를 클릭해 확정한다. DXF를 도면에 통째로 `삽입`한 외부 블록은 대상이 아니다. 시험 DXF는 `열기`로 연다.
6. `지시 승인` 다음 `승인된 변경 실행`: 현재 도면의 `INSUNITS=4`(mm), 대상 핸들, 승인 로그를 재검증한 뒤 WCS X/Y 기준으로 블록 한 건을 이동한다. 자동 저장하지 않으며 AutoCAD의 `UNDO`로 되돌릴 수 있다.

승인/실행 기록은 `%LOCALAPPDATA%\Himec\Changes`에 저장한다. 사용자 데이터가 Git에 올라가지 않는다. 녹음은 사전에 참여자 동의를 받아야 한다.

## 빌드

AutoCAD 2026이 설치된 Windows와 .NET 8 SDK가 필요하다. AutoCAD 관리 DLL은 설치 폴더에서 참조한다. 경로가 다르면 `-p:AutoCadDir="..."`를 전달한다. SDK 설치는 [Microsoft 공식 안내](https://learn.microsoft.com/en-us/dotnet/core/install/windows)를 따른다.

```powershell
dotnet run --project autocad-plugin/Himec.ChangeCore.Tests/Himec.ChangeCore.Tests.csproj
dotnet build autocad-plugin/Himec.AutoCad2026/Himec.AutoCad2026.csproj -c Release
./autocad-plugin/package.ps1 -Version 0.2.1
```

`package.ps1`은 기존 버전을 덮어쓰지 않는다. 예시는 `dist/0.2.1/Himec.ChangeLoop.bundle`을 만든다. 빌드 결과에 Autodesk DLL은 포함하지 않고 NAudio 및 프로젝트 DLL만 포함한다.
새 버전 패키지마다 Autodesk 권장대로 `ProductCode`를 새 GUID로 만들고 `UpgradeCode`는 유지한다. 같은 버전을 다시 만들 때도 결과 디렉터리가 이미 있으면 중단한다.

UI 레이아웃은 AutoCAD 어두운 작업 화면과 맞춘 4단계 카드, 상단 고정 상태 메시지, 구분된 보조/주요/실행 버튼으로 구성한다. AutoCAD를 재시작하지 않고 레이아웃만 확인할 때는 `dotnet run --project autocad-plugin/Himec.PalettePreview/Himec.PalettePreview.csproj -c Release -- autocad-plugin/dist/palette-preview.png`를 사용한다. 미리보기는 AutoCAD 명령을 실행하지 않는다.

## AutoCAD에서 로드

- 먼저 **복사본/합성 도면**으로 시험한다. mm 도면(`INSUNITS=4`)에서 블록 하나를 만든다.
- AutoCAD를 종료한 뒤 `./autocad-plugin/install-user.ps1 -BundlePath ./autocad-plugin/dist/0.2.1/Himec.ChangeLoop.bundle`로 사용자별 `ApplicationPlugins` 위치에 설치하고 AutoCAD를 다시 연다. 이 스크립트는 이전 버전을 `.himec-backups`에 옮겨 보존하며, AutoCAD가 실행 중이면 설치하지 않는다. 설치/신뢰 경로는 Autodesk의 [번들 설치 안내](https://help.autodesk.com/cloudhelp/2023/KOR/AutoCAD-Customization/files/GUID-5E50A846-C80B-4FFD-8DD3-C20B22098008.htm)를 따른다. 보안 설정을 끄지 않는다.
- 명령창에 `HIMEC`을 입력한다. 팔레트가 나타나면 녹음 또는 전사문 직접 입력으로 시험한다.
- 빌드 성공과 AutoCAD 내부 로드 성공은 다르다. 현재 검증 결과는 아래 기록을 확인한다.

## 아직 안 된 것

- 여러 층/줄/공간에 걸친 “왼쪽 세 번째”의 정확한 범위 해석, 도면 하이라이트, 대화형 모호성 질문, 전체 회의에서 여러 지시 분리, LLM 자연어 추출, 다른 도면 연쇄 수정, PDF 주석, MCP 연동.
- AutoCAD 2024 호환 빌드, 자동 업데이트. 현재는 검증 후 수동으로 실행하는 사용자별 설치 스크립트만 있다.
- 사용자가 AutoCAD 2026에서 v0.1.2 로드·팔레트·수동 문장 X 0/Y +300 mm 분석을 확인했다. 녹음 WAV 파일 3개는 메타데이터(길이·형식·에너지)만 확인했다. 마이크 음성 품질·API 전사·도면 변경은 별도 검증이다. 새 UI·키 입력·기존 WAV 선택 기능이 포함된 v0.2.1은 AutoCAD 재시작 후 호스트 검증이 필요하다.

## 배포·업데이트

플러그인은 각 사용자 PC에 설치되는 DLL이다. 새 버전은 서명·검증·설치와 AutoCAD 재시작/재로드가 필요하다. AI 해석 서비스를 별도 HTTPS API로 운영하면 그 서버 쪽은 모든 사용자에게 한 번에 갱신할 수 있지만, **서버 배포만으로 설치된 DLL이 자동 교체되지는 않는다.** Vercel은 선택 가능한 서버 호스팅 중 하나일 뿐 필수 구성 요소가 아니다. 버전과 롤백을 관리하는 업데이트 절차를 후속 작업으로 둔다.
