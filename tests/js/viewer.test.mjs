// Interaction tests for the single-file HTML viewer (assets/viewer.html), loaded
// into jsdom the way a browser opens it. Run by tests/test_frontend.py.
import { test, before } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const scripts = process.env.DRAFTSMAN_SCRIPTS;
const require = createRequire(path.join(scripts, "package.json"));
const { JSDOM, VirtualConsole } = require("jsdom");
const html = fs.readFileSync(process.env.DRAFTSMAN_VIEWER, "utf8");
const graph = JSON.parse(fs.readFileSync(process.env.DRAFTSMAN_GRAPH, "utf8"));

let window, document, errors;

async function waitFor(check, what, ms = 5000) {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    if (check()) return;
    await new Promise((r) => setTimeout(r, 10));
  }
  throw new Error("timed out waiting for " + what);
}
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];
const nodes = () => $$("#canvas > svg .node");
const nodeId = (label) => graph.nodes.find((n) => n.label === label).id;
const nodeEl = (label) => $(`#canvas > svg .node[data-id="${nodeId(label)}"]`);
const settled = () => waitFor(() => $("#status").hidden, "layout");
function tap(el) {   // what a pointer click on the canvas sends
  el.dispatchEvent(new window.MouseEvent("pointerdown", { bubbles: true }));
  el.dispatchEvent(new window.MouseEvent("pointerup", { bubbles: true }));
}
const key = (k, target = document.body) =>
  target.dispatchEvent(new window.KeyboardEvent("keydown", { key: k, bubbles: true }));

before(async () => {
  errors = [];
  const vc = new VirtualConsole();
  vc.on("jsdomError", (e) => { if (!/getContext|Not implemented/.test(e.message)) errors.push(e.message); });
  vc.on("error", (e) => errors.push(String(e)));
  const dom = new JSDOM(html, {
    runScripts: "dangerously", pretendToBeVisual: true, virtualConsole: vc,
    beforeParse(w) {
      w.matchMedia = () => ({ matches: false, addEventListener() {}, removeEventListener() {} });
      w.CSS = { escape: (s) => String(s).replace(/["\\]/g, "\\$&") };
      w.HTMLCanvasElement.prototype.getContext = () => null;
    },
  });
  window = dom.window; document = window.document;
  await waitFor(() => $("#canvas > svg") && $("#status").hidden, "first layout");
});

test("opens at the focus with the title block filled", () => {
  assert.equal($("#title").textContent, graph.title);
  const focus = $(`#canvas > svg .node.focus`);
  assert.equal(focus.dataset.id, graph.focus);
  const shown = $$("#side .tb .row .cell")[0].querySelector(".v").firstChild.textContent;
  assert.equal(Number(shown), nodes().length);
  assert.ok(nodes().length < graph.nodes.length, "starts focused, not with everything");
  assert.deepEqual(errors, []);
});

test("agent text is shown as text, never as markup", () => {
  assert.equal($$("img").length, 0);
  assert.ok($("#side").textContent.includes("<img src=x onerror=alert(1)>"));
});

test("selecting a class opens its detail and fades the rest", () => {
  tap(nodeEl("Order"));
  assert.match($("#side .tb .head .v").textContent, /^Order$/);
  assert.ok(nodeEl("Order").classList.contains("selected"));
  assert.ok($$("#canvas > svg .edge.hot").length > 0);
  const dim = nodes().filter((n) => n.classList.contains("dim")).map((n) => n.dataset.id);
  const neighbours = new Set(graph.edges.filter((e) => e.from === nodeId("Order") || e.to === nodeId("Order"))
    .flatMap((e) => [e.from, e.to]));
  assert.ok(dim.length > 0 && dim.every((d) => !neighbours.has(d)));
});

test("a relation in the detail panel goes to that class", () => {
  const row = $$("#side .rel").find((r) => r.querySelector(".rn").textContent.startsWith("OrderLine"));
  row.click();
  assert.match($("#side .tb .head .v").textContent, /^OrderLine$/);
});

test("Escape returns to the sheet", () => {
  key("Escape");
  assert.equal($("#side .tb .head .k").textContent, "Drawing");
  assert.equal($$("#canvas > svg .dim").length, 0);
});

test("search finds a class by part of its name and jumps to it", () => {
  const input = $("#search");
  input.value = "receipt";
  input.dispatchEvent(new window.Event("input"));
  const hits = $$("#results button").map((b) => b.querySelector(".rn").textContent);
  assert.ok(hits[0] === "Receipt" && hits.includes("Receipt.Money"));
  key("Enter", input);
  assert.match($("#side .tb .head .v").textContent, /^Receipt$/);
  assert.ok($("#results").hidden);
  key("Escape");
});

test("a kind row fades the other kinds", () => {
  $("#side tr[data-kind=interface]").click();
  for (const n of nodes()) {
    const kind = graph.nodes.find((g) => g.id === n.dataset.id).kind;
    assert.equal(n.classList.contains("dim"), kind !== "interface", n.dataset.id);
  }
  $("#side tr[data-kind=interface]").click();
  assert.equal($$("#canvas > svg .node.dim").length, 0);
});

test("short cycles are marked and the mark can be switched off", () => {
  assert.ok($$("#canvas > svg .edge.cycle").length > 0);
  $("#cycles").click();
  assert.equal($$("#canvas > svg .edge.cycle").length, 0);
  assert.equal($("#cycles").getAttribute("aria-pressed"), "false");
  $("#cycles").click();
});

test("dependencies can be hidden", async () => {
  assert.ok($$("#canvas > svg .edge.k-dependency").length > 0);
  $("#deps").click();
  await settled();
  assert.equal($$("#canvas > svg .edge.k-dependency:not(.inferred)").length, 0);
  $("#deps").click();
  await settled();
});

test("the members switch empties and refills the boxes", async () => {
  const on = $("#members").getAttribute("aria-pressed") === "true";
  assert.equal($$("#canvas > svg .member").length > 0, on);
  $("#members").click();
  await settled();
  assert.equal($$("#canvas > svg .member").length > 0, !on);
  $("#members").click();
  await settled();
});

test("hops widen the focus; All shows every class", async () => {
  const before = nodes().length;
  $("#hopsUp").click();
  await settled();
  assert.ok(nodes().length >= before);
  $("#modeAll").click();
  await settled();
  assert.equal(nodes().length, graph.nodes.length);
  assert.equal($("#modeAll").getAttribute("aria-pressed"), "true");
  assert.deepEqual(errors, []);
});
