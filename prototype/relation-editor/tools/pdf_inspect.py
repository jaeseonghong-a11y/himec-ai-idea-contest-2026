"""PDF 안에 레이어·벡터 선·문자가 남아 있는지 조사."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import fitz
from collections import Counter
path = sys.argv[1]
doc = fitz.open(path)
page = doc[0]
print("pymupdf", fitz.__doc__.split()[1] if fitz.__doc__ else "", "| pages", len(doc), "| page size(pt)", page.rect, "| producer:", doc.metadata.get("producer"), "| creator:", doc.metadata.get("creator"))
ocgs = doc.get_ocgs()
print(f"\n== PDF 레이어(OCG): {len(ocgs)}개")
names = sorted(v["name"] for v in ocgs.values())
print("  ", names)
dr = page.get_drawings()
print(f"\n== 벡터 경로: {len(dr)}개")
by_layer = Counter(d.get("layer") or "(레이어 없음)" for d in dr)
for l, n in by_layer.most_common(45): print(f"   {l:30s} {n}")
items = Counter(it[0] for d in dr for it in d["items"])
print("   경로 요소 종류:", dict(items), "(l=선, c=곡선, re=사각형, qu=사변형)")
print("\n== 레이어별 선 속성 (색, 굵기, 점선)")
for l in ("CEN", "COL", "WAL", "RXDIM", "DOOR", "WID-S", "마감선"):
    ds = [d for d in dr if d.get("layer") == l]
    if not ds: print(f"   {l}: 없음"); continue
    col = Counter(tuple(round(c, 2) for c in (d.get("color") or ())) for d in ds).most_common(2)
    wid = Counter(round(d.get("width") or 0, 3) for d in ds).most_common(2)
    dash = Counter(d.get("dashes") for d in ds).most_common(2)
    print(f"   {l:8s} n={len(ds):4d} color={col} width={wid} dashes={dash}")
words = page.get_text("words")
print(f"\n== 문자(실제 글자로 남은 것): {len(words)}개 단어")
print("   예:", [w[4] for w in words[:40]])
nums = [w[4] for w in words if w[4].replace(",", "").isdigit()]
print("   숫자 문자(치수 후보):", len(nums), nums[:30])
blocks = page.get_text("dict")["blocks"]
fonts = Counter(s["font"] for b in blocks if b["type"] == 0 for l in b["lines"] for s in l["spans"])
print("   글꼴:", dict(fonts.most_common(6)))
print("   이미지 블록:", sum(1 for b in blocks if b["type"] == 1), "| 주석(annots):", len(list(page.annots() or [])))
pix = page.get_pixmap(dpi=110); out = path.replace(".pdf", "_page.png"); pix.save(out); print("\nsaved", out)
