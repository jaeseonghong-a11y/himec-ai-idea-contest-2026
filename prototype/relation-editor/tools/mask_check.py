"""가린 도면 파일 안에 알아볼 수 있는 정보가 남아 있는지, 파일 내용을 직접 검색한다.

찾을 낱말은 저장소에 적지 않는다. 명령줄이나 파일로 넘긴다.
사용: python tools/mask_check.py real_dxf 낱말1 낱말2 ...
      python tools/mask_check.py real_dxf @낱말목록.txt
"""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
folder = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "real_dxf")
words = []
for a in sys.argv[2:]:
    words += Path(a[1:]).read_text(encoding="utf-8").split() if a.startswith("@") else [a]
SHAPES = re.compile(r"\d{2,3}[)-]\s?\d{3,4}-\d{4}|[\w.]+@[\w.]+\.\w+|www\.[\w.]+|https?://\S+|(?:Documents and Settings|Users)\\(?!user\\)[^\\\r\n]+\\")
bad = 0
for f in sorted(folder.glob("*.dxf")):
    raw = f.read_bytes()
    hits = []
    for w in words:
        forms = [w.encode("utf-8"), "".join("\\U+%04X" % ord(c) if ord(c) > 127 else c for c in w).encode()]
        for enc in ("cp949", "utf-16-le"):
            try:
                forms.append(w.encode(enc))
            except UnicodeEncodeError:
                pass
        if any(b in raw for b in forms):
            hits.append(w)
    txt = raw.decode("utf-8", errors="replace")
    txt = re.sub(r"\{[0-9A-Fa-f-]{36}\}", "", txt)                                  # 블록 식별 번호(GUID)는 전화번호가 아니다
    txt = "\n".join(l for l in txt.splitlines() if "Product Desc:" not in l and "Enabler" not in l)      # CAD 프로그램 제작사 안내문
    more = sorted(set(SHAPES.findall(txt)))
    print(f"{f.name}: 낱말 {hits or '없음'} | 전화·메일·주소·계정 모양 {more or '없음'}")
    bad += len(hits) + len(more)
print("통과" if not bad else "확인 필요")
sys.exit(1 if bad else 0)
