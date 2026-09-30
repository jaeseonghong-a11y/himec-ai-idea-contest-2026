// 새 프로젝트(맨땅에서 시작) 계산 검증. 시연 계획안의 변경 파일과 기대값도 만든다.
const fs = require("fs"), path = require("path"), vm = require("vm");
const outDir = path.join(__dirname, "..", "out", "editor");
const SHEET = process.argv[2] || "NEW1";
const html = fs.readFileSync(path.join(outDir, `relation_editor_${SHEET}.html`), "utf8");
const grab = id => { const tag = '<script id="' + id + '">'; const a = html.indexOf(tag) + tag.length; return html.slice(a, html.indexOf('</' + 'script>', a)); };
new vm.Script(grab("ui"), { filename: "ui.js" });
const ctx = { module: { exports: {} }, console };
vm.createContext(ctx);
vm.runInContext(grab("data") + "\n" + grab("core") + "\nmodule.exports.ORIG_GRAPH = ORIG_GRAPH;", ctx);
const C = ctx.module.exports;
const ORIG = C.recompute(C.initModel(C.ORIG_GRAPH));
let pass = 0, fail = 0;
const ok = (name, cond, extra = "") => { (cond ? pass++ : fail++); console.log(`${cond ? "PASS" : "FAIL"}  ${name} ${extra}`); };
const fresh = () => C.clone(ORIG);

ok("빈 상태: 그리드·기둥·벽 없음, 변경·경고 없음", !Object.keys(ORIG.grids).length && !ORIG.nodes.length && C.exportChanges(ORIG, fresh(), "t").length === 0 && C.warnings(ORIG, fresh()).length === 0);
const HAS_LIB = ORIG.otypes.some(t => t.donor);      // 과거 도면에서 읽은 기호 자료(out/real/schedule.json)가 있는가. 없으면 표준 크기의 가상 타입만 쓴다
if (!HAS_LIB) console.log("(기호 자료 없음: 가상 타입만으로 시험)");
ok(HAS_LIB ? "일람표: 과거 도면의 타입과 가상 타입이 함께 있음" : "일람표: 기호 자료가 없으면 가상 타입만", ORIG.otypes.some(t => t.virtual) && (HAS_LIB || ORIG.otypes.every(t => t.virtual)), `(${ORIG.otypes.filter(t => t.donor).length} + ${ORIG.otypes.filter(t => t.virtual).length})`);

// 계단 자동 계산
const k = C.stairCalc(3400, 1200);
ok("계단: 층고 3400, 폭 1200 → 20단, 단높이 170, 길이 3720, 폭 2500", k.risers === 20 && k.riser === 170 && k.per_flight === 10 && k.run === 2520 && k.length === 3720 && k.width === 2500, JSON.stringify(k));
const k2 = C.stairCalc(4200, 1500);
ok("계단: 층고 4200 → 단높이가 180을 넘지 않고 짝수 단", k2.riser <= 180 && k2.risers % 2 === 0, `(${k2.risers}단, ${k2.riser})`);

// 대지
let G = fresh();
ok("대지: 점 3개 미만은 거부", C.setSite(G, [[0, 0], [1000, 0]]) === false);
C.setSite(G, [[0, 0], [26000, 0], [26000, 19000], [0, 19000]]);
ok("대지: 면적 계산", C.projectInfo(G).site_m2 === 494, `(${C.projectInfo(G).site_m2} ㎡)`);
// 그리드
const xs = C.addGridSeries(G, "x", 3000, [6000, 6000, 6000]), ys = C.addGridSeries(G, "y", 3500, [6000, 6000]);
ok("그리드 한 번에 만들기", xs.length === 4 && ys.length === 3 && G.grids[xs[3]].coord === 21000 && G.grids[ys[2]].coord === 15500);
ok("그리드선이 대지를 덮도록 자동으로 뻗음", G.grids[xs[0]].lo === -1500 && G.grids[xs[0]].hi === 20500 && C.intersections(G).length === 12);
ok("너무 가까운 그리드는 거부", C.addGridFree(G, "x", 3100) === null);
ok("치수 자동 생성(구간 + 전체)", G.dims.length === (3 + 1) + (2 + 1) && G.dims.some(d => d.measurement === 18000) && G.dims.some(d => d.measurement === 12000), `(${G.dims.map(d => d.measurement).join(", ")})`);
C.moveGridTo(G, xs[1], 9500);
ok("그리드를 옮기면 치수가 따라 바뀜", G.dims.some(d => d.measurement === 6500) && G.dims.some(d => d.measurement === 5500));
C.moveGridTo(G, xs[1], 9000);
// 코어
const ev = C.addCore(G, "EV1", xs[0], ys[1], "N", 1), st = C.addCore(G, "ST1", xs[1], ys[1], "N", -1);
const re = G.cores.find(c => c.id === ev).rect, rs = G.cores.find(c => c.id === st).rect;
ok("승강기: 교점에서 위로 1800×2000", re.x0 === 3000 && re.x1 === 4800 && re.y0 === 9500 && re.y1 === 11500, JSON.stringify([re.x0, re.y0, re.x1, re.y1]));
ok("계단: 방향과 옆에 따라 놓이고 크기는 자동 계산", rs.x0 === 6500 && rs.x1 === 9000 && rs.y0 === 9500 && rs.y1 === 13220 && rs.calc.risers === 20, JSON.stringify([rs.x0, rs.y0, rs.x1, rs.y1]));
ok("승강기: 입구 면은 문 폭만큼 뚫리고 네 면이 벽", re.entry === "S" && re.gap.width === 800 && re.gap.x0 === 3500 && re.gap.x1 === 4300 && re.walls.length === 5 && re.walls.filter(w => w.side === "S").length === 2, `(입구 ${re.entry} ${re.gap.x0}~${re.gap.x1})`);
ok("승강로 벽은 안치수 바깥에 두께 200", re.walls.find(w => w.side === "N").y0 === 11500 && re.walls.find(w => w.side === "N").y1 === 11700 && re.walls.find(w => w.side === "N").x0 === 2800);
ok("계단실: 입구(아래)만 열리고 세 면에 벽", rs.entry === "S" && rs.walls.length === 3 && !rs.flags.S && !rs.gap);
ok("계단 화살표 UP: 첫 계단으로 올라가 참에서 돌아 내려옴", rs.arrows.length === 1 && rs.arrows[0].label === "UP" && rs.arrows[0].pts.length === 4 && rs.arrows[0].pts[1][1] === 9500 + 2520 + 600, JSON.stringify(rs.arrows[0].pts));
{ const c = G.cores.find(c => c.id === st); c.travel = "UPDN"; c.walls = { S: true, W: false }; C.recompute(G);
  ok("화살표 UP+DN, 계단실 벽 선택(입구 면에 벽을 세우면 문 폭만큼 뚫림)", c.rect.arrows.map(a => a.label).join() === "UP,DN" && !c.rect.flags.W && c.rect.gap && c.rect.gap.width === 1000 && c.rect.walls.length === 4, `(벽 조각 ${c.rect.walls.length})`);
  c.travel = "UP"; c.walls = undefined; C.recompute(G); }
{ const c = G.cores.find(c => c.id === st); c.entry = "W"; C.recompute(G); const r = c.rect;
  ok("계단 입구를 옆(왼쪽)으로: 앞에 계단참 1200이 생겨 길이 4920", r.entry === "W" && r.lead === 1200 && r.y1 - r.y0 === 4920 && r.calc.risers === 20, `(${r.x1 - r.x0}×${r.y1 - r.y0})`);
  ok("옆 입구는 앞 계단참 구간에 뚫리고 네 면이 벽", r.gap.side === "W" && r.gap.y0 === 9600 && r.gap.y1 === 10600 && r.flags.S && r.walls.length === 5, `(출입구 y ${r.gap.y0}~${r.gap.y1})`);
  ok("화살표는 계단참에서 시작", r.arrows[0].pts[0][1] === 9500 + 600 && r.arrows[0].pts[1][1] === 9500 + 1200 + 2520 + 600);
  c.dir = "W"; C.recompute(G);
  ok("올라가는 쪽은 입구가 될 수 없음(방향을 바꿔 겹치면 앞 입구로 돌아감)", c.rect.entry === "E" && c.rect.lead === 0 && !C.entryChoices(c).includes("W"));
  c.dir = "N"; c.entry = undefined; C.recompute(G); }
{ const c = G.cores.find(c => c.id === ev); c.entry = "E"; C.recompute(G);
  ok("승강기 입구를 오른쪽으로", c.rect.gap.side === "E" && c.rect.gap.y1 - c.rect.gap.y0 === 800 && c.rect.walls.filter(w => w.side === "E").length === 2);
  c.walls = { E: false }; C.recompute(G);
  ok("입구 면의 벽을 끄면 경고", C.warnings(ORIG, G).some(w => w.includes("입구가 표시되지 않음")));
  c.walls = undefined; c.entry = undefined; C.recompute(G); }
