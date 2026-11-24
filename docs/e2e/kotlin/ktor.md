# Ktor — Kotlin

An asynchronous client and server framework, Kotlin Multiplatform: common code with `expect` declarations and `actual`s for JVM, native, JS and Wasm, across about 140 Gradle modules.

| | |
|---|---|
| Repository | [github.com/ktorio/ktor](https://github.com/ktorio/ktor) |
| Commit | `cc3d345bc2` (2026-11-16) |
| Extracted | the whole repository without test source sets (`<module>/<platform>/test`), test-support modules (`ktor-server-test-host`, `ktor-client-tests`, ...), the compiler plugin's test data and the Gradle build logic |

Measured on 2026-11-24 with Draftsman after 0.7.0 (at `a51520e`); the declared relations are the same as 0.3.0's.

## Run

From any directory, with `DRAFTSMAN` pointing at `skills/draftsman/scripts` of this repository (see [the index](../README.md#re-running)):

```bash
git clone https://github.com/ktorio/ktor ktor && git -C ktor checkout cc3d345bc2
cd ktor
python3 "$DRAFTSMAN"/extract.py . --lang kotlin \
  --exclude '**/test/**' --exclude '**/test-*/**' --exclude '**/testData/**' \
  --exclude '**/*-test/**' --exclude '**/*-test-*/**' --exclude '**/*-tests/**' \
  --exclude '**/build/**' --exclude 'build-logic/**' --exclude 'build-settings-logic/**' -o ir.json
python3 "$DRAFTSMAN"/render.py ir.json view.json -o focus.mmd
"$DRAFTSMAN"/validate.sh focus.mmd
python3 "$DRAFTSMAN"/render.py ir.json view.json --format svg -o focus.svg
python3 "$DRAFTSMAN"/render.py ir.json view.json --format html -o viewer.html
```

`**/test/**` also matches a package directory named `test` (`io/ktor/server/test/base`); here those packages live only in the test-support modules, which are excluded anyway. Excluding only `**/test/**` while keeping those modules would leave their users pointing at types that are not extracted.

`view.json`:

```json
{
  "focus": "HttpClientCall",
  "hops": 1,
  "hidden": ["*#get*", "*#set*"]
}
```

## Result

`extract.py` prints:

```text
draftsman: 1578 files, 2137 types, relations: association 1686, dependency 3775, extends 714, implements 722, body dependency 2872, 586 unresolved (49 ambiguous, 537 outside the sources), 0 diagnostics
```

| Files | Types | association | dependency | extends | implements | body dependency | Unresolved | Diagnostics |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1578 | 2137 | 1686 | 3775 | 714 | 722 | 2872 | 586 (49 ambiguous, 537 outside) | 0 |

Types by kind: 1406 classes, 73 abstract classes, 277 interfaces, 266 objects, 69 enums, 46 annotation classes.

The Mermaid and SVG renders of the view draw 38 boxes and 104 relations (`HttpClientCall` and its neighbours one hop away), and the Mermaid file passes `validate.sh`. The HTML viewer carries all 2137 types, as 1688 boxes with 449 nested types folded into their outer types, and 5275 relations (body relations among them) and opens on the same focus. No inferred edges.

## Unresolved

586 references to 252 names, every one with a hint: 49 ambiguous, 537 outside the sources.
Ktor imports almost everything with star imports (`import kotlinx.coroutines.*`):

- Coroutine, reflection and serialization types are resolved through the Kotlin library
  tables when the file star-imports their package (see
  [lang-notes](../../../skills/draftsman/references/lang-notes.md#kotlin)): 377 references
  that were unresolved before, 90 of them supertypes, now `implements` and `extends`
  relations to external ids (`class X : CoroutineScope` 47 times, `AbstractDecoder` 8,
  `KSerializer` 6, `CoroutineDispatcher`, `CopyableThrowable`, `AbstractEncoder`).
  `: JsAny`, a core type like `Any`, adds 12 more supertypes.
- 7 names of those tables stay unresolved on purpose: they are written in a class whose
  external supertype may declare a nested type of the same name, which Kotlin would pick
  first (Netty handlers, `java.io` streams).
- `Runnable` is not in the table: in kotlinx.coroutines it is `java.lang.Runnable` on the
  JVM (an `actual typealias`), so it stays the uncertain default import below. `Json` is
  not taken from it either, as kotlin.js has a default import of that name.
- The other library types have no table: servlet (`HttpServletRequest` 28,
  `HttpServletResponse` 22), `java.nio.ByteBuffer` 24, Netty (`ChannelHandlerContext` 17),
  kotlinx.io (`Source`), Apple's `platform.Foundation` (`NSURLSession`, `NSError`) and
  `kotlinx.cinterop` (`COpaquePointer`).
- 34 are default imports that a star import of an outside package could shadow, so they
  are not certain (*may be the default import java.lang.ClassLoader*): `ClassLoader`,
  `Runnable`, `Class`, `Map.Entry`.
- 49 are ambiguous: they share a simple name with a top-level project type (`Callback`,
  `Request`, `Logger`, `HttpRequest`, `Uint8Array`); the project types are listed as
  candidates and none is picked. A project type nested in another class cannot be meant
  outside it, so it is no candidate there; 18 hints name such types instead
  (*project nested type of the name, out of scope here: ...*), for `Map.Entry`,
  `IOException`, `Config`, `File`.
- 32 are dotted names whose head is itself one of the above (`Map.Entry`,
  `Flow.Subscription`).
- 45 are opt-in markers named as class literals in `@OptIn(...)`, star-imported from
  `kotlinx.cinterop` (`ExperimentalForeignApi` 21, `UnsafeNumber` 7),
  `kotlinx.coroutines` (`ExperimentalCoroutinesApi` 7, `DelicateCoroutinesApi`) and
  `kotlin.experimental` and friends; `ExperimentalUnsignedTypes` is a default import that
  the `kotlinx.cinterop.*` star import could shadow.

65 of the 586 are supertypes; the rest are member types and annotation arguments, which
would draw nothing if resolved (fields, signatures and annotations of external types make no
relation).

## What it covers

- Names in bodies (`evidence: "body"`): 3443 names are drawn as 2872 body dependencies, and each matches what the Kotlin compiler resolves there (`bench/kotlin_oracle`: 1089 compilations of every target a Linux host builds, a file's answer only where all its compilations agree; 0 mismatches). Not checked: 27 names in modules Ktor's build leaves out (ktor-client-tracing and stetho, not in its settings; ktor-client-webrtc-rs, which needs cargo), which the extractor reads as any other; Apple source sets (`darwin/`, `ios/`, ...) draw nothing, as no Linux host compiles them. Code outside every type draws nothing (3967 of the 7600 project type names the compiler finds in bodies; #8).
- Kotlin Multiplatform: `expect` declarations and their `actual`s in other source sets become one type at the `expect`, every member once (56 types carry `expect`).
- 266 objects, 210 data classes, 59 sealed types, 55 `external` declarations for Kotlin/JS and 46 annotation classes.
- Library supertypes: with `"externals": true` in the view, the 102
  library supertypes (`CoroutineScope`, `AbstractDecoder`, `JsAny`, ...) are drawn as external
  boxes; the numbers above do not count them, as the view leaves externals out.
- Function types (`suspend (HttpResponse) -> Boolean`, `HttpRequestBuilder.() -> Unit`, also in supertypes such as `ClientHook<suspend (HttpResponse) -> HttpResponse?>`): every project type they name is a dependency.
- Annotations: 446 dependencies, mostly opt-in and DSL markers (`InternalAPI` named by 203 types, `KtorDsl` by 119); `"annotations": false` leaves them out of a diagram. `@Serializable(with = X.Companion.Serializer::class)` reaches the serializer nested in a plain companion object.
