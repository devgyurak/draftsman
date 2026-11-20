// The viewer's own neighbourhood (focus and hops changed by the reader) follows the same
// rules as scene.py: annotations lead one way, nested boxes start with their outer type.
// Run by tests/test_frontend.py on a viewer of a small annotated project.
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

test("an annotation does not lead back to the other classes that carry it", async () => {
  // focus A, 3 hops: A -@Mark-> Mark; B only carries @Mark too; C uses Mark in a signature
  assert.deepEqual(shown(), ["A", "C", "D", "Mark"]);
});

test("the focus itself sees the classes that carry its annotation", async () => {
  document.querySelector("#hopsDown").click(); document.querySelector("#hopsDown").click();
  window.eval('state.focus = "p.Mark"; relayout(true);');
  await settled();
  assert.deepEqual(shown(), ["A", "B", "C", "Mark"]);
});
