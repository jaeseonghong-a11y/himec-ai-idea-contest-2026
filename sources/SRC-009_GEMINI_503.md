# Gemini 전사 HTTP 503 처리 근거 (2026-09-30)

- 사용자 화면: `v0.5.0-lab`의 Gemini 파일 전사에서 HTTP 503. 이는 서버 응답 상태 확인이지 키/계정 상태를 직접 확인한 결과가 아니다. 기존 플러그인은 모든 오류에 결제·한도·권한·네트워크를 함께 제시해 오해를 불렀다.
- Google [API errors](https://ai.google.dev/gemini-api/docs/api-errors): 503 `service_unavailable`은 일시적인 과부하 또는 서비스 중단. 401/403과 구분해야 한다.
- Google [Troubleshooting](https://ai.google.dev/gemini-api/docs/troubleshooting): 503·429 같은 일시 오류에 제한된 지수 백오프와 지터 권장. 400/403 같은 요청·권한 오류에는 재시도하지 않는다.
- Google [Gemini 3.5 Flash 모델 카드](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash): 음성 입력·텍스트 출력 지원. 3.8 Flash가 두 차례 일시 오류일 때 한 번만 대체 모델로 시도한다. 사용한 모델을 플러그인 상태줄에 알린다.

구현 경계: 녹음 파일을 외부 전송하기 전에 사용자 동의를 받고, 그 확인창에 최대 3회 시도를 명시한다. 동일 파일을 같은 Gemini 서비스로 다시 보낼 수 있으므로 요금·개인정보 취급은 각 계정 조건에 따른다. 응답 본문/API 키는 화면·로그에 출력하지 않는다. 합성 HTTP 테스트는 실제 서비스 상태나 사용자 계정의 성공을 증명하지 않는다.
