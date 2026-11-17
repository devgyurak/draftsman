# TypeORM — TypeScript

An ORM for many databases: entity metadata, query builders, drivers, migrations and a CLI.

| | |
|---|---|
| Repository | [github.com/typeorm/typeorm](https://github.com/typeorm/typeorm) |
| Commit | `d5b143dd7e` (2026-11-16) |
| Extracted | `packages/typeorm/src` (tests are under `packages/typeorm/test`) |

Measured on 2026-11-17 with Draftsman `82118c5` and the change that splits unresolved references by reason (the summary line below).

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
draftsman: 496 files, 694 types, relations: association 701, dependency 2863, extends 353, implements 51, 1 unresolved (1 unexplained), 0 diagnostics
```

| Files | Types | association | dependency | extends | implements | Unresolved | Diagnostics |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 496 | 694 | 701 | 2863 | 353 | 51 | 1 (1 unexplained) | 0 |

Types by kind: 357 classes, 11 abstract classes, 325 interfaces, 1 enum.

The Mermaid and SVG renders of the view draw 23 types and 68 relations (`EntityManager` and its neighbours one hop away), and the Mermaid file passes `validate.sh`. The HTML viewer carries all 694 types and 1857 relations and opens on the same focus. No inferred edges.

## Unresolved

Unexplained: nothing outside the sources could provide it either.

- `LongWithoutOverridesClass`, the base of `Timestamp` in `driver/mongodb/bson.typings.ts`: it is declared as a value, `export declare const LongWithoutOverridesClass: LongWithoutOverrides`, not as a class, so `extends` names no type.

## What it covers

- Vendored declaration files: 301 of the 694 types come from `driver/mongodb/typings.ts` (263) and `bson.typings.ts` (38), copies of the MongoDB driver's `export declare` typings.
- Ids are module paths (`entity-manager/EntityManager.EntityManager`), as the sources import each other by relative path.
- A dense core: `EntityManager`, `DataSource`, `QueryRunner` and `EntityMetadata` reach dozens of types one hop away (`QueryRunner` 71, `EntityMetadata` 69), so the view focuses on `EntityManager`.
- Node and CLI supertypes outside the sources are external ids (`events.EventEmitter`, `stream.Readable`, yargs' `CommandModule`).
