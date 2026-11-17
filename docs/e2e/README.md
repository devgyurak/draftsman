# End-to-end runs

Each supported language is run on a real project: extract, then render a focused Mermaid
diagram (syntax-checked), an SVG and an HTML viewer. Each page pins the project's commit
and the exact commands, records what came out, and explains every unresolved reference
and parse diagnostic, so a later run can tell a change in Draftsman from a change in the
project.

| Language | Project | Commit | Files | Types | Relations | Unresolved | Diagnostics |
|---|---|---|---:|---:|---:|---:|---:|
| Java | [spring-petclinic](java/spring-petclinic.md) | `500158f732` (2026-09-29) | 30 | 25 | 73 | 0 | 0 |
| Java | [jsoup](java/jsoup.md) | `d90d57521d` (2026-11-04) | 105 | 230 | 1310 | 2 | 0 |
| C# | [eShopOnWeb](csharp/eshoponweb.md) | `4da8212117` (2025-01-13) | 209 | 208 | 356 | 199 | 0 |
| Kotlin | [nowinandroid](kotlin/nowinandroid.md) | `2982e63cb6` (2026-10-20) | 226 | 237 | 388 | 4 | 0 |
| TypeScript | [nest](typescript/nest.md) | `09b656cb8d` (2026-11-16) | 730 | 738 | 2304 | 0 | 0 |
| Python | [httpx](python/httpx.md) | `7cff5f79bc` (2026-11-16) | 23 | 87 | 283 | 0 | 0 |
| C++ | [leveldb](cpp/leveldb.md) | `29465588d3` (2026-11-12) | 102 | 161 | 885 | 2 | 10 |

Measured on 2026-11-17 with Draftsman `6c455fc`. The README's status table summarises this one; changes to the numbers are
recorded in [`CHANGELOG.md`](../../CHANGELOG.md).

## Re-running

The pages run the scripts from a checkout of this repository. With the Python and Node
dependencies installed (see [CONTRIBUTING](../../CONTRIBUTING.md#setup)):

```bash
export DRAFTSMAN="$PWD/skills/draftsman/scripts"     # from the root of this repository
```

Then follow a page's *Run* section. If the files or types differ from the page, the
project changed, not Draftsman: check out the pinned commit.

## Keeping the pages current

Re-run every page after a change to extraction or resolution. When a number moves:

1. Check each relation that appeared or disappeared against the source (a diff of the old
   and new `ir.json` relations is enough to find them). A new relation must be in the
   code; a lost one is a regression unless it was wrong.
2. Update the page: the summary line, the table, and the unresolved and diagnostics
   sections.
3. Update the matching row of the table above and of the status table in `README.md` and
   `README-KO.md`.
4. Say in `CHANGELOG.md` what moved and why (`nest 2172 -> 2304 relations: ...`).

## Adding a project

Pick a real, maintained project of a language, exclude tests and generated code, and copy
an existing page. A project earns a page when it exercises something the others do not:
a language, a build layout (workspaces, multi-module), or a family of constructs.
