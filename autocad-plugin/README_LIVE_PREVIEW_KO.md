# AutoCAD 2026 실시간 전사·객체 태그 개발판

이 문서는 `work/jaeseonghong-a11y/r05-live-transcription`의 개발 동작을 설명한다. 현재 공개된 `v0.3.1-preview` ZIP에는 이 기능이 없다. **AutoCAD 호스트·실제 OpenAI 계정 검증 전에는 팀 배포판으로 취급하지 않는다.**

## 사용 흐름

1. 합성 시험 도면을 `열기`로 열고 `HIMEC`를 실행한다. 실제 고객 도면과 회의는 사용하지 않는다.
2. `녹음 시작`을 누른다. WAV는 로컬 `%LOCALAPPDATA%\Himec\Recordings`에 저장된다.
3. `전사 API 키 입력`에 본인의 OpenAI API 키를 넣는다. 키는 이번 실행 메모리에만 둔다.
4. `실시간 전사 시작`을 누르고 매 녹음마다 별도 동의창의 체크박스를 직접 선택한다. 동의한 시점 이후의 마이크 PCM만 OpenAI로 전송한다. 도면 데이터나 태그는 전송하지 않는다.
5. 확정된 말은 전사문과 태그 목록에 추가된다. `C1`처럼 도면 블록의 이름·속성값과 정확히 하나만 일치하면 `제안 연결 · 확인 필요`로 보인다. 복수/0건, `기둥` 같은 일반어는 `선택 필요`다.
6. `선택된 객체 확인`으로 도면 선택 강조를 보고, 맞으면 `제안 연결 확정`을 누른다. 틀리면 `객체 연결 해제` 후 `선택 태그에 객체 지정`으로 직접 선택한다. 이 단계는 도면 자체를 수정하지 않는다.
7. `실시간 전사 중지` 또는 `녹음 중지`를 누른다. 녹음 파일은 계속 로컬에 남는다. 별도의 `지시 승인`·`승인된 변경 실행` 없이는 도면 이동이 일어나지 않는다.

## 오류와 제한

- 녹음 후 `녹음 전사(API 호출)`은 **파일 전사**이고, 위 실시간 기능과 별개다.
- HTTP 429는 API 잔액·지출 한도·속도 제한 등을 의미할 수 있다. 실제 계정의 [결제·잔액](https://platform.openai.com/settings/organization/billing/overview)과 [한도](https://platform.openai.com/settings/organization/limits)를 확인해야 한다. 로컬 코드가 계정의 결제 상태를 고칠 수는 없다.
- 실시간 전사는 OpenAI `gpt-live-transcribe` 사용 권한과 네트워크가 필요하다. 무료 API 등급에서는 모델 접근이 제한될 수 있다. 실제 요금과 한도는 계정에서 확인한다.
- 현재는 약 4초 단위로 오디오를 마감한다. 이는 발화 경계의 정확한 검출이 아니며 단어 중간에서 잘릴 수 있다. 태그 시각도 근사값이다.
- 24 kHz PCM을 지원하지 않는 마이크 장치에서는 녹음 시작이 실패할 수 있다. 이 경우 장치 지원 형식을 확인해야 한다.
- 비밀키, 실제 음성, 고객 도면은 GitHub 이슈·PR·로그에 첨부하지 않는다.

## 현재 검증 경계

- .NET 8 AutoCAD 2026 DLL 빌드와 가짜 완료 이벤트/동의 전 PCM 차단/태그 저장의 독립 검사는 통과했다.
- 실제 AutoCAD 팔레트의 새 기능 로드, 마이크 24 kHz 품질, 실제 OpenAI WebSocket 연결·429 원인, 도면 선택 강조는 아직 현장 검증 전이다.
- 이전 번들을 덮어써 시험하려면 AutoCAD를 완전히 종료하고 `install-user.ps1`의 백업/복원 절차를 따른다. 원본 도면은 사용하지 않는다.

API 계약 근거: [OpenAI 실시간 전사 가이드](https://developers.openai.com/api/docs/guides/realtime-transcription), [429 안내](https://help.openai.com/en/articles/5955604-troubleshooting-api-rate-limits-and-429-errors).
