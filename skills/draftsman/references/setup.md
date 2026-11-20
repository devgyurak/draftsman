# Setup

Read this when a script exits with code 2 (a missing dependency), or before SVG output.

## Python packages

The extractor needs tree-sitter, its language pack and PyYAML:

```bash
python3 -c "import tree_sitter, tree_sitter_language_pack, yaml" \
  || pip install "tree-sitter>=0.25" tree-sitter-language-pack pyyaml
```

If `pip` is unavailable or blocked, prefix every Python command with
`uv run --with "tree-sitter>=0.25" --with tree-sitter-language-pack --with pyyaml`:

```bash
uv run --with "tree-sitter>=0.25" --with tree-sitter-language-pack --with pyyaml \
  python3 scripts/draw.py <path> --focus OrderService
```

In a sandbox without network access (e.g. Codex's default), request permission for the
install command or ask the user to run it; do not fall back to drawing by hand.

Drawing again from an `ir.json` (`draw.py <ir.json>`, `render.py`, `summary.py`) needs
none of these packages.

## Node (SVG output and the Mermaid check)

```bash
npm ci --prefix scripts
```

installs elkjs, mermaid and jsdom into `scripts/node_modules` once.

- **svg** is laid out by ELK in Node; without it `draw.py --format svg` exits 2.
- **Mermaid check**: without Node (or `mmdc` on `PATH`) `draw.py` reports
  `mermaid: not syntax-checked`; say so in the answer.
- **html** works without Node: the viewer then loads the same elkjs version from a CDN.

## Scratch files

`draw.py` keeps ir.json and the diagram in a new temporary directory (`--work DIR` to
choose one), not in the user's repository; write there only when the user asks for a file
(`-o`).
