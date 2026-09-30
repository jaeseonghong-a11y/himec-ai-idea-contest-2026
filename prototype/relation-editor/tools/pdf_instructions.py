"""팀 플러그인이 출력한 '설계 변경 지시 일람표' PDF를 읽어, 확정된 지시만 도면에 반영한다.

PDF에는 표(번호 / 대상 / 변경 / 층 / 상태)가 실제 글자로 들어 있다. 사람이 단 주석이 아니라 표를 읽는다.
- 상태에 "확정"이 있고 "확인 필요"가 없는 행만 반영한다. 나머지는 보고서에만 남긴다.
- 대상은 태그(C1, COLUMN 1 ...)로 도면에서 찾는다. 그 태그 글자에 가장 가까운 기둥(블록 또는 사각 폴리선) 하나가 대상이다.
  태그가 여러 개(예: 기둥 타입 표기 C1이 12개)면 대상을 확정할 수 없으므로 반영하지 않고 보고한다.
- 대상에 "#8E"처럼 DXF 객체 핸들이 붙어 있으면(플러그인이 도면에서 고른 객체) 그 핸들의 객체를 바로 대상으로 삼는다.
  핸들이 도면에 없으면(다른 도면이거나 다시 저장되어 핸들이 바뀐 경우) 태그로 찾는 방식으로 돌아간다.
- 변경은 "X +300 mm", "Y -200 mm" 꼴의 이동만 처리한다. 기둥과 함께 기둥에 닿아 있던 선의 끝점도 같이 옮긴다(띠 STRETCH).
- 원본은 건드리지 않고 out/real/<이름>_pdf_edited.dxf 로 쓴다.

사용: python tools/pdf_instructions.py <지시 PDF>              # 편집기용 JSON(out/real/instructions_*.json)으로 변환
      python tools/pdf_instructions.py <지시 PDF> <대상 DXF>   # 관계도 없이 도면 객체를 직접 옮김
"""
import json
import re
import sys
from pathlib import Path

import ezdxf
import pymupdf

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "propagate"))
from stretch import stretch_region  # noqa: E402

MOVE = re.compile(r"^([XY])\s*([+-]?\d+)\s*mm$", re.I)
HANDLE = re.compile(r"^(.*?)\s*#([0-9A-Fa-f]{1,16})$")      # "C1 #8E" → 태그 C1, 핸들 8E


def split_target(target):
    m = HANDLE.match(target.strip())
    return (m.group(1).strip(), m.group(2).upper()) if m else (target.strip(), None)


def read_table(pdf_path):
    """표 글자를 줄로 묶어 지시 목록을 만든다."""
    doc = pymupdf.open(pdf_path)
    items, page_no = [], None
    for pno, pg in enumerate(doc):
        words = pg.get_text("words")
        hdr = [w for w in words if w[4] == "번호"]
        if not hdr:
            continue
        page_no = pno
        x_num, y_hdr = hdr[0][0], hdr[0][1]
        cols = {w[4]: w[0] for w in words if abs(w[1] - y_hdr) < 3 and w[4] in ("번호", "대상", "변경", "층", "상태")}
        bounds = sorted(cols.items(), key=lambda kv: kv[1])
        body = sorted((w for w in words if w[1] > y_hdr + 3 and w[0] >= x_num - 3 and w[0] <= max(c for _, c in bounds) + 120), key=lambda w: w[1])
        rows = []                                   # 기준선이 3pt 안에 있는 글자들을 한 줄로 (한글과 숫자의 기준선이 조금 다르다)
        for w in body:
            if rows and abs(rows[-1][0] - w[1]) <= 3:
                rows[-1][1].append(w)
            else:
                rows.append([w[1], [w]])
        for _, ws in rows:
            ws = sorted(ws, key=lambda w: w[0])
            if not re.fullmatch(r"\d+", ws[0][4]):
                continue
            cells = {name: [] for name, _ in bounds}
            for w in ws:
                name = max((n for n, x in bounds if w[0] >= x - 3), key=lambda n: cols[n], default=bounds[0][0])
                cells[name].append(w[4])
            txt = {k: " ".join(v) for k, v in cells.items()}
            status = "confirmed" if "확정" in txt.get("상태", "") and "확인" not in txt.get("상태", "") else "needs_review"
            m = MOVE.match(txt.get("변경", ""))
            tag, handle = split_target(txt.get("대상", ""))
            items.append({"no": int(txt["번호"]), "target": txt.get("대상", ""), "tag": tag, "handle": handle, "change": txt.get("변경", ""), "floor": txt.get("층", ""), "status_text": txt.get("상태", ""),
                          "status": status, "action": "move" if m else None, "axis": m.group(1).upper() if m else None, "delta": int(m.group(2)) if m else None})
        break
    notes = [l.strip() for l in doc[page_no].get_text("text").splitlines() if l.strip().startswith("[")] if page_no is not None else []
    return items, notes


