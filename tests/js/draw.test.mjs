// Unit tests for assets/draw.js (layout input and SVG output), run by
// tests/test_frontend.py with node's test runner.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const scripts = process.env.DRAFTSMAN_SCRIPTS;
const require = createRequire(path.join(scripts, "package.json"));
const ELK = require("elkjs/lib/elk.bundled.js");
const D = require(path.join(scripts, "..", "assets", "draw.js"));
const graph = JSON.parse(fs.readFileSync(process.env.DRAFTSMAN_GRAPH, "utf8"));

const node = (label) => graph.nodes.find((n) => n.label === label);
const id = (label) => node(label).id;
const edge = (from, kind, to) =>
  graph.edges.find((e) => e.from === id(from) && e.kind === kind && e.to === id(to));
const layout = (g, opts) => new ELK().layout(D.toElk(g, opts));
const count = (s, needle) => s.split(needle).length - 1;

// a tiny hand-made graph for cases the shop fixture does not have
function tiny(edges, extra = {}) {
  const nodes = ["A", "B", "C"].map((n) => ({ id: n, label: n, kind: "class", members: [],
    stereotype: null, abstract: false, annotations: [] }));
  return { title: "tiny", nodes, edges: edges.map((e, i) => ({ id: "e" + i, multiplicity: null,
    ownership: null, via: null, inferred: false, ...e })), groups: [], notes: [], highlights: [],
    cycles: [], ...extra };
}

test("inheritance is laid out parent first; the arrow is drawn back to the child", () => {
  const e = edge("Customer", "extends", "BaseEntity");
  const elkEdge = D.toElk(graph).edges.find((x) => x.id === e.id);
  assert.deepEqual(elkEdge.sources, [e.to]);
  assert.deepEqual(elkEdge.targets, [e.from]);
});

test("role names sit at the target end, inferred tags in the middle", () => {
  const edges = D.toElk(graph).edges;
  const lines = edges.find((x) => x.id === edge("Order", "association", "OrderLine").id);
  assert.equal(lines.labels[0].text, "lines *");
  assert.equal(lines.labels[0].layoutOptions["elk.edgeLabels.placement"], "HEAD");
  const inferred = edges.find((x) => graph.edges.find((e) => e.id === x.id)?.inferred);
  assert.match(inferred.labels[0].text, /^«inferred» /);
  assert.equal(inferred.labels[0].layoutOptions["elk.edgeLabels.placement"], "CENTER");
});

test("a nested type's folded inheritance is labelled in the middle of the arrow", () => {
  const g = tiny([{ from: "A", to: "B", kind: "dependency", label: "Acc implements" }]);
  const [edge] = D.toElk(g, {}).edges;
  assert.equal(edge.labels[0].text, "Acc implements");
  assert.equal(edge.labels[0].layoutOptions["elk.edgeLabels.placement"], "CENTER");
});

test("dependencies, inferred edges and invisible classes can be left out", () => {
  const kindOf = (x) => graph.edges.find((e) => e.id === x.id);
  const noDeps = D.toElk(graph, { showDependencies: false }).edges.map(kindOf).filter(Boolean);
  assert.ok(noDeps.every((e) => e.kind !== "dependency" || e.inferred));
  const noInf = D.toElk(graph, { showInferred: false }).edges.map(kindOf).filter(Boolean);
  assert.ok(noInf.every((e) => !e.inferred));
  const visible = new Set([id("Order"), id("OrderLine")]);
  const some = D.toElk(graph, { visible });
  const ids = some.children.flatMap((c) => c.children ? c.children.map((x) => x.id) : [c.id]);
  assert.deepEqual(new Set(ids.filter((i) => !i.startsWith("note:"))), visible);
  assert.ok(some.edges.every((e) => visible.has(e.sources[0]) || e.id.startsWith("noteedge:")));
});

test("groups wrap their members; notes become boxes only when asked", () => {
  const g = { ...graph, groups: [{ name: "ordering", members: [id("Order"), id("OrderLine")] }] };
  const elk = D.toElk(g, { notes: false });
  const group = elk.children.find((c) => c.id === "group:ordering");
  assert.deepEqual(group.children.map((c) => c.id).sort(), [id("Order"), id("OrderLine")].sort());
  assert.ok(!elk.children.some((c) => c.id.startsWith("note:")));
  assert.ok(D.toElk(g, { notes: true }).children.some((c) => c.id.startsWith("note:")));
});

