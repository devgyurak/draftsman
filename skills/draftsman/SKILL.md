---
name: draftsman
description: Draws UML class diagrams from Java, C#, Kotlin, TypeScript, Python or C++ source where every class and relation comes from a tree-sitter parser, never from guessing. Outputs Mermaid, a static SVG, or a single-file interactive HTML viewer. Use when the user asks for a class diagram, a structure/architecture diagram of classes, inheritance or dependency relationships between classes, or says things like "클래스 다이어그램", "구조 그려줘", "상속 관계 보여줘".
---

# Draftsman

The parser measures, you draft. `extract.py` turns source into **ir.json** (facts).
You decide what to show by writing **view.json** (editorial choices). `render.py`
merges the two. You never edit ir.json and never write diagram text by hand.

All paths below are relative to this skill's directory.

## Hard rules

1. **No invented relations.** Every line in the diagram must come from ir.json. If you
   believe a relation exists that ir.json lacks, it may only go in `inferred_edges`, with a
   `rationale`; the renderer draws it dotted and labelled «inferred». `render.py` rejects
   inferred edges whose endpoints are not ir.json types, externals, or unresolved names.
2. **No hand-written diagrams.** If the output is wrong, change view.json and re-render.
   If the facts are wrong, that is an extractor bug: tell the user, do not patch the output.
3. **Report what you left out.** Mention hidden types/members and list unresolved
   references at the end of your answer, by reason: *ambiguous* ones (a project type has
   the name) and *unexplained* ones one by one, *outside* ones as a group.

## Setup (once per session)

```bash
python3 -c "import tree_sitter, tree_sitter_language_pack, yaml" \
  || pip install "tree-sitter>=0.25" tree-sitter-language-pack pyyaml
```

If `pip` is unavailable or blocked, prefix every Python command with
`uv run --with "tree-sitter>=0.25" --with tree-sitter-language-pack --with pyyaml`.
In a sandbox without network access (e.g. Codex's default), request permission for the
install command or ask the user to run it; do not fall back to drawing by hand.

SVG output and Mermaid validation also need node: `npm ci --prefix scripts` once
(installs elkjs, mermaid, jsdom into `scripts/node_modules`). HTML output works without
it (the viewer then loads its layout library from a CDN).

Keep ir.json, view.json and the output in a scratch directory (`$WORK` below), not in
the user's repository, unless the user asks for a file there.

## Workflow

1. **Target.** Confirm the source path. Languages: Java, C#, Kotlin, TypeScript (incl.
   TSX), Python, C++. For anything else, say it is not supported rather than reading the
   code and drawing a diagram yourself.
2. **Extract.**
   ```bash
   python3 scripts/extract.py <path> -o $WORK/ir.json --exclude '**/test/**' --exclude '**/tests/**'
   ```
   Drop the excludes if the user wants test classes; add `--lang <name>` in mixed
   repositories (e.g. a Kotlin app with Java tests), and more excludes for generated code
   (`'**/Migrations/**'`, `'**/*.spec.ts'`, `'third_party/**'`). `--wrappers file.yaml`
   adds project-specific container types (format: `config/wrappers.yaml`).
3. **Survey.** `python3 scripts/summary.py $WORK/ir.json` — counts, namespaces, the
   most connected types, annotations, unresolved references, parse diagnostics.
   `--type Name` (repeatable) prints one type's members and incoming/outgoing
   relations; use it instead of reading ir.json, which gets large.
4. **Scope.**
   - ≤ 30 types: draw everything (no `focus`).
   - More: use the class the user named as `focus` with `hops: 2` (reduce to 1, or
     restrict `relations` to `["extends","implements","association"]`, if still over
     ~30 types). If they named none, show the top connected types from the summary and
     ask which one to centre on — or offer the HTML viewer, which lets them explore.
5. **Choose the output** (`output` in view.json, or `--format`):
   - documentation, README, PR description, chat answer → `mermaid` (default)
   - "show me", "let me explore", onboarding, or more than ~50 classes → `html`
   - an image to embed or put on a slide → `svg`
6. **Write view.json** (schema: `references/view-schema.md`). Decide:
   - `hidden`: noise for this diagram's purpose — `*#get*`, `*#set*`, `*#toString`,
     `*#equals`, `*#hashCode`, DTO/mapper packages, framework boilerplate. Prefer
     `members: "public"` or `"none"` over long hide lists when the diagram is about
     structure rather than API. Per class: `{"*": "none", "OrderService": "all"}`
     (last match wins) — e.g. full detail for the focus, names only around it.
   - `groups`: meaningful clusters (domain areas, layers), not just packages.
   - `notes` / `highlights`: design smells you can point to *in the facts* — cycles,
     deep inheritance, god classes (many associations), interfaces with one implementor.
     In HTML they appear in the side panel next to the diagram.
   - `inferred_edges`: only for entries in ir.json's `unresolved` list, with a rationale
     citing the import or naming evidence.
   - `externals: true` when framework base classes matter (e.g. Spring repositories).
7. **Render.**
   ```bash
   python3 scripts/render.py $WORK/ir.json $WORK/view.json -o $WORK/diagram.<mmd|svg|html>
   ```
   Fix any `view error` and heed warnings (a hidden pattern that matched nothing is
   usually a typo). Exit code 2 means a missing dependency; the message says which.
8. **Validate Mermaid.** `scripts/validate.sh $WORK/diagram.mmd`. Exit 1: adjust the view
   and re-render. Exit 2: no validator installed; say the diagram was not syntax-checked.
9. **Answer** with the Mermaid block (or the path of the SVG/HTML file), then briefly:
   scope (focus/hops, what was hidden), your notes, and the unresolved references with
   their locations. Each entry of `unresolved` has a `reason`. Those with `"outside"`, only
   explained by a wildcard or default import or by an external supertype (a nested type
   such as `LayoutParams` inherited from `FrameLayout`), are almost always framework types:
   `summary.py` lists them compactly; mention them as a group, not one by one.

## References

- `references/ir-schema.md` — ir.json fields and how each relation is derived.
- `references/view-schema.md` — every view.json key, with examples.
- `references/lang-notes.md` — per-language behaviour and known gaps; read only the
  section for the language at hand.
- `references/query-protocol.md` — only when adding or fixing a language.
