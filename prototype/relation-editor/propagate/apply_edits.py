"""편집기가 내보낸 changes.json → 실제 DXF 반영 (그리드 이동, 기둥·벽·보·문·창호의 추가/삭제/수정).

사용: python propagate/apply_edits.py A12 <changes.json> [expected.json]
출력: out/real/<sheet>_edited.dxf, <sheet>_edit_before.png, <sheet>_edit_after.png, edit_report.json
      expected.json(편집기의 최종 관계도 요약)을 주면, 수정된 도면에서 관계도를 다시 읽어 대조한다(왕복 검증).

적용 순서: 그리드 이동 → 삭제 → 기둥 단면 → 개구부 수정 → 추가. 좌표는 모두 최종 상태 기준.
도면 수정 방식은 실무의 캐드 조작을 따른다.
- 그리드 이동: 띠 STRETCH
- 개구부 이동: 개구부를 옮기고 양쪽 문틀 주변의 벽선 끝을 함께 STRETCH
- 개구부 크기 변경: 일람표의 타입 교체. 기존 기호를 지우고 그 타입이 그려진 곳의 기호를 복사(벽 방향이 다르면 회전, 안팎이 다르면 반전).
  문틀 위치만 새 폭에 맞춰 옮긴다. 일람표에 새로 추가한 타입은 복사할 원본이 없어 기본 기호를 그린다
- 개구부 추가: 벽선을 폭만큼 잘라내고 문틀선과 기호를 그림
- 개구부 삭제: 기호를 지우고 끊어진 벽선을 다시 이음
"""
import json
import math
import sys
from pathlib import Path

import ezdxf
import ezdxf.enums
from ezdxf import bbox as bb
from ezdxf.math import Matrix44

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "graph"))
from stretch import grid_move_with_checks, stretch_region  # noqa: E402
from apply_to_dxf import render_window, resize_poly  # noqa: E402
import drawing_std as std  # noqa: E402
import walls as wl  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out" / "real"
WALLS = ("WAL", "마감선", "단열재", "COL")   # 이 도면은 콘크리트 벽체를 COL 레이어에 그린다
ZONE = 450        # 벽 중심(그리드)에서 벽선이 있을 수 있는 거리
JAMB = 200        # 문틀 주변으로 보는 범위
ORDER = ["set_site", "move", "delete_core", "delete_grid", "delete_opening", "delete_wall", "delete_beam", "delete_column", "resize", "edit_opening",
         "add_grid", "add_column", "add_wall", "add_beam", "add_opening", "add_core", "mep_delete", "mep_relocate", "mep_route", "mep_add", "add_dims", "add_schedule"]


def ensure_layer(doc, name, color=7):
    if name not in doc.layers:
        doc.layers.add(name, color=color)


def pt(horiz, a, q):
    """벽 방향 좌표 a, 직각 방향 좌표 q → (x, y)"""
    return (a, q) if horiz else (q, a)


def aq(horiz, p):
    return (p[0], p[1]) if horiz else (p[1], p[0])


def explode_polys(msp, layers, horiz, s, e, wall_c, zone):
    n = 0
    for pl in list(msp.query("LWPOLYLINE")):
        if pl.dxf.layer not in layers:
            continue
        hit = False
        pts = [(p[0], p[1]) for p in pl.get_points()]
        if pl.dxf.layer == "COL" and 4 <= len(pts) <= 5:   # 기둥 사각형은 분해하지 않는다
            xs, ys = [q[0] for q in pts], [q[1] for q in pts]
            if 250 <= max(xs) - min(xs) <= 1200 and 250 <= max(ys) - min(ys) <= 1200:
                continue
        if pl.closed and len(pts) > 2:
            pts.append(pts[0])
        for p1, p2 in zip(pts, pts[1:]):
            (a1, q1), (a2, q2) = aq(horiz, p1), aq(horiz, p2)
            if max(a1, a2) >= s and min(a1, a2) <= e and max(q1, q2) >= wall_c - zone and min(q1, q2) <= wall_c + zone:
                hit = True
                break
        if hit:
            try:
                pl.explode()
                n += 1
            except Exception:
                pass
    return n


def wall_lines(msp, layers, horiz, wall_c, zone):
    """벽과 나란한 LINE: (entity, lo, hi, q)"""
    out = []
    for ln in msp.query("LINE"):
        if ln.dxf.layer not in layers:
            continue
        (a1, q1), (a2, q2) = aq(horiz, ln.dxf.start), aq(horiz, ln.dxf.end)
        if abs(q1 - q2) < 1 and abs(q1 - wall_c) <= zone and abs(a1 - a2) > 1:
            out.append((ln, min(a1, a2), max(a1, a2), q1))
    return out


def cross_lines(msp, layers, horiz, wall_c, zone, max_len=450):
    """벽을 가로지르는 짧은 LINE(문틀선 등): (entity, a)"""
    out = []
    for ln in msp.query("LINE"):
        if ln.dxf.layer not in layers:
            continue
        (a1, q1), (a2, q2) = aq(horiz, ln.dxf.start), aq(horiz, ln.dxf.end)
        if abs(a1 - a2) < 1 and abs(q1 - q2) <= max_len and min(q1, q2) >= wall_c - zone and max(q1, q2) <= wall_c + zone:
            out.append((ln, a1))
    return out


def set_line(ln, horiz, lo, hi, q):
    z = ln.dxf.start[2] if len(ln.dxf.start) > 2 else 0
    ln.dxf.start = (*pt(horiz, lo, q), z)
    ln.dxf.end = (*pt(horiz, hi, q), z)


def cut_range(doc, horiz, wall_c, s, e, layers=WALLS, zone=ZONE):
    """벽선에서 [s, e] 구간을 잘라낸다. 잘린 선들의 직각 방향 오프셋을 돌려준다."""
    msp = doc.modelspace()
    explode_polys(msp, layers, horiz, s, e, wall_c, zone)
    offsets, cut = [], 0
    for ln, lo, hi, q in wall_lines(msp, layers, horiz, wall_c, zone):
        if hi <= s + 1 or lo >= e - 1:
            continue
        offsets.append(q - wall_c)
        cut += 1
        keep_l, keep_r = lo < s - 1, hi > e + 1
        if keep_l and keep_r:
            msp.add_line(pt(horiz, e, q), pt(horiz, hi, q), dxfattribs={"layer": ln.dxf.layer, **({"lineweight": ln.dxf.lineweight} if ln.dxf.hasattr("lineweight") else {})})      # 잘린 나머지도 같은 굵기
            set_line(ln, horiz, lo, s, q)
        elif keep_l:
            set_line(ln, horiz, lo, s, q)
        elif keep_r:
            set_line(ln, horiz, e, hi, q)
        else:
            msp.delete_entity(ln)
    removed = 0
    for ln, a in cross_lines(msp, layers, horiz, wall_c, zone):
        if s + 1 < a < e - 1:
            msp.delete_entity(ln); removed += 1
    return offsets, {"cut_lines": cut, "removed_cross": removed}


def heal_range(doc, horiz, wall_c, s, e, layers=WALLS, zone=ZONE, tol=JAMB):
    """[s, e]에서 끊긴 벽선을 다시 잇는다."""
    msp = doc.modelspace()
    explode_polys(msp, layers, horiz, s - tol, e + tol, wall_c, zone)
    lines = wall_lines(msp, layers, horiz, wall_c, zone)
    left = [x for x in lines if abs(x[2] - s) <= tol]
    right = [x for x in lines if abs(x[1] - e) <= tol]
    joined, used = 0, set()
    for ln, lo, hi, q in left:
        if id(ln) in used:
            continue
        m = next((r for r in right if id(r[0]) not in used and r[0] is not ln and abs(r[3] - q) <= 5 and r[0].dxf.layer == ln.dxf.layer), None)
        if m:
            set_line(ln, horiz, lo, m[2], q)
            used.add(id(m[0]))
            msp.delete_entity(m[0]); joined += 1
    removed = 0
    for ln, a in cross_lines(msp, layers, horiz, wall_c, zone):
        if ln.is_alive and (abs(a - s) <= tol or abs(a - e) <= tol):
            msp.delete_entity(ln); removed += 1
    return {"joined": joined, "removed_jambs": removed, "unpaired_left": len(left) - joined}


def entities_of(doc, handles):
    return [doc.entitydb[h] for h in handles if h in doc.entitydb and doc.entitydb[h].is_alive]


def along_extent(ents, horiz):
    ext = bb.extents(ents, fast=True)
    if not ext.has_data:
        return None
    return (ext.extmin.x, ext.extmax.x) if horiz else (ext.extmin.y, ext.extmax.y)


def jamb_stretch(doc, horiz, wall_c, a_lo, a_hi, delta, exclude):
    dx, dy = (delta, 0) if horiz else (0, delta)
    def inside(x, y):
        a, q = (x, y) if horiz else (y, x)
        return a_lo <= a <= a_hi and abs(q - wall_c) <= ZONE
    # 벽 계열 레이어만 늘인다. 벽에 닿아 있는 칸막이·가구·지시선 끝점이 끌려가지 않도록
    return stretch_region(doc, inside, dx, dy, exclude_handles=exclude, only_layers=WALLS, rigid_cross=True)