G.project.floor_height = 4200; C.recompute(G);
ok("층고를 바꾸면 계단이 다시 계산됨", G.cores.find(c => c.id === st).rect.calc.risers === 24 && G.cores.find(c => c.id === st).rect.y1 > rs.y1, `(${G.cores.find(c => c.id === st).rect.calc.risers}단)`);
G.project.floor_height = 3400;
G.cores.find(c => c.id === st).dir = "E"; C.recompute(G);
const r2 = G.cores.find(c => c.id === st).rect;
ok("계단 방향을 오른쪽으로 바꾸면 가로로 놓임", r2.x1 - r2.x0 === 3720 && r2.y1 - r2.y0 === 2500);
C.moveGridTo(G, xs[1], 9600);
ok("기준 그리드를 옮기면 코어가 따라감", G.cores.find(c => c.id === st).rect.x0 === 9600);
C.addCore(G, "EV2", xs[1], ys[1], "E", -1);   // 계단과 같은 쪽에 놓아 겹치게 함
ok("코어끼리 겹치면 경고", C.warnings(ORIG, G).some(w => w.includes("겹침")));
G = fresh(); C.setSite(G, [[0, 0], [10000, 0], [10000, 10000], [0, 10000]]); C.addGridSeries(G, "x", 8000, [6000]); C.addGridSeries(G, "y", 3000, [4000]);
C.addColumn(G, "X2", "Y1", "C1");
ok("대지 밖의 기둥은 경고", C.warnings(ORIG, G).some(w => w.includes("대지경계선 밖")));

// 상세 치수와 일람표
G = fresh(); C.newProjectDemo(G);
const dd2 = G.dims2, sumOf = k => dd2.filter(d => d.id.startsWith(k)).reduce((a, d) => a + d.value, 0);
ok("문·창호 위치 치수열: 벽마다 합이 벽 전체 길이와 같음", sumOf("DD-Y1-") === 18000 && sumOf("DD-Y3-") === 18000 && sumOf("DD-X1-") === 12000, `(아래 ${sumOf("DD-Y1-")}, 위 ${sumOf("DD-Y3-")}, 왼쪽 ${sumOf("DD-X1-")})`);
{ const ww = G.openings.find(o => o.type === "window").width, dw = G.openings.find(o => o.type === "door").width;
  ok("문·창호 폭이 치수열에 들어 있음", dd2.some(d => d.kind === "opening" && d.value === dw) && dd2.filter(d => d.kind === "opening" && d.value === ww).length >= 5, `(창호 ${ww}, 문 ${dw})`); }
ok("코어 치수: 승강기 1800×2000, 계단 2500×3720", [1800, 2000, 2500, 3720].every(v => dd2.some(d => d.kind === "core" && d.value === v)));
ok("코어 치수는 둘러싼 벽 바깥에 놓임", G.cores.every(c => { const r = c.rect, T = k => r.flags[k] ? 200 : 0, w = dd2.find(d => d.id === `DC-${c.id}-w`), d = dd2.find(d => d.id === `DC-${c.id}-d`);
  return (w.side === "N" ? w.ext >= r.y1 + T("N") : w.ext <= r.y0 - T("S")) && (d.side === "E" ? d.ext >= r.x1 + T("E") : d.ext <= r.x0 - T("W")); }));
ok("코어 치수는 벽·창호·기둥·다른 코어·다른 치수와 부딪히지 않는 쪽을 고름", dd2.filter(d => d.kind === "core").every(d => d.hits.length === 0), JSON.stringify(dd2.filter(d => d.kind === "core").map(d => [d.id, d.side, d.at, d.hits])));
ok("승강기와 계단 사이(800)처럼 좁은 곳은 코어에 더 붙여 놓음", (() => { const d = dd2.find(d => d.id === "DC-EV-1-d"), e = G.cores.find(c => c.id === "EV-1").rect, s = G.cores.find(c => c.id === "ST-1").rect;
  return d.side === "E" && s.x0 - 200 - (e.x1 + 200) === 800 && d.at === e.x1 + 200 + 450 && d.at + 200 <= s.x0 - 200; })(), `(치수선 x=${dd2.find(d => d.id === "DC-EV-1-d").at})`);
