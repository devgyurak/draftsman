// The viewer's body relations follow scene.py's rules as the reader moves the focus: those
// touching the focus are drawn, and the class at their other end leads nowhere.
// Run by tests/test_frontend.py on a viewer of tests/test_body_relations.py's _AROUND.
import { test, before } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(path.join(process.env.DRAFTSMAN_SCRIPTS, "package.json"));
const { JSDOM, VirtualConsole } = require("jsdom");
const html = fs.readFileSync(process.env.DRAFTSMAN_VIEWER, "utf8");
let document, window;

async function waitFor(check, what, ms = 5000) {
  const end = Date.now() + ms;
  while (Date.now() < end) { if (check()) return; await new Promise((r) => setTimeout(r, 10)); }
  throw new Error("timed out waiting for " + what);
}
const shown = () => [...document.querySelectorAll("#canvas > svg .node")]
  .map((n) => n.dataset.id.split(".").pop()).sort();
const settled = () => waitFor(() => document.querySelector("#status").hidden, "layout");

before(async () => {
  const dom = new JSDOM(html, {
    runScripts: "dangerously", pretendToBeVisual: true, virtualConsole: new VirtualConsole(),
    beforeParse(w) {
      w.matchMedia = () => ({ matches: false, addEventListener() {}, removeEventListener() {} });
      w.CSS = { escape: (s) => String(s).replace(/["\\]/g, "\\$&") };
      w.HTMLCanvasElement.prototype.getContext = () => null;
    },
  });
  window = dom.window; document = window.document;
  await waitFor(() => document.querySelector("#canvas > svg") && document.querySelector("#status").hidden, "first layout");
});

const edges = () => [...document.querySelectorAll("#canvas > svg .edge.body")]
  .map((e) => [e.dataset.from, e.dataset.to].map((id) => id.split(".").pop()).join(">")).sort();

test("a body relation of the focus draws its other end, and no further", async () => {
  // focus F, 2 hops: G only through F's body (its field H is not followed), U names F in
  // its body, K holds an F; K's body names G, which does not touch F
  assert.deepEqual(shown(), ["F", "G", "K", "U"]);
  assert.deepEqual(edges(), ["F>G", "U>F"]);
});

test("moving the focus moves the body relations with it", async () => {
  window.eval('state.focus = "p.G"; relayout(true);');
  await settled();
  assert.deepEqual(shown(), ["F", "G", "H", "K"]);
  assert.deepEqual(edges(), ["F>G", "K>G"]);
});

test("the toggle leaves them out", async () => {
  document.querySelector("#bodies").click();
  await settled();
  assert.deepEqual(shown(), ["G", "H"]);
  assert.deepEqual(edges(), []);
});