def source_drawing(pdf_path):
    """제목 줄 '설계 변경 지시 일람표 — <도면 이름>'에서 도면 이름. 핸들은 그 도면 안에서만 뜻이 있다."""
    for pg in pymupdf.open(pdf_path):
        for l in pg.get_text("text").splitlines():
            m = re.search(r"설계 변경 지시 일람표\s*[—-]+\s*(\S+)", l)
            if m:
                return m.group(1)
    return None


def same_drawing(pdf_name, dxf_path):
    """PDF의 도면 이름과 DXF 파일 이름이 확장자를 빼고 같은가 (pdf-test.dxf.dwg ↔ pdf-test.dxf, pdf-test)."""
    if not pdf_name:
        return False
    strip = lambda n: re.sub(r"(\.(dwg|dxf))+$", "", n.lower())
    return strip(pdf_name) == strip(Path(dxf_path).name)


def entity_center(e):
    if e.dxftype() == "INSERT":
        return (e.dxf.insert.x, e.dxf.insert.y)
    if e.dxftype() == "LWPOLYLINE":
        pts = [(p[0], p[1]) for p in e.get_points("xy")]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        return ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
    return None


def is_column_entity(e):
    """Only a known column block or a four-corner COL outline may be moved."""
    if e.dxftype() == "INSERT":
        return e.dxf.name.upper() == "COLUMN"
    if e.dxftype() == "LWPOLYLINE" and e.closed and e.dxf.layer.upper() == "COL":
        pts = list(e.get_points("xy"))
        if len(pts) != 4:
            return False
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        return 250 <= max(xs) - min(xs) <= 1200 and 250 <= max(ys) - min(ys) <= 1200
    return False


def find_by_handle(doc, handle):
    """플러그인이 적은 객체 핸들로 바로 찾는다. 모델 공간의 블록 참조나 폴리선이어야 한다."""
    e = doc.entitydb.get(handle)
    if e is None or e.dxf.owner != doc.modelspace().block_record.dxf.handle or not is_column_entity(e):
        return None
    c = entity_center(e)
    if c is None:
        return None
    near = [(((t.dxf.insert.x - c[0]) ** 2 + (t.dxf.insert.y - c[1]) ** 2) ** 0.5, t.dxf.text.strip()) for t in doc.modelspace().query("TEXT")]
    near = min(near, default=None)
    return {"entity": e, "text": None, "xy": c, "handle": e.dxf.handle, "by": "handle", "near_text": near[1] if near and near[0] <= 1500 else None}