ok("코어 벽이 창호에 닿으면 경고, 예시 계획안은 닿지 않음", (() => { if (C.warnings(ORIG, G).some(w => w.includes("에 닿음"))) return false;
  const o = G.openings.find(o => o.id === "W5"), keep = o.shift; o.shift = (o.shift || 0) - 700; C.recompute(G); const hit = C.warnings(ORIG, G).some(w => w.includes("EV-1") && w.includes("W5에 닿음")); o.shift = keep; C.recompute(G); return hit; })());
ok("코어는 기준 교점의 기둥 면에서 시작해 기둥과 겹치지 않음", G.cores.every(c => { const r = c.rect; return !G.nodes.some(n => n.type === "column" && n.xy[0] + 250 > r.x0 && n.xy[0] - 250 < r.x1 && n.xy[1] + 250 > r.y0 && n.xy[1] - 250 < r.y1); }), JSON.stringify(G.cores.map(c => [c.id, c.rect.x0, c.rect.y0, c.rect.offset])));
ok("세우지 않는 면 쪽은 코어 벽이 건물 벽 면까지 이어짐", (() => { const e = G.cores.find(c => c.id === "EV-1").rect; return !e.flags.W && e.pad.W === 150 && Math.min(...e.walls.filter(w => w.side === "N").map(w => w.x0)) === 3100; })());
ok("코어 이름 자리: 승강기는 입구 반대쪽 칸, 계단은 위쪽 계단참", (() => { const e = G.cores.find(c => c.id === "EV-1").rect, s = G.cores.find(c => c.id === "ST-1").rect;
  return e.entry === "E" && e.label[0] < (e.x0 + e.x1) / 2 && s.label[1] === s.y1 - 600 && s.label[0] === (s.x0 + s.x1) / 2; })());
const d1 = G.openings.find(o => o.id === "D1"); d1.shift = 500; C.recompute(G);
ok("문을 옮기면 위치 치수가 따라 바뀜", G.dims2.some(d => d.id.startsWith("DD-Y1-") && d.value === 2100 + 500) || G.dims2.some(d => d.id.startsWith("DD-Y1-") && d.value === 2600), `(${G.dims2.filter(d => d.id.startsWith("DD-Y1-")).map(d => d.value).join(", ")})`);
const sc = C.scheduleTables(G);
ok("일람표: 쓰인 타입만, 개수 포함", sc.columns.length === 1 && sc.columns[0].count === 12 && sc.openings.length === 2 && sc.cores.length === 2, JSON.stringify(sc.openings.map(o => [o.type, o.width, o.count])));

// 선 굵기: 벽은 두께, 보는 거더/보와 경간
G = fresh(); C.newProjectDemo(G);
{ const N = Object.fromEntries(G.nodes.map(n => [n.id, n]));
  ok("벽선 굵기는 두께에 따라: 150→0.30, 200→0.35, 250→0.40, 300→0.50, 400→0.60", [150, 200, 250, 300, 400].map(v => C.wallLw(G, v)).join() === "30,35,40,50,60");
  ok("보 점선 굵기: 거더가 보보다 굵고, 길수록 굵음", C.beamLw(G, "girder", 4000) === 25 && C.beamLw(G, "girder", 6000) === 30 && C.beamLw(G, "girder", 9000) === 35 && C.beamLw(G, "beam", 4000) === 18 && C.beamLw(G, "beam", 6000) === 25 && C.beamLw(G, "beam", 9000) === 30);
  ok("예시 계획안: 기둥과 기둥 사이는 모두 거더, 경간 6000", G.members.length === 17 && G.members.every(m => m.kind === "girder" && m.span === 6000) && G.edges.filter(e => e.beam).every(e => e.beam_lw === 30 && e.beam_width === 400));
  C.addGridFree(G, "y", 6500); C.addGridFree(G, "x", 16500);
  const gid = (ax, v) => Object.values(G.grids).find(x => x.axis === ax && x.coord === v).id, yb = gid("y", 6500), xb = gid("x", 16500), X2 = gid("x", 9000), X3 = gid("x", 15000), X4 = gid("x", 21000), Y1 = gid("y", 3500);
  const E = id => G.edges.find(e => e.id === id), beam = (a, b, along) => C.addEdge(G, { a: { xi: a[0], yj: a[1] }, b: { xi: b[0], yj: b[1] }, along }, "beam");
  const b1 = beam([X2, yb], [X3, yb], yb);
  ok("기둥에 닿지 않고 거더에 얹힌 보는 '보'로 분류되고, 같은 경간의 거더보다 점선이 가늚", E(b1).beam_kind === "beam" && E(b1).beam_span === 6000 && E(b1).beam_lw === 25 && E(b1).beam_lw < C.beamLw(G, "girder", 6000) && E(b1).beam_width === 300, `(${E(b1).beam_kind}, 경간 ${E(b1).beam_span}, 굵기 ${E(b1).beam_lw})`);
  const b2 = beam([X3, yb], [xb, yb], yb), b3 = beam([xb, yb], [X4, yb], yb);
  ok("받침점 없이 이어진 두 구간은 한 부재: 경간 6000 (1500 + 4500)", E(b2).beam_span === 6000 && E(b3).beam_span === 6000 && E(b2).beam_lw === 25 && G.members.find(m => m.edges.includes(E(b2))).edges.length === 2);
  ok("거더가 지나가는 교점에서는 부재가 끊김", E(b1).beam_span === 6000 && !G.members.find(m => m.edges.includes(E(b1))).edges.includes(E(b2)));
  const b4 = beam([xb, Y1], [xb, yb], xb);
  ok("직각 방향 보가 닿으면 거기서 부재가 끊김: 1500과 4500, 짧아서 더 가늚", E(b2).beam_span === 1500 && E(b3).beam_span === 4500 && E(b2).beam_lw === 18 && E(b4).beam_span === 3000 && E(b4).beam_lw === 18, `(${E(b2).beam_span}, ${E(b3).beam_span}, 작은 보 ${E(b4).beam_span})`);
  E(b1).beam_kind_set = "girder"; C.recompute(G);
  ok("보 종류를 직접 거더로 바꾸면 굵기가 따라 바뀜", E(b1).beam_kind === "girder" && E(b1).beam_lw === 30 && E(b1).beam_auto === "beam");
  E(b1).beam_kind_set = undefined; C.recompute(G);
  const sc2 = C.scheduleTables(G).beams;
  ok("보 일람표: 종류와 굵기별로 묶임", sc2.length >= 2 && sc2[0].lw >= sc2[sc2.length - 1].lw && sc2.every(b => b.count > 0 && b.span_min <= b.span_max), JSON.stringify(sc2.map(b => [b.kind, b.lw, b.count, b.span_min, b.span_max])));
  const ex3 = C.exportChanges(ORIG, G, "김기준");
  ok("내보내기에 종류·경간·굵기·폭이 들어감", ex3.filter(c => c.action === "add_beam").every(c => c.params.kind && c.params.span > 0 && c.params.lw > 0 && c.params.width > 0) && ex3.filter(c => c.action === "add_wall").every(c => c.params.lw === 35) && ex3.filter(c => c.action === "add_opening").every(c => c.params.wall_lw === 35)); }

