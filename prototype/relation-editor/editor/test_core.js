// 편집기 계산 부분 검증 (브라우저 없이). 시연 시나리오의 변경 파일과 기대값도 만든다.
const fs = require("fs"), path = require("path"), vm = require("vm");
const outDir = path.join(__dirname, "..", "out", "editor");
const SHEET = process.argv[2] || "A12M";
const html = fs.readFileSync(path.join(outDir, `relation_editor_${SHEET}.html`), "utf8");
const grab = id => { const tag = '<script id="' + id + '">'; const a = html.indexOf(tag) + tag.length; return html.slice(a, html.indexOf('</' + 'script>', a)); };
new vm.Script(grab("ui"), { filename: "ui.js" });   // 화면 스크립트 문법 검사
const ctx = { module: { exports: {} }, console };
vm.createContext(ctx);
vm.runInContext(grab("data") + "\n" + grab("core") + "\nmodule.exports.ORIG_GRAPH = ORIG_GRAPH;", ctx);
const C = ctx.module.exports;
const ORIG = C.recompute(C.initModel(C.ORIG_GRAPH));
let pass = 0, fail = 0;
const ok = (name, cond, extra = "") => { (cond ? pass++ : fail++); console.log(`${cond ? "PASS" : "FAIL"}  ${name} ${extra}`); };
const fresh = () => C.clone(ORIG);
const X = id => ORIG.grids[id].coord;

console.log("타입 일람표:", ORIG.types.map(t => `${t.id}=${t.spec}`).join(", "));
ok("원본 그대로면 변경·경고 없음", C.exportChanges(ORIG, fresh(), "t").length === 0 && C.warnings(ORIG, fresh()).length === 0);

// --- 그리드 이동 ---
let G = fresh(); C.moveGridTo(G, "X6", X("X6") + 500);
let d = C.diff(ORIG, G);
ok("X6 +500: 기둥 3개 이동", d.grids[0].delta === 500 && d.nodes.filter(n => n.moved && n.type === "column").length === 3);
const dimPairs = d.dims.map(x => `${x.from}→${x.to}`).sort().join(",");
ok("X6 +500: 치수 4개 갱신", dimPairs === "2900→2400,5700→5200,5700→6200,5700→6200", dimPairs);
// 개구부는 제자리: 띠(±700) 밖의 문 띠는 움직이지 않음
const d5o = ORIG.openings.find(o => o.id === "D5"), d5 = G.openings.find(o => o.id === "D5");
ok("X6 +500: 벽 가운데의 문 띠 D5는 제자리", d5.xy[0] === d5o.xy[0], `(${d5o.xy[0]} → ${d5.xy[0]})`);
G = fresh(); C.moveGridTo(G, "X6", X("X7") + 5000);
ok("X6는 X7을 넘지 못함", G.grids.X6.coord === X("X7") - 300);

// --- 기둥 ---
G = fresh(); const colId = C.addColumn(G, "X6", "Y1", "C1");
ok("기둥 추가 X6-Y1", !!colId && C.diff(ORIG, G).cols_added.length === 1 && G.nodes.find(n => n.id === colId).spec === "600x400");
ok("같은 자리에 기둥 중복 추가 불가", C.addColumn(G, "X6", "Y1", "C1") === null);
G = fresh(); C.deleteColumn(G, "C@X8-Y7");
d = C.diff(ORIG, G);
ok("기둥 삭제 X8-Y7 → 벽이 있어 교점으로 남음", d.cols_deleted.length === 1 && G.nodes.some(n => n.id === "C@X8-Y7" && n.type === "joint"));
ok("기둥 삭제 시 보 지지 경고", C.warnings(ORIG, G).some(w => w.includes("지지 기둥")));
G = fresh(); G.nodes.find(n => n.id === "C@X8-Y2").ctype = "C5"; C.recompute(G);
ok("기둥 타입 변경 → 단면 반영", G.nodes.find(n => n.id === "C@X8-Y2").spec === "880x400");
G = fresh(); G.types[0].spec = "700x400"; C.recompute(G);
ok("타입 단면 변경이 같은 타입 전체에 반영", C.diff(ORIG, G).nodes.filter(n => n.respec).length === 3);