# ---------- 기호 ----------
_SRC_DOCS = {}


def clean_layers(doc):
    """다른 도면에서 딸려 온 레이어가 이 도면에 없는 재질·출력 스타일을 가리키면 그 참조를 지운다(AutoCAD 도면 검사 오류 방지)."""
    n = 0
    base = doc.layers.get("0")
    for layer in doc.layers:
        for attr, kind in (("material_handle", "MATERIAL"), ("plotstyle_handle", "ACDBPLACEHOLDER")):
            if not layer.dxf.hasattr(attr):
                continue
            h = layer.dxf.get(attr)
            target = doc.entitydb.get(h)
            if target is None or target.dxftype() != kind:     # 없는 객체이거나 엉뚱한 객체를 가리킴
                if base is not None and base.dxf.hasattr(attr) and base.dxf.get(attr) != h:
                    layer.dxf.set(attr, base.dxf.get(attr))
                else:
                    layer.dxf.discard(attr)
                n += 1
    return n


def snapshot_donor(doc, donor, sheet):
    """타입의 원본 기호를 다른 편집보다 먼저 떠 둔다(원본이 뒤에 지워지거나 옮겨져도 쓸 수 있게).
    원본이 다른 도면에 있으면 그 도면에서 가져와 이 도면으로 들여온다(레이어·선종류 포함)."""
    src_sheet = donor.get("sheet") or sheet
    label = donor["id"] if src_sheet == sheet else f'{src_sheet} 도면 {donor["id"]}'
    if src_sheet == sheet:
        ents = entities_of(doc, donor["handles"])
        if not ents:
            return None
        return {"masters": [e.copy() for e in ents], "xy": donor["xy"], "horiz": donor["horiz"], "id": label, "sheet": src_sheet}
    from ezdxf.addons import Importer
    if src_sheet not in _SRC_DOCS:
        _SRC_DOCS[src_sheet] = ezdxf.readfile(ROOT / "real_dxf" / f"{src_sheet}.dxf")
    sdoc = _SRC_DOCS[src_sheet]
    ents = [sdoc.entitydb[h] for h in donor["handles"] if h in sdoc.entitydb]
    if not ents:
        return None
    msp = doc.modelspace()
    before = {e.dxf.handle for e in msp}
    imp = Importer(sdoc, doc)
    imp.import_entities(ents, msp)
    imp.finalize()
    clean_layers(doc)
    new = [e for e in msp if e.dxf.handle not in before]
    masters = [e.copy() for e in new]
    for e in new:
        msp.delete_entity(e)
    return {"masters": masters, "xy": donor["xy"], "horiz": donor["horiz"], "id": label, "sheet": src_sheet}


def place_donor(doc, snap, horiz, center_xy, want_sign=0):
    """원본 기호를 복사해 목표 위치에 놓는다. 벽 방향이 다르면 회전, 안팎이 뒤집히면 반전."""
    import math
    msp = doc.modelspace()
    dx, dy = snap["xy"]
    chain = [Matrix44.translate(-dx, -dy, 0)]
    rotated = snap["horiz"] != horiz
    if rotated:
        chain.append(Matrix44.z_rotate(math.pi / 2))
    chain.append(Matrix44.translate(center_xy[0], center_xy[1], 0))
    m = Matrix44.chain(*chain)
    new = []
    for master in snap["masters"]:
        c = master.copy()
        try:
            c.transform(m)
            msp.add_entity(c)
            new.append(c)
        except Exception:
            pass
    wall_c = center_xy[1] if horiz else center_xy[0]
    ext = bb.extents(new, fast=True)
    mirrored = False
    if ext.has_data and want_sign:
        q = ((ext.extmin.y + ext.extmax.y) / 2 if horiz else (ext.extmin.x + ext.extmax.x) / 2) - wall_c
        if abs(q) > 30 and (q > 0) != (want_sign > 0):
            mm = Matrix44.chain(Matrix44.translate(0, -wall_c, 0), Matrix44.scale(1, -1, 1), Matrix44.translate(0, wall_c, 0)) if horiz else \
                 Matrix44.chain(Matrix44.translate(-wall_c, 0, 0), Matrix44.scale(-1, 1, 1), Matrix44.translate(wall_c, 0, 0))
            for c in new:
                try:
                    c.transform(mm)
                except Exception:
                    pass
            mirrored = True
    return new, {"copied": len(new), "rotated": rotated, "mirrored": mirrored}


def wall_band(doc, horiz, wall_c, s, e, thick=200):
    """[s, e] 양 끝에서 끝나는 벽선들의 직각 방향 범위 (벽 두께 구간)"""
    qs = [x[3] for x in wall_lines(doc.modelspace(), WALLS, horiz, wall_c, ZONE) if abs(x[2] - s) <= 30 or abs(x[1] - e) <= 30]
    if len(qs) >= 2 and max(qs) - min(qs) >= 50:
        return min(qs), max(qs)
    return wall_c - thick / 2, wall_c + thick / 2


def draw_generic(doc, kind, leaves, horiz, s, e, qlo, qhi, side=1):
    """일람표에 새로 추가한 타입(복사할 원본 없음)의 기본 기호."""
    msp = doc.modelspace()
    if kind == "window":
        ensure_layer(doc, "WID", 4)
        qm = (qlo + qhi) / 2
        for q in (qlo, qm - 25, qm + 25, qhi):
            msp.add_line(pt(horiz, s, q), pt(horiz, e, q), dxfattribs={"layer": "WID"})
        return 4
    ensure_layer(doc, "DOOR", 4)
    q0 = qhi if side >= 0 else qlo
    w = (e - s) / max(1, leaves)
    n = 0
    for k, (hinge_a, direction) in enumerate([(s, 1), (e, -1)][:max(1, leaves)]):
        hinge = pt(horiz, hinge_a, q0)
        tip = pt(horiz, hinge_a, q0 + side * w)
        msp.add_line(hinge, tip, dxfattribs={"layer": "DOOR"})
        # 호: 문짝 끝에서 반대편 문틀 쪽으로 90도
        import math
        a_open = math.degrees(math.atan2(tip[1] - hinge[1], tip[0] - hinge[0]))
        closed = pt(horiz, hinge_a + direction * w, q0)
        a_closed = math.degrees(math.atan2(closed[1] - hinge[1], closed[0] - hinge[0]))
        a1, a2 = a_closed, a_open
        if (a2 - a1) % 360 > 180:
            a1, a2 = a2, a1
        msp.add_arc(hinge, w, a1, a2, dxfattribs={"layer": "DOOR"})
        n += 2
    return n


# ---------- 개별 동작 ----------
def do_move(doc, ch, log):
    p = ch["params"]
    res = grid_move_with_checks(doc, p["axis"], p["old_coord"], p["delta"])
    ok = all(c["ok"] for c in res["column_checks"])
    log.append(f'{ch["id"]} 그리드 {ch["target"]} {p["delta"]:+.0f}: 객체 {res["moved_count"]}개 이동, 치수 {[str(d["old"]) + "→" + str(d["new"]) for d in res["dims"] if d["old"] != d["new"]]}, 기둥-벽선 {"OK" if ok else "확인 필요"}')
    return {"moved": res["moved_count"], "dims": res["dims"], "checks": res["column_checks"], "flagged": res["flagged"]}


def do_delete_grid(doc, ch, log):
    msp = doc.modelspace()
    n = 0
    for e in entities_of(doc, ch["params"]["handles"]):
        msp.delete_entity(e); n += 1
    log.append(f'{ch["id"]} 그리드 {ch["target"]} 삭제: 선 {n}개')
    return {"deleted": n}


def do_delete_opening(doc, ch, log):
    p, msp = ch["params"], doc.modelspace()
    ents = entities_of(doc, p["handles"])
    if not ents:
        log.append(f'{ch["id"]} {ch["target"]} 삭제: 도면 객체를 찾지 못함'); return {"deleted": 0}
    horiz = p["horiz"]
    s, e = along_extent(ents, horiz)
    ext = bb.extents(ents, fast=True)
    # 벽 중심: 개구부 객체들의 직각 방향 범위 중 벽선이 있는 쪽. 문 궤적 때문에 범위가 치우치므로 벽선으로 추정
    cands = [x[3] for x in wall_lines(msp, WALLS, horiz, (ext.extmin.y + ext.extmax.y) / 2 if horiz else (ext.extmin.x + ext.extmax.x) / 2, 1500) if abs(x[2] - s) <= JAMB or abs(x[1] - e) <= JAMB]
    wall_c = sum(cands) / len(cands) if cands else ((ext.extmin.y + ext.extmax.y) / 2 if horiz else (ext.extmin.x + ext.extmax.x) / 2)
    for x in ents:
        msp.delete_entity(x)
    h = heal_range(doc, horiz, wall_c, s, e)
    log.append(f'{ch["id"]} {ch["target"]} 삭제: 객체 {len(ents)}개 삭제, 벽선 {h["joined"]}쌍 이음, 문틀선 {h["removed_jambs"]}개 제거')
    return {"deleted": len(ents), **h}


