# B-1 단계 — 변경지시 추출

합성 회의 대본에서 설계 변경 지시를 뽑아 `prototype/CONTRACT.md`의 `changes.json` 형식으로 저장한다.
담당은 `archuni`(이슈 #18)이고 이 디렉터리와 `prototype/annotate/`만 편집한다.

## 실행

```powershell
python prototype/extract/run_extract.py
python prototype/extract/run_extract.py --provider openai
python -m unittest discover -s prototype/extract/tests -t . -v
```

기본 실행은 `mode: fixture_replay`다. `--provider`를 주면 해당 환경변수(`OPENAI_API_KEY`,
`ANTHROPIC_API_KEY`, `GEMINI_API_KEY`)에서 키를 읽어 한 번 호출하고, 키가 없거나 호출이
실패하면 저장된 예시 재생으로 내려간다. 키는 로컬 환경변수에만 두고 저장소·팀 채팅에 올리지 않는다.

## 규칙

- `source.quote`는 대본에 실제로 있는 문자열이어야 한다. 아니면 항목 전체를 거부한다.
- 사이드카에 `(sheet, tag)` 매핑이 정확히 하나일 때만 `target.handle`을 채운다. 없거나 중복이면
  `handle: null` + `needs_review`로 두고 좌표를 추정하지 않는다.
- `confidence`는 항상 `null`이다. 제공자가 보정된 확률을 주지 않으므로 점수를 신뢰도처럼 쓰지 않는다.
- 실행 가능한 변경은 `A-101` / `C1` / `move` / `dx_mm 0, dy_mm 500` 한 건뿐이다. 나머지는 근거가
  확인돼도 `needs_review`로 남아 주석·검토까지만 간다.
- `mode: fixture_replay`는 저장된 예시 재생이며 실시간 AI 추론 결과가 아니다.

## 합성 예시

`fixtures/`의 파일은 전부 팀이 만든 합성 자료다. 실제 회의·고객 도면이 아니다.

| 파일 | 내용 |
|---|---|
| `transcript_demo.txt` | 5문장 대본 (명확한 지시 3, 모호한 지시 1, 잡담 1) |
| `replay_changes.json` | 제공자 응답을 대신하는 저장된 예시 4건 |
| `sidecar_A-101.json`, `sidecar_A-301.json` | A(`kijun-0108`)의 `prototype/sidecar/` 산출물이 나오기 전까지 쓰는 임시 사이드카 |

A의 실제 사이드카가 병합되면 `--sidecars prototype/out`으로 바꿔 실행하고 위 임시 파일은 팀장 판단에 따라 정리한다.
