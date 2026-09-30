// 한계 찾기 3: 기둥 어긋남·보조 축·변경 지시 (새 프로젝트 S12~S16, 기존 도면 R7~R8)
// node editor/test_stress2.js  →  python tools/stress_run.py S12 S13 S14 S15 S16 R7 R8
const fs = require("fs"), path = require("path"), vm = require("vm");
function load(file) {
  const html = fs.readFileSync(path.join(__dirname, "..", "out", "editor", file), "utf8");
  const grab = id => html.match(new RegExp(`<script id="${id}"[^>]*>([\\s\\S]*?)</script>`))[1];
  const ctx = { module: { exports: {} }, console }; vm.createContext(ctx);
  vm.runInContext(grab("data") + "\n" + grab("core") + "\nmodule.exports.ORIG_GRAPH = ORIG_GRAPH;", ctx);
  return ctx.module.exports;
}
const outDir = path.join(__dirname, "..", "out", "editor", "stress"); fs.mkdirSync(outDir, { recursive: true });
const findings = [];
const note = (sheet, kind, text) => { findings.push({ sheet, kind, text }); console.log(`  [${kind}] ${sheet}: ${text}`); };
const lab = n => n.grid.join("-");
function expectedOf(C, ORIG, G) {
  const dd = C.diff(ORIG, G);
  return {
    columns: G.nodes.filter(n => n.type === "column").map(n => ({ label: lab(n), xy: n.cxy || n.xy, spec: n.spec })),
    columns_deleted: dd.cols_deleted.map(c => ({ label: c.grid.join("-"), xy: c.xy })),
    walls_checked: [...dd.walls_added.map(e => ({ label: e.id, from_xy: e.from_xy, to_xy: e.to_xy, thick: e.thick, expect: true })), ...dd.walls_deleted.map(e => ({ label: e.id, from_xy: e.from_xy, to_xy: e.to_xy, expect: false }))],
    openings_checked: [...dd.openings_added.map(o => ({ id: o.id, type: o.type, xy: o.center, width: o.width, expect: true })), ...dd.openings.filter(o => o.edited).map(o => ({ id: o.id, type: o.type, xy: o.to_xy, width: o.to_w, expect: true }))],
    dims_checked: dd.dims.map(x => ({ handle: x.handle, to: x.to })),
    site: G.site, floor_height: G.project.floor_height,
    cores: (G.cores || []).map(c => ({ id: c.id, type: c.type, anchor: c.anchor, anchor_xy: [G.grids[c.anchor[0]].coord, G.grids[c.anchor[1]].coord], dir: c.dir, side: c.side, entry: c.rect.entry, travel: c.kind === "stair" ? (c.travel || "UP") : null, walls: c.rect.flags, wall_thick: c.rect.T, rect: [c.rect.x0, c.rect.y0, c.rect.x1, c.rect.y1] })),
    auto_dims: [...G.dims.map(d => ({ orient: d.orient, value: d.measurement })), ...G.dims2.map(d => ({ orient: d.orient, value: d.value }))],
    mep: { devices: (G.mep ? G.mep.devices : []).filter(d => !d.orphan).map(x => ({ id: x.id, type: x.type, xy: x.xy })), checked: [], routes: [] },
  };
}
function save(C, ORIG, G, name, sheet, label) {
  const w = C.warnings(ORIG, G), out = C.exportChanges(ORIG, G, "시험").map(c => Object.assign({}, c, { sheet }));
  fs.writeFileSync(path.join(outDir, `changes_${name}.json`), JSON.stringify(out, null, 1));
  fs.writeFileSync(path.join(outDir, `expected_${name}.json`), JSON.stringify(expectedOf(C, ORIG, G), null, 1));
  console.log(`\n== ${name}: ${label}\n   변경 ${out.length}건 (${[...new Set(out.map(c => c.action))].join(", ")}), 경고 ${w.length}건`); w.slice(0, 8).forEach(x => console.log("   - " + x));
  return w;
}
const gid = (G, ax, v) => { const g = Object.values(G.grids).find(x => x.axis === ax && Math.abs(x.coord - v) < 1); return g && g.id; };
const nodeOf = (G, x, y) => G.nodes.find(n => n.grid[0] === x && n.grid[1] === y);

