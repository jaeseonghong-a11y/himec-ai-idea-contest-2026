"""실도면 관계도에서 변경 입력 → 연결 요소·창호·문·치수 갱신 → changes.json 기록.

사용법:
  python graph/apply_change_real.py "X6 move 500"              # 그리드선 이동 (그 위 기둥·교점·벽·보·창호·문·치수 갱신)
  python graph/apply_change_real.py "C@X6-Y2 resize 700x400"   # 기둥 단면 변경
  여러 개는 ; 로 구분
"""
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_graph_real import render  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out" / "real"
SPAN_WARN = 7500  # mm, 데모용 가정


def parse(cmd):
    p = cmd.split()
    if p[1] == "move":
        return p[0], "move", {"delta": float(p[2])}
    if p[1] == "resize":
        return p[0], "resize", {"spec": p[2]}
    raise ValueError(cmd)


def apply(graph, target, action, params):
    grids, nodes = graph["grids"], {n["id"]: n for n in graph["nodes"]}
    hot = {"nodes": set(), "edges": set(), "grids": set(), "dims": set(), "openings": set()}
    impacts, warnings = [], []

    if action == "move" and target in grids:
        g = grids[target]
        axis = 0 if g["axis"] == "x" else 1
        old = g["coord"]
        g["coord"] = old + params["delta"]
        hot["grids"].add(target)
        impacts.append({"element": target, "kind": "grid", "change": f"{old} → {g['coord']}", "handles": g["handles"], "delta": params["delta"], "axis": g["axis"]})
        for n in graph["nodes"]:
            if n["grid"][axis] == target:
                n["xy"][axis] = g["coord"]
                hot["nodes"].add(n["id"])
                if n["type"] == "column":
                    impacts.append({"element": n["id"], "kind": "column", "change": f"위치 {g['axis']}={g['coord']}", "handle": n["handle"], "delta": params["delta"], "axis": g["axis"]})
        for e in graph["edges"]:
            a, b = nodes[e["from"]]["xy"], nodes[e["to"]]["xy"]
            L = round(abs(a[0] - b[0]) + abs(a[1] - b[1]))
            if L != e["length"]:
                old_L = e["length"]
                e["length"] = L
                hot["edges"].add(e["id"])
                kind = ("벽" if e["wall"] else "") + ("+보" if e["beam"] and e["wall"] else ("보" if e["beam"] else ""))
                impacts.append({"element": e["id"], "kind": kind, "change": f"길이 {old_L} → {L}", "handles": e.get("wall_handles", [])})
                if e["beam"] and L > SPAN_WARN and L > old_L:
                    warnings.append(f'{e["id"]} 보 스팬 {old_L} → {L} mm, 기준 {SPAN_WARN} 초과. 보 단면 재검토')
                for o in graph["openings"]:
                    if o["on_edge"] == e["id"]:
                        t = o["t"]
                        o["xy"] = [round(a[0] + t * (b[0] - a[0])), round(a[1] + t * (b[1] - a[1]))]
                        hot["openings"].add(o["id"])
                        impacts.append({"element": o["id"], "kind": o["type"], "change": f'{e["id"]} 위 위치 재계산 → {o["xy"]}', "handles": o["handles"]})
                        if o["type"] == "door" and o.get("band") and L < old_L:
                            warnings.append(f'{o["id"]} 문 띠(폭 {o["width"]})가 놓인 벽이 {old_L} → {L}로 줄어듦. 개구부 폭 재검토')
        for d in graph["dims"]:
            if target in (d["from_grid"], d["to_grid"]):
                gm = {k: v for k, v in grids.items() if v["axis"] == g["axis"]}
                new_m = abs(gm[d["to_grid"]]["coord"] - gm[d["from_grid"]]["coord"]) if d["attached"] else d["measurement"]
                old_m = d["measurement"]
                d["measurement"] = round(new_m)
                hot["dims"].add(d["handle"])
                impacts.append({"element": f'DIM {d["handle"]}', "kind": "dimension", "change": f'{d["from_grid"]}~{d["to_grid"]} {old_m} → {d["measurement"]}', "handle": d["handle"],
                                "moved_grid": target, "delta": params["delta"], "axis": g["axis"], "old_coord": old})
        for d in graph["dims"]:
            if d["attached"] and target in (d["from_grid"], d["to_grid"]) and d["measurement"] >= 10000:
                warnings.append(f'전체 치수 {d["from_grid"]}~{d["to_grid"]}가 {d["measurement"]} mm로 변경. 건축면적·면적산출표 재검토')

    elif action == "resize" and target in nodes:
        n = nodes[target]
        old = n["spec"]
        n["spec"] = params["spec"]
        hot["nodes"].add(target)
        impacts.append({"element": target, "kind": "column", "change": f"단면 {old} → {params['spec']}", "handle": n["handle"], "new_spec": params["spec"], "old_spec": old})
        for e in graph["edges"]:
            if target in (e["from"], e["to"]):
                hot["edges"].add(e["id"])
                impacts.append({"element": e["id"], "kind": "보" if e["beam"] else "벽", "change": "지지폭 변경, 순스팬·마감선 확인"})
        # 일람표 갱신
        for c in graph["schedule"]["columns"]:
            if c["id"] == target:
                c["spec"] = params["spec"]
    else:
        raise KeyError(f"{target} 을 관계도에서 찾지 못함")
    return hot, impacts, warnings


def record(cmd, target, action, params, impacts, warnings, sheet):
    path = OUT / "changes.json"
    changes = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    cid = f"CR-{len(changes) + 1:03d}"
    now = datetime.now().isoformat(timespec="seconds")
    changes.append({"id": cid, "source": {"type": "graph_input", "text": cmd, "speaker": None, "time": now}, "sheet": sheet, "target": target,
                    "action": action, "params": params, "confidence": 1.0, "status": "confirmed", "reviewer": "graph-operator", "reviewed_at": now,
                    "impacts": impacts, "warnings": warnings})
    path.write_text(json.dumps(changes, ensure_ascii=False, indent=1), encoding="utf-8")
    return cid


def main(cmds):
    graph = json.loads((OUT / "graph_real.json").read_text(encoding="utf-8"))
    allhot = {"nodes": set(), "edges": set(), "grids": set(), "dims": set(), "openings": set()}
    for cmd in cmds:
        t, a, p = parse(cmd)
        hot, impacts, warnings = apply(graph, t, a, p)
        cid = record(cmd, t, a, p, impacts, warnings, graph["sheet"])
        for k in allhot:
            allhot[k] |= hot[k]
        print(f"[{cid}] {cmd}")
        for i in impacts:
            print(f'   영향 {i["kind"]:10s} {i["element"]:24s} {i["change"]}')
        for w in warnings:
            print(f"   경고 {w}")
    (OUT / "graph_real_after.json").write_text(json.dumps(graph, ensure_ascii=False, indent=1), encoding="utf-8")
    render(graph, OUT / "graph_real_after.png", highlight=allhot, title=f'관계도 {graph["sheet"]} — 변경 후 (빨강: 영향) : {"; ".join(cmds)}')
    print("saved out/real/graph_real_after.png, changes.json")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "X6 move 500"
    main([c.strip() for c in arg.split(";") if c.strip()])