test("box sizes follow content: members, badge and stereotype", () => {
  const order = node("Order");
  const open = D.nodeSize(order, true), shut = D.nodeSize(order, false);
  assert.ok(open.height > shut.height && open.width >= shut.width);
  const iface = node("PaymentGateway");
  assert.ok(D.nodeSize(iface, false).height > D.nodeSize({ ...iface, stereotype: null }, false).height);
});

test("a standalone SVG is a sheet with a title block; the viewer's is bare", async () => {
  const laid = await layout(graph, { notes: true });
  const sheet = D.toSvg(graph, laid, { standalone: true });
  assert.ok(sheet.includes('class="sheet"') && sheet.includes('class="titleblock"'));
  assert.ok(sheet.includes("OrderService ±1 · nested folded"));
  const bare = D.toSvg(graph, laid, {});
  assert.ok(!bare.includes('class="sheet"') && !bare.includes('class="titleblock"'));
  assert.equal(count(bare, 'class="node '), graph.nodes.length);
  assert.ok(D.toSvg(graph, laid, { theme: "dark" }).includes('class="dm dark"'));
});

test("user text is escaped everywhere it is drawn", async () => {
  const laid = await layout(graph, { notes: true });
  const svg = D.toSvg(graph, laid, { standalone: true });
  assert.ok(!svg.includes("<img"), "note text must not become markup");
  assert.ok(svg.includes("&lt;img"));
  assert.ok(svg.includes(graph.title.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")));
});

test("UML markers follow the relation kind", async () => {
  const g = tiny([{ from: "A", to: "B", kind: "extends" }, { from: "B", to: "C", kind: "association", ownership: "owned" },
    { from: "A", to: "C", kind: "dependency" }, { from: "C", to: "A", kind: "association", inferred: true, rationale: "r" }]);
  const svg = D.toSvg(g, await layout(g), {});
  const path = (eid) => svg.split("\n").find((l) => l.includes(`data-edge="${eid}"`));
  assert.match(path("e0"), /marker-end="url\(#dm-tri\)"/);
  assert.match(path("e1"), /marker-start="url\(#dm-diamond\)"/);
  assert.match(path("e2"), /class="edge k-dependency"/);
  assert.match(path("e3"), /class="edge k-association inferred".*marker-end="url\(#dm-arrow-inf\)"/);
});

test("cycles mark associations and dependencies, never inheritance", async () => {
  const g = tiny([{ from: "A", to: "B", kind: "association" }, { from: "B", to: "A", kind: "dependency" },
    { from: "A", to: "B", kind: "extends" }], { cycles: [["A", "B"]] });
  const laid = await layout(g);
  const svg = D.toSvg(g, laid, {});
  const line = (eid) => svg.split("\n").find((l) => l.includes(`data-edge="${eid}"`));
  assert.match(line("e0"), /\bcycle\b/);
  assert.match(line("e1"), /\bcycle\b/);
  assert.doesNotMatch(line("e2"), /\bcycle\b/);
  assert.ok(!D.toSvg(g, laid, { highlightCycles: false }).includes(" cycle"));
});

test("selection, fading and notes are drawn on the right classes", async () => {
  const laid = await layout(graph, { notes: false });
  const order = id("Order"), line = id("OrderLine");
  const svg = D.toSvg(graph, laid, { selected: order, dimmed: new Set([line]), noted: new Set([order]) });
  const group = (nid) => svg.split("\n").find((l) => l.includes(`data-id="${nid}"`));
  assert.match(group(order), /\bselected\b/);
  assert.match(group(order), /class="crop"/);
  assert.match(group(order), /class="notedot"/);
  assert.match(group(line), /\bdim\b/);
  assert.equal(count(svg, 'class="crop"'), 1);
});

test("member names stand apart from their types", async () => {
  const laid = await layout(graph, { notes: false });
  const svg = D.toSvg(graph, laid, {});
  assert.ok(svg.includes('<tspan class="vis">- </tspan><tspan>lines</tspan><tspan class="mt">: List&lt;OrderLine&gt;</tspan>'));
});

test("the same graph always gives the same drawing", async () => {
  const a = D.toSvg(graph, await layout(graph), { standalone: true });
  const b = D.toSvg(graph, await layout(graph), { standalone: true });
  assert.equal(a, b);
});