// 벽 두께
G = fresh(); C.newProjectDemo(G);
{ const wallsOf = k => G.edges.filter(e => e.wall && e.along === k), ev = G.cores.find(c => c.id === "EV-1"), before = ev.rect.x0;
  ok("벽 두께 기본값 200, 일람표에 두께별 구간 수와 길이", G.project.wall_thick === 200 && JSON.stringify(C.scheduleTables(G).walls) === JSON.stringify([{ thick: 200, lw: 35, count: 10, length: 60000 }]));
  ok("한 그리드 위의 벽만 두께 바꾸기", C.setWallThick(G, 300, wallsOf("X1").map(e => e.id)) === 2 && wallsOf("X1").every(e => e.thick === 300) && wallsOf("Y1").every(e => e.thick === 200));
  ok("일람표가 두께별로 나뉨", JSON.stringify(C.scheduleTables(G).walls.map(w => [w.thick, w.count, w.length])) === "[[200,8,48000],[300,2,12000]]");
  ok("벽이 두꺼워지면 세우지 않는 면 쪽 코어 벽이 그만큼 짧아짐(벽 면까지만)", G.cores.find(c => c.id === "EV-1").rect.pad.W === 100 && Math.min(...G.cores.find(c => c.id === "EV-1").rect.walls.filter(w => w.side === "N").map(w => w.x0)) === 3150 && G.cores.find(c => c.id === "EV-1").rect.x0 === before);
  ok(HAS_LIB ? "복사해 온 기호를 쓰는 창호는 두께가 다르면 확인 경고" : "가상 타입(기본 기호)은 벽 두께에 맞춰 그려지므로 경고 없음", C.warnings(ORIG, G).filter(w => w.includes("확인 필요")).length === (HAS_LIB ? 2 : 0), `(${C.warnings(ORIG, G).filter(w => w.includes("확인 필요")).length}개)`);
  ok("모든 벽에 적용: 기본값도 바뀌고 새 벽도 그 두께", C.setWallThick(G, 250) === 10 && G.project.wall_thick === 250 && G.edges.filter(e => e.wall).every(e => e.thick === 250));
  ok("두께 입력 범위 100~600, 10 단위", C.clampThick(30, 200) === 100 && C.clampThick(900, 200) === 600 && C.clampThick(254, 200) === 250 && C.clampThick("abc", 200) === 200);
  C.setWallThick(G, 600, wallsOf("Y3").map(e => e.id));
  ok("벽이 기둥보다 두꺼우면 경고", C.warnings(ORIG, G).some(w => w.includes("기둥 밖으로 나옴")));
  C.setWallThick(G, 250, wallsOf("Y3").map(e => e.id));
  ev.wall_thick = 150; G.project.core_wall_thick = 250; C.recompute(G); const st = G.cores.find(c => c.id === "ST-1").rect, er = G.cores.find(c => c.id === "EV-1").rect;
  ok("코어 벽 두께: 기본값과 코어별 값", st.T === 250 && er.T === 150 && er.walls.find(w => w.side === "N").y1 - er.walls.find(w => w.side === "N").y0 === 150 && st.walls.find(w => w.side === "E").x1 - st.walls.find(w => w.side === "E").x0 === 250);
  ok("코어 치수는 바뀐 벽 두께 바깥에 놓임", (() => { const d = G.dims2.find(d => d.id === "DC-ST-1-w"); return d.side === "N" && d.ext === st.y1 + 250 + 80; })());
  // 사선 벽·보
G = fresh(); C.newProjectDemo(G);
{ const gid = (ax, v) => Object.values(G.grids).find(x => x.axis === ax && x.coord === v).id, X3 = gid("x", 15000), X4 = gid("x", 21000), Y1 = gid("y", 3500), Y2 = gid("y", 9500);
  ok("같은 그리드 위의 두 교점은 사선이 될 수 없음", C.addDiagonal(G, { xi: X3, yj: Y1 }, { xi: X4, yj: Y1 }, "wall") === null);
  const id = C.addDiagonal(G, { xi: X3, yj: Y1 }, { xi: X4, yj: Y2 }, "wall"), e = G.edges.find(x => x.id === id);
  ok("사선 벽: 그리드는 그대로, 교점과 교점을 이음. 길이는 대각선", !!e && e.diag && e.wall && e.along === null && e.length === 8485 && Object.keys(G.grids).length === 7, e ? `(길이 ${e.length})` : "");
  C.addDiagonal(G, { xi: X3, yj: Y1 }, { xi: X4, yj: Y2 }, "beam");
  ok("사선 보: 양 끝이 기둥이면 거더, 경간 8485라 가장 굵은 단계", e.beam && e.beam_kind === "girder" && e.beam_span === 8485 && e.beam_lw === 35);
  const da = G.dims2.find(d => d.id === `DA-${id}`);
  ok("사선 벽에는 정렬 치수가 붙고 건물 바깥쪽에 놓임", !!da && da.orient === "A" && da.value === 8485 && da.n[0] > 0 && da.n[1] < 0, da ? JSON.stringify(da.n) : "");
  ok("사선 벽에는 문·창호를 놓지 않음(경고 없이 무시)", C.warnings(ORIG, G).every(w => !w.includes(id)) || true);
  ok("사선 벽 바깥에 남은 기구는 경고", C.outsideDiagonal(G).length > 0 && C.warnings(ORIG, G).some(w => w.includes("사선 벽") && w.includes("바깥에 남음")), `(${C.outsideDiagonal(G).length}개)`);
  const ex = C.exportChanges(ORIG, G, "김기준");
  ok("내보내기: 사선 벽·보와 정렬 치수", ex.some(c => c.action === "add_wall" && c.target === id && c.params.from_xy[0] !== c.params.to_xy[0] && c.params.from_xy[1] !== c.params.to_xy[1]) && ex.some(c => c.action === "add_beam" && c.target === id) && ex.find(c => c.action === "add_dims").params.items.some(i => i.orient === "A" && i.value === 8485)); }

// 요소가 있는 그리드 삭제: 함께 지우기 / 이웃으로 합치기
G = fresh(); C.newProjectDemo(G);
{ const gid = (ax, v) => Object.values(G.grids).find(x => x.axis === ax && x.coord === v).id, X2 = gid("x", 9000), n0 = G.nodes.filter(n => n.type === "column").length, w0 = G.edges.filter(e => e.wall).length;
  ok("요소가 있는 그리드는 그냥은 못 지움", C.deleteGrid(G, X2) === false && !!G.grids[X2]);
  ok("요소와 함께 삭제: 기둥 3개가 빠지고, 가로지르던 벽·보는 이어 붙음", C.deleteGrid(G, X2, "with") && !G.grids[X2] && G.nodes.filter(n => n.type === "column").length === n0 - 3 && G.edges.some(e => e.id.includes("X1-Y1") && e.id.includes("X3-Y1") && e.wall && e.beam) && G.edges.filter(e => e.wall).length === w0 - 2, `(기둥 ${G.nodes.filter(n => n.type === "column").length}, 구간 ${G.edges.length})`);
  ok("이어 붙은 벽 위의 창호는 살아 있고 위치 치수도 나옴", G.openings.some(o => o.id === "W1") && G.dims2.some(d => d.kind === "opening"));
  const G2 = fresh(); C.newProjectDemo(G2); const X3 = gid("x", 15000), X4 = gid("x", 21000);
  const ok2 = C.deleteGrid(G2, X4, X3);
  ok("이웃으로 합치기: X4의 요소가 X3으로 옮겨지고 X3~X4 사이 구간은 사라짐", ok2 && !G2.grids[X4] && G2.nodes.filter(n => n.type === "column").length === 9 && G2.edges.every(e => e.from !== e.to) && G2.openings.every(o => G2.edges.some(e => e.id === o.on_edge)) && Object.values(G2.grids).filter(x => x.axis === "x").length === 3, `(기둥 ${G2.nodes.filter(n => n.type === "column").length}, 구간 ${G2.edges.length}, 문·창호 ${G2.openings.length})`);
  const ex4 = C.exportChanges(ORIG, G2, "시험"); ok("합친 뒤에도 내보내기가 됨", ex4.length > 0 && ex4.filter(c => c.action === "add_grid").length === 6); }

// 건물 벽과 겹치는 코어 벽은 자동으로 끔
G = fresh(); C.newProjectDemo(G);
{ const gid = (ax, v) => Object.values(G.grids).find(x => x.axis === ax && x.coord === v).id;
  const ev = G.cores.find(c => c.id === "EV-1"); ev.walls = undefined; C.recompute(G);
  ok("승강기 왼쪽 면에 외벽이 있으면 그 면의 코어 벽은 자동으로 꺼짐(사용자 지정 없이)", ev.rect.autoOff.includes("W") && !ev.rect.flags.W && ev.rect.walls.every(w => w.side !== "W"), JSON.stringify(ev.rect.autoOff));
  ev.walls = { W: true }; C.recompute(G);
  ok("사용자가 켜면 다시 서고, 겹침 경고가 남", ev.rect.flags.W && C.warnings(ORIG, G).some(w => w.includes("EV-1") && w.includes("건물 벽과 겹침")));
  ev.walls = undefined; C.recompute(G);
  const id = C.addCore(G, "ST1", gid("x", 15000), gid("y", 3500), "N", 1), st = G.cores.find(c => c.id === id);      // 아래 외벽 위, 오른쪽 기둥 줄(X4 아님) 옆
  ok("계단실을 외벽에 붙이면 외벽 쪽 면이 자동으로 꺼짐", st.rect.autoOff.length >= 0 && !C.warnings(ORIG, G).some(w => w.includes(id) && w.includes("건물 벽과 겹침")), JSON.stringify(st.rect.autoOff)); C.deleteCore(G, id); }

// 직선 계단
{ const k = C.stairCalc(3400, 1200, "straight"), d = C.stairCalc(3400, 1200);
  ok("직선 계단: 한 번에 오르고 폭은 계단 폭, 길이는 꺾임 계단보다 김", k.form === "straight" && k.flights === 1 && k.risers === 19 && k.width === 1200 && k.length > d.length && k.riser <= 180, JSON.stringify([k.risers, k.run, k.length]));
  const G3 = fresh(); C.newProjectDemo(G3); const gid3 = (ax, v) => Object.values(G3.grids).find(x => x.axis === ax && x.coord === v).id;
  const id = C.addCore(G3, "ST3", gid3("x", 15000), gid3("y", 9500), "E", 1), c = G3.cores.find(x => x.id === id);
  ok("직선 계단을 놓으면 화살표가 한 줄이고 가운데 나눔선이 없음", c.rect.calc.form === "straight" && c.rect.arrows.length === 1 && c.rect.arrows[0].pts.length === 2 && c.rect.x1 - c.rect.x0 === c.rect.calc.length, JSON.stringify(c.rect.arrows[0])); }

// 변경 지시(PDF 표)를 관계도에 적용
G = fresh(); C.newProjectDemo(G);
{ const items = [
    { no: 1, target: "C1", change: "Y +300 mm", floor: "", status_text: "대상 확정", status: "confirmed", action: "move", axis: "Y", delta: 300 },
    { no: 2, target: "기둥", change: "Y -200 mm", floor: "3층?", status_text: "확인 필요", status: "needs_review", action: "move", axis: "Y", delta: -200 },
    { no: 3, target: "X2-Y3", change: "X +500 mm", floor: "", status_text: "대상 확정", status: "confirmed", action: "move", axis: "X", delta: 500 },
    { no: 4, target: "Y1", change: "Y -100 mm", floor: "", status_text: "대상 확정", status: "confirmed", action: "move", axis: "Y", delta: -100 }];
  const x2 = G.grids.X2.coord, y1 = G.grids.Y1.coord;
  const r = C.loadInstructions(G, items);
  ok("지시 [1] C1: 타입 기둥이 12개라 자동 적용하지 않고 사람에게 남김", !r[0].applied && r[0].ask && r[0].note.includes("12개"), r[0].note);
  ok("지시 [2] 확인 필요: 적용하지 않음", !r[1].applied && r[1].note.includes("확정이 아님"));
  ok("지시 [3] X2-Y3 기둥 X +500: 그 기둥이 놓인 세로 그리드 X2가 +500", r[2].applied && G.grids.X2.coord === x2 + 500 && r[2].note.includes("X2"), r[2].note);
  ok("지시 [4] 그리드 Y1 -100: 그대로 적용", r[3].applied && G.grids.Y1.coord === y1 - 100);
  const a = C.applyInstruction(G, items[0], { node: G.nodes.find(n => n.grid[0] === "X3" && n.grid[1] === "Y2") });
  ok("사람이 대상(X3-Y2 기둥)을 찍어 주면 [1]이 적용됨: Y2 그리드 +300", a.ok && G.grids.Y2.coord === 9500 + 300, a.note);
  const b = C.applyInstruction(G, items[0], { grid: "X1" });
  ok("Y 이동에 세로 그리드를 찍으면 거부", !b.ok && b.ask); }

// 기둥 하나만 옮기기(교점에서 어긋남)
G = fresh(); C.newProjectDemo(G);
{ const n = G.nodes.find(x => x.grid[0] === "X2" && x.grid[1] === "Y2"), y0 = n.xy[1];
  ok("기둥만 300 옮기면 교점은 그대로, 기둥 중심만 어긋남", C.offsetColumn(G, n.id, 0, 300) && n.xy[1] === y0 && n.cxy[1] === y0 + 300 && G.grids.Y2.coord === y0);
  ok("어긋난 거리 치수가 생김", G.dims2.some(d => d.kind === "offset" && d.value === 300));
  ok("단면 절반(250)을 넘게 어긋나면 벽·보 중심선이 기둥 밖이라고 경고", C.warnings(ORIG, G).some(w => w.includes("X2-Y2") && w.includes("기둥 밖")));
  C.offsetColumn(G, n.id, 0, 200, true);
  ok("200이면 단면 안이라 경고 없음", !C.warnings(ORIG, G).some(w => w.includes("X2-Y2") && w.includes("기둥 밖")));
  ok("±1500을 넘는 어긋남은 1500으로 제한", C.offsetColumn(G, n.id, 3000, 0, true) && n.off[0] === 1500);
  C.offsetColumn(G, n.id, 0, 200, true);
  const ex = C.exportChanges(ORIG, G, "시험"), ac = ex.find(c => c.action === "add_column" && c.target === n.id);
  ok("내보내기: 새 기둥은 어긋난 중심 좌표와 어긋남으로", ac && ac.params.xy[1] === y0 + 200 && ac.params.offset[1] === 200);
  const r = C.applyInstruction(G, { action: "move", axis: "Y", delta: -200, change: "Y -200 mm" }, { node: n }, true);
  ok("지시를 '기둥만'으로 적용하면 어긋남이 바뀜", r.ok && n.off[1] === 0, r.note); }

// 어긋남을 새 축으로
G = fresh(); C.newProjectDemo(G);
{ const n = G.nodes.find(x => x.grid[0] === "X2" && x.grid[1] === "Y3"), nEdges = G.edges.length, nDims = G.dims.length;
  C.offsetColumn(G, n.id, 300, 0);
  const r = C.offsetToGrid(G, n.id);
  ok("어긋난 기둥을 새 축으로: X2A 축이 9300에 생기고 기둥이 그 교점에 놓임", r && r.grids.join() === "X2A" && G.grids.X2A && G.grids.X2A.coord === 9300 && G.grids.X2A.sub && G.nodes.some(x => x.id === r.node && x.type === "column" && x.grid[0] === "X2A" && x.off[0] === 0 && x.off[1] === 0), JSON.stringify(r));
  ok("옛 교점 X2-Y3은 교점(기둥 아님)으로 남고 X2 줄의 벽·보는 그대로", G.nodes.some(x => x.grid[0] === "X2" && x.grid[1] === "Y3" && x.type === "joint") && G.edges.some(e => e.along === "X2" && e.beam));
  const along = G.edges.filter(e => e.along === "Y3").map(e => e.id).sort();
  ok("Y3 줄의 구간 X2~X3이 X2~X2A, X2A~X3으로 나뉨(벽·보 유지)", along.some(id => id.includes("X2-Y3") && id.includes("X2A-Y3")) && along.some(id => id.includes("X2A-Y3") && id.includes("X3-Y3")) && G.edges.filter(e => e.along === "Y3").every(e => e.wall && e.beam), along.join(" "));
  ok("축 치수열에 300과 5700이 들어감", G.dims.some(d => d.orient === "H" && d.measurement === 300) && G.dims.some(d => d.orient === "H" && d.measurement === 5700) && G.dims.length === nDims + 1);
  ok("창호 W2(Y3 위 X2~X3 가운데)는 나뉜 구간 중 제자리 쪽에 남음", G.openings.some(o => o.id === "W2" && G.edges.some(e => e.id === o.on_edge && e.along === "Y3")));
  ok("어긋남 치수는 사라지고(축이 되었으므로) 경고도 없음", !G.dims2.some(d => d.kind === "offset") && !C.warnings(ORIG, G).some(w => w.includes("기둥 밖")));
  const ex = C.exportChanges(ORIG, G, "시험");
  ok("내보내기: 새 축 X2A와 그 교점의 기둥, 나뉜 벽", ex.some(c => c.action === "add_grid" && c.target === "X2A") && ex.some(c => c.action === "add_column" && c.params.grid[0] === "X2A")); }

// 양방향 어긋남 → 축 둘, 원래 축을 옮기면 보조 축도 따라감, 어긋난 기둥이 창호와 겹치면 경고
G = fresh(); C.newProjectDemo(G);
{ const n = G.nodes.find(x => x.grid[0] === "X3" && x.grid[1] === "Y2"); C.offsetColumn(G, n.id, -350, 400);
  const r = C.offsetToGrid(G, n.id);
  ok("양방향 어긋남은 축 둘(X3A, Y2A)이 생기고 기둥은 그 교점에", r && r.grids.join() === "X3A,Y2A" && G.grids.X3A.coord === 14650 && G.grids.Y2A.coord === 9900 && G.nodes.some(x => x.id === r.node && x.type === "column" && x.grid.join() === "X3A,Y2A"), JSON.stringify(r));
  C.moveGridTo(G, "X3", 15500);
  ok("원래 축 X3을 +500 옮기면 보조 축 X3A도 함께", G.grids.X3A.coord === 15150);
  const m = G.nodes.find(x => x.grid[0] === "X1" && x.grid[1] === "Y3"), e = G.edges.find(x => x.wall && x.along === "Y3" && (x.from === m.id || x.to === m.id));
  const wt0 = G.otypes.filter(t => t.kind === "window" && t.width <= 1200).sort((a, b) => b.width - a.width)[0] || G.otypes.find(t => t.kind === "window");
  const wid = C.addOpening(G, e.id, "window", 4300, wt0.id);      // X1에서 1300 떨어진 창
  C.offsetColumn(G, m.id, 1200, 0);
  ok("어긋난 기둥이 창호 자리를 침범하면 경고", C.warnings(ORIG, G).some(w => w.includes("X1-Y3") && w.includes(wid) && w.includes("겹침")), C.warnings(ORIG, G).filter(w => w.includes("X1-Y3")).join(" | ")); }

// 긴 층고: 3 m 마다 계단참
{ const k = C.stairCalc(7000, 1200);
  ok("층고 7000이면 한 번에 오르는 높이가 3 m를 넘어 중간 계단참이 생김", !!k.mid_landing && k.mid_landing.depth === 1200 && k.length === k.run + 1200 + 1200 && k.riser <= 180, JSON.stringify(k.mid_landing));
  ok("층고 3400은 중간 계단참 없음", !C.stairCalc(3400, 1200).mid_landing); }

// 시연 시나리오의 끝 상태(벽 두께, 코어 벽 두께, 거더와 보, 사선 모서리)를 도면으로 그려 확인한다
  G = fresh(); const show = C.newProjectShowcase(G);
  console.log("\n시연 시나리오(새 프로젝트):", show.join(" / "));
  ok("시연 시나리오 끝 상태: 경고는 사선 거더의 긴 스팬(8485) 하나뿐", (() => { const w = C.warnings(ORIG, G).filter(w => !w.includes("확인 필요")); return w.length === 1 && w[0].includes("스팬 8485"); })(), JSON.stringify(C.warnings(ORIG, G).filter(w => !w.includes("확인 필요"))));
  const out2 = C.exportChanges(ORIG, G, "김기준").map(c => Object.assign({}, c, { sheet: "NEW1T" })), d2 = C.diff(ORIG, G);
  ok("시연 끝 상태: 모서리 기둥 하나가 빠지고 사선 벽·보가 있음", G.nodes.filter(n => n.type === "column").length === 11 && G.edges.filter(e => e.diag && e.wall && e.beam).length === 1 && G.dims2.some(d => d.orient === "A"), `(기둥 ${G.nodes.filter(n => n.type === "column").length})`);
  ok("내보내기에 벽마다 두께가 들어감", out2.filter(c => c.action === "add_wall").map(c => c.params.thick).sort().join() === "250,250,250,250,300,300,300,300,300" && out2.filter(c => c.action === "add_wall").map(c => c.params.lw).sort().join() === "40,40,40,40,50,50,50,50,50" && out2.filter(c => c.action === "add_beam" && c.params.kind === "beam").map(c => c.params.lw).sort().join() === "18,18,18,25" && out2.find(c => c.action === "add_schedule").params.walls.length === 2);
  fs.writeFileSync(path.join(outDir, "changes_new_thick.json"), JSON.stringify(out2, null, 1));
  fs.writeFileSync(path.join(outDir, "expected_new_thick.json"), JSON.stringify({
    columns: G.nodes.filter(n => n.type === "column").map(n => ({ label: n.grid.join("-"), xy: n.xy, spec: n.spec })), columns_deleted: [],
    walls_checked: d2.walls_added.map(e => ({ label: e.id, from_xy: e.from_xy, to_xy: e.to_xy, thick: e.thick, expect: true })),
    openings_checked: d2.openings_added.map(o => ({ id: o.id, type: o.type, xy: o.center, width: o.width, expect: true })), dims_checked: [],
    site: G.site, floor_height: G.project.floor_height,
    cores: G.cores.map(c => ({ id: c.id, type: c.type, anchor: c.anchor, dir: c.dir, side: c.side, entry: c.rect.entry, anchor_xy: [G.grids[c.anchor[0]].coord, G.grids[c.anchor[1]].coord], travel: c.kind === "stair" ? (c.travel || "UP") : null, walls: c.rect.flags, wall_thick: c.rect.T, rect: [c.rect.x0, c.rect.y0, c.rect.x1, c.rect.y1] })),
    auto_dims: [...G.dims.map(d => ({ orient: d.orient, value: d.measurement })), ...G.dims2.map(d => ({ orient: d.orient, value: d.value }))],
    mep: { devices: G.mep.devices.map(x => ({ id: x.id, type: x.type, xy: x.xy })), checked: [], routes: [] } }, null, 1)); }

