# TypeORM — TypeScript

An ORM for many databases: entity metadata, query builders, drivers, migrations and a CLI.

| | |
|---|---|
| Repository | [github.com/typeorm/typeorm](https://github.com/typeorm/typeorm) |
| Commit | `d5b143dd7e` (2026-11-16) |
| Extracted | `packages/typeorm/src` (tests are under `packages/typeorm/test`) |

Measured on 2026-11-26 with Draftsman 0.11.0 (at `b631f56`; 0.11.0 extracts the same `ir.json`). In 0.11.0 (#9) the type parser reads every TypeScript type: unions with a leading `|`, intersections, object type literals, function types with optional parameters, indexed access, conditional types and type predicates name their types, as do destructured and `this` parameters, a supertype that is an alias of several types and a supertype's type arguments: 1040 declared relations added, 12 changed: a field naming a type and an array of it is one association of `*` (10: `transformer?: ValueTransformer | ValueTransformer[]`, `UpdateFilter<T> | Document[]`), and a field of an indexed access type depends on the type (2: `explain`); the body relations are the same as 0.5.0's. A member's type now carries a type predicate (`value is Long`) and a destructured parameter is named by its pattern (14 types).

## Run

From any directory, with `DRAFTSMAN` pointing at `skills/draftsman/scripts` of this repository (see [the index](../README.md#re-running)):

```bash
git clone https://github.com/typeorm/typeorm typeorm && git -C typeorm checkout d5b143dd7e
cd typeorm
python3 "$DRAFTSMAN"/extract.py packages/typeorm/src -o ir.json
python3 "$DRAFTSMAN"/render.py ir.json view.json -o focus.mmd
"$DRAFTSMAN"/validate.sh focus.mmd
python3 "$DRAFTSMAN"/render.py ir.json view.json --format svg -o focus.svg
python3 "$DRAFTSMAN"/render.py ir.json view.json --format html -o viewer.html
```

`view.json`:

```json
{
  "focus": "EntityManager",
  "hops": 1,
  "hidden": ["*#get*", "*#set*"]
}
```

## Result

`extract.py` prints:

```text
draftsman: 496 files, 694 types, relations: association 756, dependency 3834, extends 355, implements 51, body dependency 2076, 1 unresolved (1 unexplained), 0 diagnostics
```

| Files | Types | association | dependency | extends | implements | body dependency | Unresolved | Diagnostics |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 496 | 694 | 756 | 3834 | 355 | 51 | 2076 | 1 (1 unexplained) | 0 |

Types by kind: 357 classes, 11 abstract classes, 325 interfaces, 1 enum.

The Mermaid and SVG renders of the view draw 36 types and 120 relations (`EntityManager` and its neighbours one hop away, 9 of the types only through the 10 body relations of `EntityManager`), and the Mermaid file passes `validate.sh`. The HTML viewer carries all 694 types and 2937 relations (679 from bodies, shown around the class in focus) and opens on the same focus. No inferred edges.

## Unresolved

Unexplained: nothing outside the sources could provide it either.

- `LongWithoutOverridesClass`, the base of `Timestamp` in `driver/mongodb/bson.typings.ts`: it is declared as a value, `export declare const LongWithoutOverridesClass: LongWithoutOverrides`, not as a class, so `extends` names no type.

## What it covers

- Vendored declaration files: 301 of the 694 types come from `driver/mongodb/typings.ts` (263) and `bson.typings.ts` (38), copies of the MongoDB driver's `export declare` typings.
- Ids are module paths (`entity-manager/EntityManager.EntityManager`), as the sources import each other by relative path.
- A dense core: `EntityManager`, `DataSource`, `QueryRunner` and `EntityMetadata` reach dozens of types one hop away (`QueryRunner` 71, `EntityMetadata` 73), so the view focuses on `EntityManager`.
- Node and CLI supertypes outside the sources are external ids (`events.EventEmitter`, `stream.Readable`, yargs' `CommandModule`).
- Bodies: 2076 dependencies from names in method bodies, between 935 pairs of types; no declaration relates 694 of those pairs in that direction. They match what the TypeScript compiler resolves at every place (`bench/tsc_oracle`); a parameter that hides a type-only import of another name (`create(dataSource: dataSource)` under `import type { DataSource as dataSource }`) draws nothing.
