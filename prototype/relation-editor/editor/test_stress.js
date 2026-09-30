// 한계 찾기: 극단적인 계획안 여러 개를 만들어 내보내고, 도면으로 그려 다시 읽는다(파이썬 tools/stress_run.py 가 이어서 돌림)
// node editor/test_stress.js
const fs = require("fs"), path = require("path"), vm = require("vm");
const html = fs.readFileSync(path.join(__dirname, "..", "out", "editor", "relation_editor_NEW1.html"), "utf8");
const grab = id => html.match(new RegExp(`<script id="${id}"[^>]*>([\\s\\S]*?)</script>`))[1];
const ctx = { module: { exports: {} }, console }; vm.createContext(ctx);
vm.runInContext(grab("data") + "\n" + grab("core") + "\nmodule.exports.ORIG_GRAPH = ORIG_GRAPH;", ctx);
const C = ctx.module.exports, ORIG = C.initModel(C.ORIG_GRAPH);
const outDir = path.join(__dirname, "..", "out", "editor", "stress"); fs.mkdirSync(outDir, { recursive: true });
const fresh = () => C.initModel(C.ORIG_GRAPH);
const gid = (G, ax, v) => { const g = Object.values(G.grids).find(x => x.axis === ax && Math.abs(x.coord - v) < 1); return g && g.id; };
const node = (G, x, y) => G.nodes.find(n => n.grid[0] === x && n.grid[1] === y);
const seg = (G, a, b, along) => ({ a: { xi: a[0], yj: a[1] }, b: { xi: b[0], yj: b[1] }, along });
const findings = [];
const note = (sheet, kind, text) => { findings.push({ sheet, kind, text }); console.log(`  [${kind}] ${sheet}: ${text}`); };

function expected(G, name) {
  const dd = C.diff(ORIG, G);
  return {
    columns: G.nodes.filter(n => n.type === "column").map(n => ({ label: n.grid.join("-"), xy: n.xy, spec: n.spec })), columns_deleted: [],
    walls_checked: dd.walls_added.map(e => ({ label: e.id, from_xy: e.from_xy, to_xy: e.to_xy, thick: e.thick, expect: true })),
    openings_checked: dd.openings_added.map(o => ({ id: o.id, type: o.type, xy: o.center, width: o.width, expect: true })), dims_checked: [],
    site: G.site, floor_height: G.project.floor_height,
    cores: G.cores.map(c => ({ id: c.id, type: c.type, anchor: c.anchor, anchor_xy: [G.grids[c.anchor[0]].coord, G.grids[c.anchor[1]].coord], dir: c.dir, side: c.side, entry: c.rect.entry, travel: c.kind === "stair" ? (c.travel || "UP") : null, walls: c.rect.flags, wall_thick: c.rect.T, rect: [c.rect.x0, c.rect.y0, c.rect.x1, c.rect.y1] })),
    auto_dims: [...G.dims.map(d => ({ orient: d.orient, value: d.measurement })), ...G.dims2.map(d => ({ orient: d.orient, value: d.value }))],
    mep: { devices: (G.mep ? G.mep.devices : []).map(x => ({ id: x.id, type: x.type, xy: x.xy })), checked: [], routes: [] },
  };
}
function save(G, name, label) {
  const w = C.warnings(ORIG, G);
  const out = C.exportChanges(ORIG, G, "시험").map(c => Object.assign({}, c, { sheet: name }));
  fs.writeFileSync(path.join(outDir, `changes_${name}.json`), JSON.stringify(out, null, 1));
  fs.writeFileSync(path.join(outDir, `expected_${name}.json`), JSON.stringify(expected(G, name), null, 1));
  console.log(`\n== ${name}: ${label}\n   변경 ${out.length}건, 경고 ${w.length}건`); w.forEach(x => console.log("   - " + x));
  return w;
}