def seg_params(p):
    (x1, y1), (x2, y2) = p["from_xy"], p["to_xy"]
    horiz = abs(y1 - y2) < 1
    s, e = (min(x1, x2), max(x1, x2)) if horiz else (min(y1, y2), max(y1, y2))
    return horiz, (y1 if horiz else x1), s, e


def do_delete_wall(doc, ch, log):
    horiz, wall_c, s, e = seg_params(ch["params"])
    off, st = cut_range(doc, horiz, wall_c, s, e)
    log.append(f'{ch["id"]} 벽 삭제 {ch["target"]}: 벽선 {st["cut_lines"]}개 잘라냄, 가로선 {st["removed_cross"]}개 제거')
    return st


def do_delete_beam(doc, ch, log):
    if ch["params"].get("evidence") == "columns":
        log.append(f'{ch["id"]} 보 삭제 {ch["target"]}: 도면에 그려진 보 선이 없음(기둥 사이 구조 추정). 관계도에만 반영')
        return {"cut_lines": 0}
    horiz, wall_c, s, e = seg_params(ch["params"])
    off, st = cut_range(doc, horiz, wall_c, s, e, layers=("HID",))
    log.append(f'{ch["id"]} 보 삭제 {ch["target"]}: 은선 {st["cut_lines"]}개 잘라냄')
    return st


def do_delete_column(doc, ch, log):
    p, msp = ch["params"], doc.modelspace()
    n, cx, cy = 0, p["xy"][0], p["xy"][1]
    w, h = map(float, p["spec"].split("x"))
    for e in entities_of(doc, [p["handle"]] if p.get("handle") else []):
        ext = bb.extents([e], fast=True)
        if ext.has_data:
            cx, cy = (ext.extmin.x + ext.extmax.x) / 2, (ext.extmin.y + ext.extmax.y) / 2
        msp.delete_entity(e); n += 1
    wrap = 0
    for pl in list(msp.query("LWPOLYLINE")):   # 기둥을 감싼 마감 사각형
        if pl.dxf.layer not in WALLS:
            continue
        ext = bb.extents([pl], fast=True)
        if ext.has_data and abs((ext.extmin.x + ext.extmax.x) / 2 - cx) <= 80 and abs((ext.extmin.y + ext.extmax.y) / 2 - cy) <= 80 and ext.size.x <= w + 500 and ext.size.y <= h + 500:
            msp.delete_entity(pl); wrap += 1
    log.append(f'{ch["id"]} 기둥 삭제 {ch["target"]}: 기둥 {n}개, 감싼 마감선 {wrap}개 삭제')
    return {"deleted": n, "wrap": wrap}


def do_resize(doc, ch, log):
    n = 0
    for imp in ch["impacts"]:
        if imp.get("kind") == "column" and imp.get("new_spec") and imp.get("handle") in doc.entitydb:
            resize_poly(doc.entitydb[imp["handle"]], imp["new_spec"]); n += 1
            log.append(f'{ch["id"]} 기둥 {imp["element"]} 단면 {imp["old_spec"]} → {imp["new_spec"]}')
    if not n:
        log.append(f'{ch["id"]} {ch["target"]} 단면 변경: 도면 객체 없음(새로 추가한 기둥은 추가 단계에서 최종 단면으로 그림)')
    return {"resized": n}


def opening_blocked(p, s, e):
    """그릴 수 없는 개구부인지: 벽의 기둥 면 사이를 벗어나거나 다른 개구부와 겹치면 그리지 않는다(편집기가 이미 경고한 상태)."""
    clear = p.get("clear")
    if clear and (s < clear[0] - 1 or e > clear[1] + 1):
        return f"폭 {e - s:.0f}({s:.0f}~{e:.0f})이 벽의 기둥 면 사이({clear[0]:.0f}~{clear[1]:.0f})를 벗어남"
    if p.get("overlaps"):
        return f'다른 개구부 {", ".join(p["overlaps"])}와 겹침'
    return None


def do_edit_opening(doc, ch, log):
    p, msp = ch["params"], doc.modelspace()
    ents = entities_of(doc, p["handles"])
    if not ents:
        log.append(f'{ch["id"]} {ch["target"]} 수정: 도면 객체를 찾지 못함'); return {"ok": False}
    horiz, hs = p["horiz"], set(p["handles"])
    wall_c = p["center_to"][1] if horiz else p["center_to"][0]
    c_to = p["center_to"][0] if horiz else p["center_to"][1]
    w_to = p.get("width_to") or p.get("width_from") or 0
    why = opening_blocked(p, c_to - w_to / 2, c_to + w_to / 2)
    if why:
        log.append(f'{ch["id"]} {ch["target"]} 수정: {why}. 원래 자리에 그대로 둠. 편집기 경고대로 고친 뒤 다시 반영해야 함')
        return {"ok": False, "skipped": why}
    s, e = along_extent(ents, horiz)
    ext = bb.extents(ents, fast=True)
    q_old = ((ext.extmin.y + ext.extmax.y) / 2 if horiz else (ext.extmin.x + ext.extmax.x) / 2) - wall_c
    notes, info = [], {"ok": True}
    if p["shift"]:
        dx, dy = (p["shift"], 0) if horiz else (0, p["shift"])
        for x in ents:
            x.translate(dx, dy, 0)
        r = jamb_stretch(doc, horiz, wall_c, s - JAMB, e + JAMB, p["shift"], hs)
        s, e = s + p["shift"], e + p["shift"]
        notes.append(f'이동 {p["shift"]:+.0f} (벽선 {r["moved_count"]}개 STRETCH)')
    if p.get("type_to") and p["type_to"] != p.get("type_from"):
        # 타입 교체: 기존 기호를 지우고, 문틀 위치를 새 폭에 맞춘 뒤, 그 타입의 기호를 넣는다 (늘이지 않는다)
        c = (p["center_to"][0] if horiz else p["center_to"][1])
        for x in ents:
            msp.delete_entity(x)
        grow = (p["width_to"] - p["width_from"]) / 2
        rl = jamb_stretch(doc, horiz, wall_c, s - JAMB, s + JAMB, -grow, ())
        rr = jamb_stretch(doc, horiz, wall_c, e - JAMB, e + JAMB, grow, ())
        ns, ne = c - p["width_to"] / 2, c + p["width_to"] / 2
        snap = ch.get("_donor")
        if snap:
            new, st = place_donor(doc, snap, horiz, pt(horiz, c, wall_c), want_sign=(1 if q_old > 0 else -1) if abs(q_old) > 30 else 0)
            notes.append(f'타입 {p["type_from"]}({p["width_from"]}) → {p["type_to"]}({p["width_to"]}): {snap["id"]}의 기호 {st["copied"]}개 복사' + (", 90도 회전" if st["rotated"] else "") + (", 반전" if st["mirrored"] else "") + f', 문틀 벽선 {rl["moved_count"] + rr["moved_count"]}개 이동')
            info.update(st)
        else:
            qlo, qhi = wall_band(doc, horiz, wall_c, ns, ne)
            n = draw_generic(doc, p["type"], p.get("leaves_to", 1), horiz, ns, ne, qlo, qhi, side=1 if q_old >= 0 else -1)
            notes.append(f'타입 {p["type_from"]}({p["width_from"]}) → {p["type_to"]}({p["width_to"]}): 새 타입이라 기본 기호 {n}개를 그림, 문틀 벽선 {rl["moved_count"] + rr["moved_count"]}개 이동')
    log.append(f'{ch["id"]} {ch["target"]} 수정: ' + ", ".join(notes))
    return info


def KOR(doc):
    return {"style": "KOR"} if "KOR" in doc.styles else {}


def new_drawing():
    """맨땅에서 시작하는 새 도면. 읽기 쪽이 아는 레이어 이름을 그대로 쓴다."""
    doc = ezdxf.new("R2013", setup=True)
    doc.header["$INSUNITS"] = 4
    if "KOR" not in doc.styles:
        doc.styles.add("KOR", font="malgun.ttf")     # 한글이 깨지지 않게
    std.apply_profile(doc)      # 역할별 레이어, 색, 선 굵기, 선종류, 치수 스타일 (layer_profile.json)
    return doc


