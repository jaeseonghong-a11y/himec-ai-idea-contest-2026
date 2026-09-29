# CURRENT_STATE.md — 최신 인수인계

## 현재 상태 (2026-09-30, 팀장 AI)

- 2026-09-30 김기준 팀원 [PR #52](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/pull/52)를 원본 SHA `ba434aa` 검토 후 squash 병합(`8dde212`)했다. `prototype/relation-editor/` 독립 관계도 편집기·DXF 생성/재읽기·마스킹 도면 4장·시나리오 이미지를 기존 기능과 함께 보존했다. 팀원 주장과 팀장 승인에 따른 실제 도면 공개 예외는 `prototype/CONTRACT.md` 참조. 원본 동의·저작권은 독립 검증 전이다. 검증: 도면 4장 문자열 마스킹 검사, 새 프로젝트 로직 75/75·기존 도면 44/44, 합성 계획안 2종의 DXF 재읽기 33/33, Edge 새 프로젝트 화면 29/29. 기존 플러그인과 런타임 연결은 하지 않았고, 김기준 PC의 AutoCAD 2024 결과는 이 PC에서 재검증하지 않았다. #17의 합성 A-101/A-301/E-201·대본·사이드카 계약은 별도 미완료다.
- 사용자 PC의 AutoCAD 종료 후 v0.5.1-lab 번들을 설치했고 매니페스트 `0.5.1.0`과 DLL SHA-256 `F40C372A70BFB21B81A967050AA56E61C4927E3DC142AB7850556AB3ED291F59`를 확인했다. 이전 번들은 ApplicationPlugins의 `.himec-backups`에 보존했다. 사용자 Gemini 503이 이 버전에서 해결됐는지는 AutoCAD 재시작 후 같은 시험 WAV로 확인해야 한다.

- Gemini 파일 전사 후속 [#47](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/issues/47): 사용자 PC의 `v0.5.0-lab`에서 HTTP 503 화면 확인. Google 공식 기준 503은 서비스 일시 불가/과부하이며 화면의 기존 결제·권한 안내는 과도한 일반화다. [PR #48](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/pull/48)에 Gemini 파일 전사 최대 3회(3.8 Flash 2회, 3.5 Flash 1회) 제한 재시도, 성공 모델 표시, 401/403/429 비재시도, 상태별 안전한 오류 문구를 병합했다. [v0.5.1-lab 시험판](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/releases/tag/v0.5.1-lab)을 배포하고 원격 ZIP SHA-256 `83615C7E5AC1D6BBC36BED6702A309240EC5B19C579D1C07BDEA0A905D0F1DF9` 일치를 확인했다. 합성 HTTP 테스트와 빌드는 통과했으나 실제 키·음성으로 성공 여부는 아직 검증 전이다. `sources/SRC-009_GEMINI_503.md` 참조. 현재 사용자 PC에는 0.5.1을 설치했다.

- 제공자 통합 [#42](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/issues/42), [PR #43](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/pull/43): AutoCAD 2026용 소스에 OpenAI/Gemini 녹음 후·실시간 전사 선택과 OpenAI/Gemini/Claude 전사문 AI 검토를 추가했다. [v0.5.0-lab 시험판](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/releases/tag/v0.5.0-lab) ZIP 13파일을 배포하고 원격 재다운로드 SHA-256 `3EE31B682AE5A399AF07AF3811A21C79E0A41FA44DA44CF2437C6ED835DA9AC5` 일치를 확인했다. 2026-09-30 AutoCAD 종료 상태에서 사용자 PC에 설치해 매니페스트 `0.5.0.0`과 DLL SHA-256 `20105A93D4F7C6DD3D3A3EE0F01001F240039BB45C73CCE2DFDFF536D77DF25E`를 확인했다. 이전 0.4.3 번들은 사용자 ApplicationPlugins의 `.himec-backups`에 보존했다. Claude 직접 WAV 전사는 지원하지 않으며 AI 검토 결과는 읽기 전용 제안이다. 합성 팔레트/이벤트 테스트와 빌드는 통과했으나 **실계정 호출·AutoCAD 호스트·마이크는 미검증**이다. Computer Use 연결은 native pipe 오류로 3회 실패하여 호스트 화면 시험을 진행하지 못했다. 키는 Git에 두지 않는다. 공급자 근거는 `sources/SRC-007_008_PROVIDER_APIS.md`.

- 실시간 전사 후속 [#39](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/issues/39): [PR #40](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/pull/40)의 소스를 `main`에 병합하고 [v0.4.3-lab 실험판](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/releases/tag/v0.4.3-lab)을 예비 배포했다. 24 kHz 로컬 녹음에서 명시적 체크박스 동의 후 WebSocket 전송, 확정 문장만 로컬 태그에 반영하는 코드다. ChangeCore 테스트·독립 UI/합성 이벤트·Release 빌드·13파일 ZIP 및 원격 재다운로드 SHA-256 `46EA40520CA83DF66091018DA4F3ADF8B4DCFE17A1F4F092C449BA464555DBA9`를 확인했다. **실제 AutoCAD 마이크/API 연결과 사용자 계정의 429 원인은 미검증**이다. 기존 `v0.3.1-preview`는 그대로 두었고 설치는 아직 하지 않았다. 사용법은 `autocad-plugin/README_LIVE_PREVIEW_KO.md`를 따른다.

- 플러그인 후속 개선 [#37](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/issues/37): [PR #38](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/pull/38)의 HTTP 429 코드별 안내, 팔레트 최소 크기 완화, 단일 도면 식별자·명확한 상대 위치의 검토 전 자동 대상 제안, `선택된 객체 확인` 도면 강조를 `main`에 반영했다. 도면 이동은 별도 승인 전에는 일어나지 않는다. 실제 호스트 강조와 사용자 계정 429 원인은 여전히 미확정이다.

- AutoCAD 2024 호환판: `archuni`에게 [#35](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/issues/35)를 별도 배정했다. `work/archuni/r03`에서 2024 전용 .NET Framework 4.8 빌드·공존 번들·실제 호스트 검증을 진행한다. 기존 #18/PR #34는 유지한다. 2024 호환 기능은 아직 구현·검증되지 않았다.

- 출품안 확정: `설계 변경 피드백 루프`, 분야 `설계·엔지니어링`. 기준 문서는 `docs/PROJECT_BRIEF.md`, 팀원 초안은 `HIMEC_아이디어_평가_및_워크플로우.md`.
- 목표: 2026-09-30까지 합성 대본 → 구조화 변경 → PDF 주석 → 사람 승인 데모를 먼저 완성. 이어 승인된 C1 이동 한 건을 합성 DXF 2장에 반영·검사한다. 관계도는 선택 기능.
- 팀원 4명 모두 API 키 사용 가능. OpenAI·Anthropic·Google Gemini 세 제공자 사용 예정이나 실제 통합·호출·비용 상한은 아직 검증 전. 키는 각자 로컬에만 둔다.
- Round 02 파일 계약: `prototype/CONTRACT.md`. #17~#20 이슈 배정, 세 팀원 `r02` 브랜치 원격 생성·SHA `14f199e` 확인. 팀장만 공통 문서와 C 단계 전파 코드를 편집한다.
- 제출: 실제 제출·팀명·대표·작성된 붙임 1~3·정확한 마감 시각은 별도 확인 필요. 고객/개인 자료는 공개 GitHub에 올리지 않는다.
- 제품 검증: C 단계의 계약 기반 합성 DXF 단위 테스트 5건 통과(Python 3.14.4, ezdxf 1.4.4). A/B 실제 산출물과의 통합, 실제 API 호출, AutoCAD에서 DXF 열기, PDF↔DWG 대응은 각각 별도로 확인해야 한다.
- 제출 문안: `docs/ATTACHMENT_4_DRAFT.md`에 붙임 4 내용 초안을 작성했다. 공식 DOCX 양식 반영·팀 정보·실제 데모 결과 갱신 전이며 제출 완료가 아니다.
- 사용자 추가 요청: AutoCAD 2026 플러그인을 우선 개발(#25). v0.1.2 `NETLOAD`·팔레트·예문 X 0 mm / Y +300 mm 화면 확인. 녹음 WAV 3개가 로컬에서 생성됐고 형식·길이·비영 신호 확인(내용 미청취). API 키가 로컬 환경에 없어 외부 전사는 호출 전 막혔을 가능성이 높고, 구버전 오류 상태란이 화면 아래에 있었다. v0.2.1에 이번 실행 전용 키 입력·기존 WAV 선택·상단 오류·어두운 4단계 UI·기둥 선택 안전장치를 반영했고, 사용자별 설치 후 AutoCAD 재시작/새 UI 표시까지 확인했다. API 호출과 플러그인 승인·DWG 이동/UNDO는 미검증이다. 팀원 #17/#18/#20 작업은 유지한다.
- 공동 개발 배포: 사용자 결정에 따라 실제 전사/편집의 최종 검증 전에 v0.2.1-preview 소스를 PR #26/#27의 squash merge로 `main`에 공유했다. [GitHub Release](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/releases/tag/v0.2.1-preview)의 팀 배포 ZIP에는 설치 스크립트와 `README_INSTALL_KO.md`가 들어 있다. 원격 Release 파일을 다시 내려받아 SHA-256 일치를 확인했다. 설치·업데이트·개별 API 키 안내는 `docs/AUTOCAD_PLUGIN_TEAM_INSTALL.md`, 팀원 AI 붙여넣기 문장은 `prompts/TEAM_INSTALL_AUTOCAD_PLUGIN.md`를 따른다. 이는 기능 완성/제출 검증을 의미하지 않는다.
- 녹음 태그 개발: 기존에는 태그 목록 기능이 없었다. v0.3.1 소스에 녹음 중 객체 직접 선택/시각 기록, 전사문 언급 목록, 태그 이름 수정·추가·삭제·재연결, WAV별 로컬 세션 저장을 추가했다. 실시간 음성 자동 태그와 모호한 객체의 자동 확정은 아직 아니다. 로직 검사 18건, 독립 UI/저장 검사, AutoCAD 2026 v0.3.0의 태그 카드 표시를 확인했다. v0.3.1은 PR #29로 `main`에 병합하고 [시험용 Release](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/releases/tag/v0.3.1-preview)를 공개했다. v0.3.1 실제 호스트 전체 흐름은 미검증이다.
- 실시간 태그 RT-01: [PR #32](https://github.com/jaeseonghong-a11y/himec-ai-idea-contest-2026/pull/32)로 완료된 전사 문장·근사 시각·객체 후보·확정 상태의 순수 데이터 계약을 `main`에 병합했다. 정확히 하나인 식별자만 검토 전 제안으로 연결하고, 복수/0개·일반 명사는 선택 필요로 남긴다. 사용자 삭제 뒤 같은 전사 이벤트가 반복돼도 다시 태그를 만들지 않는다. 기존 세션 JSON 역호환과 로직 테스트, AutoCAD 2026 DLL 빌드는 통과했다. 실제 스트리밍, 녹음 연동, AutoCAD 호스트의 새 UI는 아직 구현·검증하지 않았다.

## Recommended Next Step

0. AutoCAD 2026을 다시 열어 설치된 v0.5.1-lab에서 동일한 **시험용** WAV로 Gemini 전사를 재시도하고 성공 모델명 또는 상태 코드를 확인한다. 키·녹음 파일·전체 서버 응답을 GitHub에 기록하지 않는다.

0. 관계도 편집기와 플러그인은 아직 별도 데모다. `prototype/relation-editor/README.md`로 관계도 데모를 재현하고, A/B/C/D 계약과 연결할 데이터 변환은 후속 과제로 정한다. 실제 공개 도면을 다른 서비스/API에 전송하거나 추가 공개하지 않는다.

0. 합성 시험 도면에서 팔레트 크기 조절, 단일/복수 객체 태그, 선택 강조, 24 kHz 녹음·재열기를 현 설치판으로 검증한다. 시험용 음성의 외부 전송은 사용자 동의 후 수행하며, 오류가 나면 로컬 WAV와 구버전 백업을 보존한다.

1. 기존 미저장 `Drawing1.dwg`의 시험 변경은 `autocad-plugin/dist/Drawing1-session-backup-20260929-155328.dwg`로 보존하고 다시 열어 두었다. 새 태그 기능은 합성 WAV와 `three_columns_mm.dxf`를 **삽입이 아닌 열기**로 연 시험 사본에서 객체 연결·이름 편집·재열기를 검사한다. 실제 프로젝트 도면은 사용하지 않는다. 키는 사용자가 가림 입력창에 직접 넣고 시험용 음성으로 API 전사를 별도 확인한다. 이후 후보/수동 선택·승인·블록 이동/UNDO도 별도 시험한다.
2. 팀원에게 `prompts/ROUND_02_START.md`와 플러그인 설치가 필요하면 `prompts/TEAM_INSTALL_AUTOCAD_PLUGIN.md`를 전달한다. #17/#18/#20은 기존 계획대로 진행하고, 입력/출력 계약과 플러그인 연계는 통합 시 확인한다.
3. 팀장 AI가 팀원 PR을 통합해 #19를 재검증하고, 출품 문안에는 실제 구현·검증된 부분만 반영한다.

## 최신 체크포인트

### 2026-09-29 / AutoCAD 플러그인 v0 우선 개발

- 변경: AutoCAD 2026 .NET 플러그인, 녹음/전사 팔레트, 로컬 규칙 이동 추출, 기둥 후보 추천(제한적), 수동 선택, 승인 후 블록 이동, 번들 패키징 코드 작성.
- 검증: `.NET 8` 파서·대상 선택 검사 10건과 팔레트 WAV 선택/오류 상태 검사 통과, 호스트 빌드 오류 0개, v0.2.1 번들 필수 DLL 포함. v0.1.2에서 사용자 제공 `HIMEC` 팔레트·예문 X 0/Y +300 mm 화면 확인. v0.2.1 사용자별 설치·AutoCAD 재시작·새 UI/키 미설정 안내 실제 호스트 화면 확인(`docs/assets/autocad-palette-v0.2.1-host.png`). AutoCAD MCP `health` 및 합성 DXF의 기둥 블록 3개/mm 단위 감사 성공. MCP 쓰기 1회는 IPC 시간 초과로 실패했고 감사 결과 이동 없음 확인·복구 수행. 별도 합성 도면 복사본에서 AutoCAD COM 블록 이동 Y 0→300→0 확인 후 저장 없이 닫음(플러그인 실행 검증 아님). WAV 3개 메타데이터, 420×640/1200 독립 UI 미리보기, 사용자별 설치 스크립트의 시험 경로 설치·백업 확인. `WindowsBase` 버전 충돌 빌드 경고 1개는 남아 있다.
- 미검증: 녹음 장치 음성 품질·OpenAI 실제 전사·플러그인 승인 후 DWG 편집/UNDO, AutoCAD 2024. 새 UI 표시만으로 전체 기능을 검증했다고 보지 않는다.
- 팀 배포: v0.2.1 번들을 포함한 ZIP 12파일·266636바이트를 생성했다. ZIP 안에 한국어 설치 README, 설치 스크립트, 매니페스트, 필수 DLL이 있는지 확인했고 SHA-256은 `114AB5A9C77A0A9CC588D110F6858BA8ED2373F08BC8FFA1E9AE2E4ACB493423`이다. ZIP 압축 해제 후 README·DLL을 원본과 해시 대조했고, GitHub Release에 업로드한 파일을 다시 다운로드해 ZIP 해시 일치도 확인했다.
- 후속 녹음 태그: v0.3.1 소스·번들·팀 ZIP 제작. 태그 순수 로직 검사 18건, 독립 팔레트의 합성 WAV 선택/태그 행/객체 연결/로컬 저장 검사, v0.3.0 개발 번들의 AutoCAD 2026 태그 카드 표시 확인. 실제 음성 자동 태그는 미구현이고 실제 AutoCAD의 태그 편집 전체 흐름은 미검증. v0.3.1 ZIP SHA-256 `D0CE547F3DEE4AC047AEBEDCA76AB8E09AC2409DB10F17548FD8146128D7C72C`; GitHub Release를 다시 다운로드해 동일 해시를 확인했다.

### 2026-09-29 / 붙임 4 내용 초안

- 변경: 확정 아이디어·공식 배점·현재 검증 경계에 맞춘 출품 문안 작성. 공식 양식은 아직 편집하지 않음.
- 검증: SRC-001/003/004 정리와 초안의 사실·팀 해석 구분 대조. 실제 제출 서류 적합성 및 데모 통합은 미검증.
- 위험: 팀명·대표·기능 실적이 미확정이고, 팀원 PR 결과에 따라 문안을 다시 써야 함.

### 2026-09-29 / C 단계 승인된 DXF 이동 단위 구현

- 변경: 승인 로그를 갖춘 C1 Y+500 mm 한 건만 A-101/A-301 합성 DXF 사본에 적용하고, E-201 영향 검토를 보고한다. 원본은 덮어쓰지 않는다.
- 검증: `python -m unittest discover -s prototype/tests -v` 5건 통과. 승인 누락, 예상 밖 명령, 매핑 누락·중복·핸들 불일치를 차단한다.
- 미검증: A/B 산출물, 실제 LLM, PDF 주석, AutoCAD 열기, 설비 간섭·구조 안전성.
