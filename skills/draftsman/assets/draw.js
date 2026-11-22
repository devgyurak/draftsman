/*
 * Draftsman drawing code, shared by the static SVG renderer (scripts/layout.mjs,
 * run by node) and the interactive viewer (assets/viewer.html).
 *
 *   toElk(graph, opts)        -> ELK input graph (sizes, edges, groups, notes)
 *   toSvg(graph, laid, opts)  -> SVG markup for an ELK result
 *
 * The graph JSON comes from scripts/draftsman/graph.py. Nothing here decides
 * *what* to show; it only measures, places and draws.
 *
 * The look is a drafting sheet: ink on paper, UML boxes with a kind badge,
 * amber for the focus and the selection, red pencil for markup (highlights,
 * cycles) and blue pencil for construction lines (inferred edges), which are
 * not part of the measured drawing. A standalone SVG gets a sheet frame and a
 * title block.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.DraftsmanDraw = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const MONO = '"JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace';
  const FONT = "12px " + MONO;
  const CHAR_W = 7.3;
  const LINE_H = 16;
  const PAD_X = 12;
  const NAME_H = 30;
  const STEREO_H = 12;
  const BADGE = 15;             // kind badge diameter, left of the name
  const NOTE_CHARS = 38;

  const DIRECTIONS = { TB: "DOWN", BT: "UP", LR: "RIGHT", RL: "LEFT" };
  const BADGES = {
    class: "C", interface: "I", abstract_class: "A", enum: "E", record: "R", struct: "S", union: "U",
    object: "O", trait: "T", mixin: "M", annotation: "@",
  };

  function textWidth(s) {
    let w = 0;
    for (const ch of String(s)) w += ch.codePointAt(0) >= 0x1100 ? 1.9 : 1;
    return w * CHAR_W;
  }

  function esc(s) {
    return String(s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function wrap(text, width) {
    const out = [];
    for (const para of String(text).split("\n")) {
      let line = "";
      for (const word of para.split(/\s+/)) {
        if (line && (line + " " + word).length > width) { out.push(line); line = word; }
        else line = line ? line + " " + word : word;
      }
      out.push(line);
    }
    return out;
  }

  function headHeight(node) {
    return NAME_H + (node.stereotype ? STEREO_H : 0);
  }

  function nodeSize(node, expanded) {
    const members = expanded ? node.members : [];
    const badge = BADGES[node.kind] ? BADGE + 7 : 0;
    let w = textWidth(node.label) * 1.08 + badge;
    if (node.stereotype) w = Math.max(w, textWidth("«" + node.stereotype + "»") * 0.86);
    for (const m of members) w = Math.max(w, textWidth(m.text) * 0.96);
    const h = headHeight(node) + (members.length ? members.length * LINE_H + 12 : 0);
    return { width: Math.max(110, Math.ceil(w + 2 * PAD_X)), height: h };
  }

  function noteSize(text) {
    const lines = wrap(text, NOTE_CHARS);
    const w = Math.max(...lines.map(textWidth));
    return { lines, width: Math.ceil(w + 24), height: lines.length * LINE_H + 14 };
  }

  // inheritance is laid out parent-first, so the arrow is drawn reversed
  function reversed(edge) {
    return edge.kind === "extends" || edge.kind === "implements";
  }

  /**
   * opts: {
   *   visible: Set<id> | null      nodes to include (null = all)
   *   expanded: (id) => boolean    show members
   *   showInferred, showDependencies: booleans
   *   edge: (edge) => boolean       further edges to leave out (null = none)
   *   notes: boolean               draw notes as note boxes (static SVG)
   * }
   */
  function toElk(graph, opts) {
    opts = Object.assign({ visible: null, expanded: () => true, showInferred: true,
      showDependencies: true, notes: true, edge: null }, opts || {});
    const visible = (id) => !opts.visible || opts.visible.has(id);
    const byId = new Map(graph.nodes.map((n) => [n.id, n]));
    const groupOf = new Map();
    for (const g of graph.groups || []) for (const m of g.members) groupOf.set(m, g.name);

    const top = [];
    const groupNodes = new Map();
    for (const n of graph.nodes) {
      if (!visible(n.id)) continue;
      const size = nodeSize(n, opts.expanded(n.id));
      const elkNode = { id: n.id, width: size.width, height: size.height };
      const g = groupOf.get(n.id);
      if (g) {
        if (!groupNodes.has(g)) {
          const gn = { id: "group:" + g, children: [], labels: [{ text: g }],
            layoutOptions: { "elk.padding": "[top=34,left=16,bottom=16,right=16]" } };
          groupNodes.set(g, gn);
          top.push(gn);
        }
        groupNodes.get(g).children.push(elkNode);
      } else {
        top.push(elkNode);
      }
    }

    const edges = [];
    for (const e of graph.edges) {
      if (!visible(e.from) || !visible(e.to)) continue;
      if (e.inferred && !opts.showInferred) continue;
      if (e.kind === "dependency" && !e.inferred && !opts.showDependencies) continue;
      if (opts.edge && !opts.edge(e)) continue;
      const elkEdge = {
        id: e.id,
        sources: [reversed(e) ? e.to : e.from],
        targets: [reversed(e) ? e.from : e.to],
      };
      // UML puts a role name and its multiplicity at the end of the class they
      // describe (the target); an inferred edge keeps its tag in the middle
      const roleText = e.via ? (e.multiplicity ? `${e.via} ${e.multiplicity}` : e.via)
        : e.multiplicity;
      // a nested type's inheritance drawn between outer types says whose it is
      const label = e.inferred ? { text: "«inferred» " + e.kind, placement: "CENTER" }
        : e.label ? { text: e.label, placement: "CENTER" }
        : roleText ? { text: roleText, placement: "HEAD" } : null;
      if (label) {
        elkEdge.labels = [{ text: label.text, width: textWidth(label.text) * 0.92 + 4,
          height: 14, layoutOptions: { "elk.edgeLabels.placement": label.placement } }];
      }
      edges.push(elkEdge);
    }

    if (opts.notes) {
      (graph.notes || []).forEach((note, i) => {
        if (!visible(note.target) || !byId.has(note.target)) return;
        const s = noteSize(note.text);
        top.push({ id: "note:" + i, width: s.width, height: s.height });
        edges.push({ id: "noteedge:" + i, sources: ["note:" + i], targets: [note.target] });
      });
    }

    return {
      id: "root",
      layoutOptions: {
        "elk.algorithm": "layered",
        "elk.direction": DIRECTIONS[graph.direction] || "DOWN",
        "elk.hierarchyHandling": "INCLUDE_CHILDREN",
        "elk.edgeRouting": "ORTHOGONAL",
        // measured on real projects: shorter edges, fewer detours and crossings than
        // keeping the input order; the fixed seed keeps the output deterministic
        "elk.layered.considerModelOrder.strategy": "NONE",
        "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
        // extra crossing-minimisation passes pay off on readable sizes, not on
        // thousand-class dumps
        "elk.layered.thoroughness": top.length + edges.length > 600 ? "7" : "20",
        "elk.randomSeed": "1",
        "elk.layered.spacing.nodeNodeBetweenLayers": "56",
        "elk.spacing.nodeNode": "36",
        "elk.spacing.edgeNode": "18",
        "elk.spacing.edgeEdge": "12",
        "elk.spacing.edgeLabel": "4",
        "elk.edgeLabels.inline": "false",
        "elk.padding": "[top=24,left=24,bottom=24,right=24]",
      },
      children: top,
      edges: edges,
    };
  }

  // ------------------------------------------------------------------ SVG

  const LIGHT = "--paper:#FAF8F3;--box:#FFFFFF;--head:rgba(21,24,29,.035);--ink:#15181D;--ink2:#4A4F57;" +
    "--ink3:#8A8F96;--rule:rgba(21,24,29,.14);--line:#3A3F46;--amber:#D96A00;--red:#C23B2A;" +
    "--blue:#3A7FB0;--note:#FDF4E6;--noteline:#D9A766;--group:rgba(21,24,29,.022)";
  const DARK = "--paper:#15181D;--box:#1B1F25;--head:rgba(250,248,243,.04);--ink:#ECE8DF;--ink2:#A8ADB5;" +
    "--ink3:#6C727B;--rule:rgba(250,248,243,.14);--line:#B4B9C0;--amber:#EE8A2E;--red:#E0614F;" +
    "--blue:#6FA8D6;--note:#2A2418;--noteline:#8F6C3A;--group:rgba(250,248,243,.025)";

  const STYLE = `
.dm{${LIGHT}}
@media (prefers-color-scheme:dark){.dm:not(.light){${DARK}}}
.dm.dark{${DARK}}
.dm text{font:${FONT};fill:var(--ink)}
.dm .bg{fill:var(--paper)}
.dm .box{fill:var(--box);stroke:var(--line);stroke-width:1}
.dm .head{fill:var(--head)}
.dm .sep{stroke:var(--rule)}
.dm .name{font-weight:700;font-size:12.5px}
.dm .abstract .name,.dm .m-abstract{font-style:italic}
.dm .m-static{text-decoration:underline}
.dm .stereo{fill:var(--ink3);font-size:10px}
.dm .badge{fill:var(--box);stroke:var(--ink3);stroke-width:1}
.dm .badge-t{font-size:8.5px;font-weight:700;fill:var(--ink2)}
.dm .member{font-size:11.5px}
.dm .vis,.dm .mt{fill:var(--ink3)}
.dm .kind-external .box{fill:var(--paper);stroke:var(--ink3);stroke-dasharray:4 3}
.dm .kind-inferred .box{fill:var(--paper);stroke:var(--blue);stroke-dasharray:3 3}
.dm .kind-external .name{fill:var(--ink2);font-weight:500}
.dm .kind-inferred .name,.dm .kind-inferred .stereo{fill:var(--blue);font-weight:500}
.dm .cycle .box{stroke:var(--red);stroke-width:1.4}
.dm .highlight .box{stroke:var(--red);stroke-width:2.2}
.dm .focus .box{stroke:var(--amber);stroke-width:2.2}
.dm .selected .box{stroke:var(--amber);stroke-width:2.2;stroke-dasharray:none}
.dm .crop{fill:none;stroke:var(--amber);stroke-width:1.6}
.dm .match .box{stroke:var(--amber);stroke-width:2.2}
.dm .dim{opacity:.18}
.dm .notedot{fill:var(--amber)}
.dm .edge{fill:none;stroke:var(--line);stroke-width:1.1}
.dm .edge.k-implements,.dm .edge.k-dependency{stroke-dasharray:5 3.5}
.dm .edge.k-dependency{stroke:var(--ink3)}
.dm .edge.body{stroke-dasharray:1.5 3}
.dm .edge.inferred{stroke:var(--blue);stroke-dasharray:1.5 3.5;stroke-width:1.6;stroke-linecap:round}
.dm .edge.cycle{stroke:var(--red);stroke-width:1.5}
.dm .edge.hot{stroke:var(--amber);stroke-width:1.7;opacity:1}
.dm.hub .edge.hot{stroke-width:1;opacity:.55}
.dm .edge.note{stroke:var(--noteline);stroke-dasharray:2 3}
.dm .elabel{font-size:10.5px;fill:var(--ink2)}
.dm .elabel.inferred{fill:var(--blue)}
.dm .lbg{fill:var(--paper);opacity:.9}
.dm .lab.dim{opacity:.12}
.dm .lab.hot .elabel{fill:var(--amber)}
.dm .mk{fill:var(--line);stroke:var(--line)}
.dm .mk.open{fill:var(--box)}
.dm .mk.inf{fill:none;stroke:var(--blue)}
.dm .notebox{fill:var(--note);stroke:var(--noteline)}
.dm .groupbox{fill:var(--group);stroke:var(--ink3);stroke-dasharray:6 4}
.dm .gtab{fill:var(--paper);stroke:var(--ink3)}
.dm .gtitle{font-size:9.5px;font-weight:700;letter-spacing:.12em;fill:var(--ink2)}
.dm .sheet{fill:none;stroke:var(--ink);stroke-width:1.4}
.dm .trim,.dm .tick{fill:none;stroke:var(--ink3);stroke-width:.6}
.dm .tb{fill:var(--paper);stroke:var(--ink);stroke-width:1.4}
.dm .tbl{stroke:var(--ink);stroke-width:.6}
.dm .tbk{font-size:8px;letter-spacing:.14em;fill:var(--ink3)}
.dm .tbv{font-size:12.5px;font-weight:700}
.dm .tbt{font-size:15px;font-weight:700}
.dm .tbm{font-size:7px;letter-spacing:.16em;font-weight:700;fill:var(--ink2)}
.dm .hit{cursor:pointer}`;

  const DEFS = `<defs>
<marker id="dm-tri" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="13" markerHeight="13" orient="auto-start-reverse" markerUnits="userSpaceOnUse"><path class="mk open" d="M1,1 L11,6 L1,11 z"/></marker>
<marker id="dm-arrow" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="11" markerHeight="11" orient="auto-start-reverse" markerUnits="userSpaceOnUse"><path class="mk" style="fill:none" d="M1,1 L11,6 L1,11"/></marker>
<marker id="dm-arrow-inf" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="11" markerHeight="11" orient="auto-start-reverse" markerUnits="userSpaceOnUse"><path class="mk inf" d="M1,1 L11,6 L1,11"/></marker>
<marker id="dm-diamond" viewBox="0 0 16 10" refX="1" refY="5" markerWidth="16" markerHeight="10" orient="auto-start-reverse" markerUnits="userSpaceOnUse"><path class="mk" d="M1,5 L8,1 L15,5 L8,9 z"/></marker>
</defs>`;

  // the Draftsman mark (assets/logo/draftsman-symbol.svg), 256 units
  const MARK = '<path fill="#D96A00" fill-rule="evenodd" d="M128 39 L234 145 L22 145 Z M120.93 77.89 L81.39 117.43 Q74.32 124.5 84.32 124.5 L171.68 124.5 Q181.68 124.5 174.61 117.43 L135.07 77.89 Q128 70.82 120.93 77.89 Z"/>' +
    '<path style="fill:var(--ink)" d="M121.5 145 H134.5 V229 H121.5 Z"/>';

  function absolutePositions(laid) {
    const pos = new Map();
    (function walk(node, ox, oy) {
      for (const c of node.children || []) {
        const x = ox + (c.x || 0), y = oy + (c.y || 0);
        pos.set(c.id, { x, y, w: c.width, h: c.height, node: c });
        walk(c, x, y);
      }
    })(laid, 0, 0);
    return pos;
  }

  function collectEdges(laid) {
    const out = [];
    (function walk(node) {
      for (const e of node.edges || []) out.push(e);
      for (const c of node.children || []) walk(c);
    })(laid);
    return out;
  }

  function pathPoints(e, offset) {
    const pts = [];
    for (const s of e.sections || []) {
      pts.push(s.startPoint, ...(s.bendPoints || []), s.endPoint);
    }
    return pts.map((p) => ({ x: p.x + offset.x, y: p.y + offset.y }));
  }

  // "+ name(params): Type" -> visibility, name and the rest, so names stand out
  function memberSpans(text) {
    const m = /^([-+#~] )?([^(:]*)(.*)$/.exec(text);
    const vis = m[1] ? `<tspan class="vis">${esc(m[1])}</tspan>` : "";
    return `${vis}<tspan>${esc(m[2])}</tspan>${m[3] ? `<tspan class="mt">${esc(m[3])}</tspan>` : ""}`;
  }

  // registration-style corner marks around the selected class
  function cropMarks(w, h) {
    const o = 5, l = 9;
    return `<path class="crop" d="M${-o},${-o + l} V${-o} H${-o + l} M${w + o - l},${-o} H${w + o} V${-o + l}` +
      ` M${w + o},${h + o - l} V${h + o} H${w + o - l} M${-o + l},${h + o} H${-o} V${h + o - l}"/>`;
  }

  function drawNode(n, p, cls, expanded, noted) {
    const out = [];
    const classes = ["node", "kind-" + n.kind, n.abstract ? "abstract" : ""]
      .concat(cls).filter(Boolean).join(" ");
    const w = p.w, h = p.h;
    out.push(`<g class="${classes}" data-id="${esc(n.id)}" transform="translate(${p.x},${p.y})">`);
    if (cls.includes("selected")) out.push(cropMarks(w, h));
    const headH = headHeight(n);
    out.push(`<rect class="box" width="${w}" height="${h}" rx="2"/>`);
    out.push(`<path class="head" d="M1,${headH} V3 Q1,1 3,1 H${w - 3} Q${w - 1},1 ${w - 1},3 V${headH} Z"/>`);
    let y = 19;
    if (n.stereotype) {
      out.push(`<text class="stereo" x="${w / 2}" y="${y - 2}" text-anchor="middle">«${esc(n.stereotype)}»</text>`);
      y += STEREO_H;
    }
    const letter = BADGES[n.kind];
    const nameW = textWidth(n.label) * 1.08;
    if (letter) {
      // badge and name are centred together
      const left = (w - (BADGE + 7 + nameW)) / 2;
      const cx = left + BADGE / 2, cy = y - 4.5;
      out.push(`<circle class="badge" cx="${cx}" cy="${cy}" r="${BADGE / 2}"/>` +
        `<text class="badge-t" x="${cx}" y="${cy + 3}" text-anchor="middle">${letter}</text>`);
      out.push(`<text class="name" x="${left + BADGE + 7}" y="${y}">${esc(n.label)}</text>`);
    } else {
      out.push(`<text class="name" x="${w / 2}" y="${y}" text-anchor="middle">${esc(n.label)}</text>`);
    }
    if (noted) out.push(`<circle class="notedot" cx="${w - 9}" cy="9" r="3"><title>has a note</title></circle>`);
    const members = expanded ? n.members : [];
    if (members.length) {
      out.push(`<line class="sep" x1="0" x2="${w}" y1="${headH}" y2="${headH}"/>`);
      let my = headH + 6 + 12;
      for (const m of members) {
        const mc = ["member", m.static ? "m-static" : "", m.abstract ? "m-abstract" : ""].join(" ").trim();
        out.push(`<text x="${PAD_X}" y="${my}" class="${mc}">${memberSpans(m.text)}</text>`);
        my += LINE_H;
      }
    }
    out.push(`<rect class="hit" width="${w}" height="${h}" fill="transparent"/>`);
    out.push("</g>");
    return out.join("");
  }

  // sheet frame and title block around a standalone drawing
  const SHEET = { margin: 14, pad: 18, tbH: 64, markW: 64 };

  function titleBlock(graph, x, y, w) {
    const s = SHEET, h = s.tbH;
    const types = graph.nodes.filter((n) => n.kind !== "external" && n.kind !== "inferred").length;
    const facts = graph.edges.filter((e) => !e.inferred).length;
    const inferred = graph.edges.length - facts;
    const scope = scopeText(graph);
    const cells = [["CLASSES", String(types)], ["RELATIONS", facts + (inferred ? ` +${inferred}` : "")],
      ["SCOPE", scope]];
    const cw = (w - s.markW) / cells.length;
    const out = [`<g class="titleblock" transform="translate(${x},${y})">`,
      `<rect class="tb" width="${w}" height="${h}"/>`,
      `<line class="tbl" x1="${s.markW}" y1="0" x2="${s.markW}" y2="${h}"/>`,
      `<line class="tbl" x1="${s.markW}" y1="33" x2="${w}" y2="33"/>`,
      `<g transform="translate(${s.markW / 2 - 19},2) scale(0.148)">${MARK}</g>`,
      `<text class="tbm" x="${s.markW / 2}" y="${h - 7}" text-anchor="middle">DRAFTSMAN</text>`,
      `<text class="tbk" x="${s.markW + 8}" y="11">TITLE</text>`,
      `<text class="tbt" x="${s.markW + 8}" y="27">${esc(graph.title || "Class diagram")}</text>`];
    cells.forEach(([k, v], i) => {
      const cx = s.markW + i * cw;
      if (i) out.push(`<line class="tbl" x1="${cx}" y1="33" x2="${cx}" y2="${h}"/>`);
      out.push(`<text class="tbk" x="${cx + 8}" y="43">${k}</text>` +
        `<text class="tbv" x="${cx + 8}" y="${h - 7}">${esc(v)}</text>`);
    });
    out.push("</g>");
    return out.join("");
  }

  // what the sheet covers: the focus and its radius, and whether nested types are
  // drawn inside their outer types
  function scopeText(graph) {
    const focus = graph.focus && graph.nodes.find((n) => n.id === graph.focus);
    const folded = graph.nodes.some((n) => (n.folded || []).length);
    return (focus ? `${focus.label} ±${graph.hops}` : "all") + (folded ? " · nested folded" : "");
  }

  function tbWidth(graph) {
    const title = textWidth(graph.title || "Class diagram") * 1.2;
    const scope = graph.focus || graph.nodes.some((n) => (n.folded || []).length)
      ? textWidth(scopeText(graph).replace(/±\d+/, "±0")) * 3 : 0;
    return Math.ceil(Math.max(340, SHEET.markW + title + 24, SHEET.markW + scope + 40));
  }

  /**
   * opts: { expanded, focus, selected, highlightCycles, dimmed: Set<id>,
   *         noted: Set<id>, theme: "light" | "dark",
   *         standalone (paper background, sheet frame and title block) }
   */
  function toSvg(graph, laid, opts) {
    opts = Object.assign({ expanded: () => true, highlightCycles: true }, opts || {});
    const byId = new Map(graph.nodes.map((n) => [n.id, n]));
    const edgeById = new Map(graph.edges.map((e) => [e.id, e]));
    const pos = absolutePositions(laid);
    const highlighted = new Set((graph.highlights || []).map((h) => h.target));
    const cycleNodes = new Set();
    const cycleOf = new Map();
    (graph.cycles || []).forEach((c, i) => c.forEach((id) => { cycleNodes.add(id); cycleOf.set(id, i); }));
    const focus = opts.focus !== undefined ? opts.focus : graph.focus;

    const DW = Math.ceil(laid.width || 100), DH = Math.ceil(laid.height || 100);
    let W = DW, H = DH, ox = 0, oy = 0, tbw = 0;
    if (opts.standalone) {
      const s = SHEET;
      tbw = tbWidth(graph);
      W = Math.max(DW, tbw) + 2 * (s.margin + s.pad);
      H = DH + s.tbH + s.pad + 2 * (s.margin + s.pad);
      ox = s.margin + s.pad + Math.max(0, (W - 2 * (s.margin + s.pad) - DW) / 2);
      oy = s.margin + s.pad;
    }
    const parts = [];
    parts.push(`<svg xmlns="http://www.w3.org/2000/svg" class="dm${opts.theme ? " " + opts.theme : ""}" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">`);
    parts.push(`<style>${STYLE}</style>${DEFS}`);
    if (opts.standalone) {
      const m = SHEET.margin;
      parts.push(`<rect class="bg" width="${W}" height="${H}"/>`);
      parts.push(`<rect class="trim" x="4.5" y="4.5" width="${W - 9}" height="${H - 9}"/>`);
      parts.push(`<rect class="sheet" x="${m}" y="${m}" width="${W - 2 * m}" height="${H - 2 * m}"/>`);
      // centring marks on each side, as on a printed sheet
      parts.push(`<path class="tick" d="M${W / 2},4.5 V${m} M${W / 2},${H - 4.5} V${H - m} M4.5,${H / 2} H${m} M${W - 4.5},${H / 2} H${W - m}"/>`);
      parts.push(titleBlock(graph, W - m - tbw, H - m - SHEET.tbH, tbw));
    }
    parts.push(`<g class="viewport"${opts.standalone ? ` transform="translate(${ox},${oy})"` : ""}>`);

    // groups: a dashed zone with its name on a tab
    for (const [id, p] of pos) {
      if (!id.startsWith("group:")) continue;
      const title = id.slice(6).toUpperCase();
      const tw = textWidth(title) * 0.95 + 16;
      parts.push(`<g class="group"><rect class="groupbox" x="${p.x}" y="${p.y}" width="${p.w}" height="${p.h}" rx="2"/>` +
        `<rect class="gtab" x="${p.x + 10}" y="${p.y - 8}" width="${tw}" height="16" rx="1"/>` +
        `<text class="gtitle" x="${p.x + 18}" y="${p.y + 3.5}">${esc(title)}</text></g>`);
    }

    // edges
    const labels = [];
    for (const le of collectEdges(laid)) {
      const container = le.container && le.container !== "root" ? pos.get(le.container) : null;
      const offset = container ? { x: container.x, y: container.y } : { x: 0, y: 0 };
      let pts = pathPoints(le, offset);
      if (pts.length < 2) continue;
      if (le.id.startsWith("noteedge:")) {
        parts.push(`<path class="edge note" d="${pts.map((p, i) => (i ? "L" : "M") + p.x + "," + p.y).join(" ")}"/>`);
        continue;
      }
      const e = edgeById.get(le.id);
      if (!e) continue;
      if (reversed(e)) pts = pts.slice().reverse();
      const d = pts.map((p, i) => (i ? "L" : "M") + p.x.toFixed(1) + "," + p.y.toFixed(1)).join(" ");
      const inCycle = opts.highlightCycles && e.kind !== "extends" && e.kind !== "implements" &&
        cycleOf.has(e.from) && cycleOf.get(e.from) === cycleOf.get(e.to);
      const cls = ["edge", "k-" + e.kind, e.inferred ? "inferred" : "", e.body ? "body" : "",
        inCycle ? "cycle" : "",
        opts.dimmed && (opts.dimmed.has(e.from) || opts.dimmed.has(e.to)) ? "dim" : ""]
        .filter(Boolean).join(" ");
      let markers;
      if (e.inferred) markers = ` marker-end="url(#dm-arrow-inf)"`;
      else if (e.kind === "extends" || e.kind === "implements") markers = ` marker-end="url(#dm-tri)"`;
      else if (e.kind === "association" && e.ownership === "owned")
        markers = ` marker-start="url(#dm-diamond)" marker-end="url(#dm-arrow)"`;
      else markers = ` marker-end="url(#dm-arrow)"`;
      const title = e.inferred ? `inferred: ${e.rationale || ""}` :
        `${e.kind}${e.body ? " from a body" : ""}${e.via ? " (" + e.via + ")" : ""} — ${e.location || ""}`;
      const ends = ` data-from="${esc(e.from)}" data-to="${esc(e.to)}"`;
      parts.push(`<path class="${cls}" d="${d}"${markers} data-edge="${esc(e.id)}"${ends}><title>${esc(title)}</title></path>`);
      const dim = opts.dimmed && (opts.dimmed.has(e.from) || opts.dimmed.has(e.to)) ? " dim" : "";
      for (const l of le.labels || []) {
        // a background box keeps crossing edges from cutting through the text
        const lx = l.x + offset.x, ly = l.y + offset.y;
        labels.push(`<g class="lab${dim}"${ends}><rect class="lbg" x="${(lx - 1).toFixed(1)}" y="${(ly - 1).toFixed(1)}" width="${(l.width + 4).toFixed(1)}" height="${(l.height + 2).toFixed(1)}" rx="1"/>` +
          `<text class="elabel${e.inferred ? " inferred" : ""}" x="${(lx + 2).toFixed(1)}" y="${(ly + 11).toFixed(1)}">${esc(l.text)}</text></g>`);
      }
      if (e.multiplicity && !(le.labels || []).length) {
        const a = pts[pts.length - 1], b = pts[pts.length - 2];
        const dx = Math.sign(b.x - a.x), dy = Math.sign(b.y - a.y);
        const x = a.x + dx * 14 + (dy !== 0 ? 6 : 0);
        const y = a.y + dy * 16 + (dx !== 0 ? -5 : 4);
        labels.push(`<text class="elabel" x="${x.toFixed(1)}" y="${y.toFixed(1)}">${esc(e.multiplicity)}</text>`);
      }
    }

    // nodes
    for (const [id, p] of pos) {
      if (id.startsWith("group:")) continue;
      if (id.startsWith("note:")) {
        const note = graph.notes[Number(id.slice(5))];
        const s = noteSize(note.text);
        const f = 10;
        parts.push(`<g class="note"><path class="notebox" d="M${p.x},${p.y} H${p.x + p.w - f} L${p.x + p.w},${p.y + f} V${p.y + p.h} H${p.x} Z M${p.x + p.w - f},${p.y} V${p.y + f} H${p.x + p.w}"/>` +
          s.lines.map((line, i) => `<text x="${p.x + 10}" y="${p.y + 19 + i * LINE_H}">${esc(line)}</text>`).join("") + "</g>");
        continue;
      }
      const n = byId.get(id);
      if (!n) continue;
      const cls = [
        id === focus ? "focus" : "",
        highlighted.has(id) ? "highlight" : "",
        opts.highlightCycles && cycleNodes.has(id) ? "cycle" : "",
        opts.selected === id ? "selected" : "",
        opts.dimmed && opts.dimmed.has(id) ? "dim" : "",
      ];
      parts.push(drawNode(n, p, cls, opts.expanded(id), opts.noted && opts.noted.has(id)));
    }
    parts.push(labels.join(""));
    parts.push("</g></svg>");
    return parts.join("\n");
  }

  return { toElk, toSvg, nodeSize, textWidth, wrap, BADGES, FONT };
});