// --- 벽·보 ---
G = fresh(); const seg = C.candidateSegments(G).find(s => s.along === "Y2" && s.a.xi === "X6" && s.b.xi === "X8");
const wid = C.addEdge(G, seg, "wall");
ok("보만 있던 구간에 벽 추가", !!wid && C.diff(ORIG, G).walls_added.length === 1 && G.edges.find(e => e.id === wid).beam);
G = fresh(); const seg2 = C.candidateSegments(G).find(s => { const a = C.nodeAt(G, s.a.xi, s.a.yj), b = C.nodeAt(G, s.b.xi, s.b.yj); return !(a && b && C.findEdge(G, a.id, b.id)); });
const nid = C.addEdge(G, seg2, "beam");
ok("빈 구간에 보 추가(교점 노드 자동 생성)", !!nid && C.diff(ORIG, G).beams_added.length === 1, `(${nid})`);
G = fresh(); const wallWithOps = ORIG.edges.find(e => ORIG.openings.some(o => o.on_edge === e.id));
C.deleteEdgeKind(G, wallWithOps.id, "wall"); d = C.diff(ORIG, G);
ok("벽 삭제 시 그 위 개구부도 삭제", d.walls_deleted.length === 1 && d.openings_deleted.length === ORIG.openings.filter(o => o.on_edge === wallWithOps.id).length);

// --- 문·창호 ---
G = fresh(); const we = G.edges.find(e => e.id === "J@X2-Y3~J@X2-Y5"); const wId = C.addOpening(G, we.id, "window", 14500, 1500);
const wNew = G.openings.find(o => o.id === wId);
ok("창호 추가", !!wId && wNew.xy[0] === X("X2") && wNew.xy[1] === 14500 && C.diff(ORIG, G).openings_added.length === 1, `(${wId} @ ${wNew.xy})`);
ok("벽이 아닌 구간에는 개구부 추가 불가", C.addOpening(G, "C@X6-Y2~C@X8-Y2", "door", 24000, 900) === null);
console.log("문·창호 타입:", ORIG.otypes.map(t => `${t.id}=${t.kind === "window" ? "창" : "문"}${t.width}${t.band ? "띠" : t.kind === "door" ? "/" + t.leaves + "짝" : ""}(${t.virtual ? "가상" : t.donor ? t.donor.sheet : "-"})`).join(", "));
ok("일람표: 이 도면의 개구부가 모두 타입에 연결되고 폭은 호칭 치수", ORIG.openings.every(o => ORIG.otypes.some(t => t.id === o.otype)) && ORIG.openings.find(o => o.id === "W1").width === 600 && ORIG.openings.find(o => o.id === "D1").width === 800);
ok("일람표: 다른 층의 타입과 가상 타입이 포함됨", ORIG.otypes.some(t => t.donor && t.donor.sheet !== ORIG.sheet) && ORIG.otypes.some(t => t.virtual));
G = fresh(); const w1 = G.openings.find(o => o.id === "W1"); w1.shift = 200; C.recompute(G); d = C.diff(ORIG, G);
ok("창호 이동", d.openings.length === 1 && d.openings[0].edited && !d.openings[0].retype && w1.xy[1] === ORIG.openings.find(o => o.id === "W1").xy[1] + 200);
G = fresh(); const d1 = G.openings.find(o => o.id === "D1"), dbl = G.otypes.find(t => t.kind === "door" && t.leaves === 2);
d1.otype = dbl.id; C.recompute(G); d = C.diff(ORIG, G);
const ex1 = C.exportChanges(ORIG, G, "t").find(c => c.action === "edit_opening");
ok("문 타입 교체: 일람표의 폭이 적용되고 복사할 원본이 기록됨", d1.width === dbl.width && d1.leaves === 2 && d.openings[0].retype && ex1.params.donor.id === dbl.donor.id && ex1.params.donor.handles.length > 0, `(${d1.id} ${ORIG.openings.find(o => o.id === "D1").width} → ${d1.width}, 원본 ${ex1.params.donor.id})`);
G = fresh(); const nt = C.addOpeningType(G, "window", 2700); const w2 = G.openings.find(o => o.id === "W2"); w2.otype = nt; C.recompute(G);
ok("새 타입 추가 후 교체(복사 원본 없음)", w2.width === 2700 && C.diff(ORIG, G).otypes_added.length === 1 && C.exportChanges(ORIG, G, "t").find(c => c.action === "edit_opening").params.donor === null);
ok("같은 크기의 타입은 중복 추가되지 않음", C.addOpeningType(G, "window", 2700) === nt && C.addOpeningType(G, "window", 900) === ORIG.otypes.find(t => t.kind === "window" && t.width === 900).id);
G = fresh(); const t9 = G.otypes.find(t => t.kind === "window" && t.width === 900); G.openings.find(o => o.id === "W2").otype = t9.id; C.recompute(G);
const exX = C.exportChanges(ORIG, G, "t").find(c => c.action === "edit_opening");
ok("다른 층 도면의 타입으로 교체: 원본 도면이 기록됨", exX.params.donor && exX.params.donor.sheet !== ORIG.sheet && exX.params.width_from === 600 && exX.params.width_to === 900, `(${exX.params.donor.sheet} ${exX.params.donor.id})`);
G = fresh(); const big = C.addOpeningType(G, "door", 9000); G.openings.find(o => o.band).otype = big; C.recompute(G);
ok("개구부가 벽보다 크면 경고", C.warnings(ORIG, G).some(w => w.includes("개구부") || w.includes("벗어남")));
G = fresh(); C.deleteOpening(G, "D1");
ok("문 삭제", C.diff(ORIG, G).openings_deleted.length === 1);

