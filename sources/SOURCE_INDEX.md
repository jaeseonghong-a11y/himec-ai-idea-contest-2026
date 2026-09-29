# SOURCE INDEX

> 최신 등록 — **SRC-006 OpenAI 실시간 전사·발화 경계·파일 전사 가이드**: [Realtime transcription guide](https://developers.openai.com/api/docs/guides/realtime-transcription), `SRC-006_OPENAI_REALTIME_TRANSCRIPTION.md`, 확인일 2026-09-29, 상태: 실시간 전사 세션·24 kHz PCM·부분/완료 이벤트·수동 commit·제약 확인.

이 디렉터리는 모든 AI와 팀원이 공유하는 근거 저장소다. 공식 원본과 분석 문서를 분리하고, 확인하지 않은 내용을 사실처럼 쓰지 않는다.

| ID | 자료 | 유형 | 원본 위치 | 확인일 | 상태 |
|---|---|---|---|---|---|
| SRC-001 | 제1회 HIMEC AI 활용 아이디어 공모전 공고 | 주최사 공식 | `official/SRC-001_official_notice.pdf`, [공식 뉴스룸](https://www.himec.co.kr/ko/info/newsroom/?bbsid=33&gbn=viewok&ix=508&scroll=Y) | 2026-09-29 | 원본 확보·3쪽 시각 검토 |
| SRC-002 | 붙임 1~4 제출서류 | 주최사 공식 | `official/SRC-002_submission_forms.docx`, `.hwp` | 2026-09-29 | 원본 확보·DOCX 필드 추출 |
| SRC-003 | 하이멕 업무·산업 맥락 | 주최사 공식 웹 | `SRC-003_HIMEC_CONTEXT.md`의 링크 | 2026-09-29 | 페이지별 확인 |
| SRC-004 | 건축설비엔지니어링 DX 구축 사례 및 AI 전략 | 하이멕 저자 학술발표 논문 | `official/SRC-004_HIMEC_DX_AI_strategy.pdf`, [게시물](https://www.himec.co.kr/ko/info/technical/?gbn=viewok&gp=2&ix=427) | 2026-09-29 | 원본 확보·4쪽 전체 시각 검토 |
| SRC-005 | OpenAI 녹음 파일 전사 API 규격 | 공급자 공식 개발 문서 | [Audio API Reference](https://platform.openai.com/docs/api-reference/audio/voice-consent-object?lang=curl), `SRC-005_OPENAI_TRANSCRIPTION.md` | 2026-09-29 | 엔드포인트·WAV·모델·JSON 텍스트 필드 확인 |

## 원본 무결성

`sources/official/`의 파일은 수정하지 않는다. 새 버전을 받으면 덮어쓰지 말고 날짜 또는 버전을 붙여 추가한 뒤 해시를 갱신한다.

| 파일 | SHA-256 |
|---|---|
| `HIMEC_AI_contest_official_package.zip` | `248268C10D432D1BF05CB8AC0397E5FDACE0BFBA2B56E09A3717A58E1E342901` |
| `SRC-001_official_notice.pdf` | `2E150234D229237E211928F07421D8FC53437A055A15DD64E66518B74698B979` |
| `SRC-002_submission_forms.docx` | `94A92E8462CB2B6DC99765D33B675DC1D68F581C11F1C2121024B871DC5CF6AA` |
| `SRC-002_submission_forms.hwp` | `17E504418D4D2BF5F3876411C2492724C22E0F5DE86F28590F7877ACCF863557` |
| `SRC-004_HIMEC_DX_AI_strategy.pdf` | `6D1B5D347D0CCFECE68919082631D81FA5D3C86D9F83D3FF3ED4906C4A754329` |

## 근거 사용 규칙

- `공식 확인`: SRC-001~004처럼 주최사 또는 원문에서 직접 확인한 사실
- `팀 가정`: 아이디어 설계를 위해 임시로 둔 가정이며 검증 계획을 함께 기록
- `분석`: 공식 사실을 바탕으로 한 팀의 해석이며 원문 문구로 가장하지 않음
- `미검증`: 접근하지 못했거나 제목만 확인한 자료
- 웹 수치와 일정은 바뀔 수 있으므로 최종 제출 전에 공식 페이지를 다시 확인
