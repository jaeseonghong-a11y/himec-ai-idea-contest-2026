# Round 02 파일 계약 (v1, 2026-09-29)

이 문서는 팀원 A/B/C/D가 서로 다른 브랜치에서 개발할 때의 최소 인터페이스다. 아이디어 초안의 7장을 구현 가능한 범위로 좁혔다. 계약 변경은 팀장에게 PR로 제안하고, 다른 작업자에게 알리기 전 독자적으로 바꾸지 않는다.

## 경로와 소유권

| 경로 | 담당 | 입력 / 출력 |
|---|---|---|
| `prototype/samples/`, `prototype/sidecar/` | A `kijun-0108` | 합성 DXF 3장, PDF, `transcript.txt`, 사이드카 생성 코드 |
| `prototype/extract/`, `prototype/annotate/` | B `archuni` | 대본·사이드카·PDF → 변경 목록·주석 PDF·승인 결과 |
| `prototype/propagate/`, `prototype/run_demo.py` | C 팀장 | 승인 목록·DXF → 수정 DXF·검사 보고서 |
| `prototype/graph/` | D `ehgudwns18` | 사이드카 → 관계 그래프·그림 (선택 기능) |

공통 `prototype/CONTRACT.md`, `docs/PROJECT_BRIEF.md`, `CURRENT_STATE.md`, `prototype/README.md`는 팀장만 편집한다. 각 팀원의 코드는 다른 담당자의 디렉터리를 수정하지 않는다. 생성 결과는 `prototype/out/`에 저장하고 Git에는 재현에 필요한 작은 합성 예시만 선택적으로 포함한다. 개인·고객 도면, 키, 실제 회의록은 금지한다.

## 공통 합성 사례

- 도면 ID: `A-101` 평면, `A-301` 단면, `E-201` 전기. 파일명은 `<sheet_id>.dxf`, `<sheet_id>.pdf`.
- 위치 단위: mm. `C1` 태그 블록을 A-101과 A-301에 하나씩 넣고 원본 좌표를 명시한다. `B12`는 C1 이동에 따라 재검토해야 할 보로 표시한다. E-201은 자동 변경 대상이 아니라 설비 영향 검토 도면이다.
- 대본 5문장: 명확한 변경 3건, 모호한 변경 1건, 잡담 1건. 예시·기대 정답을 함께 작성하고, 실제 회의 발화로 표현하지 않는다.

## JSON 형식

`prototype/out/sidecar_<sheet_id>.json` (A 산출):

```json
{
  "schema_version": 1,
  "sheet_id": "A-101",
  "source_dxf": "samples/A-101.dxf",
  "source_pdf": "samples/A-101.pdf",
  "unit": "mm",
  "coordinate_system": "synthetic_pdf_points",
  "objects": [
    {"handle": "1A", "tag": "C1", "type": "INSERT", "layer": "COLUMN", "xy_mm": [1000, 2000], "pdf_page": 0, "pdf_rect_pt": [100, 120, 130, 150]}
  ]
}
```

`pdf_rect_pt`는 합성 PDF를 만들 때 A가 함께 기록한 명시적 좌표다. PDF 파일에서 CAD 핸들을 역추출했다고 주장하지 않는다. A가 좌표를 만들 수 없으면 `null`로 두고 B는 위치 미확정 경고를 표시한다. `handle`은 시트별 고유 값이고 시트 간 연결은 `tag`로 한다.

`prototype/out/changes.json` (B 산출):

```json
{
  "schema_version": 1,
  "mode": "live_api",
  "provider": "openai",
  "items": [
    {
      "id": "CR-001",
      "source": {"quote": "C1 기둥을 위로 500 밀어주세요", "speaker": "synthetic-speaker-1", "time": "00:00:12"},
      "sheet": "A-101", "target": {"tag": "C1", "handle": "1A"},
      "action": "move", "params": {"dx_mm": 0, "dy_mm": 500},
      "confidence": null, "status": "proposed", "reviewer": null, "reviewed_at": null,
      "impacts": ["A-301", "E-201"]
    }
  ]
}
```

- `mode`: `live_api` 또는 `fixture_replay`. 후자는 저장된 예시를 재생한 것이며 AI 실시간 추론으로 소개하면 안 된다.
- `provider`: 실제 호출된 제공자만 적는다(`openai`, `anthropic`, `gemini`); replay면 `null`. 세 제공자를 *사용할 계획*인 것과 *검증 완료*는 다르다.
- `confidence`: 제공자가 보정된 확률을 주지 않으면 `null`. 임의 수치를 신뢰도처럼 꾸미지 않는다. 승인 기준은 명시적 대상 매칭과 검토자 판단이다.
- `status`: `proposed`, `needs_review`, `confirmed`, `rejected`, `applied`. B는 `confirmed`까지; C만 사본에서 `applied`로 전환한다. `confirmed`에는 `reviewer`와 ISO 8601 `reviewed_at` 필수.
- `source.quote`는 대본에 실제 있는 부분 문자열이어야 한다. 모호한 항목은 `needs_review`, `target.handle: null`로 두고 추정 좌표를 확정하지 않는다.
- 실행 가능한 범위는 `action: move`, `target.tag: C1`, `dx_mm: 0`, `dy_mm: 500` 한 건뿐이다. 다른 변경은 PDF 표시·검토까지만 한다.

## C 단계 안전 조건

1. `mode`와 제공자·승인 로그를 읽어 보고서에 기록한다.
2. `confirmed`이고 승인자·시각이 있는 C1 이동 한 건만 처리한다. 모호·기각·중복 또는 예상 외 명령은 수정하지 않고 보고한다.
3. 원본 `samples/*.dxf`를 덮어쓰지 않고 `out/modified_*.dxf`로 쓴다. 실행 전후 좌표를 기록한다.
4. A-101·A-301에 동일 태그가 정확히 하나씩 있는지 확인한다. 불일치 시 전체 변경을 중단한다. E-201은 영향 검토 대상으로 보고서에만 남긴다.
5. 보고서의 보 스팬 값은 실제 샘플 좌표에서 계산한 값만 쓰고, 구조 안전성 판단·설비 간섭 해결이라고 표현하지 않는다.

## API 키와 실행 상태

팀원 네 명은 각자 키를 사용할 수 있다. `.env`는 Git에서 제외한다. 키를 팀원 간에 전송하지 않는다. `prototype/.env.example`에는 변수 *이름*만 넣을 수 있다. 각 제공자 어댑터는 같은 `changes.json` 형식을 출력하며, 외부 호출 실패 시 명시적으로 `fixture_replay`로 전환한다. 어떤 모델이 실제로 호출되었는지는 PR 검증란에 모델명·호출 날짜·비용 또는 사용량을 기록하되 키·원본 응답의 개인정보는 기록하지 않는다.