// --- 그리드 추가·삭제 ---
G = fresh(); const gid = C.addGrid(G, "x", X("X6") + 1500, "X6");
ok("그리드 추가", !!gid && C.diff(ORIG, G).grids_added[0].coord === X("X6") + 1500 && C.intersections(G).some(p => p.xi === gid), `(${gid})`);
ok("너무 가까운 그리드는 추가 불가", C.addGrid(G, "x", X("X6") + 100, "X6") === null);
ok("요소가 놓인 그리드는 삭제 불가", C.deleteGrid(G, "X6") === false);
ok("빈 그리드는 삭제 가능", C.deleteGrid(G, gid) === true && C.exportChanges(ORIG, G, "t").length === 0);

// --- 설비·전기·소방 (가상 배치) ---
if (ORIG.mep) {
  const M = ORIG.mep, dev = (g, id) => g.mep.devices.find(x => x.id === id);
  console.log("기구:", M.devices.length, "개, 덕트", M.routes.length, "구간");
  ok("원본 상태에서 설비·전기 경고 없음(기준선 제외)", C.warnings(ORIG, fresh()).length === 0);
  // 구획 비율 배치: X6 +500 이면 X5~X6 구획의 조명이 같은 비율로 재배치
  G = fresh(); C.moveGridTo(G, "X6", X("X6") + 500);
  const l0 = M.devices.find(x => x.type === "EL1" && x.host.gx[0] === "X5" && Math.abs(x.host.fx - 0.75) < 1e-6), l1 = dev(G, l0.id);
  ok("그리드 이동 → 구획 안 조명이 비율대로 재배치", l1.xy[0] === l0.xy[0] + 375 && l1.xy[1] === l0.xy[1], `(${l0.id} x ${l0.xy[0]} → ${l1.xy[0]})`);
  const md = C.mepDiff(ORIG, G);
  ok("그리드 이동 → 양쪽 구획의 기구가 자동 재배치", md.moved.length >= 20 && md.moved.every(x => !x.edited), `(${md.moved.length}개)`);
  let W = C.warnings(ORIG, G);
  ok("그리드 이동 → 덕트-기둥 간섭 경고", W.some(w => w.includes("덕트") && w.includes("기둥")), `(${(W.find(w => w.includes("덕트") && w.includes("기둥")) || "").slice(0, 46)})`);
  ok("그리드 이동 → 헤드 간격 초과 경고", W.some(w => w.includes("헤드") && w.includes("간격")), `(${(W.find(w => w.includes("헤드")) || "").slice(0, 44)})`);
  // 벽 부착: 벽이 옆으로 움직이면 따라감
  G = fresh(); C.moveGridTo(G, "X5", X("X5") - 200);
  const o0 = M.devices.find(x => x.type === "EO1" && x.host.kind === "wall" && x.host.edge.includes("X5-Y4~J@X5-Y6")), o1 = dev(G, o0.id);
  ok("벽(그리드)이 움직이면 벽 부착 콘센트가 따라감", o1.xy[0] === o0.xy[0] - 200 && o1.xy[1] === o0.xy[1], `(${o0.id} x ${o0.xy[0]} → ${o1.xy[0]})`);
  // 벽 삭제 → 고아
  G = fresh(); C.deleteEdgeKind(G, o0.host.edge, "wall");
  ok("벽 삭제 → 그 벽의 기구가 고아로 경고", dev(G, o0.id).orphan && C.warnings(ORIG, G).some(w => w.includes(o0.id) && w.includes("재배치")));
  // 문 추가 → 콘센트와 겹침
  G = fresh(); const oc = M.devices.find(x => x.type === "EO1" && x.host.edge === "J@X2-Y1~J@X5-Y1");
  C.addOpening(G, oc.host.edge, "door", oc.host.a, "DT4");
  ok("콘센트 자리에 문 추가 → 겹침 경고", C.warnings(ORIG, G).some(w => w.includes(oc.id) && w.includes("겹침")));
  // 기구 추가·삭제·이동
  G = fresh(); const nid = C.addDevice(G, "EL1", { x: X("X6") + 1000, y: 16000 });
  ok("구획 배치 기구 추가(가장 가까운 그리드 칸에 연결)", !!nid && dev(G, nid).host.kind === "bay" && dev(G, nid).xy[0] === X("X6") + 1000 && C.mepDiff(ORIG, G).added.length === 1, `(${nid} ${dev(G, nid).host.gx.join("~")})`);
  ok("덕트 타입은 기구로 추가 불가", C.addDevice(G, "MR1", { x: 0, y: 0 }) === null);
  C.deleteDevice(G, M.devices[0].id);
  ok("기구 삭제", C.mepDiff(ORIG, G).deleted.length === 1);
}