// ===== 새 프로젝트 =====
{
  const C = load("relation_editor_NEW1.html"), ORIG = C.initModel(C.ORIG_GRAPH), fresh = () => C.initModel(C.ORIG_GRAPH);

  // S12: 양방향 어긋남 → 축 두 개, 그리고 그 뒤 원래 축을 옮겨도 보조 축이 따라오는가
  { const G = fresh(); C.newProjectDemo(G); const n = nodeOf(G, "X3", "Y2");
    C.offsetColumn(G, n.id, -350, 400); const r = C.offsetToGrid(G, n.id);
    if (!r || r.grids.length !== 2) note("S12", "이상", `축 두 개가 생겨야 함: ${JSON.stringify(r)}`);
    const x3a = G.grids.X3A, y2a = G.grids.Y2A;
    C.moveGridTo(G, "X3", 15500);
    if (x3a && x3a.coord !== 15500 - 350) note("S12", "이상", `원래 축 X3을 옮기면 보조 축 X3A도 따라와야 함(${x3a.coord})`);
    C.moveGridTo(G, "X3", 15000);
    save(C, ORIG, G, "S12", "S12", "X3-Y2를 (-350, +400) 어긋나게 한 뒤 축 두 개로"); }

  // S13: 어긋난 자리에 창호가 있는 벽 (기둥이 창호 위로 감)
  { const G = fresh(); C.newProjectDemo(G); const n = nodeOf(G, "X1", "Y3"), e = G.edges.find(x => x.wall && x.along === "Y3" && (x.from === n.id || x.to === n.id));
    const wt = G.otypes.filter(t => t.kind === "window" && t.width <= 1200).sort((a, b) => b.width - a.width)[0] || G.otypes.find(t => t.kind === "window");
    const wid = C.addOpening(G, e.id, "window", 4300, wt.id);
    C.offsetColumn(G, n.id, 1200, 0);      // 위쪽 외벽을 따라 오른쪽으로 → 창호 자리에 걸침
    const w = save(C, ORIG, G, "S13", "S13", `X1-Y3 기둥을 벽 따라 1200 → 창호 ${wid} 자리로 (경고 확인, 도면은 경고된 채 그림)`);
    if (!w.some(x => x.includes(wid) && x.includes("겹침"))) note("S13", "누락", "어긋난 기둥이 창호와 겹치는데 경고 없음"); }

  // S14: 이미 축이 있는 자리로 어긋남 → 기존 축 사용, 그 교점에 기둥이 이미 있으면?
  { const G = fresh(); C.newProjectDemo(G); const n = nodeOf(G, "X2", "Y2");
    C.offsetColumn(G, n.id, 1500, 0); C.offsetColumn(G, n.id, 1500, 0);      // 두 번 → 3000? (한계 1500)
    if (n.off[0] !== 1500) note("S14", "이상", `어긋남 한계 1500이 지켜지지 않음: ${n.off}`);
    const g5 = C.addGridFree(G, "x", 10500); const r = C.offsetToGrid(G, n.id);
    if (!r || r.grids[0] !== g5) note("S14", "이상", `이미 있는 축 ${g5}을 써야 하는데 ${JSON.stringify(r)}`);
    const m = nodeOf(G, "X3", "Y2"); C.offsetColumn(G, m.id, -1500, 0);      // 13500 — 다른 기둥 없음
    const r2 = C.offsetToGrid(G, m.id);
    const dup = G.nodes.filter(x => x.type === "column" && x.cxy[0] === 13500 && x.cxy[1] === 9500).length;
    save(C, ORIG, G, "S14", "S14", `기존 축 재사용(${r && r.grids}), 두 번째 보조 축 ${r2 && r2.grids}`);
    if (dup > 1) note("S14", "이상", "같은 자리에 기둥 둘"); }

  // S15: 보조 축을 다시 없애기 — 이웃(원래 축)으로 합치기 → 원래 상태로 돌아가는가
  { const G = fresh(); C.newProjectDemo(G); const n = nodeOf(G, "X2", "Y3"); const before = { cols: G.nodes.filter(x => x.type === "column").length, walls: G.edges.filter(e => e.wall).length, dims: G.dims.length };
    C.offsetColumn(G, n.id, 300, 0); C.offsetToGrid(G, n.id);
    const ok = C.deleteGrid(G, "X2A", "X2");
    const after = { cols: G.nodes.filter(x => x.type === "column").length, walls: G.edges.filter(e => e.wall).length, dims: G.dims.length };
    if (!ok || JSON.stringify(before) !== JSON.stringify(after)) note("S15", "이상", `보조 축을 원래 축으로 합쳤는데 원래 개수로 돌아오지 않음: ${JSON.stringify(before)} → ${JSON.stringify(after)}`);
    if (!nodeOf(G, "X2", "Y3") || nodeOf(G, "X2", "Y3").type !== "column") note("S15", "이상", "합친 뒤 X2-Y3에 기둥이 없음");
    save(C, ORIG, G, "S15", "S15", "보조 축 X2A를 만들었다가 X2로 합침 (원래대로여야 함)"); }

  // S16: 변경 지시 여러 건을 한 번에 → 내보내기 → 도면
  { const G = fresh(); C.newProjectDemo(G);
    const items = [
      { no: 1, target: "X2-Y3", change: "X +300 mm", status: "confirmed", action: "move", axis: "X", delta: 300 },      // 줄째: X2 → 9300 (문 D1 위치도 따라감)
      { no: 2, target: "Y1", change: "Y -200 mm", status: "confirmed", action: "move", axis: "Y", delta: -200 },
      { no: 3, target: "C1", change: "Y +300 mm", status: "confirmed", action: "move", axis: "Y", delta: 300 },       // 12개 → 보류
      { no: 4, target: "X9", change: "X +100 mm", status: "confirmed", action: "move", axis: "X", delta: 100 }];       // 없는 축
    const r = C.loadInstructions(G, items);
    if (r.some(x => x.applied)) note("S16", "이상", "PDF 불러오기가 지시를 자동 적용함");
    const c1 = C.applyInstruction(G, items[0], { node: nodeOf(G, "X2", "Y3") });
    const c2 = C.applyInstruction(G, items[1], { grid: "Y1" });
    if (!c1.ok || !c2.ok) note("S16", "이상", "사람이 확인한 그리드 이동 실패");
    const c4 = C.applyInstruction(G, items[2], { node: nodeOf(G, "X4", "Y2") }, true);      // 사람이 X4-Y2 기둥만으로 정함
    if (!c4.ok) note("S16", "이상", "기둥만 적용 실패: " + c4.note);
    save(C, ORIG, G, "S16", "S16", "지시 4건: 줄째 2건 적용, 보류 2건 중 1건은 사람이 기둥만으로 적용"); }
}

