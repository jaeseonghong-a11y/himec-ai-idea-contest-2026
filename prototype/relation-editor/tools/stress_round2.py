"""한계 찾기 3단계: 관계도에서 새로 그린 도면을 '기존 도면'으로 다시 열어 고칠 수 있는가.

새 도면(NEW1T_edited.dxf)을 real_dxf/NEW1R.dxf 로 두고 → 관계도 읽기 → 편집기 만들기 → 그리드 이동·창 추가·코어 벽 두께 변경 →
기존 도면 경로(띠 STRETCH, 벽선 자르기)로 반영 → 다시 읽어 대조.
python tools/stress_round2.py
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "graph"))
import build_graph_real as bgr  # noqa: E402

src = ROOT / "out" / "real" / "NEW1T_edited.dxf"
dst = ROOT / "real_dxf" / "NEW1R.dxf"
shutil.copyfile(src, dst)
g = bgr.build(dst, "NEW1R")
g["source"] = "real"
for e in g["edges"]:
    e.pop("wall_handles", None)
sched = ROOT / "out" / "real" / "schedule.json"
if sched.exists():
    g["schedule_types"] = json.loads(sched.read_text(encoding="utf-8"))["types"]
print(f'다시 읽은 새 도면: 그리드 {len(g["grids"])}, 기둥 {sum(n["type"] == "column" for n in g["nodes"])}, 구간 {len(g["edges"])}(사선 {len(g.get("diagonal_edges") or [])}), 문·창호 {len(g["openings"])}, 치수 {len(g["dims"])}, 코어 {len(g.get("cores", []))}, 대지 {"있음" if g.get("site") else "없음"}, 기구 {len((g.get("mep") or {}).get("devices", []))}')
html = (ROOT / "editor" / "template.html").read_text(encoding="utf-8").replace("/*__GRAPH__*/null", json.dumps(g, ensure_ascii=False).replace("</", "<\\/"))
ed = ROOT / "out" / "editor" / "relation_editor_NEW1R.html"
ed.write_text(html, encoding="utf-8")

js = r'''
const fs = require("fs"), vm = require("vm");
const html = fs.readFileSync(process.argv[2], "utf8");
const grab = id => html.match(new RegExp(`<script id="${id}"[^>]*>([\\s\\S]*?)</script>`))[1];
const ctx = { module: { exports: {} }, console }; vm.createContext(ctx);
vm.runInContext(grab("data") + "\n" + grab("core") + "\nmodule.exports.ORIG_GRAPH = ORIG_GRAPH;", ctx);
const C = ctx.module.exports, ORIG = C.initModel(C.ORIG_GRAPH), G = C.initModel(C.ORIG_GRAPH);
const log = [];
const gx = Object.values(G.grids).filter(x => x.axis === "x").sort((a, b) => a.coord - b.coord);
const x2 = gx[1]; C.moveGridTo(G, x2.id, x2.coord + 500); log.push(`${x2.id} +500`);
const wall = G.edges.find(e => e.wall && !e.diag && !G.openings.some(o => o.on_edge === e.id) && e.length >= 5000);
const N = Object.fromEntries(G.nodes.map(n => [n.id, n]));
if (wall) { const a = N[wall.from].xy, b = N[wall.to].xy, hz = G.grids[wall.along].axis === "y"; const vt = G.otypes.find(t => t.kind === "window" && t.virtual) || G.otypes.find(t => t.kind === "window");
  const id = C.addOpening(G, wall.id, "window", hz ? (a[0] + b[0]) / 2 : (a[1] + b[1]) / 2, vt.id); log.push(`창 추가 ${id} on ${wall.id}`); }
const ev = G.cores.find(c => c.kind === "elevator"); if (ev) { ev.wall_thick = 200; log.push(`${ev.id} 벽 두께 200`); }
C.recompute(G);
const w = C.warnings(ORIG, G), dd = C.diff(ORIG, G), lab = n => n.grid.join("-");
const out = C.exportChanges(ORIG, G, "시험");
const expected = {
  columns: G.nodes.filter(n => n.type === "column").map(n => ({ label: lab(n), xy: n.xy, spec: n.spec })), columns_deleted: [],
  walls_checked: dd.walls_added.map(e => ({ label: e.id, from_xy: e.from_xy, to_xy: e.to_xy, expect: true })),
  openings_checked: dd.openings_added.map(o => ({ id: o.id, type: o.type, xy: o.center, width: o.width, expect: true })),
  dims_checked: dd.dims.map(x => ({ handle: x.handle, to: x.to })),
  cores: G.cores.map(c => ({ id: c.id, type: c.type, anchor: c.anchor, anchor_xy: [G.grids[c.anchor[0]].coord, G.grids[c.anchor[1]].coord], dir: c.dir, side: c.side, entry: c.rect.entry, travel: c.kind === "stair" ? (c.travel || "UP") : null, walls: c.rect.flags, wall_thick: c.rect.T, rect: [c.rect.x0, c.rect.y0, c.rect.x1, c.rect.y1] })),
  mep: { devices: G.mep ? G.mep.devices.filter(d => !d.orphan).map(x => ({ id: x.id, type: x.type, xy: x.xy })) : [], checked: [], routes: [] },
};
fs.writeFileSync(process.argv[3], JSON.stringify(out, null, 1)); fs.writeFileSync(process.argv[4], JSON.stringify(expected, null, 1));
console.log("편집:", log.join(" / ")); console.log("내보낸 동작:", out.map(c => c.action).join(", ")); console.log("경고:", w.length); w.slice(0, 8).forEach(x => console.log("  - " + x));
'''
sd = ROOT / "out" / "editor" / "stress"; sd.mkdir(parents=True, exist_ok=True)
(sd / "_round2.js").write_text(js, encoding="utf-8")
ch, ex = sd / "changes_NEW1R.json", sd / "expected_NEW1R.json"
r = subprocess.run(["node", str(sd / "_round2.js"), str(ed), str(ch), str(ex)], capture_output=True, text=True, encoding="utf-8", errors="replace")
print(r.stdout); print(r.stderr[-800:] if r.returncode else "")
r = subprocess.run([sys.executable, str(ROOT / "propagate" / "apply_edits.py"), "NEW1R", str(ch), str(ex), "--quick"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT)
for l in r.stdout.splitlines():
    if l.strip().startswith(("CR-", "FAIL", "OK")) or "일치" in l or "오류" in l:
        print(l[:200])
if r.returncode:
    print(r.stderr[-800:])
