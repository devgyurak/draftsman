# End-to-end runs

Each supported language is run on real projects: extract, then render a focused Mermaid
diagram (syntax-checked), an SVG and an HTML viewer. Each page pins the project's commit
and the exact commands, records what came out, and explains every unresolved reference
and parse diagnostic, so a later run can tell a change in Draftsman from a change in the
project.

| Language | Project | Commit | Files | Types | Relations | Unresolved | Diagnostics |
|---|---|---|---:|---:|---:|---:|---:|
| Java | [spring-petclinic](java/spring-petclinic.md) | `500158f732` (2026-09-29) | 30 | 25 | 74 + 27 body | 0 | 0 |
| Java | [jsoup](java/jsoup.md) | `d90d57521d` (2026-11-04) | 105 | 230 | 1310 + 1724 body | 0 | 0 |
| Java | [Netty](java/netty.md) | `e3cab70052` (2026-11-16) | 2076 | 2752 | 17812 + 13818 body | 3 (2 outside, 1 unexplained) | 0 |
| C# | [eShopOnWeb](csharp/eshoponweb.md) | `4da8212117` (2025-01-13) | 209 | 208 | 366 + 207 body | 199 (1 ambiguous, 198 outside) | 0 |
| C# | [eShop](csharp/eshop.md) | `5e526931f7` (2026-11-16) | 497 | 506 | 960 + 442 body | 520 (1 ambiguous, 515 outside, 4 unexplained) | 0 |
| C# | [Serilog](csharp/serilog.md) | `43105b3509` (2026-10-24) | 113 | 119 | 566 + 363 body | 23 (23 outside) | 0 |
| Kotlin | [nowinandroid](kotlin/nowinandroid.md) | `2982e63cb6` (2026-10-20) | 226 | 237 | 416 | 4 (3 outside, 1 unexplained) | 0 |
| Kotlin | [Ktor](kotlin/ktor.md) | `cc3d345bc2` (2026-11-16) | 1578 | 2137 | 6897 | 586 (49 ambiguous, 537 outside) | 0 |
| TypeScript | [nest](typescript/nest.md) | `09b656cb8d` (2026-11-16) | 730 | 738 | 2307 + 1117 body | 0 | 0 |
| TypeScript | [TypeORM](typescript/typeorm.md) | `d5b143dd7e` (2026-11-16) | 496 | 694 | 3968 + 2076 body | 1 (1 unexplained) | 0 |
| Python | [httpx](python/httpx.md) | `7cff5f79bc` (2026-11-16) | 23 | 87 | 283 + 152 body | 0 | 0 |
| Python | [Django](python/django.md) | `d3954c9813` (2026-11-16) | 879 | 1964 | 1865 + 3203 body | 0 | 0 |
| C++ | [leveldb](cpp/leveldb.md) | `29465588d3` (2026-11-12) | 102 | 161 | 885 | 2 (2 unexplained) | 9 |
| C++ | [POCO](cpp/poco.md) | `2ef5cec8a9` (2026-11-17) | 2317 | 2066 | 9983 | 309 (1 ambiguous, 4 outside, 304 unexplained) | 333 |

Unresolved references are split by reason as `extract.py` prints them: ambiguous, outside
(the sources), unexplained; see [`ir-schema.md`](../../skills/draftsman/references/ir-schema.md#unresolved).
Measured on 2026-11-20, the Java, C#, TypeScript and Python rows again on 2026-11-23
(the pages say with which Draftsman); a Java, C#, TypeScript or Python row's relations are
the declared ones, then those read from names in method bodies. The README's status table summarises this one; changes to the numbers are
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
