"""도면에서 사무소·대지 위치·사람을 알 수 있는 정보를 가린 복사본을 만든다. 원본은 건드리지 않는다.

가리는 것
- 표제란 블록의 전화·팩스, 주소, 홈페이지 문자
- 표제란 안의 로고(채움 도형과 로고 블록). 글자가 아니라 그림이라 문자 검색에 걸리지 않으므로, 가린 뒤 그림으로 확인한다
- 도면 안의 대지 위치, 필지 번호 문자
- 파일 속성의 마지막 저장한 사람, 파일 안에 남은 컴퓨터 계정 이름
객체를 지우지 않고 글자만 비우므로 나머지 객체의 핸들은 그대로다(관계도와 시험이 핸들을 쓴다).

사용: python tools/mask_dxf.py A12 A13 A14 A15        # real_dxf/ → masked_dxf/
"""
import json
import re
import sys
from pathlib import Path

import ezdxf

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
SRC, DST = ROOT / "real_dxf", ROOT / "masked_dxf"
sys.path.insert(0, str(ROOT / "graph"))

# 표제란에서 지울 문자, 도면 안에서 지울 문자
TITLE = re.compile(r"TEL|FAX|www\.|https?://|\d{2,3}\)\s*\d{3,4}-\d{4}|\d{2,3}-\d{3,4}-\d{4}|(시|군|구|동|로|길)\s*\d|빌딩|\d+층$")
PLACE = re.compile(r"지구\s*[A-Z]-?\d|^[A-Z]\d?-\d+-\d+$|\d+-\d+\s*번지|번지")
CHECK = re.compile(r"TEL|FAX|www\.|\d{2,3}\)\s*\d{3,4}-\d{4}|빌딩|지구\s*[A-Z]-?\d|^[A-Z]\d?-\d+-\d+$|번지")
MARK = "(가림)"


def text_of(e):
    return (e.text if e.dxftype() == "MTEXT" else e.dxf.text).strip()


def set_text(e, s):
    if e.dxftype() == "MTEXT":
        e.text = s
    else:
        e.dxf.text = s


def all_text(doc):
    for lay in list(doc.blocks):
        for e in lay.query("TEXT MTEXT ATTRIB ATTDEF"):
            yield lay, e
    for ins in doc.query("INSERT"):
        for a in ins.attribs:
            yield None, a


def mask(sheet):
    doc = ezdxf.readfile(SRC / f"{sheet}.dxf")
    rep = {"sheet": sheet, "title_text": 0, "place_text": 0, "logo_entities": 0, "saved_by": False, "account": 0}
    title = [b for b in doc.blocks if any("TEL" in text_of(x) for x in b.query("TEXT MTEXT"))]
    for b in title:
        for e in b.query("TEXT MTEXT ATTDEF"):
            if TITLE.search(text_of(e)):
                set_text(e, "")
                rep["title_text"] += 1
        for e in list(b.query("HATCH SOLID IMAGE")):      # 로고: 표제란 안의 채움 도형(글자가 아니라 그림으로 그린 사무소 이름)
            b.delete_entity(e)
            rep["logo_entities"] += 1
        for ins in b.query("INSERT"):          # 로고: 표제란 안에 들어 있는 다른 블록. 속을 비운다
            logo = doc.blocks.get(ins.dxf.name)
            if logo is not None:
                for e in list(logo):
                    logo.delete_entity(e)
                    rep["logo_entities"] += 1
    seen = set()
    for _, e in all_text(doc):
        if id(e) in seen:
            continue
        seen.add(id(e))
        if PLACE.search(text_of(e)):
            set_text(e, MARK)
            rep["place_text"] += 1
    if doc.header.get("$LASTSAVEDBY"):
        doc.header["$LASTSAVEDBY"] = ""
        rep["saved_by"] = True
    DST.mkdir(exist_ok=True)
    out = DST / f"{sheet}.dxf"
    doc.saveas(out)
    raw = out.read_text(encoding="utf-8", errors="surrogateescape")      # 파일 안에 남은 컴퓨터 계정 이름
    new, n = re.subn(r"(Documents and Settings|Users)\\[^\\\r\n]+\\", lambda m: m.group(1) + "\\user\\", raw)
    if n:
        out.write_text(new, encoding="utf-8", errors="surrogateescape")
        rep["account"] = n
    return rep


def verify(sheet):
    """가린 뒤에 남은 것이 없는지, 관계도가 전과 같게 읽히는지."""
    import build_graph_real as bgr
    doc = ezdxf.readfile(DST / f"{sheet}.dxf")
    left = sorted({text_of(e)[:40] for _, e in all_text(doc) if CHECK.search(text_of(e))})
    raw = (DST / f"{sheet}.dxf").read_text(encoding="utf-8", errors="replace")
    paths = [m for m in set(re.findall(r"(?:Documents and Settings|Users)\\([^\\\r\n]+)\\", raw)) if m != "user"]

    def key(g):
        g = json.loads(json.dumps(g, ensure_ascii=False, default=str))
        g.pop("dwg", None)
        return json.dumps(g, ensure_ascii=False, sort_keys=True)
    a, b = bgr.build(SRC / f"{sheet}.dxf", sheet), bgr.build(DST / f"{sheet}.dxf", sheet)
    same = key(a) == key(b)
    art = sum(len(b.query("HATCH SOLID IMAGE")) + sum(len(doc.blocks.get(i.dxf.name) or []) for i in b.query("INSERT"))
              for b in doc.blocks if any(text_of(x) == "TITLE" for x in b.query("TEXT")))      # 표제란에 남은 그림
    left = left + ([f"표제란 그림 {art}개"] if art else [])
    return {"left_text": left, "left_account": paths, "saved_by": doc.header.get("$LASTSAVEDBY", ""), "graph_same": same,
            "graph": f'그리드 {len(b["grids"])}, 기둥 {sum(n["type"] == "column" for n in b["nodes"])}, 구간 {len(b["edges"])}, 문·창호 {len(b["openings"])}, 치수 {len(b["dims"])}'}


if __name__ == "__main__":
    sheets = sys.argv[1:] or ["A12", "A13", "A14", "A15"]
    ok = True
    for s in sheets:
        r = mask(s)
        v = verify(s)
        good = not v["left_text"] and not v["left_account"] and not v["saved_by"] and v["graph_same"]
        ok &= good
        print(f'{s}: 표제란 문자 {r["title_text"]}개, 로고 객체 {r["logo_entities"]}개, 위치 문자 {r["place_text"]}개, 저장한 사람 {"지움" if r["saved_by"] else "없음"}, 계정 이름 {r["account"]}곳')
        print(f'     남은 것: 문자 {v["left_text"] or "없음"}, 계정 {v["left_account"] or "없음"} | 관계도 {"전과 같음" if v["graph_same"] else "달라짐"} ({v["graph"]}) → {"통과" if good else "확인 필요"}')
    print("saved", DST)
    sys.exit(0 if ok else 1)