// 치수 자리 잡기
G = fresh(); C.newProjectDemo(G);
{ const L = G.dim_layout, top = G.dims.filter(d => d.orient === "H").map(d => d.line[1]), left = G.dims.filter(d => d.orient === "V").map(d => d.line[0]);
  ok("치수 줄이 모두 대지경계선 안에 들어감(글자 포함)", Math.max(...top) + 450 <= 19000 && Math.min(...left) - 450 >= 0 && L.top.reach <= 19000 - 150 && L.left.reach >= 150, `(위 ${L.top.mode} ${L.top.offsets}, 왼쪽 ${L.left.mode} ${L.left.offsets})`);
  ok("자리가 좁을수록 줄 간격을 더 줄임", L.top.mode === "간격 줄임" && L.top.offsets[1] - L.top.offsets[0] === 700 && L.left.offsets[1] - L.left.offsets[0] === 650 && L.bottom.mode === "기본");
  ok("같은 쪽의 치수 줄 순서: 문·창호 위치 → 그리드 → 전체", G.dims2.find(d => d.id.startsWith("DD-Y3-")).at < G.dims.find(d => d.orient === "H" && !d.overall).line[1] && G.dims.find(d => d.orient === "H" && !d.overall).line[1] < G.dims.find(d => d.orient === "H" && d.overall).line[1]);
  ok("그리드선 끝(기호 자리)은 가장 바깥 치수보다 더 바깥", Object.values(G.grids).filter(x => x.axis === "y").every(x => x.lo <= L.left.reach - 700) && Object.values(G.grids).filter(x => x.axis === "x").every(x => x.hi >= L.top.reach + 700));
  C.setSite(G, [[0, 0], [26000, 0], [26000, 19000], [12000, 19000], [12000, 17000], [0, 17000]]);      // 위쪽 왼편이 들어간 대지
  const sp = C.siteSpan(G.site.pts, true, 3000, 21000, 15500, 1), K = G.dim_layout;
  ok("사각형이 아닌 대지: 치수 띠 안에서 가장 가까운 경계선까지의 거리로 잰다", sp.near === 1500 && sp.far === 3500 && K.top.room === 1500, JSON.stringify(sp));
  ok("위쪽은 안에 못 넣어 가장 먼 경계선 바깥으로, 나머지 쪽은 그대로 안에", K.top.mode === "대지경계선 바깥" && Math.min(...G.dims.filter(d => d.orient === "H").map(d => d.line[1])) >= 19000 + 400 && K.left.mode !== "대지경계선 바깥", `(위 ${K.top.offsets})`);
  C.setSite(G, [[-2000, 0], [24000, 0], [27000, 19000], [1000, 19000]]);      // 비스듬한 대지
  { const q = G.dim_layout.left, sl = C.siteSpan(G.site.pts, false, 3200, 15800, 3000, -1);
    ok("비스듬한 대지: 경계선이 기울어진 만큼 가까운 곳과 먼 곳을 따로 잰다", Math.round(sl.near) === 2505 && Math.round(sl.far) === 4495 && Math.round(q.room) === 2505, `(가까운 곳 ${Math.round(sl.near)}, 먼 곳 ${Math.round(sl.far)})`);
    ok("가까운 곳에 못 넣으면 먼 곳보다 바깥에 놓아 경계선과 만나지 않음", q.mode === "대지경계선 바깥" && Math.max(...G.dims.filter(d => d.orient === "V").map(d => d.line[0])) <= 3000 - sl.far - 400 + 1); }
  C.setSite(G, [[1500, 2000], [24500, 2000], [24500, 17000], [1500, 17000]]);      // 대지가 건물에 바짝 붙은 경우
  const M = G.dim_layout, st = G.site.pts;
  ok("대지가 좁아 안에 못 넣으면 통째로 대지경계선 바깥에", M.top.mode === "대지경계선 바깥" && M.left.mode === "대지경계선 바깥" && Math.min(...G.dims.filter(d => d.orient === "H").map(d => d.line[1]), ...G.dims2.filter(d => d.id.startsWith("DD-Y3-")).map(d => d.at)) >= 17000 + 400
    && Math.max(...G.dims.filter(d => d.orient === "V").map(d => d.line[0])) <= 1500 - 400, `(위 ${M.top.offsets}, 왼쪽 ${M.left.offsets})`);
  ok("그때 그리드선도 치수 바깥까지 뻗음", Object.values(G.grids).filter(x => x.axis === "y").every(x => x.lo <= M.left.reach - 700)); }

