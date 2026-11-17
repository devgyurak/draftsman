# Netty — Java

An asynchronous network framework: buffers, channels, pipelines, codecs and native transports in 38 Maven modules.

| | |
|---|---|
| Repository | [github.com/netty/netty](https://github.com/netty/netty) |
| Commit | `e3cab70052` (2026-11-16) |
| Extracted | the whole repository without `src/test`, the `testsuite*` and `*-tests` modules, `microbench/` and `example/` |

Measured on 2026-11-17 with Draftsman `2e6c77b`.

## Run

From any directory, with `DRAFTSMAN` pointing at `skills/draftsman/scripts` of this repository (see [the index](../README.md#re-running)):

```bash
git clone https://github.com/netty/netty netty && git -C netty checkout e3cab70052
cd netty
python3 "$DRAFTSMAN"/extract.py . --lang java --exclude '**/src/test/**' --exclude 'testsuite*/**' --exclude '*-tests/**' --exclude 'microbench/**' --exclude 'example/**' -o ir.json
python3 "$DRAFTSMAN"/render.py ir.json view.json -o focus.mmd
"$DRAFTSMAN"/validate.sh focus.mmd
python3 "$DRAFTSMAN"/render.py ir.json view.json --format svg -o focus.svg
python3 "$DRAFTSMAN"/render.py ir.json view.json --format html -o viewer.html
```

`--lang java` keeps the C headers of the native transports out.

`view.json`:

```json
{
  "focus": "DefaultChannelPipeline",
  "hops": 1,
  "hidden": ["*#get*", "*#set*"]
}
```

## Result

`extract.py` prints:

```text
draftsman: 2076 files, 2752 types, relations: association 1752, dependency 13686, extends 1383, implements 779, 6 unresolved (5 outside the sources, 1 unexplained), 0 diagnostics
```

| Files | Types | association | dependency | extends | implements | Unresolved | Diagnostics |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2076 | 2752 | 1752 | 13686 | 1383 | 779 | 6 (5 outside, 1 unexplained) | 0 |

Types by kind: 1931 classes, 222 abstract classes, 422 interfaces, 161 enums, 16 annotation types.

The Mermaid and SVG renders of the view draw 25 types and 96 relations (`DefaultChannelPipeline` and its neighbours one hop away), and the Mermaid file passes `validate.sh`. The HTML viewer carries all 2752 types and 8015 relations and opens on the same focus. No inferred edges.

## Unresolved

5 outside the sources (`Entry` three times, `ExitCondition`, `WaitStrategy`), 1 unexplained (`UnsatisfiedLinkError`).

- `Entry` in `io.netty.util.internal.WeakIdentityHashMap`, its `EntrySet`, and `io.netty.handler.codec.serialization.ReferenceMap`: `Map.Entry`, written by its simple name and inherited from `java.util.Map` / `AbstractMap`, which are not in the sources. Three project classes are also called `Entry` (`ChannelOutboundBuffer.Entry`, ...), but they are nested in other classes and cannot be meant here: the hint names them, they are no candidates.
- `ExitCondition` and `WaitStrategy` in `io.netty.util.Recycler.BlockingMessageQueue`: nested interfaces inherited from JCTools' `MessagePassingQueue`. The hint names it.
- `UnsatisfiedLinkError` in the `throws` clause of `NativeLibraryLoader.loadLibraryByHelper`: a `java.lang` class missing from Draftsman's list of `java.lang` names, so it is neither resolved nor hinted.

## What it covers

- Scale: 38 modules in one extraction, the largest Java run. Dependencies outnumber every other kind (13686), which is why the view hides getters and setters and stays at one hop.
- 773 nested types (`ChannelOutboundBuffer.Entry`, ...) and 180 generic types (`Future<V>`, `Promise<V>`, ...).
- 116 external types with qualified ids: the JDK (`java.lang.Runnable`, `javax.net.ssl.SSLEngine`, ...) and libraries outside the sources (`io.netty.internal.tcnative.*` from netty-tcnative, JCTools).
