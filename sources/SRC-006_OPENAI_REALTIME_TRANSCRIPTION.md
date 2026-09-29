# SRC-006 — OpenAI 실시간 전사 API 규격

- 원본: [OpenAI Realtime transcription guide](https://developers.openai.com/api/docs/guides/realtime-transcription)
- 함께 확인한 원본: [OpenAI Realtime VAD guide](https://developers.openai.com/api/docs/guides/realtime-vad), [OpenAI Speech-to-text guide](https://developers.openai.com/api/docs/guides/speech-to-text)
- 유형: 공급사 공식 개발 문서
- 확인일: 2026-09-29
- 원본 보존 상태: 웹 기반의 수시 갱신 문서이므로 이 파일은 원문 사본이 아니라, 확인 시점과 프로젝트 적용 범위를 기록한 인덱스다. 구현 전과 릴리스 전 원문을 다시 확인한다.

## 확인한 사실

1. OpenAI의 실시간 전사 안내는 `gpt-live-transcribe`를 실시간 마이크 전사 모델로 제시하며, 전사 세션(`type: transcription`)과 24 kHz PCM 오디오 입력을 설명한다.
2. 부분 전사 결과와 완료 전사 결과는 구분되어 전달된다. 프로젝트에서는 부분 결과를 화면 표시용으로만 쓰고, 완료 결과만 세션·태그 후보에 저장한다.
3. `gpt-live-transcribe`에서는 turn detection을 생략하거나 `null`로 두고, 발화 끝에 클라이언트가 오디오 버퍼 commit을 보내는 방식이 요구된다.
4. 해당 가이드는 `gpt-live-transcribe`에 단어별 시간, 화자 구분, 신뢰도 점수를 제공하지 않는다고 명시한다.
5. 완료된 WAV 파일을 보내는 기존 전사와 실시간 마이크 전사는 다른 흐름이다. 현재 플러그인의 파일 전사 기능은 별도로 유지한다.

## 프로젝트 해석

- 실시간 전사는 사용자의 명시 동의 뒤에만 시작하고, 로컬 PCM 프레임을 짧게 보내는 경로로 제한한다.
- 발화 종료는 클라이언트 무음 감지 또는 사용자의 중지로 처리하며, 서버 VAD가 자동으로 해결한다고 가정하지 않는다.
- 화면에 보이는 발화 시각은 녹음 프레임 누적 기준 근사치일 뿐, 단어별 정확한 타임코드라고 표시하지 않는다.
- 실제 요청·비용·속도·장치 호환성은 이 문서만으로 검증되지 않는다. `docs/REALTIME_SPEECH_OBJECT_TAGGING_PLAN.md`의 RT-05 수동 검증에서 분리해 기록한다.