def do_set_site(doc, ch, log):
    p = ch["params"]
    ensure_layer(doc, "SITE", 30)
    msp = doc.modelspace()
    lt = next((n for n in ("PHANTOM", "DASHDOT", "CENTER") if n in doc.linetypes), None)
    attr = {"layer": "SITE"}
    if lt:
        attr["linetype"] = lt
    msp.add_lwpolyline([tuple(q) for q in p["pts"]], close=True, dxfattribs=attr)
    cx = sum(q[0] for q in p["pts"]) / len(p["pts"]); ymin = min(q[1] for q in p["pts"])
    msp.add_text(f'대지경계선  {p["area_m2"]} ㎡', dxfattribs={"layer": "SITE", "height": 300, **KOR(doc)}).set_placement((cx - 2000, ymin - 700))
    log.append(f'{ch["id"]} 대지경계선 {len(p["pts"])}점, {p["area_m2"]} ㎡')
    return {"added": 1}


CORE_APP = "HIMEC_CORE"     # 코어 객체에 심는 확장 데이터. 도면에서 관계도로 다시 읽을 때 쓴다


def core_tag(doc, ents, cid, info=None):
    if CORE_APP not in doc.appids:
        doc.appids.add(CORE_APP)
    for i, e in enumerate(ents):
        tags = [(1000, cid)]
        if info is not None and i == 0:      # 첫 객체(외곽선)에 코어 정보 전체
            s = json.dumps(info, ensure_ascii=False, separators=(",", ":"))
            tags += [(1000, s[k:k + 200]) for k in range(0, len(s), 200)]
        e.set_xdata(CORE_APP, tags)


def core_entities(doc, cid):
    return [e for e in doc.modelspace() if e.has_xdata(CORE_APP) and e.get_xdata(CORE_APP)[0].value == cid]


def do_delete_core(doc, ch, log):
    ents = core_entities(doc, ch["target"])
    for e in ents:
        doc.modelspace().delete_entity(e)
    log.append(f'{ch["id"]} 코어 {ch["target"]} 삭제: 객체 {len(ents)}개' + ("" if ents else " (도면에 표식이 있는 코어 객체가 없음)"))
    return {"deleted": len(ents)}


