# nest — TypeScript

The NestJS framework monorepo: decorators, dependency injection, microservice transports.

| | |
|---|---|
| Repository | [github.com/nestjs/nest](https://github.com/nestjs/nest) |
| Commit | `09b656cb8d` (2026-11-16) |
| Extracted | `packages/`, without tests and spec files |

Measured on 2026-11-23 with Draftsman at `ef0eb0d` (0.4.1 and the TypeScript body relations of #5, not yet released).

## Run

From any directory, with `DRAFTSMAN` pointing at `skills/draftsman/scripts` of this repository (see [the index](../README.md#re-running)):

```bash
git clone https://github.com/nestjs/nest nest && git -C nest checkout 09b656cb8d
cd nest
python3 "$DRAFTSMAN"/extract.py packages --lang typescript --exclude '**/test/**' --exclude '**/*.spec.ts' -o ir.json
python3 "$DRAFTSMAN"/render.py ir.json view.json -o focus.mmd
"$DRAFTSMAN"/validate.sh focus.mmd
python3 "$DRAFTSMAN"/render.py ir.json view.json --format svg -o focus.svg
python3 "$DRAFTSMAN"/render.py ir.json view.json --format html -o viewer.html
```

`view.json`:

```json
{
  "focus": "NestContainer",
  "hops": 1,
  "hidden": ["*#get*", "*#set*"]
}
```

## Result

`extract.py` prints:

```text
draftsman: 730 files, 738 types, relations: association 449, dependency 1601, extends 214, implements 43, body dependency 1117, 0 unresolved, 0 diagnostics
```

| Files | Types | association | dependency | extends | implements | body dependency | Unresolved | Diagnostics |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 730 | 738 | 449 | 1601 | 214 | 43 | 1117 | 0 | 0 |

Types by kind: 321 classes, 11 abstract classes, 372 interfaces, 34 enums.

The Mermaid and SVG renders of the view draw 51 types and 162 relations (`NestContainer` and its neighbours one hop away, 10 of the types only through the 10 body relations of `NestContainer`), and the Mermaid file passes `validate.sh`. The HTML viewer carries all 738 types and 1793 relations (528 from bodies, shown around the class in focus) and opens on the same focus. No inferred edges.

## Unresolved

None.

## What it covers

- Workspace packages: imports by package name (`@nestjs/common`) reach the package inside `packages/` through its `package.json`; only 9 external types remain (`Error`, `Map`, `http.IncomingMessage`, `stream.Transform`, ...).
- Barrel re-exports (`export *`), type aliases drawn through to what they name (`type TransportId = Transport | symbol`), rest parameters, optional parameter properties, tuples and function types.
- More interfaces than classes (372 to 332): option and metadata shapes.
- Decorators: the classes listed in `@Module({providers: [...]})` are dependencies of the module class (3 in nest's own packages).
- Bodies: 1117 dependencies from names in method bodies, between 831 pairs of types; no declaration relates 545 of those pairs in that direction. They match what the TypeScript compiler resolves at every place (`bench/tsc_oracle`), also where a local of a class's name stands (`const { NestMicroservice } = loadPackage(...)`, which draws nothing).
