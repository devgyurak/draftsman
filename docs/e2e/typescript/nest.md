# nest — TypeScript

The NestJS framework monorepo: decorators, dependency injection, microservice transports.

| | |
|---|---|
| Repository | [github.com/nestjs/nest](https://github.com/nestjs/nest) |
| Commit | `09b656cb8d` (2026-11-16) |
| Extracted | `packages/`, without tests and spec files |

Measured on 2026-11-26 with Draftsman 0.11.0 (at `b631f56`; 0.11.0 extracts the same `ir.json`). In 0.11.0 (#9) the type parser reads every TypeScript type: unions with a leading `|`, intersections, object type literals, function types with optional parameters, indexed access, conditional types and type predicates name their types, as do destructured and `this` parameters, a supertype that is an alias of several types and a supertype's type arguments: 911 declared relations added, 7 retyped (a field of an indexed access type, `inject?: FactoryProvider['inject']`, depends on the type, no association); the body relations are the same as 0.5.0's. A member's type now carries a type predicate (`err is Error`) and a destructured parameter is named by its pattern (21 types).

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
draftsman: 730 files, 738 types, relations: association 548, dependency 2404, extends 214, implements 45, body dependency 1117, 0 unresolved, 0 diagnostics
```

| Files | Types | association | dependency | extends | implements | body dependency | Unresolved | Diagnostics |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 730 | 738 | 548 | 2404 | 214 | 45 | 1117 | 0 | 0 |

Types by kind: 321 classes, 11 abstract classes, 372 interfaces, 34 enums.

The Mermaid and SVG renders of the view draw 56 types and 215 relations (`NestContainer` and its neighbours one hop away, 10 of the types only through the 10 body relations of `NestContainer`), and the Mermaid file passes `validate.sh`. The HTML viewer carries all 738 types and 2221 relations (479 from bodies, shown around the class in focus) and opens on the same focus. No inferred edges.

## Unresolved

None.

## What it covers

- Workspace packages: imports by package name (`@nestjs/common`) reach the package inside `packages/` through its `package.json`; only 9 external types remain (`Error`, `Map`, `http.IncomingMessage`, `stream.Transform`, ...).
- Barrel re-exports (`export *`), type aliases drawn through to what they name (`type TransportId = Transport | symbol`), rest parameters, optional parameter properties, tuples and function types.
- More interfaces than classes (372 to 332): option and metadata shapes.
- Decorators: the classes listed in `@Module({providers: [...]})` are dependencies of the module class (3 in nest's own packages).
- Bodies: 1117 dependencies from names in method bodies, between 831 pairs of types; no declaration relates 494 of those pairs in that direction. They match what the TypeScript compiler resolves at every place (`bench/tsc_oracle`), also where a local of a class's name stands (`const { NestMicroservice } = loadPackage(...)`, which draws nothing).
