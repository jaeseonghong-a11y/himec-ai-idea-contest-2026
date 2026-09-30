// CAD 플러그인의 JSON이 관계도에 연결될 때 자동 이동 없이 대상만 찾는 계약 검사.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const html = fs.readFileSync(path.join(__dirname, "template.html"), "utf8");
const startTag = '<script id="core">';
const start = html.indexOf(startTag) + startTag.length;
assert(start >= startTag.length, "core script missing");
const core = html.slice(start, html.indexOf("</script>", start));
const context = { module: { exports: {} } };
vm.createContext(context);
vm.runInContext(core, context);
const C = context.module.exports;

const sample = JSON.parse(fs.readFileSync(path.join(__dirname, "../../../autocad-plugin/tests/final_plug_in_test.json"), "utf8"));
const graph = {
  sheet: "pdf-test.dxf",
  nodes: [{ id: "C@X1-Y2", type: "column", handle: "8E", grid: ["X1", "Y2"], ctype: "C1" }],
  grids: { X1: { coord: 0 }, Y2: { coord: 0 } },
};
const before = JSON.stringify(graph);
const items = C.loadInstructions(graph, sample.items, sample);
assert.equal(JSON.stringify(graph), before, "import must not alter the drawing");
assert.equal(items.length, 2);
assert.equal(items[0].applied, false);
assert.equal(C.instructionTarget(graph, items[0], null).node.id, "C@X1-Y2");
assert.equal(C.instructionTarget(graph, items[1], null).ask.includes("직접"), true);

const wrongDrawing = C.loadInstructions(graph, sample.items, { ...sample, drawing: "other.dwg" });
assert.match(wrongDrawing[0].sourceWarning, /다릅니다/);
assert(C.instructionTarget(graph, wrongDrawing[0], null).ask);
assert.equal(C.instructionTarget(graph, wrongDrawing[0], { node: graph.nodes[0] }).node.id, "C@X1-Y2");

const wrongGrid = { ...sample.items[0], grid: "X2-Y2" };
assert(C.resolveInstruction(graph, wrongGrid).ask);
assert.throws(() => C.loadInstructions(graph, sample.items, { ...sample, units: "cm" }), /mm/);
console.log("CAD instruction JSON import checks passed");
