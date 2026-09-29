"""도면 표현 규칙: 레이어 체계, 선 굵기·선종류, 치수 스타일, 일람표, 도면 틀.

레이어 체계는 layer_profile.json 에 있다. 사무소마다 그 파일만 바꾸면 된다.
"""
import json
from datetime import date
from pathlib import Path

from ezdxf import bbox as bb

HERE = Path(__file__).resolve().parent
PAPERS = [("A3", 420, 297), ("A2", 594, 420), ("A1", 841, 594), ("A0", 1189, 841)]


def load_profile(path=None):
    return json.loads(Path(path or HERE / "layer_profile.json").read_text(encoding="utf-8"))


def mep_layers(profile):
    """설비·전기·소방 레이어. 건축 치수는 이 레이어의 기구를 피하지 않는다(건축도에서는 끄는 레이어)."""
    return tuple(n for k, r in profile["roles"].items() if k.split("_")[0] in ("elec", "mech", "fire", "beam") for n in r["layers"])      # 보(은선)도 치수가 지나가도 된다


def layer_of(profile, role):
    return profile["roles"][role]["layers"][0]


def apply_profile(doc, profile=None):
    """역할별 레이어를 만들고 색·선 굵기·선종류를 지정한다. 이미 있는 레이어(가져온 기호의 레이어 포함)도 같은 규칙으로 맞춘다."""
    profile = profile or load_profile()
    made, styled = 0, 0
    if "HIDDEN" not in doc.linetypes:      # ezdxf 기본 선종류에는 은선이 없다
        doc.linetypes.add("HIDDEN", pattern=[0.9525, 0.635, -0.3175], description="Hidden __ __ __ __")
    for role, r in profile["roles"].items():
        lt = r["linetype"] if r["linetype"] in doc.linetypes else "Continuous"
        for i, name in enumerate(r["layers"]):
            if name not in doc.layers:
                if i > 0:
                    continue          # 보조 레이어는 도면에 있을 때만 맞춘다
                doc.layers.add(name)
                made += 1
            L = doc.layers.get(name)
            L.dxf.color = r["color"]
            L.dxf.lineweight = r["lineweight"]
            L.dxf.linetype = lt if i == 0 else L.dxf.get("linetype", "Continuous")
            styled += 1
    doc.header["$LTSCALE"] = profile["ltscale"]
    doc.header["$LWDISPLAY"] = 1
    t = profile["text"]
    if t["style"] not in doc.styles:
        doc.styles.add(t["style"], font=t["font"])
    ds = profile["dimstyle"]
    if ds["name"] not in doc.dimstyles:
        d = doc.dimstyles.new(ds["name"])
        d.dxf.dimtxt = ds["text_height"]
        d.dxf.dimasz = ds["tick"]
        d.dxf.dimtsz = ds["tick"]          # 화살표 대신 사선(건축 표기)
        d.dxf.dimexe = ds["ext_beyond"]
        d.dxf.dimexo = ds["ext_offset"]
        d.dxf.dimgap = ds["text_gap"]
        d.dxf.dimdec = 0
        d.dxf.dimtad = 1                    # 문자를 치수선 위에
        d.dxf.dimtxsty = t["style"]
        d.dxf.dimlfac = 1
    return {"profile": profile["name"], "layers_created": made, "layers_styled": styled, "dimstyle": ds["name"], "ltscale": profile["ltscale"]}


def text(msp, profile, s, xy, role="text", height=None, **kw):
    t = msp.add_text(s, dxfattribs={"layer": layer_of(profile, role), "height": height or profile["text"]["height"], "style": profile["text"]["style"], **kw})
    t.set_placement(xy)
    return t


def table(msp, profile, x, y, title, header, rows, widths, row_h=550):
    """(x, y)를 왼쪽 위로 하는 표. 아래쪽 y를 돌려준다."""
    L = layer_of(profile, "schedule")
    text(msp, profile, title, (x, y + 200), role="schedule", height=profile["text"]["title_height"] * 0.8)
    n, W = len(rows) + 1, sum(widths)
    for i in range(n + 1):
        msp.add_line((x, y - i * row_h), (x + W, y - i * row_h), dxfattribs={"layer": L, "lineweight": 35 if i in (0, 1, n) else 13})
    cx = x
    for j, w in enumerate(widths + [0]):
        msp.add_line((cx, y), (cx, y - n * row_h), dxfattribs={"layer": L, "lineweight": 35 if j in (0, len(widths)) else 13})
        cx += w
    for i, row in enumerate([header] + rows):
        cx = x
        for j, cell in enumerate(row):
            text(msp, profile, str(cell), (cx + 120, y - i * row_h - row_h + 160), role="schedule", height=profile["text"]["height"] * (1.0 if i else 1.05))
            cx += widths[j]
    return y - n * row_h


