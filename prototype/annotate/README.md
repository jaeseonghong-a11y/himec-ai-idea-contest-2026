# B-2 단계 — PDF 주석과 사람 승인

`changes.json`의 각 변경을 합성 PDF 위에 표시하고, 검토자의 승인·기각을 기록한다.
담당은 `archuni`(이슈 #18)다.

## 실행

```powershell
python prototype/annotate/run_annotate.py
python prototype/annotate/run_annotate.py --reviewer archuni --approve CR-001 --reject CR-004
python prototype/annotate/run_annotate.py --reviewer archuni --interactive
python -m unittest discover -s prototype/annotate/tests -t . -v
```

산출물은 `prototype/out/`에 쓴다. `annotations.json`(주석 계획)과, 원본 PDF가 있을 때
`annotated_<sheet>.pdf`가 만들어진다. 원본 PDF는 수정하지 않는다.

## 위치 확정과 경고

사이드카가 해당 핸들에 `pdf_page`와 `pdf_rect_pt`를 **명시**했을 때만 위치를 확정해 주석을 쓴다.
그 외에는 전부 경고로 남기고 좌표를 추정하지 않는다.

| 경고 | 뜻 |
|---|---|
| `도면 미확정` | 발화에서 대상 도면을 특정할 수 없음 |
| `대상 객체 미확정` | 태그를 특정할 수 없음 |
| `사이드카에 해당 핸들 매핑 없음` | 태그는 있으나 사이드카에 일치하는 핸들이 없음 |
| `사이드카에 PDF 좌표 없음` | 매핑은 있으나 A가 좌표를 제공하지 않음 |

PDF에서 CAD 핸들을 역추출하지 않는다. 좌표는 A가 합성 PDF를 만들 때 함께 기록한 값만 쓴다.

## 승인 규칙

- 승인·기각에는 `reviewer`와 ISO 8601 `reviewed_at`이 함께 기록된다.
- `confirmed`는 C 단계가 실제로 적용할 수 있는 변경(`A-101` / `C1` / `move` / `dy_mm 500`)에만 붙는다.
  그 밖의 항목을 승인하면 `needs_review`로 남고 검토 기록만 추가된다. C 단계가 거부할 변경을
  승인 상태로 넘기지 않기 위한 장치다.
- `confirmed`는 최대 한 건이다. 두 건 이상이면 저장하지 않고 중단한다.

## PDF 주석기

`pdfstamp.py`는 외부 의존성 없이 증분 업데이트(incremental update)로 주석을 덧붙인다.
원본 바이트는 그대로 두고 뒤에 새 객체와 xref를 붙이므로 변경 이력이 그대로 남는다.
고전적인 `xref` 테이블만 지원하며, 상호참조 스트림(PDF 1.5+)은 파일을 쓰지 않고 오류로 보고한다.
한글은 UTF-16BE 16진 문자열로 기록한다.
