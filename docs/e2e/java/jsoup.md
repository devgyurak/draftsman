# jsoup — Java

An HTML parser: a deep node and evaluator hierarchy with many nested types.

| | |
|---|---|
| Repository | [github.com/jhy/jsoup](https://github.com/jhy/jsoup) |
| Commit | `d90d57521d` (2026-11-04) |
| Extracted | `src/main` (language detected) |

Measured on 2026-11-17 with Draftsman `6c455fc`.

## Run

From any directory, with `DRAFTSMAN` pointing at `skills/draftsman/scripts` of this repository (see [the index](../README.md#re-running)):

```bash
git clone https://github.com/jhy/jsoup jsoup && git -C jsoup checkout d90d57521d
cd jsoup
python3 "$DRAFTSMAN"/extract.py src/main -o ir.json
python3 "$DRAFTSMAN"/render.py ir.json view.json -o focus.mmd
"$DRAFTSMAN"/validate.sh focus.mmd
python3 "$DRAFTSMAN"/render.py ir.json view.json --format svg -o focus.svg
python3 "$DRAFTSMAN"/render.py ir.json view.json --format html -o viewer.html
```

`view.json`:

```json
{
  "focus": "Element",
  "hops": 1,
  "hidden": ["*#get*", "*#set*"]
}
```

## Result

`extract.py` prints:

```text
draftsman: 105 files, 230 types, relations: association 147, dependency 1014, extends 118, implements 31, 2 unresolved, 0 diagnostics
```

| Files | Types | association | dependency | extends | implements | Unresolved | Diagnostics |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 105 | 230 | 147 | 1014 | 118 | 31 | 2 | 0 |

Types by kind: 187 classes, 17 abstract classes, 13 interfaces, 13 enums.

The Mermaid and SVG renders of the view draw 101 types and 327 relations (`Element` and its neighbours one hop away), and the Mermaid file passes `validate.sh`. The HTML viewer carries all 230 types and 666 relations and opens on the same focus. No inferred edges.

## Unresolved

- `Entry` in `org.jsoup.nodes.Attributes.Dataset` and in its `DatasetIterator`: `Map.Entry`, written by its simple name and inherited from `java.util.AbstractMap`, which is not in the sources. The hint says so (*may be a nested type inherited from java.util.AbstractMap, ...*). Draftsman does not guess members of external types.

## What it covers

- 134 nested types (`Outer.Inner` ids), the largest share of the measured projects.
- The most connected type is `Evaluator` (37 non-dependency relations): many small nested subclasses, which is the case focus and hops are for.
- Supertypes from `java.lang` and `java.io` (`Cloneable`, `Iterable`, `Reader`, ...) are qualified external ids.