def draw_schedules(doc, profile, data, origin):
    msp = doc.modelspace()
    x, y = origin
    rows_c = [[c["type"], c["spec"], c["count"]] for c in data.get("columns", [])]
    rows_o = [[o["type"], "창호" if o["kind"] == "window" else f'문 {o["leaves"]}짝', o["width"], o["count"], o["source"]] for o in data.get("openings", [])]
    rows_k = [[c["id"], c["name"], c["size"], c.get("wall_thick", "-"), c["note"]] for c in data.get("cores", [])]
    rows_w = [[f'W{i + 1}', w["thick"], w["count"], f'{w["length"] / 1000:.1f} m', f'{w["lw"] / 100:.2f}' if w.get("lw") else "-"] for i, w in enumerate(data.get("walls", []))]
    rows_b = [["거더" if b["kind"] == "girder" else "보", b["count"], str(b["span_min"]) if b["span_min"] == b["span_max"] else f'{b["span_min"]}~{b["span_max"]}', f'{b["lw"] / 100:.2f}'] for b in data.get("beams", [])]
    n = 0
    if rows_c:
        y = table(msp, profile, x, y, "기둥 일람표", ["타입", "단면", "개수"], rows_c, [1600, 2400, 1400]) - 1500; n += 1
    if rows_o:
        y = table(msp, profile, x, y, "문·창호 일람표", ["타입", "종류", "폭", "개수", "기호 출처"], rows_o, [1600, 2000, 1600, 1400, 4400]) - 1500; n += 1
    if rows_w:
        y = table(msp, profile, x, y, "벽 일람표", ["타입", "두께", "구간 수", "길이 합", "선 굵기"], rows_w, [1600, 1600, 1800, 2400, 2200]) - 1500; n += 1
    if rows_b:
        y = table(msp, profile, x, y, "보 일람표", ["종류", "부재 수", "경간", "점선 굵기"], rows_b, [1600, 1800, 3000, 2200]) - 1500; n += 1
    if rows_k:
        y = table(msp, profile, x, y, "코어 일람표", ["번호", "종류", "안치수", "벽 두께", "비고"], rows_k, [1600, 5200, 2600, 1800, 9800]) - 1500; n += 1
    return n, y


def draw_frame(doc, profile, title, sheet):
    """그려진 범위에 맞는 가장 작은 표준 용지를 골라 테두리와 표제란을 그린다."""
    msp = doc.modelspace()
    ext = bb.extents(msp, fast=True)
    sc = profile["scale"]
    w, h = ext.size.x, ext.size.y
    name, pw, ph = next(((n, a * sc, b * sc) for n, a, b in PAPERS if a * sc >= w + 2 * 2500 and b * sc >= h + 2 * 2500 + 2 * 5200), (PAPERS[-1][0], PAPERS[-1][1] * sc, PAPERS[-1][2] * sc))
    cx, cy = (ext.extmin.x + ext.extmax.x) / 2, (ext.extmin.y + ext.extmax.y) / 2
    x0, y0 = cx - pw / 2, cy - ph / 2
    F = layer_of(profile, "frame")
    msp.add_lwpolyline([(x0, y0), (x0 + pw, y0), (x0 + pw, y0 + ph), (x0, y0 + ph)], close=True, dxfattribs={"layer": F, "lineweight": 18})
    m = 1000
    msp.add_lwpolyline([(x0 + m, y0 + m), (x0 + pw - m, y0 + m), (x0 + pw - m, y0 + ph - m), (x0 + m, y0 + ph - m)], close=True, dxfattribs={"layer": F})
    tw, th = 12000, 4200
    tx, ty = x0 + pw - m - tw, y0 + m
    msp.add_lwpolyline([(tx, ty), (tx + tw, ty), (tx + tw, ty + th), (tx, ty + th)], close=True, dxfattribs={"layer": F, "lineweight": 35})
    rows = [("도면명", title), ("도면번호", sheet), ("축척", f"1/{sc} ({name})"), ("작성일", date.today().isoformat()), ("비고", "관계도에서 자동 생성한 계획도")]
    rh = th / len(rows)
    for i, (k, v) in enumerate(rows):
        yy = ty + th - (i + 1) * rh
        if i:
            msp.add_line((tx, yy + rh), (tx + tw, yy + rh), dxfattribs={"layer": F, "lineweight": 13})
        text(msp, profile, k, (tx + 200, yy + 250), role="frame", height=230)
        text(msp, profile, v, (tx + 3000, yy + 230), role="frame", height=300 if i else 380)
    msp.add_line((tx + 2700, ty), (tx + 2700, ty + th), dxfattribs={"layer": F, "lineweight": 13})
    return {"paper": name, "scale": sc, "size_mm": [pw / sc, ph / sc]}


