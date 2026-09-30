// 한계 찾기(기존 도면): 1층 평면도 관계도에 극단적인 편집을 넣어 내보내고, 도면에 반영해 다시 읽는다
// node editor/test_stress_real.js  →  python tools/stress_run.py R1 R2 ...
const fs = require("fs"), path = require("path"), vm = require("vm");
const html = fs.readFileSync(path.join(__dirname, "..", "out", "editor", "relation_editor_A12M.html"), "utf8");
const grab = id => html.match(new RegExp(`<script id="${id}"[^>]*>([\\s\\S]*?)</script>`))[1];
const ctx = { module: { exports: {} }, console }; vm.createContext(ctx);
vm.runInContext(grab("data") + "\n" + grab("core") + "\nmodule.exports.ORIG_GRAPH = ORIG_GRAPH;", ctx);
const C = ctx.module.exports, ORIG = C.initModel(C.ORIG_GRAPH);
const outDir = path.join(__dirname, "..", "out", "editor", "stress"); fs.mkdirSync(outDir, { recursive: true });
const fresh = () => C.initModel(C.ORIG_GRAPH), lab = n => n.grid.join("-");
const findings = [];
const note = (sheet, kind, text) => { findings.push({ sheet, kind, text }); console.log(`  [${kind}] ${sheet}: ${text}`); };

function expected(G) {
  const dd = C.diff(ORIG, G);
  return {
    columns: G.nodes.filter(n => n.type === "column").map(n => ({ label: lab(n), xy: n.xy, spec: n.spec })),
    columns_deleted: dd.cols_deleted.map(c => ({ label: c.grid.join("-"), xy: c.xy })),
    walls_checked: [...dd.walls_added.map(e => ({ label: e.id, from_xy: e.from_xy, to_xy: e.to_xy, expect: true })), ...dd.walls_deleted.map(e => ({ label: e.id, from_xy: e.from_xy, to_xy: e.to_xy, expect: false }))],
    openings_checked: [...dd.openings_added.map(o => ({ id: o.id, type: o.type, xy: o.center, width: o.width, expect: true })),
      ...dd.openings.filter(o => o.edited).map(o => ({ id: o.id, type: o.type, xy: o.to_xy, width: o.to_w, expect: true })),
      ...dd.openings_deleted.map(o => { const p = ORIG.openings.find(x => x.id === o.id); return { id: o.id, type: o.type, xy: p.xy, width: p.width, expect: false }; })],
    dims_checked: dd.dims.map(x => ({ handle: x.handle, to: x.to })),
    mep: { devices: G.mep.devices.filter(d => !d.orphan).map(x => ({ id: x.id, type: x.type, xy: x.xy })), checked: [], routes: [] },
  };
}
function save(G, name, label) {
  const w = C.warnings(ORIG, G), out = C.exportChanges(ORIG, G, "시험").map(c => Object.assign({}, c, { sheet: "A12M" }));
  // 반영 도구는 changes 의 sheet 로 원본을 고르므로 A12M 을 유지하고, 파일 이름만 시험 이름으로 둔다
  fs.writeFileSync(path.join(outDir, `changes_${name}.json`), JSON.stringify(out, null, 1));
  fs.writeFileSync(path.join(outDir, `expected_${name}.json`), JSON.stringify(expected(G), null, 1));
  console.log(`\n== ${name}: ${label}\n   변경 ${out.length}건, 경고 ${w.length}건`); w.slice(0, 12).forEach(x => console.log("   - " + x)); if (w.length > 12) console.log(`   ... 외 ${w.length - 12}건`);
  return w;
}
const gridsX = G => Object.values(G.grids).filter(x => x.axis === "x").sort((a, b) => a.coord - b.coord);

