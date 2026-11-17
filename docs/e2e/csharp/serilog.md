# Serilog — C#

A structured logging library: the logger pipeline, enrichers, sinks, formatting and configuration.

| | |
|---|---|
| Repository | [github.com/serilog/serilog](https://github.com/serilog/serilog) |
| Commit | `43105b3509` (2026-10-24) |
| Extracted | `src/Serilog` (tests are under `test/`) |

Measured on 2026-11-17 with Draftsman `82118c5` and the change that splits unresolved references by reason (the summary line below).

## Run

From any directory, with `DRAFTSMAN` pointing at `skills/draftsman/scripts` of this repository (see [the index](../README.md#re-running)):

```bash
git clone https://github.com/serilog/serilog serilog && git -C serilog checkout 43105b3509
cd serilog
python3 "$DRAFTSMAN"/extract.py src/Serilog --lang csharp -o ir.json
python3 "$DRAFTSMAN"/render.py ir.json view.json -o focus.mmd
"$DRAFTSMAN"/validate.sh focus.mmd
python3 "$DRAFTSMAN"/render.py ir.json view.json --format svg -o focus.svg
python3 "$DRAFTSMAN"/render.py ir.json view.json --format html -o viewer.html
```

`view.json`:

```json
{
  "focus": "Logger",
  "hops": 1
}
```

## Result

`extract.py` prints:

```text
draftsman: 113 files, 119 types, relations: association 94, dependency 393, extends 14, implements 59, 23 unresolved (23 outside the sources), 0 diagnostics
```

| Files | Types | association | dependency | extends | implements | Unresolved | Diagnostics |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 113 | 119 | 94 | 393 | 14 | 59 | 23 (23 outside) | 0 |

Types by kind: 91 classes, 5 abstract classes, 14 interfaces, 5 structs, 4 enums.

The Mermaid and SVG renders of the view draw 12 types and 35 relations (`Logger` and its neighbours one hop away), and the Mermaid file passes `validate.sh`. The HTML viewer carries all 119 types and 328 relations and opens on the same focus. No inferred edges.

## Unresolved

All 23 (17 names) are outside the sources, .NET library types reached through `using` directives that Draftsman has no namespace for: collections (`KeyValuePair`, `IEnumerable`, `IEnumerator`, `IGrouping`, `Hashtable`), reflection (`MethodInfo`, `Assembly`), `System.Diagnostics` (`ActivityTraceId`, `ActivitySpanId`) and `System.Diagnostics.Metrics` (`Meter`, `Counter`, `Histogram`), `System.Threading.Channels` (`Channel`, `ChannelReader`), `AsyncLocal`, `ICustomFormatter` and `StringWriter`. Each hint names where the file's wildcard imports come from (*may come from a project-wide wildcard import: Microsoft.NET.Sdk implicit usings (6 namespaces), 24 global usings (System.Collections.\*, ...)*); none is picked.

## What it covers

- Project-wide imports: SDK implicit usings, the `global using`s of `GlobalUsings.cs`, and `<Using Remove="System.Net.Http" />` in the `.csproj` (hence 6 implicit namespaces, not 7).
- `#if` in 27 files, read with the first branch of each; no parse diagnostics.
- 5 structs and nested types (`EnricherStack.Enumerator`); `System.IDisposable`, `System.IAsyncDisposable` and `System.IFormattable` as external interfaces, and the generic and non-generic `IEqualityComparer` told apart.