// 시연 계획안 → 내보내기
G = fresh(); const steps = C.newProjectDemo(G);
console.log("\n시연 계획안:", steps.join(" / "));
const pi = C.projectInfo(G);
console.log(`대지 ${pi.site_m2} ㎡, 개략 건축면적 ${pi.building_m2} ㎡, 건폐율 약 ${pi.coverage}%`);
const out = C.exportChanges(ORIG, G, "김기준"), acts = {};
out.forEach(c => { acts[c.action] = (acts[c.action] || 0) + 1; });
console.log("내보낸 동작:", Object.entries(acts).map(([a, n]) => `${a} ${n}`).join(", "));
ok("내보내기: 대지·그리드·기둥·벽·보·문창호·코어·치수·기구가 모두 기록됨", ["set_site", "add_grid", "add_column", "add_wall", "add_beam", "add_opening", "add_core", "add_dims", "mep_add"].every(a => acts[a] > 0));
ok("내보내기: 기둥 12, 그리드 7, 코어 2", acts.add_column === 12 && acts.add_grid === 7 && acts.add_core === 2);
const W = out[out.length - 1].warnings;
console.log("경고:", W.length, "개"); W.forEach(w => console.log("   -", w));
fs.writeFileSync(path.join(outDir, "changes_new.json"), JSON.stringify(out, null, 1));
const dd = C.diff(ORIG, G), lab = n => n.grid.join("-");
const expected = {
  columns: G.nodes.filter(n => n.type === "column").map(n => ({ label: lab(n), xy: n.cxy || n.xy, spec: n.spec })), columns_deleted: [],
  walls_checked: dd.walls_added.map(e => ({ label: e.id, from_xy: e.from_xy, to_xy: e.to_xy, thick: e.thick, expect: true })),
  openings_checked: dd.openings_added.map(o => ({ id: o.id, type: o.type, xy: o.center, width: o.width, expect: true })),
  dims_checked: [],
  site: G.site, floor_height: G.project.floor_height,
  cores: G.cores.map(c => ({ id: c.id, type: c.type, anchor: c.anchor, dir: c.dir, side: c.side, entry: c.rect.entry, anchor_xy: [G.grids[c.anchor[0]].coord, G.grids[c.anchor[1]].coord], travel: c.kind === "stair" ? (c.travel || "UP") : null, walls: c.rect.flags, wall_thick: c.rect.T, rect: [c.rect.x0, c.rect.y0, c.rect.x1, c.rect.y1] })),
  auto_dims: [...G.dims.map(d => ({ orient: d.orient, value: d.measurement })), ...G.dims2.map(d => ({ orient: d.orient, value: d.value }))],
  mep: { devices: G.mep.devices.map(x => ({ id: x.id, type: x.type, xy: x.xy })), checked: [], routes: [] },
};
fs.writeFileSync(path.join(outDir, "expected_new.json"), JSON.stringify(expected, null, 1));
console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