// R1: 그리드를 크게 옮긴다 (X6 을 -1500, Y2 를 +800). 이웃 그리드와의 최소 간격 300 규칙이 막는지
{
  const G = fresh(); const x6 = G.grids.X6.coord, x5 = G.grids.X5.coord;
  C.moveGridTo(G, "X6", x6 - 1500);
  if (G.grids.X6.coord !== x6 - 1500) note("R1", "정보", `X6 -1500 이동이 ${G.grids.X6.coord - x6}로 제한됨 (X5와의 간격 ${x6 - 1500 - x5})`);
  C.moveGridTo(G, "X6", x5 + 100);       // X5 바로 옆까지
  if (G.grids.X6.coord - x5 < 300) note("R1", "이상", `X6가 X5에 ${G.grids.X6.coord - x5}까지 붙음 (최소 간격 300 위반)`);
  C.moveGridTo(G, "X6", x6 - 1500);
  const y2 = G.grids.Y2.coord; C.moveGridTo(G, "Y2", y2 + 800);
  save(G, "R1", "X6 -1500, Y2 +800");
}
// R2: 그리드 삭제와 추가, 기둥 없애기
{
  const G = fresh();
  const ok = C.deleteGrid(G, "X4");     // X1·X2·X4 는 600 간격의 촘촘한 그리드
  if (!ok) note("R2", "정보", "X4 그리드 삭제가 거부됨 (기둥이나 벽이 있으면 막는 규칙?)");
  const gx = gridsX(G); const nx = C.addGridFree(G, "x", (gx[3].coord + gx[4].coord) / 2);
  if (!nx) note("R2", "이상", "그리드 사이에 새 그리드를 놓지 못함");
  const cols = G.nodes.filter(n => n.type === "column" && n.grid[0] === "X8");
  cols.forEach(n => C.deleteColumn(G, n.id));
  if (nx) { const ys = Object.values(G.grids).filter(x => x.axis === "y").sort((a, b) => a.coord - b.coord); C.addColumn(G, nx, ys[Math.floor(ys.length / 2)].id, "C1"); }
  const w = save(G, "R2", `X4 삭제${ok ? "" : "(거부)"}, X 그리드 하나 추가, X8의 기둥 ${cols.length}개 삭제, 새 그리드에 기둥`);
  if (cols.length && !w.some(x => x.includes("구조 검토"))) note("R2", "누락", "기둥을 지웠는데 구조 검토 경고 없음");
}
// R3: 문·창호 극단: 벽보다 넓은 타입으로 교체, 벽 끝으로 이동, 같은 자리에 두 개
{
  const G = fresh(); const N = () => Object.fromEntries(G.nodes.map(n => [n.id, n]));
  const win = G.openings.find(o => o.type === "window" && !o.band), wide = G.otypes.filter(t => t.kind === "window" && !t.band).sort((a, b) => b.width - a.width)[0];
  if (win && wide) { win.otype = wide.id; C.recompute(G); }
  const door = G.openings.find(o => o.type === "door" && !o.band && o.id !== (win || {}).id);
  if (door) { const e = G.edges.find(x => x.id === door.on_edge), a = N()[e.from].xy, b = N()[e.to].xy, hz = G.grids[e.along].axis === "y"; const end = Math.max(hz ? a[0] : a[1], hz ? b[0] : b[1]); door.shift = end - door.a0; C.recompute(G); }
  const win2 = G.openings.find(o => o.type === "window" && !o.band && o !== win);
  if (win2) C.addOpening(G, win2.on_edge, "door", win2.a, G.otypes.find(t => t.kind === "door" && !t.band).id);      // 창 자리에 문을 겹쳐 놓음
  const w = save(G, "R3", `${win && win.id}을 ${wide && wide.width} 창으로 교체, ${door && door.id}을 벽 끝으로, ${win2 && win2.id} 자리에 문 겹치기`);
  if (!w.some(x => x.includes("개구부 합계") || x.includes("벗어남"))) note("R3", "누락", "벽보다 넓거나 끝을 벗어난 개구부에 경고 없음");
  if (!w.some(x => x.includes("겹침"))) note("R3", "누락", "개구부끼리 겹치는데 경고 없음");
}
// R4: 창이 있는 벽 삭제, 기둥 사이 보 삭제, 기둥 타입을 아주 크게
{
  const G = fresh();
  const ew = G.edges.find(e => e.wall && G.openings.some(o => o.on_edge === e.id && !o.band)); const nOpen = G.openings.filter(o => o.on_edge === (ew || {}).id).length;
  if (ew) C.deleteEdgeKind(G, ew.id, "wall");
  const eb = G.edges.find(e => e.beam && e.beam_evidence === "columns" && !e.wall); if (eb) C.deleteEdgeKind(G, eb.id, "beam");
  const t = G.types[0]; t.spec = "1200x1200"; C.recompute(G);
  const w = save(G, "R4", `창 ${nOpen}개 있는 벽 삭제, 기둥 사이 보 삭제, ${t.id} 단면 1200x1200`);
  if (G.openings.some(o => o.on_edge === (ew || {}).id)) note("R4", "이상", "벽을 지웠는데 그 위 창이 남음");
}
// R5: 설비: 기구를 문 위로, 기구 한꺼번에 많이, 덕트 아래 기구
{
  const G = fresh();
  const door = G.openings.find(o => o.type === "door" && !o.band), e = G.edges.find(x => x.id === door.on_edge), hz = G.grids[e.along].axis === "y";
  if (C.addDevice(G, "EO1", { edge: e.id, a: undefined, side: 1 }) !== null) note("R5", "이상", "좌표 없는 기구 추가가 거부되지 않음");
  const id = C.addDevice(G, "EO1", { edge: e.id, a: hz ? door.xy[0] : door.xy[1], side: 1 });
  for (let i = 0; i < 40; i++) C.addDevice(G, "FS1", { x: 16000 + (i % 8) * 1200, y: 12000 + Math.floor(i / 8) * 1200 });
  const w = save(G, "R5", "문 위에 콘센트, 헤드 40개 촘촘히");
  if (!w.some(x => x.includes(id) && x.includes("겹침"))) note("R5", "누락", "문 위의 콘센트에 겹침 경고 없음");
}
fs.writeFileSync(path.join(outDir, "findings_real_js.json"), JSON.stringify(findings, null, 1));
console.log(`\n편집기 쪽 발견 ${findings.length}건. 이어서: python tools/stress_run.py R1 R2 R3 R4 R5`);
