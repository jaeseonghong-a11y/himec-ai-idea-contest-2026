# 합성 데모 실행 안내

파일 계약은 `CONTRACT.md`를 먼저 읽는다. 현재 구현된 것은 승인된 C1 이동을 합성 DXF 사본 2장에 반영하고 보고서를 만드는 C 단계다. A/B/D는 팀원 PR 대기 중이다. 통합 데모 전체가 작동한다고 주장하지 않는다.

필요 환경: Python, `ezdxf` (실행한 버전은 PR 검증란 확인). 설치 명령: `python -m pip install ezdxf`.

```powershell
python -m unittest discover -s prototype/tests -v
python prototype/run_demo.py --changes prototype/out/changes.json --samples prototype/samples --sidecars prototype/out --output prototype/out/propagated
```

두 번째 명령은 A의 DXF·사이드카와 B의 승인된 changes.json이 준비된 뒤에만 실행된다. 같은 출력 폴더를 덮어쓰지 않으므로 재실행할 때 `--output`에 새 경로를 지정한다. 원본 샘플은 수정하지 않는다. API 키·고객 도면·개인정보를 저장소에 넣지 않는다. 공개 예외는 `CONTRACT.md`의 관계도 프로토타입 4장에만 한정된다.
