"""관계도에서 변경 입력 → 연결 요소 갱신 → 그림 재생성 → changes.json 기록 (3단계 수정).

사용법:
  python graph/apply_change.py "C1 move 0 500"
  python graph/apply_change.py "C1 resize 600x400"
여러 개를 공백 없이 ; 로 구분: "C1 move 0 500;C2 resize 600x400"

변경 기록은 1단계(회의 발화 추출)와 같은 changes.json 스키마를 쓴다.
따라서 2단계 전파 코드는 입구가 회의든 관계도든 하나면 된다.
"""
import json
import math
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_graph import render  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BEAM_SPAN_WARN = 7500  # mm. 이 값을 넘는 보 스팬은 재검토 경고 (팀 가정, 데모용)


def parse(cmd: str):
    p = cmd.split()
    target, action = p[0], p[1]
    if action == "move":
        return target, action, {"dx": float(p[2]), "dy": float(p[3])}
    if action == "resize":
        return target, action, {"spec": p[2]}
    raise ValueError(f"지원하지 않는 변경: {cmd}")


def apply(graph: dict, target: str, action: str, params: dict):
    nodes = {n["id"]: n for n in graph["nodes"]}
    if target not in nodes:
        raise KeyError(f"{target} 노드가 관계도에 없음")
    node = nodes[target]
    hot_nodes, hot_edges, impacts, warnings = {target}, set(), [], []
    incident = [e for e in graph["edges"] if target in (e["from"], e["to"])]

    if action == "move":
        old = list(node["xy"])
        node["xy"] = [old[0] + params["dx"], old[1] + params["dy"]]
        impacts.append({"element": target, "kind": "column", "change": f"위치 {old} → {node['xy']}", "handle": node["handle"]})
        for e in incident:
            a, b = nodes[e["from"]]["xy"], nodes[e["to"]]["xy"]
            old_len = e["length"]
            e["length"] = round(math.hypot(a[0] - b[0], a[1] - b[1]))
            hot_edges.add(e["id"])
            impacts.append({"element": e["id"], "kind": e["type"], "change": f"길이 {old_len} → {e['length']}", "handle": e["handle"]})
            if e["type"] == "beam" and e["length"] > BEAM_SPAN_WARN and e["length"] - old_len >= 100:
                warnings.append(f'{e["id"]} 스팬 {old_len/1000:.2f}m → {e["length"]/1000:.2f}m, 기준 {BEAM_SPAN_WARN/1000:.1f}m 초과. 보 단면 재검토 필요')
            # 이 벽에 붙은 창호·콘센트는 비율 t를 유지하며 따라 움직인다
            for n in graph["nodes"]:
                if n.get("on_edge") == e["id"]:
                    t = n["t"]
                    n["xy"] = [round(a[0] + t * (b[0] - a[0])), round(a[1] + t * (b[1] - a[1]))]
                    hot_nodes.add(n["id"])
                    impacts.append({"element": n["id"], "kind": n["type"], "change": f"{e['id']} 위 위치 재계산 → {n['xy']}", "handle": n["handle"]})
        if node.get("schedule_handle"):
            impacts.append({"element": f"일람표 {target}", "kind": "schedule", "change": "좌표 갱신", "handle": node["schedule_handle"]})

    elif action == "resize":
        old = node["spec"]
        node["spec"] = params["spec"]
        impacts.append({"element": target, "kind": "column", "change": f"단면 {old} → {params['spec']}", "handle": node["handle"]})
        if node.get("schedule_handle"):
            impacts.append({"element": f"일람표 {target}", "kind": "schedule", "change": f"{old} → {params['spec']}", "handle": node["schedule_handle"]})
        for e in incident:
            if e["type"] == "beam":
                hot_edges.add(e["id"])
                impacts.append({"element": e["id"], "kind": "beam", "change": "지지폭 변경, 순스팬·정착 길이 확인", "handle": e["handle"]})
            elif e["type"] == "wall":
                hot_edges.add(e["id"])
                impacts.append({"element": e["id"], "kind": "wall", "change": "기둥 돌출로 벽 마감선 조정", "handle": e["handle"]})
        try:
            ow, oh = map(int, old.lower().split("x"))
            nw, nh = map(int, params["spec"].lower().split("x"))
            if nw * nh < ow * oh:
                warnings.append(f"{target} 단면 축소({old}→{params['spec']}). 축력 검토 필요")
        except ValueError:
            pass

    return {"nodes": hot_nodes, "edges": hot_edges}, impacts, warnings


def record_change(cmd, target, action, params, impacts, warnings, sheet):
    path = ROOT / "out" / "changes.json"
    changes = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    cid = f"CR-{len(changes) + 1:03d}"
    changes.append({
        "id": cid,
        "source": {"type": "graph_input", "text": cmd, "speaker": None, "time": datetime.now().isoformat(timespec="seconds")},
        "sheet": sheet,
        "target": target,
        "action": action,
        "params": params,
        "confidence": 1.0,
        "status": "confirmed",
        "reviewer": "graph-operator",
        "reviewed_at": datetime.now().isoformat(timespec="seconds"),
        "impacts": impacts,
        "warnings": warnings,
    })
    path.write_text(json.dumps(changes, ensure_ascii=False, indent=1), encoding="utf-8")
    return cid


def main(cmds):
    gpath = ROOT / "out" / "graph.json"
    graph = json.loads(gpath.read_text(encoding="utf-8"))
    all_hot = {"nodes": set(), "edges": set()}
    for cmd in cmds:
        target, action, params = parse(cmd)
        hot, impacts, warnings = apply(graph, target, action, params)
        cid = record_change(cmd, target, action, params, impacts, warnings, graph["sheet"])
        all_hot["nodes"] |= hot["nodes"]
        all_hot["edges"] |= hot["edges"]
        print(f"[{cid}] {cmd}")
        for i in impacts:
            print(f"   영향 {i['kind']:8s} {i['element']:12s} {i['change']}")
        for w in warnings:
            print(f"   경고 {w}")
    (ROOT / "out" / "graph_after.json").write_text(json.dumps(graph, ensure_ascii=False, indent=1), encoding="utf-8")
    render(graph, ROOT / "out" / "graph_after.png", highlight=all_hot, title=f'관계도 {graph["sheet"]} — 변경 후 (빨강: 영향 요소) : {"; ".join(cmds)}')
    print("saved out/graph_after.json, out/graph_after.png, out/changes.json")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "C1 move 0 500"
    main([c.strip() for c in arg.split(";") if c.strip()])