// ---------- S1: 불규칙 그리드, 좁은 스팬, 아주 두꺼운 벽, 코어 네 방향, 사선 두 곳 ----------
{
  const G = fresh();
  C.setSite(G, [[0, 0], [30000, 0], [30000, 22000], [18000, 22000], [18000, 17000], [0, 17000]]);      // ㄱ자 대지
  const xs = C.addGridSeries(G, "x", 2000, [2400, 7200, 3000, 6000, 4800]), ys = C.addGridSeries(G, "y", 2000, [1800, 6000, 4200]);
  xs.forEach(x => ys.forEach(y => C.addColumn(G, x, y, "C1")));
  C.candidateSegments(G).forEach(sg => { const edge = sg.along === xs[0] || sg.along === xs[xs.length - 1] || sg.along === ys[0] || sg.along === ys[ys.length - 1]; C.addEdge(G, sg, "beam"); if (edge) C.addEdge(G, sg, "wall"); });
  C.setWallThick(G, 600);                                                        // 기둥(500)보다 두꺼운 벽
  const wt = G.otypes.filter(t => t.kind === "window").sort((a, b) => b.width - a.width)[0], dt = G.otypes.find(t => t.kind === "door");
  const N = () => Object.fromEntries(G.nodes.map(n => [n.id, n]));
  G.edges.filter(e => e.wall && e.along === ys[ys.length - 1]).forEach(e => { const a = N()[e.from].xy, b = N()[e.to].xy; C.addOpening(G, e.id, "window", (a[0] + b[0]) / 2, wt.id); });   // 1800 스팬에 2400 창
  const e0 = G.edges.find(e => e.wall && e.along === ys[0]); { const a = N()[e0.from].xy; C.addOpening(G, e0.id, "door", a[0] + 300, dt.id); }   // 벽 끝에 걸친 문
  ["N", "E", "S", "W"].forEach((d, i) => C.addCore(G, ["EV1", "EV3", "EV2", "EV1"][i], xs[1 + i], ys[1], d, i % 2 ? -1 : 1));      // 승강기 네 방향
  const st = C.addCore(G, "ST2", xs[3], ys[2], "W", 1); G.cores.find(c => c.id === st).entry = "N"; G.cores.find(c => c.id === st).travel = "UPDN";   // 옆 입구 계단
  C.addDiagonal(G, { xi: xs[xs.length - 2], yj: ys[0] }, { xi: xs[xs.length - 1], yj: ys[1] }, "wall");
  C.addDiagonal(G, { xi: xs[0], yj: ys[ys.length - 2] }, { xi: xs[1], yj: ys[ys.length - 1] }, "wall");
  C.recompute(G);
  const w = save(G, "S1", "불규칙 그리드·600 벽·좁은 스팬에 넓은 창·벽 끝의 문·승강기 네 방향·옆 입구 계단·사선 둘·ㄱ자 대지");
  if (!w.some(x => x.includes("기둥 밖으로 나옴"))) note("S1", "누락", "600 벽이 500 기둥보다 두꺼운데 경고 없음");
  if (!w.some(x => x.includes("개구부 합계"))) note("S1", "누락", "1800 스팬에 2400 창을 넣었는데 경고 없음");
  const oc = G.cores.filter(c => c.kind === "elevator" && !c.rect.gap); if (oc.length) note("S1", "이상", `승강기 입구 없음: ${oc.map(c => c.id + " " + c.dir).join(", ")}`);
}

