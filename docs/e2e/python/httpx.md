# httpx — Python

An HTTP client: sync and async clients, transports, typed models.

| | |
|---|---|
| Repository | [github.com/encode/httpx](https://github.com/encode/httpx) |
| Commit | `7cff5f79bc` (2026-11-16) |
| Extracted | the `httpx/` package |

Measured on 2026-11-20 with Draftsman 0.3.0.

## Run

From any directory, with `DRAFTSMAN` pointing at `skills/draftsman/scripts` of this repository (see [the index](../README.md#re-running)):

```bash
git clone https://github.com/encode/httpx httpx && git -C httpx checkout 7cff5f79bc
cd httpx
python3 "$DRAFTSMAN"/extract.py httpx -o ir.json
python3 "$DRAFTSMAN"/render.py ir.json view.json -o focus.mmd
"$DRAFTSMAN"/validate.sh focus.mmd
python3 "$DRAFTSMAN"/render.py ir.json view.json --format svg -o focus.svg
python3 "$DRAFTSMAN"/render.py ir.json view.json --format html -o viewer.html
```

`view.json`:

```json
{
  "focus": "Client",
  "hops": 1,
  "hidden": ["*#get*", "*#set*"]
}
```

## Result

`extract.py` prints:

```text
draftsman: 23 files, 87 types, relations: association 31, dependency 188, extends 64, 0 unresolved, 0 diagnostics
```

| Files | Types | association | dependency | extends | implements | Unresolved | Diagnostics |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 23 | 87 | 31 | 188 | 64 | 0 | 0 | 0 |

Types by kind: 83 classes, 2 records, 2 enums.

The Mermaid and SVG renders of the view draw 11 types and 27 relations (`Client` and its neighbours one hop away), and the Mermaid file passes `validate.sh`. The HTML viewer carries all 87 types, as 85 boxes with 2 nested types folded into their outer types, and 141 relations and opens on the same focus. No inferred edges.

## Unresolved

None.

## What it covers

- Ids carry the package prefix (`httpx._client.Client`), since the extraction root is a package.
- `NamedTuple`s are records (`_urlparse.ParseResult`, `_auth._DigestAuthChallenge`), `Enum`s are enums (`codes`, `ClientState`).
- `Optional[...]` / `X | None` give `0..1` associations (10 of 31); `typing.Mapping` and `MutableMapping` are external supertypes.
