# 회의 녹음·AutoCAD·관계도를 잇는 AI 설계 변경 피드백 루프

제1회 HIMEC AI 활용 아이디어 공모전 **설계·엔지니어링** 분야 출품 프로젝트입니다. 설계 회의의 변경 발화를 도면 객체와 연결하고, 불확실한 대상은 사람이 확인한 뒤, 승인한 변경만 반영하는 작업 흐름을 제안합니다.

> 이 저장소는 공개된 **개발·시연 자료**입니다. `main`의 최신 소스와 GitHub Release의 설치 파일은 버전이 다릅니다. 현재 통합 소스로 만든 새 설치 ZIP은 아직 배포하지 않았으며, 실제 고객 도면 전체를 자동 수정하는 제품이 아닙니다.

## 흐름과 현재 구현

1. **녹음·전사:** AutoCAD 플러그인에서 녹음하거나 기존 WAV를 선택합니다. 외부 전사는 사용자가 명시적으로 요청할 때만 호출합니다. 키는 개인 PC에서만 입력합니다.
2. **지시·대상 검토:** 전사문에서 이동 지시를 추출하고 객체 태그·핸들·축으로 대상을 찾습니다. 단일 후보가 아닌 경우 사용자가 도면에서 직접 선택합니다. AI 검토는 읽기 전용 제안이며, 실행 전에 사람이 확인합니다.
3. **PDF·JSON 전달:** AutoCAD 2024/2026용 소스에서 수정사항 PDF와 관계도 편집기가 읽을 JSON을 함께 내보냅니다. 불러오기 자체는 도면을 바꾸지 않습니다.
4. **관계도·도면 반영:** 관계도 편집기에서 변경 대상과 영향을 검토합니다. 도면 이동은 별도의 승인·실행 단계로 제한합니다. 합성 DXF를 이용한 변경 전후 검사 경로도 포함합니다.

예시는 “`C1` 기둥을 Y 방향으로 300 mm 이동”입니다. [AutoCAD 2024 합성 시험 DWG·PDF·JSON](autocad-plugin/tests/)과 [2024 호스트 시험 기록](autocad-plugin/tests/SMOKE_TEST_2024.md)을 볼 수 있습니다. 이 기록의 관계도 연결 시험은 같은 핸들·축으로 만든 합성 그래프를 사용했습니다. 실제 DWG→DXF 변환 도면에서 핸들이 보존되어 끝까지 연결되는지는 아직 검증하지 않았습니다.

## 빠른 시작

| 목적 | 시작 위치 |
|---|---|
| 출품 아이디어와 검증 경계 이해 | [프로젝트 브리프](docs/PROJECT_BRIEF.md) → [현재 상태](CURRENT_STATE.md) |
| AutoCAD 2026 시험판 사용 | [설치·사용 안내](autocad-plugin/README_INSTALL_KO.md)와 [v0.5.1-lab Release](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/releases/tag/v0.5.1-lab) |
| AutoCAD 2024 소스에서 빌드·설치 | [2024 설치 안내](autocad-plugin/README_INSTALL_2024_KO.md) |
| 관계도 편집기 시연 | [직접 해 보기](prototype/relation-editor/직접_해보기.md) → [설치·빌드 안내](prototype/relation-editor/README.md) |
| 팀원 AI와 작업 시작 | [START_HERE](START_HERE.md) → [브랜치 배정](BRANCH_ASSIGNMENTS.md) → [상황별 프롬프트](prompts/README.md) |

AutoCAD에서 테스트할 때는 **합성 도면의 사본**을 열어 사용하세요. 2026 Release는 이전 시험판으로, 최신 `main`에 병합된 2024 지원·PDF/JSON·관계도 연동 변경이 담긴 통합 배포판이 아닙니다. 새 소스를 시험하려면 각 버전의 설치 안내에 따라 별도 빌드가 필요합니다.

## 개발자 검증

저장소 루트에서 실행합니다. AutoCAD 호스트 빌드는 해당 버전의 AutoCAD와 .NET SDK가 설치된 Windows에서만 가능합니다.

```powershell
dotnet run --project autocad-plugin/Himec.ChangeCore.Tests/Himec.ChangeCore.Tests.csproj -f net8.0
dotnet run --project autocad-plugin/Himec.ChangeCore.Tests/Himec.ChangeCore.Tests.csproj -f net48
dotnet build autocad-plugin/Himec.AutoCad2026/Himec.AutoCad2026.csproj -c Release
node prototype/relation-editor/editor/test_instruction_import.js
python -m unittest discover -s prototype/tests -v
```

2024용 빌드 방법과 실제 호스트 확인 항목은 [2024 설치 안내](autocad-plugin/README_INSTALL_2024_KO.md)와 [시험 기록](autocad-plugin/tests/SMOKE_TEST_2024.md)을 따릅니다. 이 저장소의 통합 검증에서는 공용 코어의 두 대상 프레임워크 테스트, 2026 Release 빌드, 관계도 로직·JSON 불러오기 테스트가 통과했습니다. **통합 후 AutoCAD 2024/2026 호스트 전체 동작, 실제 음성 API 호출, 승인 후 이동·UNDO, 실제 도면의 핸들 연결은 별도 확인이 필요합니다.** 상세 결과는 [CURRENT_STATE](CURRENT_STATE.md)에 있습니다.

## 팀 협업·제출 안전

`main`은 팀장 `jaeseonghong-a11y`만 PR로 통합합니다. 팀원은 [배정표](BRANCH_ASSIGNMENTS.md)의 자기 브랜치에만 작업하고 PR을 열어 병합을 요청합니다. 팀원이나 AI가 임의로 `main`에 push·merge하지 않습니다. 공통 작업 규칙은 [AGENTS.md](AGENTS.md)를 따릅니다.

이 공개 저장소에 API 키, 실제 회의 녹음, 개인정보·서명 서류, 권한 없는 고객 도면을 올리지 마세요. 제출 서류와 ZIP은 [제출 체크리스트](docs/SUBMISSION_CHECKLIST.md)에 따라 별도로 최종 확인합니다. 공식 규정과 원본 자료는 [자료 목록](sources/SOURCE_INDEX.md)에서 확인할 수 있습니다.