# ---------- 겹침 피하기 ----------
def _box(x0, y0, x1, y1, pad=0):
    return (min(x0, x1) - pad, min(y0, y1) - pad, max(x0, x1) + pad, max(y0, y1) + pad)


def _seg_hits(b, s):
    """선분 s가 상자 b를 지나가는가."""
    x0, y0, x1, y1 = b
    ax, ay, bx, by = s
    if max(ax, bx) < x0 or min(ax, bx) > x1 or max(ay, by) < y0 or min(ay, by) > y1:
        return False
    dx, dy, t0, t1 = bx - ax, by - ay, 0.0, 1.0
    for p, q in ((-dx, ax - x0), (dx, x1 - ax), (-dy, ay - y0), (dy, y1 - ay)):
        if abs(p) < 1e-9:
            if q < 0:
                return False
        else:
            t = q / p
            if p < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
            if t0 > t1:
                return False
    return True


def _boxes_hit(a, b):
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]


_FONT = {}


def text_width(s, h, font="malgun.ttf"):
    """글자 폭. 실제 글꼴 파일로 재고, 글꼴을 못 찾으면 어림한다(한글 1.0, 그 밖 0.65)."""
    if font not in _FONT:
        try:
            from ezdxf.fonts import fonts
            f = fonts.make_font(font, 1.0)
            _FONT[font] = f if f.text_width("0000") > 0 and "Mono" not in type(f).__name__ else None
        except Exception:
            _FONT[font] = None
    f = _FONT[font]
    if f is None:
        return sum(h * (1.0 if ord(c) > 0x2000 else 0.65) for c in s)
    return f.text_width(s) * h


def text_box(e, pad=40):
    """TEXT 객체가 차지하는 상자."""
    s, h = e.dxf.text, e.dxf.height
    w = text_width(s, h)
    al = e.get_placement()
    name, p = al[0].name, al[1]
    x0 = p.x - w / 2 if "CENTER" in name else p.x - w if "RIGHT" in name else p.x
    y0 = p.y - h / 2 if name.startswith("MIDDLE") else p.y - h if name.startswith("TOP") else p.y
    return _box(x0, y0, x0 + w, y0 + h, pad)


class Obstacles:
    """도면에 이미 그려진 것들. 선은 선분으로, 글자·기호는 상자로 본다."""

    def __init__(self, msp, skip=()):
        self.segs, self.boxes = [], []
        for e in msp:
            if e in skip or id(e) in skip:
                continue
            self.add(e)

    def add(self, e):
        t, lay = e.dxftype(), e.dxf.layer
        if t == "LINE":
            self.segs.append((e.dxf.start.x, e.dxf.start.y, e.dxf.end.x, e.dxf.end.y, lay, id(e)))
        elif t == "LWPOLYLINE":
            pts = [(p[0], p[1]) for p in e.get_points("xy")]
            if e.closed:
                pts.append(pts[0])
            for a, b in zip(pts, pts[1:]):
                self.segs.append((a[0], a[1], b[0], b[1], lay, id(e)))
        elif t == "TEXT":
            self.boxes.append((*text_box(e), lay, id(e)))
        elif t in ("CIRCLE", "ARC", "INSERT", "SOLID", "ELLIPSE"):
            try:
                x = bb.extents([e], fast=True)
                if x.has_data:
                    self.boxes.append((x.extmin.x, x.extmin.y, x.extmax.x, x.extmax.y, lay, id(e)))
            except Exception:
                pass

    def hits(self, b, skip_layers=(), skip_ids=(), only=None):
        """상자 b와 부딪히는 것의 레이어 목록. only: 'h' 가로선만, 'v' 세로선만."""
        out = []
        for s in self.segs:
            if s[4] in skip_layers or s[5] in skip_ids:
                continue
            if only == "h" and abs(s[1] - s[3]) > 1 or only == "v" and abs(s[0] - s[2]) > 1:
                continue
            if _seg_hits(b, s[:4]):
                out.append(s[4])
        if only is None:
            for x in self.boxes:
                if x[4] in skip_layers or x[5] in skip_ids:
                    continue
                if _boxes_hit(b, x[:4]):
                    out.append(x[4])
        return out


