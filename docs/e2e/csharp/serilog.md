# Serilog — C#

A structured logging library: the logger pipeline, enrichers, sinks, formatting and configuration.

| | |
|---|---|
| Repository | [github.com/serilog/serilog](https://github.com/serilog/serilog) |
| Commit | `43105b3509` (2026-10-24) |
| Extracted | `src/Serilog` (tests are under `test/`) |

Measured on 2026-11-23 with Draftsman 0.7.0 (at `3e14b4d`; 0.7.0 extracts the same `ir.json`).

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
draftsman: 113 files, 119 types, relations: association 94, dependency 399, extends 14, implements 59, body dependency 363, 23 unresolved (23 outside the sources), 0 diagnostics
```

| Files | Types | association | dependency | extends | implements | body dependency | Unresolved | Diagnostics |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 113 | 119 | 94 | 399 | 14 | 59 | 363 | 23 (23 outside) | 0 |

Types by kind: 91 classes, 5 abstract classes, 14 interfaces, 5 structs, 4 enums.

The Mermaid and SVG renders of the view draw 22 boxes and 74 relations (`Logger` and its neighbours one hop away, 9 of them only through body relations: `Guard`, `SelfLog`, `Log`, `Constants`, ...), and the Mermaid file passes `validate.sh`. The HTML viewer carries all 119 types, as 111 boxes with 8 nested types folded into their outer types, and 490 relations (169 from bodies, shown around the class in focus) and opens on the same focus. No inferred edges.

## Unresolved

All 23 (17 names) are outside the sources, .NET library types reached through `using` directives that Draftsman has no namespace for: collections (`KeyValuePair`, `IEnumerable`, `IEnumerator`, `IGrouping`, `Hashtable`), reflection (`MethodInfo`, `Assembly`), `System.Diagnostics` (`ActivityTraceId`, `ActivitySpanId`) and `System.Diagnostics.Metrics` (`Meter`, `Counter`, `Histogram`), `System.Threading.Channels` (`Channel`, `ChannelReader`), `AsyncLocal`, `ICustomFormatter` and `StringWriter`. Each hint names where the file's wildcard imports come from (*may come from a project-wide wildcard import: Microsoft.NET.Sdk implicit usings (6 namespaces), 24 global usings (System.Collections.\*, ...)*); none is picked.

## What it covers

- Project-wide imports: SDK implicit usings, the `global using`s of `GlobalUsings.cs`, and `<Using Remove="System.Net.Http" />` in the `.csproj` (hence 6 implicit namespaces, not 7).
- `#if` in 27 files, read with the first branch of each; no parse diagnostics.
- 5 structs and nested types (`EnricherStack.Enumerator`); `System.IDisposable`, `System.IAsyncDisposable` and `System.IFormattable` as external interfaces, and the generic and non-generic `IEqualityComparer` told apart.
- Bodies: 363 dependencies from names in method bodies (`Guard.AgainstNull(...)` 90 times, `LogEventLevel.Debug`, `SelfLog.WriteLine(...)`, `new ScalarValue(...)`), between 243 pairs of types; no declaration relates 176 of those pairs in that direction. All 655 places they are drawn from match what Roslyn resolves there in every one of the 5 compilations of each file (`bench/roslyn_oracle`: net10.0, net9.0, net8.0, net6.0 and netstandard2.0 with the .NET 10 SDK as C# 14, Debug, 0 compile errors, 1112 names read in bodies; the Windows-only net462 and net471 are left out). The 2 places the compilations resolve differently draw nothing: `TimeProvider.System`, Serilog's own `System.TimeProvider` below .NET 8 and the runtime's from it (the polyfill is declared in an `#if`, so no relation is drawn to it), and `s is IDisposable` beside an `#if`'d `or IAsyncDisposable`.
- Attributes: the project's `[MessageTemplateFormatMethod]`, `[CustomDefaultMethodImplementation]` and the bundled JetBrains `[NoEnumeration]` are dependencies of the types that use them.