// --- 시연 시나리오 → 내보내기 ---
G = fresh(); const steps = C.demoScenario(G);
console.log("\n시연 시나리오:", steps.join(" / "));
const out = C.exportChanges(ORIG, G, "김기준");
const acts = out.map(c => c.action);
console.log("내보낸 동작:", acts.join(", "));
ok("내보내기: 모든 종류의 편집이 기록됨", ["move", "delete_opening", "delete_wall", "delete_column", "edit_opening", "add_column", "add_wall", "add_opening"].every(a => acts.includes(a)) && acts.filter(a => a === "add_opening").length === 2 && acts.filter(a => a === "edit_opening").length === 3);
ok("내보내기: 다른 도면에서 가져올 기호와 가상 타입이 함께 있음", out.some(c => c.params.donor && c.params.donor.sheet !== ORIG.sheet) && out.some(c => c.action === "add_opening" && !c.params.donor));
ok("내보내기: 모든 기록이 confirmed이고 좌표·핸들을 가짐", out.every(c => c.status === "confirmed") && out.find(c => c.action === "delete_opening").params.handles.length > 0 && out.find(c => c.action === "delete_column").params.handle);
fs.writeFileSync(path.join(outDir, "changes_demo.json"), JSON.stringify(out, null, 1));

// 왕복 검증용 기대값: 편집기의 최종 상태
const dd = C.diff(ORIG, G), N = C.idx(G.nodes), lab = n => n.grid.join("-");
const expected = {
  columns: G.nodes.filter(n => n.type === "column").map(n => ({ label: lab(n), xy: n.cxy || n.xy, spec: n.spec })),
  columns_deleted: dd.cols_deleted.map(c => ({ label: c.grid.join("-"), xy: c.xy })),
  walls_checked: [...dd.walls_added.map(e => ({ label: e.id, from_xy: e.from_xy, to_xy: e.to_xy, expect: true })), ...dd.walls_deleted.map(e => ({ label: e.id, from_xy: e.from_xy, to_xy: e.to_xy, expect: false }))],
  openings_checked: [...dd.openings_added.map(o => ({ id: o.id, type: o.type, xy: o.center, width: o.width, expect: true })),
    ...dd.openings.filter(o => o.edited).map(o => ({ id: o.id, type: o.type, xy: o.to_xy, width: o.to_w, expect: true })),
    ...dd.openings_deleted.map(o => { const p = ORIG.openings.find(x => x.id === o.id); return { id: o.id, type: o.type, xy: p.xy, width: p.width, expect: false }; })],
  dims_checked: dd.dims.map(x => ({ handle: x.handle, to: x.to })),
};
if (G.mep) {
  const M = dd.mep;
  expected.mep = { devices: G.mep.devices.map(x => ({ id: x.id, type: x.type, xy: x.xy })),
    checked: [...M.added.map(x => ({ id: x.id, xy: x.xy, expect: true, why: "추가한 기구" })), ...M.deleted.map(x => ({ id: x.id, xy: x.xy, expect: false, why: "삭제한 기구" })),
      ...M.moved.filter(x => x.edited).map(x => ({ id: x.id, xy: x.to, expect: true, why: "옮긴 기구" }))],
    routes: G.mep.routes.map(r => ({ id: r.id, handle: r.handle, pts: r.pts })) };
  ok("내보내기: 기구 재배치·추가·삭제가 기록됨", ["mep_relocate", "mep_add", "mep_delete"].every(a => acts.includes(a)));
  console.log("경고:", out[out.length - 1].warnings.length, "개");
  out[out.length - 1].warnings.forEach(w => console.log("   -", w));
}
fs.writeFileSync(path.join(outDir, "expected_demo.json"), JSON.stringify(expected, null, 1));