// ---------- S2: 아주 작은 건물(2x2 그리드, 3000 스팬)에 코어 둘 + 문·창호 몰아넣기 ----------
{
  const G = fresh();
  C.setSite(G, [[0, 0], [9000, 0], [9000, 9000], [0, 9000]]);
  const xs = C.addGridSeries(G, "x", 1500, [3000, 3000]), ys = C.addGridSeries(G, "y", 1500, [3000, 3000]);
  xs.forEach(x => ys.forEach(y => C.addColumn(G, x, y, "C1")));
  C.candidateSegments(G).forEach(sg => { C.addEdge(G, sg, "beam"); C.addEdge(G, sg, "wall"); });      // 모든 구간이 벽
  const N = () => Object.fromEntries(G.nodes.map(n => [n.id, n]));
  const dt = G.otypes.find(t => t.kind === "door"), wt = G.otypes.find(t => t.kind === "window" && t.width <= 1200) || G.otypes.find(t => t.kind === "window");
  G.edges.filter(e => e.wall).forEach((e, i) => { const a = N()[e.from].xy, b = N()[e.to].xy, m = e.along[0] === "Y" ? (a[0] + b[0]) / 2 : (a[1] + b[1]) / 2; C.addOpening(G, e.id, i % 2 ? "door" : "window", m, i % 2 ? dt.id : wt.id); });
  C.addCore(G, "EV1", xs[0], ys[0], "N", 1); C.addCore(G, "ST1", xs[1], ys[0], "N", 1);
  C.recompute(G);
  const w = save(G, "S2", "3000 스팬 2x2, 모든 구간이 벽이고 문·창호가 다 있음, 코어 둘");
  if (!w.some(x => x.includes("겹침") || x.includes("닿음"))) note("S2", "누락", "코어가 문·창호와 부딪힐 텐데 경고 없음");
  if (!w.some(x => x.includes("건물 벽과 겹침"))) note("S2", "누락", "코어 벽이 안쪽 벽 위에 겹치는데 경고 없음");
}

// ---------- S3: 그리드 이동·삭제·추가를 사선 벽과 코어가 있는 상태에서 ----------
{
  const G = fresh(); C.newProjectShowcase(G);
  const before = G.edges.find(e => e.diag).length, x4 = gid(G, "x", 21000), y2 = gid(G, "y", 9500);
  C.moveGridTo(G, x4, 22000);
  const d = G.edges.find(e => e.diag);
  if (Math.abs(d.length - Math.hypot(7000, 6000)) > 1) note("S3", "이상", `X4를 옮겼는데 사선 길이가 ${before} → ${d.length} (기대 ${Math.round(Math.hypot(7000, 6000))})`);
  const da = G.dims2.find(x => x.id === `DA-${d.id}`); if (!da || da.value !== d.length) note("S3", "이상", "사선 치수가 그리드 이동을 따라오지 않음");
  C.moveGridTo(G, y2, 10500);
  const ev = G.cores.find(c => c.id === "EV-1"); if (ev.rect.y0 !== 10500 + 250) note("S3", "이상", `Y2를 옮겼는데 승강기가 따라오지 않음 (y0 ${ev.rect.y0})`);
  const ok1 = C.deleteGrid ? C.deleteGrid(G, gid(G, "x", 16500)) : null;
  if (ok1 === null) note("S3", "정보", "deleteGrid 함수가 노출되어 있지 않아 그리드 삭제는 시험하지 못함");
  C.recompute(G);
  save(G, "S3", "시연 끝 상태에서 X4 +1000, Y2 +1000 이동" + (ok1 ? ", 보조 그리드 삭제" : ""));
}

// ---------- S4: 벽 없이 보만, 기둥 없이 벽만 ----------
{
  const G = fresh();
  C.setSite(G, [[0, 0], [20000, 0], [20000, 14000], [0, 14000]]);
  const xs = C.addGridSeries(G, "x", 2000, [8000, 8000]), ys = C.addGridSeries(G, "y", 2000, [5000, 5000]);
  C.candidateSegments(G).forEach(sg => { const edge = sg.along === xs[0] || sg.along === xs[2] || sg.along === ys[0] || sg.along === ys[2]; if (edge) C.addEdge(G, sg, "wall"); else C.addEdge(G, sg, "beam"); });
  C.recompute(G);
  const w = save(G, "S4", "기둥이 하나도 없는 벽식 구조, 안쪽은 보만(양 끝이 교점)");
  const m = G.members; if (m.some(x => x.kind === "girder")) note("S4", "이상", "기둥이 없는데 거더로 분류된 보가 있음");
  if (!w.some(x => x.includes("스팬") && x.includes("8000"))) note("S4", "누락", "8000 스팬 보에 스팬 경고 없음");
}