// ===== 기존 도면 =====
{
  const C = load("relation_editor_A12M.html"), ORIG = C.initModel(C.ORIG_GRAPH), fresh = () => C.initModel(C.ORIG_GRAPH);
  // R7: 실제 도면의 기둥을 어긋나게 한 뒤 보조 축으로 (옛 기둥 삭제 + 새 기둥·축 추가)
  { const G = fresh(); const n = G.nodes.find(x => x.type === "column" && x.grid[0] === "X6" && x.grid[1] === "Y4");
    C.offsetColumn(G, n.id, 0, 400); const r = C.offsetToGrid(G, n.id);
    const w = save(C, ORIG, G, "R7", "A12M", `실제 도면 X6-Y4 기둥을 위로 400 → 보조 축 ${r && r.grids}`);
    const acts = new Set(C.exportChanges(ORIG, G, "시험").map(c => c.action));
    if (!acts.has("add_grid") || !acts.has("add_column") || !acts.has("delete_column")) note("R7", "이상", "보조 축·새 기둥·옛 기둥 삭제가 모두 나가야 함: " + [...acts].join()); }
  // R8: 실제 도면에서 어긋난 채로 읽힌 기둥(X8-Y2, -200)을 축 위로 되돌리기(어긋남 0)
  { const G = fresh(); const n = G.nodes.find(x => x.type === "column" && x.grid[0] === "X8" && x.grid[1] === "Y2");
    if (!n || !n.off[0]) note("R8", "정보", `X8-Y2가 어긋난 채로 읽히지 않음: ${n && n.off}`);
    else { C.offsetColumn(G, n.id, 0, 0, true); save(C, ORIG, G, "R8", "A12M", `실제 도면의 어긋난 기둥 X8-Y2(${n.offset})를 축 위로`); } }
}
fs.writeFileSync(path.join(outDir, "findings2_js.json"), JSON.stringify(findings, null, 1));
console.log(`\n편집기 쪽 발견 ${findings.length}건. 이어서: python tools/stress_run.py S12 S13 S14 S15 S16 R7 R8`);