// 플러그인 PDF의 대상 "C1 #8E" 꼴(태그 + DXF 객체 핸들): 핸들이 이 도면의 기둥이면 바로 그 기둥, 아니면 태그로
{ const H = C.initModel(C.ORIG_GRAPH), col = H.nodes.find(n => n.type === "column" && n.handle), gy = col.grid[1], y0 = H.grids[gy].coord;
  const r1 = C.resolveInstruction(H, { target: `C1 #${col.handle.toLowerCase()}` });
  ok("핸들이 있는 지시: 태그 C1과 무관하게 그 핸들의 기둥을 찾음(대소문자 무시)", r1.node && r1.node.id === col.id && r1.by === "handle", JSON.stringify(r1.node && r1.node.id));
  const r2 = C.resolveInstruction(H, { target: "C1 #8E", tag: "C1", handle: "8E" });
  ok("핸들 #8E는 이 도면에 없음 → 타입 C1 기둥이 여러 개라 사람에게 남기고 핸들이 없다고 알림", r2.ask && r2.ask.includes("#8E") && r2.ask.includes("C1"), r2.ask);
  const a = C.applyInstruction(H, { target: `C1 #${col.handle}`, change: "Y +300 mm", action: "move", axis: "Y", delta: 300 });
  ok("핸들로 찾은 기둥의 Y +300: 그 기둥이 놓인 가로 그리드가 +300", a.ok && H.grids[gy].coord === y0 + 300, a.note); }
console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