// ---------- S5: 대지가 건물을 못 담는 경우, 대지 없이 그리기 ----------
{
  const G = fresh();
  C.setSite(G, [[3000, 3000], [12000, 3000], [12000, 12000], [3000, 12000]]);
  const xs = C.addGridSeries(G, "x", 1000, [6000, 6000, 6000]), ys = C.addGridSeries(G, "y", 1000, [6000, 6000]);
  xs.forEach(x => ys.forEach(y => C.addColumn(G, x, y, "C2")));
  C.candidateSegments(G).forEach(sg => { const edge = sg.along === xs[0] || sg.along === xs[3] || sg.along === ys[0] || sg.along === ys[2]; if (edge) C.addEdge(G, sg, "wall"); C.addEdge(G, sg, "beam"); });
  C.recompute(G);
  const w = save(G, "S5", "건물이 대지보다 큼 (대지 9x9 m 안에 18x12 m 건물)");
  if (!w.some(x => x.includes("대지경계선 밖"))) note("S5", "누락", "건물이 대지 밖인데 경고 없음");
  const pi = C.projectInfo(G); if (pi.coverage !== null && pi.coverage <= 100) note("S5", "이상", `건폐율 ${pi.coverage}% (100% 넘어야 함)`);
  const G2 = fresh();
  const xs2 = C.addGridSeries(G2, "x", 0, [6000, 6000]), ys2 = C.addGridSeries(G2, "y", 0, [6000]);
  xs2.forEach(x => ys2.forEach(y => C.addColumn(G2, x, y, "C1")));
  C.candidateSegments(G2).forEach(sg => { C.addEdge(G2, sg, "wall"); C.addEdge(G2, sg, "beam"); });
  C.recompute(G2);
  save(G2, "S6", "대지 없이 그리기 (1x2 스팬, 좌표 0에서 시작)");
  if (!G2.dims.length) note("S6", "이상", "대지 없이도 그리드 치수는 나와야 함");
}

// ---------- S7: 같은 자리에 두 코어, 코어를 대지 밖으로, 층고 극단 ----------
{
  const G = fresh(); C.newProjectDemo(G);
  const st = G.cores.find(c => c.kind === "stair");
  G.project.floor_height = 2400; C.recompute(G); const k1 = st.rect.calc;
  G.project.floor_height = 6000; C.recompute(G); const k2 = st.rect.calc;
  if (k1.riser > 180 || k2.riser > 180) note("S7", "이상", `단높이 상한 초과: ${k1.riser}, ${k2.riser}`);
  if (k2.length > 12000) note("S7", "정보", `층고 6000이면 꺾임 계단 길이 ${k2.length} (2단 꺾임이 아니라 한 방향으로 길어짐)`);
  G.project.floor_height = 3400; C.recompute(G);
  const x1 = gid(G, "x", 3000), y3 = gid(G, "y", 15500);
  C.setSite(G, [[0, 0], [26000, 0], [26000, 17000], [0, 17000]]);      // 대지를 좁혀서
  C.addCore(G, "EV3", x1, y3, "N", 1);       // 대지 위쪽 경계 밖으로 나가는 승강기
  C.recompute(G);
  const w = C.warnings(ORIG, G);
  if (!w.some(x => x.includes("대지경계선 밖으로"))) note("S7", "누락", "대지 밖으로 나간 코어에 경고 없음");
  save(G, "S7", "층고 2400/6000 계단 계산, 대지 밖 승강기");
}

fs.writeFileSync(path.join(outDir, "findings_js.json"), JSON.stringify(findings, null, 1));
console.log(`\n편집기 쪽 발견 ${findings.length}건. 이어서: python tools/stress_run.py`);
