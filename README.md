<!-- README-KO.md is its Korean translation; change both together. -->

<div align="center">

<h1 align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo/draftsman-horizontal-reversed.svg">
    <img src="assets/logo/draftsman-horizontal.svg" alt="draftsman" width="380">
  </picture>
</h1>

**UML class diagrams for Claude Code and Codex, drawn from parser facts — never from guesses**

[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![Languages](https://img.shields.io/badge/languages-Java%20%C2%B7%20C%23%20%C2%B7%20Kotlin%20%C2%B7%20TS%20%C2%B7%20Python%20%C2%B7%20C%2B%2B-D96A00)](#status)
[![Agents: Claude Code · Codex](https://img.shields.io/badge/agents-Claude%20Code%20%C2%B7%20Codex-15181D)](#install)

[Status](#status) · [Install](#install) · [Use](#use) · [What it doesn't do](#what-it-doesnt-do) ·
[Development](#development) · [Documentation](#documentation) · [Korean](README-KO.md)

</div>

A **draftsman** takes measured figures and turns them into a drawing without changing a
number. Draftsman splits the work the same way: a tree-sitter extractor measures the code
and writes the facts to `ir.json`; the agent decides only *what to show* — scope, noise,
grouping, commentary — in `view.json`; a renderer merges the two.

- **Facts from a parser** — classes, members, inheritance, field associations with
  multiplicity, and signature dependencies, each with a source location.
- **Edited, not invented** — the agent can hide, group and annotate. A relation the parser
  did not find can only be added as an *inferred* edge with a rationale, drawn dotted.
- **Readable at any size** — focus on one class and its neighbours *N* hops away; hide
  getters, DTOs and framework noise by pattern.
- **Three outputs** — Mermaid for docs and PRs, a static SVG, or a single-file interactive
  HTML viewer with search, focus/hop controls, cycle highlighting and the agent's notes.

<p align="center">
  <img src="docs/images/example-shop.svg" alt="Example: the Java shop fixture rendered as SVG" width="760">
</p>

## Status

| Works today | Not yet |
|---|---|
| Extraction for Java, C#, Kotlin, TypeScript/TSX, Python and C++ | Diff mode (changed classes between two commits) |
| Mermaid (syntax-checked), static SVG (ELK layout), interactive HTML | PlantUML output, Graphviz layout |
| Focus + hops, hidden patterns, groups, notes, highlights, inferred edges, cycles | An MCP server, an LSP-backed precise mode |
| Claude Code plugin with `/draftsman`; Codex plugin with `$draftsman:draftsman` | Go and Rust (implicit interfaces and scattered `impl` blocks: out of scope by design) |

Each language was run end to end — extract, then render a focused Mermaid diagram (syntax
checked), an SVG and an HTML viewer — on a real project, tests and generated code excluded:

| Language | Project | Files | Types | Relations | Unresolved | Parse diagnostics |
|---|---|---:|---:|---:|---:|---:|
| Java | [spring-petclinic](docs/e2e/java/spring-petclinic.md) | 30 | 25 | 73 | 0 | 0 |
| Java | [jsoup](docs/e2e/java/jsoup.md) | 105 | 230 | 1310 | 2 (`Map.Entry`, with a hint) | 0 |
| C# | [eShopOnWeb](docs/e2e/csharp/eshoponweb.md) `src/` | 209 | 208 | 356 | 199 (195 library types via `using`, 4 Blazor components in `.razor` files) | 0 |
| Kotlin | [nowinandroid](docs/e2e/kotlin/nowinandroid.md) | 226 | 237 | 388 | 4 (protobuf-generated) | 0 |
| TypeScript | [nest](docs/e2e/typescript/nest.md) `packages/` | 730 | 738 | 2304 | 0 | 0 |
| Python | [httpx](docs/e2e/python/httpx.md) | 23 | 87 | 283 | 0 | 0 |
| C++ | [leveldb](docs/e2e/cpp/leveldb.md) | 102 | 161 | 885 | 2 | 10 spans in 9 files (5 in function bodies; macros, `extern "C"`, a pointer-to-member field) |

Each project has a page under [`docs/e2e/`](docs/e2e/README.md) with the pinned commit,
the exact commands, and what every unresolved name and diagnostic is. Known gaps per
language are listed in
[`lang-notes.md`](skills/draftsman/references/lang-notes.md).

## Install

The repository is a plugin and a marketplace for both agents.

**Claude Code**

```text
/plugin marketplace add devgyurak/draftsman
/plugin install draftsman@draftsman
```

**Codex** (the CLI, IDE extension and app share one plugin store)

```bash
codex plugin marketplace add devgyurak/draftsman
codex plugin add draftsman@draftsman
```

Or run `/plugins` inside Codex and pick *Draftsman*. To install only the skill:
`$skill-installer install https://github.com/devgyurak/draftsman/tree/main/skills/draftsman`.
Other agents that read the Agent Skills format can use `skills/draftsman/` as is.

**Requirements** — Python 3.10+ with three packages, which the skill installs on first use
if they are missing:

```bash
pip install "tree-sitter>=0.25" tree-sitter-language-pack pyyaml
```

SVG output and the Mermaid syntax check also need Node.js:
`npm ci --prefix skills/draftsman/scripts` (elkjs, mermaid and jsdom at the versions in
`package-lock.json`). HTML output works without it; the viewer then loads the same elkjs
version from a CDN.

## Use

Ask in plain words — *"draw a class diagram of this repo"*, *"show the classes around
OrderService as an interactive diagram"*, *"클래스 다이어그램 그려줘"* — or call it directly:

```text
/draftsman OrderService html        # Claude Code
$draftsman:draftsman                # Codex (plugin); $draftsman for a skill-only install
```

The agent extracts, surveys the result, writes a view, renders, validates, and answers with
the diagram, the scope it chose and the references it could not resolve.

The scripts also work on their own:

```bash
cd skills/draftsman
python3 scripts/extract.py path/to/src -o ir.json --exclude '**/test/**'   # *.gradle.kts are skipped
python3 scripts/summary.py ir.json                  # sizes, hubs, unresolved references
python3 scripts/summary.py ir.json --type Order     # one type in detail
python3 scripts/render.py ir.json view.json -o diagram.mmd     # or --format svg | html
python3 scripts/render.py ir.json view.json --format svg --members none -o bare.svg
scripts/validate.sh diagram.mmd
```

A view selects and annotates; every key is optional:

```json
{
  "focus": "OrderService",
  "hops": 2,
  "hidden": ["*#get*", "*#set*", "*#toString"],
  "notes": [{"target": "Order", "text": "Bidirectional with Customer"}]
}
```

Member detail can also differ per class — `"members": {"*": "none", "OrderService": "all"}`
draws the focus in full and only names around it; `--members all|public|none` overrides the
view for one render.

The diagram above is [`tests/fixtures/java/shop`](tests/fixtures/java/shop) rendered with
[`docs/images/example-shop.view.json`](docs/images/example-shop.view.json).

## What it doesn't do

- **It doesn't guess relations.** Anything not in `ir.json` is rejected unless it is an
  inferred edge between known or unresolved names — and those are drawn dotted.
- **It doesn't read method bodies.** Relations come from supertype clauses, field types and
  signatures. It is not a call graph or a sequence diagram tool.
- **It doesn't tell composition from aggregation** — syntax cannot — except C++ ownership
  (values and `unique_ptr` versus pointers, references and `shared_ptr`).
- **It doesn't run or upload your code.** Everything runs locally; the only network use is
  installing the dependencies above (and the CDN fallback of the HTML viewer).

## Development

**Prerequisites** — [uv](https://docs.astral.sh/uv/); Node.js for the SVG and Mermaid tests.

```bash
uv sync                                         # Python dependencies
npm ci --prefix skills/draftsman/scripts   # optional: ELK layout + Mermaid check
uv run pytest                                   # includes node tests of draw.js and the viewer;
                                                # they skip without node
```

A language is a tree-sitter query plus a small spec. To add one, write
`queries/<lang>.scm` following the
[capture protocol](skills/draftsman/references/query-protocol.md), add a `LanguageSpec` in
`scripts/draftsman/langs/`, and mirror the `shop` fixture under `tests/fixtures/<lang>/`.

### Repository layout

```text
skills/draftsman/SKILL.md       workflow and rules for the agent
skills/draftsman/queries/       one tree-sitter query per language: what to capture
skills/draftsman/scripts/       extract.py · summary.py · render.py · validate.sh · layout.mjs
  draftsman/                    the library: extractor, resolver, scene, renderers, langs/
skills/draftsman/assets/        draw.js (shared by SVG and the viewer) · viewer.html
skills/draftsman/config/        wrappers.yaml: containers to see through (List<T> → T, *)
skills/draftsman/references/    schemas and language notes, loaded on demand
.claude-plugin/                 Claude Code plugin and marketplace manifests
.codex-plugin/ · .agents/       Codex plugin manifest and marketplace
commands/                       the /draftsman slash command (Claude Code)
assets/                         plugin icon; logo masters and guidelines in assets/logo/
tests/                          pytest suite; the same shop fixture in all six languages
docs/                           design notes, end-to-end runs (docs/e2e/), README images
```

## Documentation

| Document | What is in it |
|---|---|
| [`SKILL.md`](skills/draftsman/SKILL.md) | The agent's workflow, hard rules, and how it picks scope and output |
| [`ir-schema.md`](skills/draftsman/references/ir-schema.md) | Every field of `ir.json` and how each relation is derived |
| [`view-schema.md`](skills/draftsman/references/view-schema.md) | Every key of `view.json`, the three outputs, an example |
| [`lang-notes.md`](skills/draftsman/references/lang-notes.md) | Per-language behaviour and known gaps |
| [`query-protocol.md`](skills/draftsman/references/query-protocol.md) | The capture names a language query uses; adding a language |
| [`docs/DESIGN.md`](docs/DESIGN.md) | Design notes (Korean): background, principles, architecture, roadmap |
| [`docs/e2e/`](docs/e2e/README.md) | One page per measured project: pinned commit, commands, results, every unresolved name and diagnostic explained |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Setup, where a change goes, tests and re-measuring, adding a language |
| [`CHANGELOG.md`](CHANGELOG.md) | Changes that affect existing `ir.json`/`view.json` files |
| [`assets/logo/GUIDELINES.md`](assets/logo/GUIDELINES.md) | Logo files, colours, clear space, minimum sizes |

## Contributing

Issues and pull requests are welcome — bug reports from real projects most of all. Read
[`CONTRIBUTING.md`](CONTRIBUTING.md) first: the never-invent rule, where a change goes, how
fixes are tested, and when to re-run the [end-to-end projects](docs/e2e/README.md).

## License

[Apache License 2.0](LICENSE). Third-party components are installed by the user, not
bundled; see [`NOTICE`](NOTICE).
