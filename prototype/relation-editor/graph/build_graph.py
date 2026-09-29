"""사이드카 JSON → 관계 그래프 (3단계 읽기).

노드: 기둥(column), 창호(window), 콘센트(outlet)
엣지: 보(beam), 벽(wall) — 선의 양 끝점을 가장 가까운 기둥에 매칭
창호·콘센트는 삽입점이 놓인 벽 엣지에 `on_edge`로 붙는다.
출력: out/graph.json, out/graph_before.png
"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOL = 300  # 끝점-기둥 매칭 허용 거리 (mm)


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def point_on_segment(p, a, b, tol=200):
    """점 p가 선분 ab 위(허용 tol)에 있는지와 a에서의 비율 t."""
    ax, ay = a
    bx, by = b
    px, py = p
    L2 = (bx - ax) ** 2 + (by - ay) ** 2
    if L2 == 0:
        return False, 0
    t = ((px - ax) * (bx - ax) + (py - ay) * (by - ay)) / L2
    if t < 0 or t > 1:
        return False, t
    cx, cy = ax + t * (bx - ax), ay + t * (by - ay)
    return dist(p, (cx, cy)) <= tol, round(t, 3)


def build(sidecar: dict) -> dict:
    objs = sidecar["objects"]
    nodes = {}
    edges = []

    columns = [o for o in objs if o["type"] == "INSERT" and o.get("block") == "COL"]
    for c in columns:
        nodes[c["tag"]] = {"id": c["tag"], "type": "column", "xy": c["insert"], "spec": c["attrs"].get("SIZE"), "handle": c["handle"], "layer": c["layer"]}

    def nearest_column(pt):
        best = min(columns, key=lambda c: dist(c["insert"], pt))
        return best["tag"] if dist(best["insert"], pt) <= TOL else None

    for o in objs:
        if o["type"] != "LINE" or o["layer"] not in ("S-BEAM", "A-WALL"):
            continue
        a, b = nearest_column(o["start"]), nearest_column(o["end"])
        if not a or not b or a == b:
            continue
        kind = "beam" if o["layer"] == "S-BEAM" else "wall"
        eid = o.get("tag") or f"{kind[0].upper()}-{a}-{b}"
        edges.append({"id": eid, "type": kind, "from": a, "to": b, "length": round(dist(o["start"], o["end"])), "handle": o["handle"], "layer": o["layer"]})

    walls = [e for e in edges if e["type"] == "wall"]
    for o in objs:
        if o["type"] != "INSERT" or o.get("block") not in ("WIN", "OUTLET"):
            continue
        ntype = "window" if o["block"] == "WIN" else "outlet"
        host, t = None, None
        for w in walls:
            ok, tt = point_on_segment(o["insert"], nodes[w["from"]]["xy"], nodes[w["to"]]["xy"])
            if ok:
                host, t = w["id"], tt
                break
        nodes[o["tag"]] = {"id": o["tag"], "type": ntype, "xy": o["insert"], "spec": o["attrs"].get("SIZE"), "on_edge": host, "t": t, "handle": o["handle"], "layer": o["layer"]}

    # 일람표 텍스트 → 기둥 노드에 연결 (2단계에서 갱신 대상)
    for o in objs:
        if o["type"] == "TEXT" and o["layer"] == "A-SCHED":
            parts = o["text"].split()
            if len(parts) == 2 and parts[0] in nodes:
                nodes[parts[0]]["schedule_handle"] = o["handle"]

    return {"sheet": sidecar["sheet"], "units": "mm", "nodes": list(nodes.values()), "edges": edges}


def render(graph: dict, out_png: Path, highlight=None, title=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle, RegularPolygon

    plt.rcParams["font.family"] = ["Malgun Gothic", "AppleSDGothicNeoR00", "NanumGothic", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    highlight = highlight or {"nodes": set(), "edges": set()}
    nodes = {n["id"]: n for n in graph["nodes"]}

    fig, ax = plt.subplots(figsize=(11, 6))
    for e in graph["edges"]:
        a, b = nodes[e["from"]]["xy"], nodes[e["to"]]["xy"]
        hot = e["id"] in highlight["edges"]
        color = "#d62728" if hot else ("#444444" if e["type"] == "wall" else "#1f77b4")
        style = "-" if e["type"] == "wall" else "--"
        lw = 3.5 if (e["type"] == "wall") else 1.6
        if hot:
            lw += 1.5
        off = 120 if e["type"] == "beam" else 0  # 보를 벽에서 살짝 띄워 겹침 방지
        ax.plot([a[0], b[0]], [a[1] + off, b[1] + off], style, color=color, lw=lw, zorder=1)
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        if e["type"] == "beam":
            ax.text(mx, my + 350, f'{e["id"]} L={e["length"]/1000:.1f}m', ha="center", fontsize=8, color=color)

    for n in graph["nodes"]:
        x, y = n["xy"]
        hot = n["id"] in highlight["nodes"]
        if n["type"] == "column":
            w, h = (n["spec"] or "400x400").lower().split("x")
            r = 220 + (int(w) - 400) * 0.6
            ax.add_patch(Circle((x, y), r, fc="#d62728" if hot else "white", ec="#d62728" if hot else "black", lw=2, zorder=3))
            ax.text(x, y - 650, f'{n["id"]}\n{n["spec"]}', ha="center", va="top", fontsize=9, fontweight="bold" if hot else "normal")
        elif n["type"] == "window":
            ax.add_patch(Rectangle((x - 400, y - 160), 800, 320, fc="#d62728" if hot else "#9edae5", ec="black", zorder=4))
            ax.text(x, y + 420, f'{n["id"]} {n["spec"]}', ha="center", fontsize=8)
        elif n["type"] == "outlet":
            ax.add_patch(RegularPolygon((x, y), 3, radius=200, fc="#d62728" if hot else "#ff9896", ec="black", zorder=4))
            ax.text(x, y - 500, n["id"], ha="center", fontsize=7)

    ax.set_aspect("equal")
    ax.set_xlim(-1500, 16500)
    ax.set_ylim(-1500, 7500)
    ax.axis("off")
    ax.set_title(title or f'관계도 {graph["sheet"]} — ○ 기둥  ─ 벽  - - 보  □ 창호  △ 콘센트', fontsize=11)
    fig.tight_layout()
    out_png.parent.mkdir(exist_ok=True)
    fig.savefig(out_png, dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    sheet = sys.argv[1] if len(sys.argv) > 1 else "A-101"
    sc = json.loads((ROOT / "out" / f"sidecar_{sheet}.json").read_text(encoding="utf-8"))
    g = build(sc)
    (ROOT / "out" / "graph.json").write_text(json.dumps(g, ensure_ascii=False, indent=1), encoding="utf-8")
    render(g, ROOT / "out" / "graph_before.png")
    kinds = {}
    for n in g["nodes"]:
        kinds[n["type"]] = kinds.get(n["type"], 0) + 1
    ek = {}
    for e in g["edges"]:
        ek[e["type"]] = ek.get(e["type"], 0) + 1
    print(f"graph.json: nodes {kinds} | edges {ek}")
    for n in g["nodes"]:
        if n.get("on_edge"):
            print(f'  {n["id"]} ({n["type"]}) on {n["on_edge"]} t={n["t"]}')
