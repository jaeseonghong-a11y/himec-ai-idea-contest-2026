"""DXF → 사이드카 JSON (0단계).

PDF 출력 시점에 함께 남길 객체 대응표. 여기서는 DXF에서 직접 읽는다.
출력: out/sidecar_<sheet>.json
"""
import json
import sys
from pathlib import Path
import ezdxf

ROOT = Path(__file__).resolve().parents[1]


def bbox_of(entity):
    try:
        from ezdxf import bbox
        b = bbox.extents([entity])
        if b.has_data:
            return [round(b.extmin.x), round(b.extmin.y), round(b.extmax.x), round(b.extmax.y)]
    except Exception:
        pass
    return None


def build(dxf_path: Path, sheet: str):
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    objects = []
    for e in msp:
        t = e.dxftype()
        rec = {"handle": e.dxf.handle, "type": t, "layer": e.dxf.layer}
        if t == "INSERT":
            rec["block"] = e.dxf.name
            rec["insert"] = [round(e.dxf.insert.x), round(e.dxf.insert.y)]
            attrs = {a.dxf.tag: a.dxf.text for a in e.attribs}
            rec["tag"] = attrs.pop("TAG", None)
            rec["attrs"] = attrs
        elif t == "LINE":
            rec["start"] = [round(e.dxf.start.x), round(e.dxf.start.y)]
            rec["end"] = [round(e.dxf.end.x), round(e.dxf.end.y)]
        elif t in ("TEXT", "MTEXT"):
            rec["text"] = e.dxf.text if t == "TEXT" else e.text
            p = e.dxf.insert
            rec["insert"] = [round(p.x), round(p.y)]
        elif t == "LWPOLYLINE":
            rec["points"] = [[round(x), round(y)] for x, y, *_ in e.get_points()]
        else:
            continue
        rec["bbox"] = bbox_of(e)
        objects.append(rec)

    # 보 라벨(B01 등)을 가장 가까운 S-BEAM 선에 붙인다
    labels = [o for o in objects if o["type"] == "TEXT" and o["layer"] == "S-BEAM"]
    beams = [o for o in objects if o["type"] == "LINE" and o["layer"] == "S-BEAM"]
    for lb in labels:
        lx, ly = lb["insert"]
        best = min(beams, key=lambda b: (lx - (b["start"][0] + b["end"][0]) / 2) ** 2 + (ly - (b["start"][1] + b["end"][1]) / 2) ** 2)
        best["tag"] = lb["text"]

    sidecar = {
        "sheet": sheet,
        "dwg": str(dxf_path.relative_to(ROOT)).replace("\\", "/"),
        "units": "mm",
        "insunits": doc.header.get("$INSUNITS"),
        "object_count": len(objects),
        "objects": objects,
    }
    out = ROOT / "out" / f"sidecar_{sheet}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(sidecar, ensure_ascii=False, indent=1), encoding="utf-8")
    return out, sidecar


if __name__ == "__main__":
    sheet = sys.argv[1] if len(sys.argv) > 1 else "A-101"
    out, sc = build(ROOT / "samples" / f"{sheet}.dxf", sheet)
    kinds = {}
    for o in sc["objects"]:
        k = f'{o["type"]}:{o["layer"]}'
        kinds[k] = kinds.get(k, 0) + 1
    print(f"saved {out} | {sc['object_count']} objects")
    for k, v in sorted(kinds.items()):
        print(f"  {k}: {v}")
