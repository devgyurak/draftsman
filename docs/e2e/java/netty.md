# Netty — Java

An asynchronous network framework: buffers, channels, pipelines, codecs and native transports in 38 Maven modules.

| | |
|---|---|
| Repository | [github.com/netty/netty](https://github.com/netty/netty) |
| Commit | `e3cab70052` (2026-11-16) |
| Extracted | the whole repository without `src/test`, the `testsuite*` and `*-tests` modules, `microbench/` and `example/` |

Measured on 2026-11-23 with Draftsman 0.4.0.

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
draftsman: 2076 files, 2752 types, relations: association 1752, dependency 13898, extends 1383, implements 779, body dependency 13818, 3 unresolved (2 outside the sources, 1 unexplained), 0 diagnostics
```

| Files | Types | association | dependency | extends | implements | body dependency | Unresolved | Diagnostics |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2076 | 2752 | 1752 | 13898 | 1383 | 779 | 13818 | 3 (2 outside, 1 unexplained) | 0 |

Types by kind: 1931 classes, 222 abstract classes, 422 interfaces, 161 enums, 16 annotation types.

The Mermaid and SVG renders of the view draw 37 boxes and 158 relations (`DefaultChannelPipeline` and its neighbours one hop away, 15 of the boxes only through the 16 body relations of `DefaultChannelPipeline`), and the Mermaid file passes `validate.sh`. The HTML viewer carries all 2752 types, as 1979 boxes with 773 nested types folded into their outer types, and 11234 relations (4414 from bodies, shown around the class in focus) and opens on the same focus. No inferred edges.

## Unresolved

2 outside the sources (`ExitCondition`, `WaitStrategy`), 1 unexplained (`UnsatisfiedLinkError`). The three `Entry` of 0.3.0 (in `WeakIdentityHashMap`, its `EntrySet`, and `ReferenceMap`) are `java.util.Map.Entry`, inherited from `Map` / `AbstractMap`: the JDK table (`langs/java_jdk.json`) says so.
- `ExitCondition` and `WaitStrategy` in `io.netty.util.Recycler.BlockingMessageQueue`: nested interfaces inherited from JCTools' `MessagePassingQueue`. The hint names it.
- `UnsatisfiedLinkError` in the `throws` clause of `NativeLibraryLoader.loadLibraryByHelper`: a `java.lang` class missing from Draftsman's list of `java.lang` names, so it is neither resolved nor hinted.

## What it covers

- Scale: 38 modules in one extraction, the largest Java run. Dependencies outnumber every other kind (13898), which is why the view hides getters and setters and stays at one hop.
- 773 nested types (`ChannelOutboundBuffer.Entry`, ...) and 180 generic types (`Future<V>`, `Promise<V>`, ...).
- 116 external types with qualified ids: the JDK (`java.lang.Runnable`, `javax.net.ssl.SSLEngine`, ...) and libraries outside the sources (`io.netty.internal.tcnative.*` from netty-tcnative, JCTools).
- Bodies: 13818 dependencies from names in method bodies, between 7922 pairs of types; no declaration relates 5491 of those pairs in that direction. They match what javac resolves at every place (`bench/javac_oracle`); four names javac resolves are not drawn, Netty's stubs of `java.lang.Module` and `ProcessHandle`.
- Annotations: 212 dependencies, on `@UnstableApi` (133 types), `@ChannelHandler.Sharable` (41, most written `@Sharable` with an import of the nested annotation) and the `jfr-stub` annotations (`@Label`, `@Description`) of the allocator events.