def do_add_core(doc, ch, log):
    p, msp = ch["params"], doc.modelspace()
    ensure_layer(doc, "CORE", 34)
    r, at = p["rect"], {"layer": "CORE"}
    old = core_entities(doc, ch["target"])      # 바뀐 코어는 지우고 다시 그린다
    for e in old:
        msp.delete_entity(e)
    n_before = len(msp)
    lead = r.get("lead", 0)
    ref = dict(at)
    if getattr(doc, "_himec_union", False):      # 안치수 외곽선은 다시 읽기 위한 기준선. 보이는 선은 합쳐 그린 벽선이 맡으므로 출력하지 않는 레이어에 둔다
        if "CORE-REF" not in doc.layers:
            doc.layers.add("CORE-REF", color=8).dxf.plot = 0
        ref = {"layer": "CORE-REF"}
    msp.add_lwpolyline([(r["x0"], r["y0"]), (r["x1"], r["y0"]), (r["x1"], r["y1"]), (r["x0"], r["y1"])], close=True, dxfattribs=ref)
    n = 1
    if p["kind"] == "elevator":
        msp.add_line((r["x0"], r["y0"]), (r["x1"], r["y1"]), dxfattribs=at)
        msp.add_line((r["x0"], r["y1"]), (r["x1"], r["y0"]), dxfattribs=at)
        n += 2
        note = f'{r["w"]}x{r["d"]}'
    else:
        k = p["calc"]
        vert, sgn = p["dir"] in ("N", "S"), (1 if p["dir"] in ("N", "E") else -1)
        for i in range(k["treads_per_flight"] + 1):
            off = lead + i * k["tread"]
            if vert:
                y = (r["y0"] if sgn > 0 else r["y1"]) + sgn * off
                msp.add_line((r["x0"], y), (r["x1"], y), dxfattribs=at)
            else:
                x = (r["x0"] if sgn > 0 else r["x1"]) + sgn * off
                msp.add_line((x, r["y0"]), (x, r["y1"]), dxfattribs=at)
            n += 1
        if vert:   # 두 계단 사이 틈과 올라가는 방향
            xm, y0 = (r["x0"] + r["x1"]) / 2, (r["y0"] if sgn > 0 else r["y1"]) + sgn * lead
            msp.add_lwpolyline([(xm - 50, y0), (xm + 50, y0), (xm + 50, y0 + sgn * k["run"]), (xm - 50, y0 + sgn * k["run"])], close=True, dxfattribs=at)
        else:
            ym, x0 = (r["y0"] + r["y1"]) / 2, (r["x0"] if sgn > 0 else r["x1"]) + sgn * lead
            msp.add_lwpolyline([(x0, ym - 50), (x0, ym + 50), (x0 + sgn * k["run"], ym + 50), (x0 + sgn * k["run"], ym - 50)], close=True, dxfattribs=at)
        n += 1
        note = f'층고 {k["floor_height"]}, {k["risers"]}단, 단높이 {k["riser"]}, 단너비 {k["tread"]}'
    # 둘러싼 벽 (관계도의 그리드 벽과 구분되도록 따로 둔 레이어)
    prof = std.load_profile()
    WL = std.layer_of(prof, "core_wall")
    ensure_layer(doc, WL, prof["roles"]["core_wall"]["color"])
    merged = getattr(doc, "_himec_core_lines", {}).pop(ch["target"], None) if getattr(doc, "_himec_union", False) else None
    if merged is None:
        for w in r.get("walls", []):
            msp.add_lwpolyline([(w["x0"], w["y0"]), (w["x1"], w["y0"]), (w["x1"], w["y1"]), (w["x0"], w["y1"])], close=True, dxfattribs={"layer": WL})
            n += 1
    g = r.get("gap")
    if g and p["kind"] == "elevator":      # 승강기 문: 벽 두께 가운데에 문짝 두 장
        hz = g["side"] in ("N", "S")
        m = (g["y0"] + g["y1"]) / 2 if hz else (g["x0"] + g["x1"]) / 2
        lo, hi = (g["x0"], g["x1"]) if hz else (g["y0"], g["y1"])
        mid = (lo + hi) / 2
        for a0, a1, off in ((lo, mid, -25), (mid, hi, 25)):
            q0, q1 = m + off - 20, m + off + 20
            pts = [(a0, q0), (a1, q0), (a1, q1), (a0, q1)] if hz else [(q0, a0), (q0, a1), (q1, a1), (q1, a0)]
            msp.add_lwpolyline(pts, close=True, dxfattribs=at)
            n += 1
    elif g and merged is None:               # 계단실 출입구: 문틀선만 (합쳐 그릴 때는 외곽선에 이미 들어 있다)
        hz = g["side"] in ("N", "S")
        for a0 in ((g["x0"], g["x1"]) if hz else (g["y0"], g["y1"])):
            msp.add_line((a0, g["y0"]) if hz else (g["x0"], a0), (a0, g["y1"]) if hz else (g["x1"], a0), dxfattribs=at)
            n += 1
    for ar in r.get("arrows", []):           # 올라가는·내려가는 방향
        pts = [tuple(q) for q in ar["pts"]]
        msp.add_lwpolyline(pts, dxfattribs=at)
        (ax, ay), (bx, by) = pts[-2], pts[-1]
        L = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5 or 1
        ux, uy = (bx - ax) / L, (by - ay) / L
        msp.add_solid([(bx, by), (bx - ux * 260 - uy * 90, by - uy * 260 + ux * 90), (bx - ux * 260 + uy * 90, by - uy * 260 - ux * 90)], dxfattribs=at)
        msp.add_circle(pts[0], 50, dxfattribs=at)
        t = msp.add_text(ar["label"], dxfattribs={"layer": "CORE", "height": 200, **KOR(doc)})
        t.set_placement((pts[0][0] + 90, pts[0][1] + 60))
        (sx, sy), (tx, ty) = pts[0], pts[1]
        D = ((tx - sx) ** 2 + (ty - sy) ** 2) ** 0.5 or 1
        vx, vy = (tx - sx) / D, (ty - sy) / D          # 화살표가 떠나는 방향. 글자는 그 뒤쪽(들어오는 쪽)부터 찾는다
        queue_label(doc, t, ([((sx + 140, sy - 100), "LEFT"), ((sx - 140, sy - 100), "RIGHT")] if abs(vy) > abs(vx) else [((sx, sy + 140), "CENTER"), ((sx, sy - 340), "CENTER")]) + [((sx - vx * k, sy - vy * k), "MIDDLE_CENTER") for k in (300, 450, 700, 950)] + [((sx + 90, sy + 60), "LEFT")], (), f'코어 {ch["target"]}의 {ar["label"]} 글자')
        n += 3
    if r.get("walls") is not None:
        note += f', 입구 {p.get("entry")}, 벽 조각 {len(r["walls"])}개'
    cx, cy = (r["x0"] + r["x1"]) / 2, (r["y0"] + r["y1"]) / 2
    lab = msp.add_text(ch["target"], dxfattribs={"layer": "CORE", "height": 200, **KOR(doc)})
    far = {"N": (cx, r["y1"] - 420), "S": (cx, r["y0"] + 420), "E": (r["x1"] - 600, cy), "W": (r["x0"] + 600, cy)}[p["dir"]]   # 계단은 위쪽 계단참 안
    if p["kind"] == "stair":
        cands = [(far, "MIDDLE_CENTER")]
    else:                                   # 승강기는 대각선 사이의 네 칸 가운데 빈 곳
        qx, qy = (r["x1"] - r["x0"]) / 4, (r["y1"] - r["y0"]) / 4
        cands = [((cx, cy + qy * 1.25), "MIDDLE_CENTER"), ((cx, cy - qy * 1.25), "MIDDLE_CENTER"), ((cx - qx * 1.1, cy), "MIDDLE_CENTER"), ((cx + qx * 1.1, cy), "MIDDLE_CENTER")]
    if r.get("label"):                      # 편집기가 정한 자리를 먼저 쓴다
        cands = [(tuple(r["label"]), "MIDDLE_CENTER")] + cands
    lab.set_placement(cands[0][0], align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    queue_label(doc, lab, cands, (), f'코어 {ch["target"]}의 이름')
    info = {"id": ch["target"], "type": p["type"], "kind": p["kind"], "dir": p["dir"], "side": p.get("side", 1), "entry": p.get("entry"), "travel": p.get("travel"),
            "walls": p.get("walls"), "wt": p.get("wall_thick"), "anchor": p.get("anchor"), "anchor_xy": p.get("anchor_xy"), "fh": p.get("floor_height")}
    core_tag(doc, list(msp)[n_before:] + [e for e in (merged or []) if e.is_alive], ch["target"], info)
    if merged:
        note += f", 벽 외곽선 {len(merged)}개(건물 벽과 이어 그림)"
    if old:
        note += f", 이전 객체 {len(old)}개 교체"
    log.append(f'{ch["id"]} 코어 {ch["target"]} {p["name"]} @ {p["anchor"][0]}-{p["anchor"][1]} 방향 {p["dir"]}: {note}, 객체 {n}개')
    return {"added": n}


def do_add_dims(doc, ch, log):
    msp = doc.modelspace()
    ensure_layer(doc, "RXDIM", 6)
    name = std.load_profile()["dimstyle"]["name"]
    style, ov = (name, {}) if name in doc.dimstyles else ("EZDXF", {"dimtxt": 250, "dimasz": 150, "dimexe": 100, "dimexo": 300, "dimlfac": 1, "dimdec": 0})
    n, kinds = 0, {}
    place_labels(doc, log)                   # 기둥 표기, 코어 이름을 먼저 빈 자리에 놓고
    items = ch["params"]["items"]
    plan, moved = std.plan_dims(items, std.Obstacles(msp), ignore=std.mep_layers(std.load_profile()))      # 치수는 그 다음에 남은 자리에
    for i, it in enumerate(items):
        if it["orient"] == "A":                       # 사선 벽의 정렬 치수: 벽에서 off 만큼 바깥쪽에
            (x1, y1), (x2, y2), (nx, ny) = it["p1"], it["p2"], it["n"]
            ang = math.degrees(math.atan2(y2 - y1, x2 - x1))
            d = msp.add_linear_dim(base=((x1 + x2) / 2 + nx * it["off"], (y1 + y2) / 2 + ny * it["off"]), p1=(x1 + nx * it["ext"], y1 + ny * it["ext"]), p2=(x2 + nx * it["ext"], y2 + ny * it["ext"]),
                                   angle=ang, dimstyle=style, override=ov, dxfattribs={"layer": "RXDIM"})
            d.render(); n += 1
            kinds["diag"] = kinds.get("diag", 0) + 1
            continue
        q, loc = plan[i]["q"], plan[i]["loc"]
        if it["orient"] == "H":
            e = it.get("ext", it["line"][1] - 800)      # 치수보조선이 시작하는 곳(잰 대상 쪽)
            d = msp.add_linear_dim(base=((it["a"] + it["b"]) / 2, q), p1=(it["a"], e), p2=(it["b"], e), angle=0, location=loc, dimstyle=style, override=ov, dxfattribs={"layer": "RXDIM"})
        else:
            e = it.get("ext", it["line"][0] + 800)
            d = msp.add_linear_dim(base=(q, (it["a"] + it["b"]) / 2), p1=(e, it["a"]), p2=(e, it["b"]), angle=90, location=loc, dimstyle=style, override=ov, dxfattribs={"layer": "RXDIM"})
        d.render(); n += 1
        k = it.get("kind", "grid"); kinds[k] = kinds.get(k, 0) + 1
    for m in moved:
        if "to" in m:
            log.append(f'{ch["id"]} 겹침 피하기: {"가로" if m["orient"] == "H" else "세로"} 치수 {m["count"]}개의 줄을 {m["from"]} → {m["to"]} ({abs(m["to"] - m["from"])} 바깥으로). 부딪힌 것: {", ".join(m["because"])}')
        else:
            log.append(f'{ch["id"]} 겹침 피하기: 치수 글자 {m["text"]}을 {abs(m["shift"])}만큼 옆으로. 부딪힌 것: 그리드선')
    log.append(f'{ch["id"]} 치수 {n}개 생성: 그리드 {kinds.get("grid", 0)}, 문·창호 위치 {kinds.get("opening", 0)}, 코어 {kinds.get("core", 0)}, 사선 {kinds.get("diag", 0)} (치수 스타일 {style})')
    return {"added": n, **kinds}


def place_labels(doc, log):
    """기둥 표기와 코어 이름을 다른 것과 겹치지 않는 자리로 옮긴다. 여러 번 불러도 한 번만 한다."""
    todo = getattr(doc, "_himec_labels", [])
    if not todo:
        return 0
    doc._himec_labels = []
    msp = doc.modelspace()
    obs = std.Obstacles(msp)
    n = fail = 0
    names = {0: "", 1: ""}
    for e, cands, own, what in todo:
        if not e.is_alive:
            continue
        i = std.place_label(e, cands, obs, own)
        obs.boxes = [b for b in obs.boxes if b[5] != id(e)]
        obs.add(e)                                  # 옮긴 자리를 다음 글자가 피하도록
        if i > 0:
            n += 1
        elif i < 0:
            fail += 1
            log.append(f"겹침 피하기: {what}을 놓을 빈 자리를 찾지 못해 원래 자리에 둠")
    if n or fail:
        log.append(f"겹침 피하기: 글자 {len(todo)}개 가운데 {n}개를 빈 자리로 옮김" + (f", {fail}개는 자리 없음" if fail else ""))
    return n


def queue_label(doc, e, cands, own, what):
    if not hasattr(doc, "_himec_labels"):
        doc._himec_labels = []
    doc._himec_labels.append((e, cands, own, what))


def do_add_schedule(doc, ch, log):
    """일람표를 도면 오른쪽에 그린다."""
    prof = std.load_profile()
    for role in ("schedule",):
        ensure_layer(doc, std.layer_of(prof, role), prof["roles"][role]["color"])
    ext = bb.extents(doc.modelspace(), fast=True)
    n, _ = std.draw_schedules(doc, prof, ch["params"], (ext.extmax.x + 3000, ext.extmax.y - 600))
    p = ch["params"]
    log.append(f'{ch["id"]} 일람표 {n}개: 기둥 {len(p.get("columns", []))}종, 문·창호 {len(p.get("openings", []))}종, 코어 {len(p.get("cores", []))}개')
    return {"tables": n}


def do_add_grid(doc, ch, log):
    p = ch["params"]
    ensure_layer(doc, "CEN", 1)
    ensure_layer(doc, "GRID-TAG", 1)
    msp = doc.modelspace()
    a, b = ((p["coord"], p["lo"]), (p["coord"], p["hi"])) if p["axis"] == "x" else ((p["lo"], p["coord"]), (p["hi"], p["coord"]))
    lt = "CENTER" if "CENTER" in doc.linetypes else None
    msp.add_line(a, b, dxfattribs={"layer": "CEN", **({"linetype": lt} if lt else {})})
    c = (p["coord"], p["lo"] - 450) if p["axis"] == "x" else (p["lo"] - 450, p["coord"])   # 그리드 기호
    msp.add_circle(c, 350, dxfattribs={"layer": "GRID-TAG"})
    msp.add_text(ch["target"], dxfattribs={"layer": "GRID-TAG", "height": 250, **KOR(doc)}).set_placement((c[0] - 200, c[1] - 120))
    log.append(f'{ch["id"]} 그리드 {ch["target"]} 추가 {p["axis"]}={p["coord"]}')
    return {"added": 1}


def do_add_column(doc, ch, log):
    p = ch["params"]
    ensure_layer(doc, "COL", 2)
    w, h = map(float, p["spec"].split("x"))
    x, y = p["xy"]
    col = doc.modelspace().add_lwpolyline([(x - w / 2, y - h / 2), (x + w / 2, y - h / 2), (x + w / 2, y + h / 2), (x - w / 2, y + h / 2)], close=True, dxfattribs={"layer": "COL"})
    tag = p.get("ctype") or p.get("type")
    if tag:
        ensure_layer(doc, "COL-TAG", 2)
        t = doc.modelspace().add_text(str(tag), dxfattribs={"layer": "COL-TAG", "height": 200, **KOR(doc)})
        t.set_placement((x + w / 2 + 120, y + h / 2 + 120))
        cands = []
        for g in (120, 420, 720):          # 기둥의 네 모서리, 자리가 없으면 조금씩 더 멀리
            cands += [((x + w / 2 + g, y + h / 2 + g), "LEFT"), ((x - w / 2 - g, y + h / 2 + g), "RIGHT"),
                      ((x + w / 2 + g, y - h / 2 - g - 200), "LEFT"), ((x - w / 2 - g, y - h / 2 - g - 200), "RIGHT")]
        queue_label(doc, t, cands, (id(col),), f'기둥 {"-".join(p["grid"])}의 표기 {tag}')
    log.append(f'{ch["id"]} 기둥 추가 {"-".join(p["grid"])} {p["spec"]}')
    return {"added": 1}


def flush_walls(doc, log):
    """새 도면: 모아 둔 벽(건물 벽 + 코어 벽)을 면으로 합쳐 외곽선만 그린다."""
    pend = getattr(doc, "_himec_walls", None)
    if not pend:
        return
    doc._himec_walls = []
    prof = std.load_profile()
    r = wl.draw(doc, pend, wl.column_rects(doc))
    doc._himec_core_lines = r["by_owner"]
    log.append(f'벽 맞물림: 벽 {r["walls"]}구간(코어 벽 포함, 사선 {r["diagonal"]}구간)을 면으로 합쳐 외곽선 {r["lines"]}개로 그림. 기둥 {r["columns"]}개의 면에서 벽선을 끊고, 벽끼리 만나는 모서리 {r["corners"]}곳을 채움')


def is_diag(p):
    (x1, y1), (x2, y2) = p["from_xy"], p["to_xy"]
    return abs(x1 - x2) > 1 and abs(y1 - y2) > 1


def do_add_wall(doc, ch, log):
    p = ch["params"]
    t = p.get("thick", 200) / 2
    L = math.hypot(p["to_xy"][0] - p["from_xy"][0], p["to_xy"][1] - p["from_xy"][1])
    kind = "사선 벽" if is_diag(p) else "벽"
    if getattr(doc, "_himec_union", False):      # 새 도면은 모아 두었다가 한꺼번에 합쳐 그린다
        doc._himec_walls.append(wl.wall_rect(p, "WAL", lw=p.get("lw")))
        log.append(f'{ch["id"]} {kind} 추가 {ch["target"]}: 두께 {2 * t:.0f}, 길이 {L:.0f}')
        return {"added": 0, "merged": True}
    ensure_layer(doc, "WAL", 3)
    msp = doc.modelspace()
    lw = p.get("lw")
    for a_, b_ in wl.offset_lines(p["from_xy"], p["to_xy"], t):      # 기존 도면: 두 줄로 (사선도 같은 방식)
        msp.add_line(a_, b_, dxfattribs={"layer": "WAL", **({"lineweight": lw} if lw else {})})
    log.append(f'{ch["id"]} {kind} 추가 {ch["target"]}: 두께 {2 * t:.0f}, 길이 {L:.0f}')
    return {"added": 2}


def do_add_beam(doc, ch, log):
    p = ch["params"]
    t = p.get("width", 400) / 2
    if is_diag(p):                                   # 사선 보: 중심선 양쪽으로 비킨 두 선, 기둥 속은 뺀다
        ensure_layer(doc, "HID", 8)
        lt = next((n for n in ("HIDDEN", "HIDDEN2", "DASHED") if n in doc.linetypes), None)
        attr = {"layer": "HID", **({"linetype": lt} if lt else {}), **({"lineweight": p["lw"]} if p.get("lw") else {})}
        cols = wl.column_rects(doc) if getattr(doc, "_himec_union", False) else []
        n = 0
        for a_, b_ in wl.offset_lines(p["from_xy"], p["to_xy"], t):
            for q1, q2 in wl.clip_line(a_, b_, cols):
                doc.modelspace().add_line(q1, q2, dxfattribs=attr)
                n += 1
        L = math.hypot(p["to_xy"][0] - p["from_xy"][0], p["to_xy"][1] - p["from_xy"][1])
        log.append(f'{ch["id"]} 사선 {"거더" if p.get("kind") == "girder" else "보"} 추가 {ch["target"]}: 폭 {2 * t:.0f}, 길이 {L:.0f}' + (f', 선 굵기 {p["lw"] / 100:.2f}' if p.get("lw") else ""))
        return {"added": n}
    horiz, wall_c, s, e = seg_params(ch["params"])
    ensure_layer(doc, "HID", 8)
    lt = next((n for n in ("HIDDEN", "HIDDEN2", "DASHED") if n in doc.linetypes), None)
    msp = doc.modelspace()
    cols = wl.column_rects(doc) if getattr(doc, "_himec_union", False) else []      # 새 도면: 보는 기둥 면에서 멈춘다
    n = 0
    for q in (wall_c - t, wall_c + t):
        attr = {"layer": "HID"}
        if lt:
            attr["linetype"] = lt
        if ch["params"].get("lw"):      # 거더/보, 경간에 따른 굵기
            attr["lineweight"] = ch["params"]["lw"]
        for a, b in wl.trim_by_columns(s, e, q, horiz, cols):
            msp.add_line(pt(horiz, a, q), pt(horiz, b, q), dxfattribs=attr)
            n += 1
    p = ch["params"]
    log.append(f'{ch["id"]} {"거더" if p.get("kind") == "girder" else "보"} 추가 {ch["target"]}: 폭 {2 * t:.0f}, 길이 {e - s:.0f}, 경간 {p.get("span", e - s):.0f}, 선종류 {lt or "ByLayer"}, 선 굵기 {p["lw"] / 100:.2f}' if p.get("lw") else f'{ch["id"]} 보 추가 {ch["target"]}: 폭 {2 * t:.0f}, 길이 {e - s:.0f}, 선종류 {lt or "ByLayer"}')
    return {"added": n}


def do_add_opening(doc, ch, log):
    p, msp = ch["params"], doc.modelspace()
    horiz = p["horiz"]
    c = p["center"][0] if horiz else p["center"][1]
    wall_c = p["center"][1] if horiz else p["center"][0]
    s, e = c - p["width"] / 2, c + p["width"] / 2
    # 벽이 개구부를 담을 수 있는지: 그 자리의 벽선이 개구부 양쪽으로 50 이상 남아야 한다 (편집기가 이미 경고한 경우)
    why = opening_blocked(p, s, e)
    if why:
        log.append(f'{ch["id"]} {"창호" if p["type"] == "window" else "문"} {ch["target"]}: {why}. 편집기 경고대로 고친 뒤 다시 반영해야 함')
        return {"added": 0, "skipped": why}
    offsets, st = cut_range(doc, horiz, wall_c, s, e)
    qlo, qhi = (wall_c + min(offsets), wall_c + max(offsets)) if len(offsets) >= 2 and max(offsets) - min(offsets) >= 50 else (wall_c - p.get("thick", 200) / 2, wall_c + p.get("thick", 200) / 2)
    ensure_layer(doc, "WAL", 3)
    for a in (s, e):   # 문틀선
        msp.add_line(pt(horiz, a, qlo), pt(horiz, a, qhi), dxfattribs={"layer": "WAL", **({"lineweight": p["wall_lw"]} if p.get("wall_lw") else {})})
    snap = ch.get("_donor")
    kind = "창호" if p["type"] == "window" else "문"
    if snap:
        new, ps = place_donor(doc, snap, horiz, pt(horiz, c, wall_c))
        try:      # 복사해 온 기호는 원본 벽 두께에 맞춰져 있다. 이 벽과 맞는지 기록한다
            x = bb.extents([e for e in new if e.is_alive], fast=True)
            depth = (x.size.y if horiz else x.size.x) if x.has_data else None
            if depth is not None and p["type"] == "window" and abs(depth - (qhi - qlo)) > 20:
                log.append(f'{ch["id"]} {kind} {ch["target"]}: 기호 깊이 {depth:.0f}, 벽 두께 {qhi - qlo:.0f}. 기호가 벽 두께와 달라 확인 필요')
        except Exception:
            pass
        log.append(f'{ch["id"]} {kind} 추가 {ch["target"]} ({p.get("otype")}, 폭 {p["width"]}): 벽선 {st["cut_lines"]}개 절단, 벽 두께 {qhi - qlo:.0f}, {snap["id"]}의 기호 {ps["copied"]}개 복사' + (", 90도 회전" if ps["rotated"] else ""))
        return {"added": ps["copied"], **st, **ps}
    n = draw_generic(doc, p["type"], p.get("leaves", 1), horiz, s, e, qlo, qhi)
    log.append(f'{ch["id"]} {kind} 추가 {ch["target"]} ({p.get("otype")}, 폭 {p["width"]}): 벽선 {st["cut_lines"]}개 절단, 벽 두께 {qhi - qlo:.0f}, 기본 기호 {n}개')
    return {"added": n, **st}


# ---------- 설비·전기·소방 ----------
def set_host(ins, host):
    for a in ins.attribs:
        if a.dxf.tag == "HOST" and host:
            a.dxf.text = host


def do_mep_delete(doc, ch, log):
    ents = entities_of(doc, [ch["params"]["handle"]])
    for e in ents:
        doc.modelspace().delete_entity(e)
    log.append(f'{ch["id"]} 기구 {ch["target"]} 삭제: {len(ents)}개')
    return {"deleted": len(ents)}


def do_mep_relocate(doc, ch, log):
    """기구를 최종 위치로 옮긴다. 띠 STRETCH로 이미 옮겨진 것은 제자리가 된다."""
    n = auto = 0
    for it in ch["params"]["items"]:
        ents = entities_of(doc, [it["handle"]])
        if not ents:
            continue
        ins = ents[0]
        dx, dy = it["to_xy"][0] - ins.dxf.insert.x, it["to_xy"][1] - ins.dxf.insert.y
        if abs(dx) > 0.5 or abs(dy) > 0.5:
            ins.translate(dx, dy, 0)
        set_host(ins, it.get("host"))
        n += 1
        auto += 0 if it.get("edited") else 1
    log.append(f'{ch["id"]} 기구 재배치: {n}개 (건축 변경에 따른 자동 {auto}, 직접 편집 {n - auto})')
    return {"relocated": n, "auto": auto}


def do_mep_route(doc, ch, log):
    ents = entities_of(doc, [ch["params"]["handle"]])
    if not ents:
        log.append(f'{ch["id"]} 덕트 {ch["target"]}: 도면 객체를 찾지 못함'); return {"ok": False}
    ents[0].set_points([(q[0], q[1]) for q in ch["params"]["pts"]], format="xy")
    log.append(f'{ch["id"]} 덕트 {ch["target"]} 경로 변경: {ch["params"]["pts"]}')
    return {"ok": True}


def do_mep_add(doc, ch, log):
    sys.path.insert(0, str(ROOT / "mep"))
    import mep_schedule as ms
    p = ch["params"]
    ms.ensure_blocks(doc)
    t = ms.BY_ID[p["type"]]
    ref = doc.modelspace().add_blockref(t["block"], p["xy"], dxfattribs={"layer": t["layer"], "rotation": p.get("rotation", 0)})
    ref.add_auto_attribs({"TAG": ch["target"], "TYPE": p["type"], "HOST": p.get("host", "")})
    log.append(f'{ch["id"]} 기구 추가 {ch["target"]} ({t["name"]}) @ {p["xy"]}')
    return {"added": 1}


HANDLERS = {"add_schedule": do_add_schedule, "set_site": do_set_site, "delete_core": do_delete_core, "add_core": do_add_core, "add_dims": do_add_dims, "mep_delete": do_mep_delete, "mep_relocate": do_mep_relocate, "mep_route": do_mep_route, "mep_add": do_mep_add, "move": do_move, "delete_grid": do_delete_grid, "delete_opening": do_delete_opening, "delete_wall": do_delete_wall, "delete_beam": do_delete_beam,
            "delete_column": do_delete_column, "resize": do_resize, "edit_opening": do_edit_opening, "add_grid": do_add_grid, "add_column": do_add_column,
            "add_wall": do_add_wall, "add_beam": do_add_beam, "add_opening": do_add_opening}


def apply(sheet, changes_path):
    changes = [c for c in json.loads(Path(changes_path).read_text(encoding="utf-8")) if c["status"] == "confirmed" and c["sheet"] == sheet]
    src = ROOT / "real_dxf" / f"{sheet}.dxf"
    is_new = not src.exists()
    doc = new_drawing() if is_new else ezdxf.readfile(src)
    log, results = [], []
    if is_new:
        log.append(f"새 도면 {sheet}: 원본 없이 관계도에서 새로 그림")
    for ch in changes:   # 타입의 원본 기호는 어떤 편집보다 먼저 떠 둔다
        d = ch["params"].get("donor")
        if d:
            ch["_donor"] = snapshot_donor(doc, d, sheet)
    if is_new:        # 새 도면은 벽을 면으로 합쳐 그린다. 코어 벽도 같이 합치도록 미리 모은다
        doc._himec_union, doc._himec_walls = True, []
        prof = std.load_profile()
        for ch in changes:
            if ch["action"] == "add_core":
                for w in ch["params"]["rect"].get("walls", []):
                    doc._himec_walls.append(wl.wall_from_box(w["x0"], w["y0"], w["x1"], w["y1"], std.layer_of(prof, "core_wall"), ch["target"], ch["params"]["rect"].get("wall_lw")))
    for action in ORDER:
        if is_new and action == "add_beam":      # 기둥과 벽이 모두 모인 뒤, 보·문·창호를 그리기 전에
            flush_walls(doc, log)
        for ch in changes:
            if ch["action"] != action:
                continue
            try:
                r = HANDLERS[action](doc, ch, log)
            except Exception as ex:
                r = {"error": str(ex)[:200]}
                log.append(f'{ch["id"]} {ch["target"]} {action}: 오류 {str(ex)[:120]}')
            results.append({"id": ch["id"], "action": action, "target": ch["target"], "result": {k: v for k, v in r.items() if k != "masters"}})
    for ch in changes:
        if ch["action"] not in HANDLERS:
            log.append(f'{ch["id"]} {ch["target"]} {ch["action"]}: 지원하지 않는 동작')
    place_labels(doc, log)       # 치수를 그리지 않는 경우에도 글자 자리는 정리
    if is_new:
        prof = std.load_profile()
        info = std.apply_profile(doc, prof)     # 가져온 기호의 레이어까지 같은 규칙으로
        fr = std.draw_frame(doc, prof, "1층 평면도 (계획)", sheet)
        log.append(f'레이어 체계 "{info["profile"]}": 레이어 {info["layers_styled"]}개에 색·선 굵기·선종류 지정, 선종류 축척 {info["ltscale"]}')
        log.append(f'도면 틀: {fr["paper"]} 1/{fr["scale"]}, 표제란 포함')
    fixed = clean_layers(doc)
    if fixed:
        log.append(f"가져온 레이어의 끊긴 참조 {fixed}개 정리")
    OUT.mkdir(parents=True, exist_ok=True)
    dst = OUT / f"{sheet}_edited.dxf"
    doc.saveas(dst)
    return (None if is_new else src), dst, log, results


def roundtrip(dst, sheet, expected_path):
    """수정된 도면에서 관계도를 다시 읽어 편집기의 최종 상태와 대조."""
    import build_graph_real as bgr
    g = bgr.build(dst, sheet)
    exp = json.loads(Path(expected_path).read_text(encoding="utf-8"))
    N = {n["id"]: n for n in g["nodes"]}
    rows, ok_all = [], True

    def near(a, b, tol):
        return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol

    got_cols = [(n["xy"], n["spec"]) for n in g["nodes"] if n["type"] == "column"]
    for c in exp["columns"]:
        hit = next((x for x in got_cols if near(x[0], c["xy"], 10)), None)
        good = bool(hit) and hit[1] == c["spec"]
        rows.append(("기둥 " + c["label"], c["spec"], hit[1] if hit else "없음", good)); ok_all &= good
    for c in exp["columns_deleted"]:
        hit = next((x for x in got_cols if near(x[0], c["xy"], 10)), None)
        rows.append(("삭제한 기둥 " + c["label"], "없음", hit[1] if hit else "없음", not hit)); ok_all &= not hit
    got_walls = [(N[e["from"]]["xy"], N[e["to"]]["xy"]) for e in g["edges"] if e["wall"]]
    got_thick = {(tuple(N[e["from"]]["xy"]), tuple(N[e["to"]]["xy"])): e.get("thick_measured") for e in g["edges"] if e["wall"]}
    def thick_of(w):
        return next((t for (p1, p2), t in got_thick.items() if (near(p1, w["from_xy"], 10) and near(p2, w["to_xy"], 10)) or (near(p1, w["to_xy"], 10) and near(p2, w["from_xy"], 10))), None)
    def chain(w):
        """읽은 쪽은 그리드 교점마다 구간을 나눈다. 같은 줄 위의 벽 구간들이 이 벽을 빈틈없이 덮는지 본다."""
        (x1, y1), (x2, y2) = w["from_xy"], w["to_xy"]
        hz = abs(y1 - y2) < 1
        if not hz and abs(x1 - x2) > 1:
            return False, None                     # 사선 벽: 끝점으로 대조
        c0, s, e = (y1, min(x1, x2), max(x1, x2)) if hz else (x1, min(y1, y2), max(y1, y2))
        iv = []
        for (p1, p2), t in got_thick.items():
            if (abs(p1[1] - p2[1]) < 1) != hz or abs((p1[1] if hz else p1[0]) - c0) > 10:
                continue
            a, b = sorted((p1[0], p2[0]) if hz else (p1[1], p2[1]))
            if b > s + 10 and a < e - 10:
                iv.append((a, b, t))
        cur = s
        for a, b, t in sorted(iv, key=lambda v: v[:2]):
            if a > cur + 10:
                return False, None
            cur = max(cur, b)
        ts = {t for _, _, t in iv}
        return (cur >= e - 10 and bool(iv)), (ts.pop() if len(ts) == 1 else None)

    def has_wall(w):
        return chain(w)[0] or any((near(a, w["from_xy"], 10) and near(b, w["to_xy"], 10)) or (near(a, w["to_xy"], 10) and near(b, w["from_xy"], 10)) for a, b in got_walls)
    for w in exp["walls_checked"]:
        got = has_wall(w)
        if w["expect"] and w.get("thick"):      # 두께까지 대조
            tm = thick_of(w) or chain(w)[1]
            good = got and tm is not None and abs(tm - w["thick"]) <= 1
            rows.append(("벽 " + w["label"], f'있음, 두께 {w["thick"]}', f'있음, 두께 {tm}' if got else "없음", good)); ok_all &= good
            continue
        rows.append((("벽 " if w["expect"] else "삭제한 벽 ") + w["label"], "있음" if w["expect"] else "없음", "있음" if got else "없음", got == w["expect"])); ok_all &= got == w["expect"]
    for o in exp["openings_checked"]:
        hit = next((x for x in g["openings"] if x["type"] == o["type"] and near(x["xy"], o["xy"], 350)), None)
        if o["expect"]:
            good = bool(hit) and abs(hit["nominal"] - o["width"]) <= 30
            rows.append((f'{"문" if o["type"] == "door" else "창호"} {o["id"]}', f'폭 {o["width"]} @ {o["xy"]}', f'폭 {hit["nominal"]} @ {hit["xy"]}' if hit else "없음", good))
        else:
            good = not hit
            rows.append((f'삭제한 {"문" if o["type"] == "door" else "창호"} {o["id"]}', "없음", f'폭 {hit["nominal"]} @ {hit["xy"]}' if hit else "없음", good))
        ok_all &= good
    for d in exp["dims_checked"]:
        hit = next((x for x in g["dims"] if x["handle"] == d["handle"]), None)
        good = bool(hit) and hit["measurement"] == d["to"]
        rows.append((f'치수 {d["handle"]}', str(d["to"]), str(hit["measurement"]) if hit else "없음", good)); ok_all &= good
    got_c = {c["id"]: c for c in g.get("cores", [])}
    for c in exp.get("cores", []):
        h = got_c.get(c["id"])
        ax = lambda q: f'{q["anchor_xy"][0]},{q["anchor_xy"][1]}'      # 그리드 이름은 읽을 때 좌표순으로 다시 붙으므로 좌표로 대조
        nm = (lambda q: ax(q)) if c.get("anchor_xy") else (lambda q: f'{q["anchor"][0]}-{q["anchor"][1]}')
        want = f'{c["type"]} {nm(c)} {c["dir"]} 입구 {c["entry"]} {c["travel"] or "-"} {c["rect"]}'
        have = f'{h["type"]} {nm(h)} {h["dir"]} 입구 {h["entry"]} {h["travel"] or "-"} {h["rect"]}' if h else "없음"
        good = bool(h) and want == have and h["walls"] == c["walls"] and h["side"] == c["side"] and (c.get("wall_thick") is None or h.get("wall_thick") == c["wall_thick"])
        if c.get("wall_thick"):
            want += f' 벽 {c["wall_thick"]}'; have += f' 벽 {h.get("wall_thick")}' if h else ""
        rows.append((f'코어 {c["id"]}', want, have, good)); ok_all &= good
    if exp.get("site"):
        h = g.get("site")
        good = bool(h) and len(h["pts"]) == len(exp["site"]["pts"]) and all(near(p1, p2, 1) for p1, p2 in zip(sorted(map(tuple, h["pts"])), sorted(map(tuple, exp["site"]["pts"]))))
        rows.append(("대지경계선", f'{len(exp["site"]["pts"])}점', f'{len(h["pts"])}점' if h else "없음", good)); ok_all &= good
        fh = (g.get("project") or {}).get("floor_height")
        if any(c["travel"] for c in exp.get("cores", [])):
            rows.append(("층고", str(exp["floor_height"]), str(fh), fh == exp["floor_height"])); ok_all &= fh == exp["floor_height"]
    if exp.get("mep"):
        got = {d["id"]: d for d in (g.get("mep") or {"devices": []})["devices"]}
        bad, n = [], 0
        for d in exp["mep"]["devices"]:
            n += 1
            h = got.get(d["id"])
            if not h or not near(h["xy"], d["xy"], 5) or h["type"] != d["type"]:
                bad.append(f'{d["id"]} 기대 {d["xy"]} 도면 {h["xy"] if h else "없음"}')
        rows.append((f"기구 {n}개의 위치·타입", "모두 일치", "모두 일치" if not bad else "; ".join(bad[:3]), not bad)); ok_all &= not bad
        for d in exp["mep"]["checked"]:
            h = got.get(d["id"])
            if d["expect"]:
                good = bool(h) and near(h["xy"], d["xy"], 5)
                rows.append((f'{d["why"]} {d["id"]}', str(d["xy"]), str(h["xy"]) if h else "없음", good))
            else:
                good = h is None
                rows.append((f'{d["why"]} {d["id"]}', "없음", str(h["xy"]) if h else "없음", good))
            ok_all &= good
        gr = {r["handle"]: r for r in (g.get("mep") or {"routes": []})["routes"]}
        for r in exp["mep"]["routes"]:
            h = gr.get(r["handle"])
            good = bool(h) and all(near(a, b, 5) for a, b in zip(h["pts"], r["pts"])) and len(h["pts"]) == len(r["pts"])
            rows.append((f'덕트 {r["id"]}', str(r["pts"]), str(h["pts"]) if h else "없음", good)); ok_all &= good
    return rows, ok_all, g


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    quick = "--quick" in sys.argv          # 전체 그림만 그리고, 수정된 도면에서 관계도를 다시 읽어 그린다
    argv = [a for a in sys.argv if a != "--quick"]
    sheet = argv[1] if len(argv) > 1 else "A12"
    cpath = argv[2] if len(argv) > 2 else str(ROOT / "out" / "editor" / "changes_demo.json")
    epath = argv[3] if len(argv) > 3 else None
    src, dst, log, results = apply(sheet, cpath)
    for l in log:
        print("  " + l)
    print("saved", dst)
    report = {"sheet": sheet, "changes": str(cpath), "output": dst.name, "log": log, "results": results}
    if epath:
        rows, ok_all, g = roundtrip(dst, sheet, epath)
        print("\n왕복 검증 (수정된 도면에서 관계도를 다시 읽어 편집기 결과와 대조)")
        for name, want, got, good in rows:
            print(f'  {"OK  " if good else "FAIL"} {name:28s} 기대 {want:28s} 도면 {got}')
        print(f'\n  {sum(r[3] for r in rows)}/{len(rows)} 일치' + ("" if ok_all else "  ← 불일치 있음"))
        report["roundtrip"] = [{"item": a, "expected": b, "drawing": c, "ok": d} for a, b, c, d in rows]
        import build_graph_real as bgr
        bgr.render(g, OUT / f"{sheet}_edited_graph.png", title=f"수정된 도면에서 다시 읽은 관계도 {sheet}")
    if quick and not epath:
        import build_graph_real as bgr
        bgr.render(bgr.build(dst, sheet), OUT / f"{sheet}_edited_graph.png", title=f"수정된 도면에서 다시 읽은 관계도 {sheet}")
    (OUT / "edit_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)), encoding="utf-8")
    wins = {"": (10500, 8500, 30500, 24500), "_W1": (11700, 10000, 13900, 12000), "_D1": (14300, 10000, 16500, 12000),
            "_W3": (11500, 13300, 13800, 15600), "_D3": (12300, 19800, 15800, 22600), "_D8": (12900, 9300, 15300, 11300), "_hall": (19500, 9000, 28500, 16500), "_X1wall": (11000, 15700, 13500, 18100)}
    if quick:
        wins = {"": wins[""]}
    if src is None:   # 새 도면: 그려진 범위 전체
        ext = bb.extents(ezdxf.readfile(dst).modelspace(), fast=True)
        wins = {"": (ext.extmin.x - 1500, ext.extmin.y - 1500, ext.extmax.x + 1500, ext.extmax.y + 1500)}
    for tag, win in wins.items():
        if src is not None:
            render_window(src, OUT / f"{sheet}_edit_before{tag}.png", win, f"{sheet} 편집 전")
        render_window(dst, OUT / f"{sheet}_edit_after{tag}.png", win, f"{sheet} 편집 후" if src is not None else f"{sheet} 관계도에서 새로 그린 도면")
    print("saved", OUT / f"{sheet}_edit_before/after*.png")
