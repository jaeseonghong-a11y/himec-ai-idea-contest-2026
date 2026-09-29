"""설비·전기·소방 가상 일람표.

이 도면 세트에는 설비·전기 도면이 없어, 시연용으로 만든 가상 타입이다. 실제 하이멕 표준이 아니다.
각 타입은 도면에 넣을 블록(기호)과 건축과의 관계 규칙(host)을 가진다.
- host = wall : 벽에 붙음. 벽을 따라 움직이고, 벽이 없어지면 고아가 된다
- host = bay  : 구획(그리드 네 줄로 둘러싸인 칸) 안에서의 비율 위치. 구획이 커지거나 작아지면 같은 비율로 재배치된다
- host = route: 경로(덕트). 벽을 관통하고 기둥과 이격해야 한다
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out" / "real"

DISC = {"E": {"name": "전기", "color": 30}, "M": {"name": "설비", "color": 140}, "F": {"name": "소방", "color": 10}}
TYPES = [
    {"id": "EO1", "disc": "E", "name": "콘센트 2구", "host": "wall", "block": "E_OUTLET", "layer": "E-POWER", "size": 200, "spec": "220V 16A 2구 접지"},
    {"id": "ES1", "disc": "E", "name": "스위치", "host": "wall", "block": "E_SWITCH", "layer": "E-POWER", "size": 160, "spec": "1로 스위치"},
    {"id": "EP1", "disc": "E", "name": "분전반", "host": "wall", "block": "E_PANEL", "layer": "E-POWER", "size": 600, "spec": "매입형 600x150"},
    {"id": "EL1", "disc": "E", "name": "다운라이트", "host": "bay", "block": "E_LIGHT", "layer": "E-LIGHT", "size": 260, "spec": "LED 15W 매입"},
    {"id": "MD1", "disc": "M", "name": "디퓨저 600각", "host": "bay", "block": "M_DIFF", "layer": "M-DIFF", "size": 600, "spec": "급기 600x600"},
    {"id": "MR1", "disc": "M", "name": "급기 덕트 400", "host": "route", "block": None, "layer": "M-DUCT", "size": 400, "spec": "400x250, 기둥 이격 100 이상"},
    {"id": "FS1", "disc": "F", "name": "스프링클러 헤드", "host": "bay", "block": "F_SPK", "layer": "F-SPK", "size": 140, "spec": "하향식, 헤드 간격 3.0 m 이하(데모용 가정)"},
    {"id": "FD1", "disc": "F", "name": "연기 감지기", "host": "bay", "block": "F_DET", "layer": "F-DET", "size": 220, "spec": "광전식"},
]
BY_ID = {t["id"]: t for t in TYPES}
BY_BLOCK = {t["block"]: t for t in TYPES if t["block"]}
# 검사 기준 (데모용 가정값)
RULES = {"head_max_spacing": 3000, "duct_clearance": 100, "device_opening_clearance": 100}


def ensure_blocks(doc):
    """기호 블록과 레이어를 도면에 만든다. 블록 원점 = 기구 위치, 벽 부착형은 +y가 실내 쪽."""
    for t in TYPES:
        if t["layer"] not in doc.layers:
            doc.layers.add(t["layer"], color=DISC[t["disc"]]["color"])

    def new(name, layer, draw):
        if name in doc.blocks:
            return
        b = doc.blocks.new(name=name)
        draw(b, {"layer": layer})
        for i, tag in enumerate(("TAG", "TYPE", "HOST")):
            a = b.add_attdef(tag, (0, -150 - 90 * i), dxfattribs={"height": 60, "layer": layer})
            a.is_invisible = True

    def outlet(b, at):
        b.add_circle((0, 100), 100, dxfattribs=at)
        b.add_line((-100, 0), (100, 0), dxfattribs=at)
        b.add_line((-35, 40), (-35, 160), dxfattribs=at)
        b.add_line((35, 40), (35, 160), dxfattribs=at)

    def switch(b, at):
        b.add_circle((0, 80), 80, dxfattribs=at)
        b.add_circle((0, 80), 30, dxfattribs=at)
        b.add_line((57, 137), (170, 250), dxfattribs=at)

    def panel(b, at):
        b.add_lwpolyline([(-300, 0), (300, 0), (300, 150), (-300, 150)], close=True, dxfattribs=at)
        b.add_line((-300, 0), (300, 150), dxfattribs=at)
        b.add_line((-300, 75), (0, 150), dxfattribs=at)
        b.add_line((0, 0), (300, 75), dxfattribs=at)

    def light(b, at):
        b.add_circle((0, 0), 130, dxfattribs=at)
        b.add_line((-92, -92), (92, 92), dxfattribs=at)
        b.add_line((-92, 92), (92, -92), dxfattribs=at)

    def diff(b, at):
        b.add_lwpolyline([(-300, -300), (300, -300), (300, 300), (-300, 300)], close=True, dxfattribs=at)
        b.add_lwpolyline([(-180, -180), (180, -180), (180, 180), (-180, 180)], close=True, dxfattribs=at)
        b.add_line((-300, -300), (-180, -180), dxfattribs=at)
        b.add_line((300, -300), (180, -180), dxfattribs=at)
        b.add_line((300, 300), (180, 180), dxfattribs=at)
        b.add_line((-300, 300), (-180, 180), dxfattribs=at)

    def spk(b, at):
        b.add_circle((0, 0), 70, dxfattribs=at)
        b.add_line((-120, 0), (120, 0), dxfattribs=at)
        b.add_line((0, -120), (0, 120), dxfattribs=at)

    def det(b, at):
        b.add_circle((0, 0), 110, dxfattribs=at)
        b.add_circle((0, 0), 45, dxfattribs=at)

    draw = {"E_OUTLET": outlet, "E_SWITCH": switch, "E_PANEL": panel, "E_LIGHT": light, "M_DIFF": diff, "F_SPK": spk, "F_DET": det}
    for t in TYPES:
        if t["block"]:
            new(t["block"], t["layer"], draw[t["block"]])


def render_schedule(out_png):
    import ezdxf
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from ezdxf.addons.drawing import RenderContext, Frontend
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

    plt.rcParams["font.family"] = ["Malgun Gothic", "AppleSDGothicNeoR00", "NanumGothic", "DejaVu Sans"]
    doc = ezdxf.new("R2013", setup=True)
    ensure_blocks(doc)
    msp = doc.modelspace()
    fig = plt.figure(figsize=(16, 4.6), facecolor="white")
    fig.suptitle("설비·전기·소방 일람표 (가상, 시연용)", fontsize=13, y=0.98)
    n = len(TYPES)
    for i, t in enumerate(TYPES):
        ax = fig.add_axes([i / n + 0.008, 0.36, 1 / n - 0.016, 0.5])
        ax.set_facecolor("black"); ax.set_xticks([]); ax.set_yticks([])
        ents = []
        if t["block"]:
            ents = [msp.add_blockref(t["block"], (i * 5000, 0), dxfattribs={"layer": t["layer"]})]
            cx, cy, half = i * 5000, 60 if t["host"] == "wall" else 0, 420
            if t["host"] == "wall":
                ents.append(msp.add_line((i * 5000 - 400, 0), (i * 5000 + 400, 0), dxfattribs={"layer": "0", "color": 8}))
        else:
            ents = [msp.add_lwpolyline([(i * 5000 - 380, 0), (i * 5000 + 380, 0)], dxfattribs={"layer": t["layer"], "const_width": 0}),
                    msp.add_line((i * 5000 - 380, 200), (i * 5000 + 380, 200), dxfattribs={"layer": t["layer"]}),
                    msp.add_line((i * 5000 - 380, -200), (i * 5000 + 380, -200), dxfattribs={"layer": t["layer"]})]
            cx, cy, half = i * 5000, 0, 420
        ctx = RenderContext(doc); ctx.set_current_layout(msp)
        Frontend(ctx, MatplotlibBackend(ax)).draw_entities(ents)
        ax.set_xlim(cx - half, cx + half); ax.set_ylim(cy - half, cy + half); ax.set_aspect("equal")
        host = {"wall": "벽에 붙음", "bay": "구획 안 비율 배치", "route": "경로(벽 관통·기둥 이격)"}[t["host"]]
        fig.text((i + 0.5) / n, 0.33, f'{t["id"]}  {t["name"]}' + chr(10) + f'{DISC[t["disc"]]["name"]} · {host}' + chr(10) + t["spec"], ha="center", va="top", fontsize=8.5)
    fig.savefig(out_png, dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "mep_schedule.json").write_text(json.dumps({"virtual": True, "disciplines": DISC, "types": TYPES, "rules": RULES}, ensure_ascii=False, indent=1), encoding="utf-8")
    for t in TYPES:
        print(f'{t["id"]:4s} {DISC[t["disc"]]["name"]:3s} {t["name"]:12s} {t["host"]:6s} {t["spec"]}')
    render_schedule(OUT / "mep_schedule.png")
    print("saved", OUT / "mep_schedule.json", OUT / "mep_schedule.png")
