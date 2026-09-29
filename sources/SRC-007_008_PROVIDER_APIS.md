# 공급자 API 기능 경계 (2026-09-29 확인)

- Google 공식 [오디오 이해](https://ai.google.dev/gemini-api/docs/generate-content/audio): `generateContent`에 WAV `inlineData`를 보내 텍스트 응답을 받을 수 있다. 이 프로젝트는 10MB 로컬 WAV 상한 내에서 사용한다. 실제 계정·모델 접근 권한은 검증 전이다.
- Google 공식 [실시간 전사](https://ai.google.dev/gemini-api/docs/live-api/live-transcribe): `gemini-3.5-transcribe-live`, 16 kHz 16-bit PCM, `interimInputTranscription`/`inputTranscription`. 녹음기는 24 kHz이므로 전송 전에 16 kHz로 변환한다. WebSocket URL의 키는 화면·로그에 출력하지 않는다.
- Anthropic 공식 [Messages API](https://platform.claude.com/docs/en/api/messages/create)와 [기능 목록](https://platform.claude.com/docs/en/build-with-claude/overview): 전사문 텍스트를 Claude에 보내 검토할 수 있다. 직접 WAV를 입력해 음성 전사하는 API 경로는 확인되지 않았으므로 제공하지 않는다. 이는 지원 부재에 대한 문서 기반 판단이며 새로운 API 출시 시 재확인한다.
- OpenAI 파일/실시간 전사는 `SRC-005`·`SRC-006`의 기존 경로를 유지한다.

설계 결정: **음성 전사 제공자**는 OpenAI/Gemini, **텍스트 지시 검토 제공자**는 OpenAI/Gemini/Claude. AI 검토 결과는 읽기 전용 제안이다. CAD 이동량 추출은 기존 로컬 규칙을 통과하고, 대상 확인·승인·실행을 별도로 거친다. 키는 실행 중 메모리 또는 사용자 환경변수에서만 읽고 저장소에 넣지 않는다.