def plan_dims(items, obs, grid_layer="CEN", ignore=(), h=250, gap=80, step=300, limit=4500, spacing=550):
    """같은 줄의 치수를 묶어, 부딪히지 않는 자리까지 치수선을 바깥으로 민다. 글자가 그리드선에 걸리면 글자만 옆으로 옮긴다.

    돌려주는 값: 항목마다 {"q": 치수선 위치, "loc": 글자 위치 또는 None}, 그리고 옮긴 기록.
    """
    groups = {}
    for i, it in enumerate(items):
        hz = it["orient"] == "H"
        q = it["line"][1] if hz else it["line"][0]
        e = it.get("ext", q - 800 if hz else q + 800)
        groups.setdefault((it["orient"], round(q), 1 if q >= e else -1), []).append((i, it, e))
    lines, texts, plan, moved = [], [], {}, []      # 이미 놓은 치수선, 치수 글자

    def tw(it):
        return text_width(str(it["value"]), h)

    def tbox(it, hz, q, s=0.0):
        m = (it["a"] + it["b"]) / 2 + s
        return _box(m - tw(it) / 2, q + gap, m + tw(it) / 2, q + gap + h, 60) if hz else _box(q - gap - h, m - tw(it) / 2, q - gap, m + tw(it) / 2, 60)

    def lbox(it, hz, q, pad):
        return _box(it["a"], q, it["b"], q, pad) if hz else _box(q, it["a"], q, it["b"], pad)

    for key in sorted(groups, key=lambda k: min(abs(k[1] - g[2]) for g in groups[k])):
        orient, q0, sgn = key
        hz, g, q, why = orient == "H", groups[key], q0, []
        while abs(q - q0) <= limit:
            why = []
            for _, it, _e in g:
                lb, tb = lbox(it, hz, q, 200), tbox(it, hz, q)
                why += obs.hits(lb, skip_layers=(grid_layer, *ignore), only="h" if hz else "v")   # 나란한 선과 붙음
                why += obs.hits(tb, skip_layers=(grid_layer, *ignore))                             # 글자가 선·글자와 겹침
                why += ["치수선" for x in lines if _boxes_hit(_box(*lb[:4], spacing - 200), x)]
                why += ["치수 글자" for x in texts if _boxes_hit(tb, x)]
            if not why:
                break
            last = why
            q += sgn * step
        else:
            q = q0                                   # 끝까지 자리가 없으면 원래 자리
        if q != q0:
            moved.append({"orient": orient, "from": q0, "to": q, "count": len(g), "because": sorted(set(last))})
        for i, it, _e in g:
            loc = None
            if obs.hits(tbox(it, hz, q), only="v" if hz else "h"):       # 그리드선이 글자를 지나감
                room = abs(it["b"] - it["a"]) / 2 - tw(it) / 2 - 100
                for s in (x * sg for x in range(150, int(max(room, 0)) + 1, 50) for sg in (1, -1)):
                    b = tbox(it, hz, q, s)
                    if not obs.hits(b) and not any(_boxes_hit(b, x) for x in texts):
                        m = (it["a"] + it["b"]) / 2 + s
                        loc = (m, q + gap + h / 2) if hz else (q - gap - h / 2, m)
                        moved.append({"orient": orient, "text": it["value"], "shift": s, "because": ["그리드선"]})
                        break
            plan[i] = {"q": q, "loc": loc}
            lines.append(lbox(it, hz, q, 0)); texts.append(tbox(it, hz, q, 0 if not loc else (loc[0] if hz else loc[1]) - (it["a"] + it["b"]) / 2))
    return plan, moved


def place_label(e, candidates, obs, own=()):
    """글자 e를 후보 자리 가운데 아무것도 겹치지 않는 첫 자리에 놓는다. 몇 번째 후보에 놓였는지 돌려준다(-1: 자리가 없어 그대로)."""
    from ezdxf.enums import TextEntityAlignment as TA
    skip = {id(e), *own}
    for i, (xy, align) in enumerate(candidates):
        e.set_placement(xy, align=getattr(TA, align))
        if not obs.hits(text_box(e, 30), skip_ids=skip):
            return i
    e.set_placement(candidates[0][0], align=getattr(TA, candidates[0][1]))
    return -1
