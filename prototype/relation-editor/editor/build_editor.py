"""관계도 JSON을 넣은 편집기 HTML 한 파일 생성 (서버 없이 브라우저에서 바로 열림).

python editor/build_editor.py            # out/real/graph_real.json (원본 DXF에서 읽은 관계도) → out/editor/relation_editor_A12.html
python editor/build_editor.py pdf        # out/pdf/graph_pdf.json (PDF에서 읽은 관계도)
python editor/build_editor.py real open  # 만들고 브라우저로 열기
"""
import json
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
src_kind = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("real", "pdf", "blank") else "real"
if src_kind == "blank":
    # 맨땅에서 시작하는 새 프로젝트. 일람표는 과거 도면에서 읽은 것(기호 복사 가능)과 표준 크기의 가상 타입을 함께 넣는다
    sys.path.insert(0, str(ROOT / "mep"))
    import mep_schedule as ms
    name = next((a for a in sys.argv[2:] if a != "open"), "NEW1")
    lib = ROOT / "out" / "real" / "schedule.json"
    types = [t for t in json.loads(lib.read_text(encoding="utf-8"))["types"] if not t.get("check") and not t.get("virtual")] if lib.exists() else []
    for t in types:
        t["instances"] = []
    nw = max([int(t["id"][2:]) for t in types if t["id"].startswith("WT")] or [0])
    nd = max([int(t["id"][2:]) for t in types if t["id"].startswith("DT")] or [0])
    for kind, leaves, width in [("window", 1, 600), ("window", 1, 900), ("window", 1, 1200), ("window", 1, 1500), ("window", 1, 1800), ("window", 1, 2400),
                                ("door", 1, 800), ("door", 1, 900), ("door", 1, 1000), ("door", 2, 1800)]:
        if any(t["kind"] == kind and t["leaves"] == leaves and t["width"] == width for t in types):
            continue
        if kind == "window":
            nw += 1; tid = f"WT{nw}"
        else:
            nd += 1; tid = f"DT{nd}"
        types.append({"id": tid, "kind": kind, "leaves": leaves, "band": False, "width": width, "virtual": True, "check": False, "count": 0, "by_sheet": {}, "donor": None, "instances": []})
    graph = {"sheet": name, "units": "mm", "source": "blank", "auto_extents": True, "auto_dims": True, "grids": {}, "nodes": [], "edges": [], "openings": [], "dims": [],
             "schedule": {"columns": [], "windows": [], "doors": []}, "schedule_types": types, "project": {"floor_height": 3400}, "site": None, "cores": [],
             "mep": {"devices": [], "routes": [], "types": ms.TYPES, "rules": ms.RULES, "disciplines": ms.DISC, "virtual": True}}
else:
    src = ROOT / "out" / ("pdf/graph_pdf.json" if src_kind == "pdf" else "real/graph_real.json")
    graph = json.loads(src.read_text(encoding="utf-8"))
graph.setdefault("source", src_kind)
# 편집기에 필요 없는 큰 필드 제거
for e in graph["edges"]:
    e.pop("wall_handles", None)
# 건물 전체 문·창호 일람표 (graph/build_schedule.py 가 만든 것). 없으면 편집기가 이 도면만으로 일람표를 만든다
sched = ROOT / "out" / "real" / "schedule.json"
if sched.exists() and src_kind == "real":
    graph["schedule_types"] = json.loads(sched.read_text(encoding="utf-8"))["types"]
prof = ROOT / "propagate" / "layer_profile.json"      # 선 굵기 규칙은 레이어 체계 파일에서
if prof.exists():
    rules = json.loads(prof.read_text(encoding="utf-8")).get("lineweight_rules")
    if rules:
        graph["lw_rules"] = {k: v for k, v in rules.items() if k != "note"}
payload = json.dumps(graph, ensure_ascii=False).replace("</", "<\\/")
html = (ROOT / "editor" / "template.html").read_text(encoding="utf-8").replace("/*__GRAPH__*/null", payload)
out = ROOT / "out" / "editor"
out.mkdir(parents=True, exist_ok=True)
dst = out / f'relation_editor_{graph["sheet"]}{"_pdf" if src_kind == "pdf" else ""}.html'
dst.write_text(html, encoding="utf-8")
print(f"saved {dst} ({dst.stat().st_size // 1024} KB) | grids {len(graph['grids'])} nodes {len(graph['nodes'])} edges {len(graph['edges'])} openings {len(graph['openings'])} dims {len(graph['dims'])}")
if "open" in sys.argv:
    webbrowser.open(dst.as_uri())
