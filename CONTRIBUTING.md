# Contributing

Issues and pull requests are welcome: bug reports from real projects most of all, then
fixes, language queries and renderer work. This page is how changes are made here.

## The rule everything follows

Draftsman's diagrams are trusted because every relation in `ir.json` is in the source.
Three consequences shape most changes:

- **Never invent.** If the extractor is not sure what a name refers to, it does not draw a
  relation. A relation that is not in the code is the worst bug there is.
- **Never drop silently.** A name that cannot be placed goes to `unresolved`, with a hint
  when one is known. It is not left out, and it is not called external because it looks
  like a library name. A relation that disappears without a trace is a bug too.
- **The project wins.** A rule keyed on a name (`List<T>` is a container, `tuple[A, B]` a
  tuple, `Literal["a"]` values) applies only when the project has no class of that name.

When in doubt, prefer `unresolved` with a good hint over a relation.

## Setup

You need [uv](https://docs.astral.sh/uv/) and, for the SVG and viewer tests, Node.js.

```bash
uv sync                                     # Python dependencies
npm ci --prefix skills/draftsman/scripts    # elkjs, mermaid, jsdom (optional)
uv run pytest
```

Without the Node packages the frontend tests (`tests/test_frontend.py`, which runs
`tests/js/*.test.mjs` under `node --test`) are skipped; everything else still runs.

## Where a change goes

| To change | Edit |
|---|---|
| What is captured from the syntax tree | `skills/draftsman/queries/<lang>.scm` ([capture protocol](skills/draftsman/references/query-protocol.md)) |
| A language's own rules (visibility, builtins, imports, preprocessing) | a hook on its `LanguageSpec` in `scripts/draftsman/langs/<lang>.py` |
| How type text is read (`Map<K, V>`, `A \| B`, `(A) -> B`) | `scripts/draftsman/typeref.py` |
| Containers to see through, names with a meaning of their own | `config/wrappers.yaml`, `scripts/draftsman/wrappers.py` |
| How a name becomes a type id | `scripts/draftsman/resolve.py` |
| Diagram output | `scene.py` and the renderers; `assets/draw.js` is shared by the SVG and the viewer |

Shared code should not test for a language. If one language needs something, add a hook
to `LanguageSpec` in `langs/base.py` with a neutral default, and override it in that
language's spec.

## Making a change

1. **Reproduce it in a test.** `extract_source` in `tests/conftest.py` extracts files you
   write inline:

   ```python
   def test_aliases_are_drawn_through(tmp_path):
       from conftest import extract_source
       ir = extract_source(tmp_path, {
           "u.ts": "export class A {}\nexport type X = A;\nexport class U { x?: X; }\n"})
       assert ("U", "association", "A") in {
           (r.from_.rsplit(".", 1)[-1], r.kind, r.to.rsplit(".", 1)[-1]) for r in ir.relations}
       assert not ir.unresolved
   ```

   Assert the whole result where you can (the set of relations, `not ir.unresolved`, `not
   ir.diagnostics`), not one relation among many: a fix that adds the right relation and
   a wrong one should fail.
2. **Fix it, then break the fix once.** Disable the change (comment out the new pattern,
   return early from the new branch) and check that your test fails. A test that passes
   either way does not protect the fix.
3. **Name-resolution rules** have a witness in every language: add the rule to
   `SCOPE_RULES` in `tests/test_languages.py`, with a relation from the `shop` fixture of
   each language that only that rule produces, or `None` and a comment where the language
   has no such rule.
4. **Run the end-to-end projects** when the change touches extraction or resolution, as
   described in [`docs/e2e/`](docs/e2e/README.md). Check each relation that appeared or
   disappeared against the source, then update the project pages, the README status table
   (`README.md` and `README-KO.md`), and `CHANGELOG.md`.
5. **Document behaviour** where readers look for it:
   [`lang-notes.md`](skills/draftsman/references/lang-notes.md) for what a language does
   and does not handle, [`ir-schema.md`](skills/draftsman/references/ir-schema.md) for how
   relations are derived, [`query-protocol.md`](skills/draftsman/references/query-protocol.md)
   for captures and hooks.

## Adding a language

1. `queries/<lang>.scm` with the captures of the protocol, and a `LanguageSpec` in
   `langs/<lang>.py`, registered in `langs/__init__.py`.
2. The `shop` fixture in `tests/fixtures/<lang>/shop`, mirroring the other languages, and
   its expectations in `tests/test_languages.py`.
3. A witness for every rule in `SCOPE_RULES`.
4. A section in `lang-notes.md`, including what is not handled.
5. An end-to-end page under `docs/e2e/<lang>/` for a real project, and its row in the
   README status table.

Go and Rust are out of scope by design: implicit interfaces and `impl` blocks spread over
files do not fit a per-file class model.

## Pull requests

- Keep `uv run pytest` passing; each commit on its own should pass too.
- One topic per commit. The message starts with a short summary line; the body says what
  changed and, for extraction changes, which measured numbers moved and why.
- `README.md` and `README-KO.md` change together.
- Changes that affect existing `ir.json` or `view.json` files, or the measured numbers,
  get an entry in `CHANGELOG.md`.
- Contributions are accepted under the project's [Apache-2.0 license](LICENSE).

## Reporting a wrong diagram

Open an issue with the language, a minimal source that shows it, and what you expected
against what `ir.json` says (the relation, or the entry in `unresolved`). For a public
project, the repository, the commit and the `extract.py` command are enough to reproduce.
