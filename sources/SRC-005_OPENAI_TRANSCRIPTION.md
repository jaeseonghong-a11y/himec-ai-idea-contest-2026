# SRC-005 — OpenAI 파일 전사 API

- 공식 원본: [OpenAI Audio API Reference](https://platform.openai.com/docs/api-reference/audio/voice-consent-object?lang=curl)
- 확인일: 2026-09-29
- 확인된 사실: `POST /v1/audio/transcriptions`는 WAV 입력과 `gpt-4o-mini-transcribe` 모델을 지원한다. 기본 JSON 응답에는 `text`가 포함된다. `language=ko` 지정은 선택 사항이다.
- 제품 해석: 현재 플러그인은 사용자가 녹음 후 전사 버튼을 누르고 외부 전송을 확인했을 때만 해당 엔드포인트를 호출한다. API 키 없이는 외부 전사가 되지 않으며, 전사문 수동 입력은 가능하다.
- 검증 경계: 공식 문서의 형식 지원과 실제 이 PC의 API 요청 성공은 별개다. 실제 키를 사용한 네트워크 호출은 아직 수행하지 않았다.