def find_target(doc, tag, handle=None):
    """핸들이 있으면 그 객체. 없으면 태그 글자에 가장 가까운 기둥(블록 참조 또는 250~1200 사각 폴리선). 후보 글자가 여러 개면 None과 개수."""
    if handle:
        t = find_by_handle(doc, handle)
        if t:
            return t, 1
    msp = doc.modelspace()
    alias = {tag}
    m = re.fullmatch(r"C(\d+)", tag)
    if m:
        alias.add(f"COLUMN {m.group(1)}")
    texts = [t for t in msp.query("TEXT") if t.dxf.text.strip() in alias]
    for ins in msp.query("INSERT"):
        for a in ins.attribs:
            if a.dxf.text.strip() in alias:
                texts.append(a)
    if len(texts) != 1:
        return None, len(texts)
    tp = texts[0].dxf.insert
    cands = []
    for e in msp:
        if e.dxftype() == "INSERT" and is_column_entity(e):
            cands.append((e, e.dxf.insert.x, e.dxf.insert.y))
        elif e.dxftype() == "LWPOLYLINE" and is_column_entity(e):
            pts = [(p[0], p[1]) for p in e.get_points("xy")]
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            if 250 <= max(xs) - min(xs) <= 1200 and 250 <= max(ys) - min(ys) <= 1200:
                cands.append((e, (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2))
    if not cands:
        return None, 0
    e, cx, cy = min(cands, key=lambda c: (c[1] - tp.x) ** 2 + (c[2] - tp.y) ** 2)
    if ((cx - tp.x) ** 2 + (cy - tp.y) ** 2) ** 0.5 > 1500:
        return None, 0
    return {"entity": e, "text": texts[0], "xy": (cx, cy), "handle": e.dxf.handle, "by": "tag"}, 1


def apply(pdf_path, dxf_path):
    items, notes = read_table(pdf_path)
    doc = ezdxf.readfile(dxf_path)
    dwg = source_drawing(pdf_path)
    same = same_drawing(dwg, dxf_path)
    report = {"pdf": str(pdf_path), "dxf": str(dxf_path), "source_drawing": dwg, "same_drawing": same, "items": [], "notes": notes}
    changed = 0
    for it in items:
        rec = dict(it)
        if it["status"] != "confirmed":
            rec["result"] = "반영하지 않음: 상태가 확정이 아님"
        elif it["action"] != "move":
            rec["result"] = f'반영하지 않음: 처리할 수 없는 변경 "{it["change"]}"'
        else:
            tgt, n = find_target(doc, it.get("tag") or it["target"], it.get("handle"))
            if tgt is not None and tgt.get("by") == "handle" and not same:
                # 핸들은 PDF를 낸 도면 안에서만 뜻이 있다. 다른 도면이면 그 객체 옆 글자가 태그와 맞을 때만 받아들인다
                tag = it.get("tag") or ""
                alias = {tag} | ({f"COLUMN {tag[1:]}"} if re.fullmatch(r"C\d+", tag) else set())
                if not tag or tgt.get("near_text") not in alias:
                    rec["result"] = f'반영하지 않음: 핸들 #{it["handle"]}은 도면 "{dwg or "?"}"의 것인데 이 도면({Path(dxf_path).name})에서 그 핸들 옆 글자는 "{tgt.get("near_text") or "없음"}"으로 태그 "{tag}"와 맞지 않음. 도면을 확인할 것'
                    report["items"].append(rec)
                    continue
            if tgt is None:
                miss = f' (핸들 #{it["handle"]}도 이 도면에 없음)' if it.get("handle") else ""
                rec["result"] = f'반영하지 않음: 태그 "{it.get("tag") or it["target"]}"에 해당하는 기둥을 {"찾지 못함" if n == 0 else f"{n}개 찾아 하나로 정할 수 없음"}{miss}'
            else:
                dx, dy = (it["delta"], 0) if it["axis"] == "X" else (0, it["delta"])
                x, y = tgt["xy"]
                # 기둥 둘레 띠 안의 꼭짓점(기둥, 태그 글자, 기둥에 닿은 선 끝)을 함께 옮긴다
                inside = lambda px, py: abs(px - x) <= 700 and abs(py - y) <= 700
                r = stretch_region(doc, inside, dx, dy, exclude_handles=set())
                moved = f'{r["moved_count"]}개 {r["by_layer"]}' if isinstance(r, dict) else r
                how = (f'핸들 #{tgt["handle"]}로 찾음' + ("" if same else f' (PDF의 도면 "{dwg}"과 파일 이름이 다르지만 옆 글자 "{tgt.get("near_text")}"가 태그와 맞음)')) if tgt.get("by") == "handle" else f'태그 글자로 찾음(핸들 {tgt["handle"]})'
                if it.get("handle") and tgt.get("by") != "handle":
                    how += f', 지시의 핸들 #{it["handle"]}은 이 도면에 없어 태그로 대신 찾음'
                rec["result"] = f'반영: {it["target"]} ({x:.0f}, {y:.0f}) → ({x + dx:.0f}, {y + dy:.0f}), {how}, 함께 옮긴 객체 {moved}'
                rec["from_xy"], rec["to_xy"], rec["handle"] = [round(x), round(y)], [round(x + dx), round(y + dy)], tgt["handle"]
                changed += 1
        report["items"].append(rec)
    out = ROOT / "out" / "real" / f"{Path(dxf_path).stem}_pdf_edited.dxf"
    out.parent.mkdir(parents=True, exist_ok=True)
    if changed:
        doc.saveas(out)
        report["output"] = str(out)
    return report


def export_json(pdf_path):
    """편집기의 '지시 불러오기'가 읽는 JSON. 도면 없이 PDF만으로 만든다."""
    items, notes = read_table(pdf_path)
    out = ROOT / "out" / "real" / f"instructions_{Path(pdf_path).stem}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"source_pdf": Path(pdf_path).name, "items": items, "notes": notes}, ensure_ascii=False, indent=1), encoding="utf-8")
    return out, items


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if len(sys.argv) == 2:                      # PDF만 주면 편집기용 JSON으로 변환
        out, items = export_json(sys.argv[1])
        print(f"지시 {len(items)}건 → {out}")
        for it in items:
            print(f'  [{it["no"]}] {it["target"]} {it["change"]} {it["floor"]} / {it["status_text"]} ({it["status"]})')
        print("편집기에서 [지시 불러오기]로 이 파일을 열면 됩니다.")
        sys.exit(0)
    rep = apply(sys.argv[1], sys.argv[2])
    print(f'지시 {len(rep["items"])}건 (PDF: {Path(rep["pdf"]).name} → DXF: {Path(rep["dxf"]).name})')
    for it in rep["items"]:
        print(f'  [{it["no"]}] {it["target"]} {it["change"]} {it["floor"]} / {it["status_text"]} → {it["result"]}')
    for n in rep["notes"]:
        print("  주기:", n)
    if rep.get("output"):
        print("saved", rep["output"])
    (ROOT / "out" / "real" / "pdf_instructions_report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
