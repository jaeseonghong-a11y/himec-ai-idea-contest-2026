# HIMEC 설계 변경 플러그인 — AutoCAD 2024용 설치 안내

이 번들은 **AutoCAD 2024(R24.3) 전용**입니다. AutoCAD 2026용 `Himec.ChangeLoop.bundle`과는
설치 폴더·DLL 이름·ProductCode가 모두 달라 **두 버전을 동시에 설치해도 서로 영향을 주지 않습니다.**

AutoCAD 2026을 쓰신다면 이 문서가 아니라 `README_INSTALL_KO.md`를 보세요. 설치 스크립트가
서로 상대 버전의 번들을 거부하므로 섞어 설치할 수 없습니다.

## 왜 별도 빌드가 필요한가

| | AutoCAD 2024 | AutoCAD 2026 |
|---|---|---|
| 릴리스 | R24.3 | R25.1 |
| 플러그인 런타임 | .NET Framework 4.8 | .NET 8 |
| 플러그인 DLL | `Himec.AutoCad2024.dll` | `Himec.AutoCad2026.dll` |
| 설치 폴더 | `Himec.ChangeLoop2024.bundle` | `Himec.ChangeLoop.bundle` |

AutoCAD 2024는 .NET Framework에서 관리형 플러그인을 로드하므로 2026용 .NET 8 DLL을
그대로 넣어도 **로드되지 않습니다.** 매니페스트의 `SeriesMin`/`SeriesMax`도 각 버전만 허용합니다.

C# 소스는 2026용과 동일한 파일을 공유하며, 대상 프레임워크와 Autodesk 참조 어셈블리만 다릅니다.

## 1. 설치 또는 업데이트

1. 작업 중인 도면을 저장하고 **AutoCAD를 완전히 종료**하세요. 설치 스크립트는 AutoCAD가
   실행 중이면 진행하지 않고 중단합니다.
2. `install-user-2024.ps1`과 `Himec.ChangeLoop2024.bundle` 폴더가 같은 위치에 있는 상태에서
   PowerShell을 열고 실행하세요.

```powershell
./install-user-2024.ps1 -BundlePath ./Himec.ChangeLoop2024.bundle
```

3. `InstalledVersion`과 설치 경로가 표시되면 끝입니다. 설치 위치는
   `%APPDATA%\Autodesk\ApplicationPlugins\Himec.ChangeLoop2024.bundle`이고
   **관리자 권한은 필요 없습니다.** 이전 버전은 `.himec-backups`에 보존됩니다.
4. AutoCAD 2024를 다시 실행하세요. Git pull만으로는 갱신되지 않으며 업데이트할 때마다
   이 절차와 재시작이 필요합니다.

## 2. 제거

1. AutoCAD를 완전히 종료합니다.
2. `%APPDATA%\Autodesk\ApplicationPlugins\Himec.ChangeLoop2024.bundle` 폴더를 삭제합니다.
3. AutoCAD 2024를 다시 실행하면 `HIMEC` 명령이 사라집니다.

2026용 번들(`Himec.ChangeLoop.bundle`)은 건드리지 마세요. 별개로 동작합니다.
녹음·태그 기록(`%LOCALAPPDATA%\Himec\`)은 남습니다. 필요 없으면 직접 삭제하세요.

## 3. 소스에서 직접 빌드

AutoCAD 2024가 설치된 PC에서 .NET SDK 8 이상이 필요합니다.

```powershell
./package-2024.ps1 -Version 0.3.1
```

`autocad-plugin/dist2024/<버전>/Himec.ChangeLoop2024.bundle`이 만들어지고 파일별 SHA-256이 출력됩니다.
AutoCAD를 기본 경로가 아닌 곳에 설치했다면 `-AutoCadDir "D:\...\AutoCAD 2024\"`로 지정하세요.

## 4. 첫 실행

1. 명령창에 `HIMEC`을 입력하면 **HIMEC 설계 변경** 팔레트가 열려야 합니다. 보안 경고가 나오면
   경로·버전을 직접 확인하세요. `SECURELOAD`를 낮추지 마세요.
2. 실제 업무 도면 대신 `autocad-plugin/tests/three_columns_mm.dxf`의 **사본**을 `열기`로 여세요.
   현재 도면에 **삽입**하면 기둥 3개가 하나의 블록으로 묶여 대상 선택이 되지 않습니다.
3. 사용법과 녹음·API 키 주의사항은 2026용 `README_INSTALL_KO.md`의 3~4장과 같습니다.
   API 키는 팀원·팀장·AI 채팅·GitHub에 절대 올리지 마세요.

## 5. 검증 상태

이 2024용 빌드에서 **실제로 확인한 것과 아닌 것**은 `tests/SMOKE_TEST_2024.md`에 기록합니다.
새로 만든 빌드라서 2026용보다 확인된 범위가 좁습니다. 합성 시험 도면의 사본에서만 사용하고,
실제 프로젝트 도면에는 사용하지 마세요.
