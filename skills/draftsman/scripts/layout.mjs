// Lay out a Draftsman graph JSON with ELK and write a standalone SVG.
//   node layout.mjs graph.json > diagram.svg
// Needs elkjs: `npm ci --prefix <skill>/scripts` (versions pinned by package-lock.json).
import fs from "node:fs";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const ELK = require("elkjs/lib/elk.bundled.js");
const draw = require("../assets/draw.js");

const graph = JSON.parse(fs.readFileSync(process.argv[2] || 0, "utf8"));
const elk = new ELK();
const laid = await elk.layout(draw.toElk(graph, { notes: true }));
process.stdout.write(draw.toSvg(graph, laid, { standalone: true }) + "\n");
