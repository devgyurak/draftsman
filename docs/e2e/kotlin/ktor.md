# Ktor — Kotlin

An asynchronous client and server framework, Kotlin Multiplatform: common code with `expect` declarations and `actual`s for JVM, native, JS and Wasm, across about 140 Gradle modules.

| | |
|---|---|
| Repository | [github.com/ktorio/ktor](https://github.com/ktorio/ktor) |
| Commit | `cc3d345bc2` (2026-11-16) |
| Extracted | the whole repository without test source sets (`<module>/<platform>/test`), test-support modules (`ktor-server-test-host`, `ktor-client-tests`, ...), the compiler plugin's test data and the Gradle build logic |

Measured on 2026-11-26 with Draftsman 0.11.0 (at `b631f56`; 0.11.0 extracts the same `ir.json`). In 0.11.0 (#9) declarations name more: a supertype's type arguments, typealiases of suspend function types and function types in parentheses, context parameters, an extension property's receiver, annotations on accessors and enum entries, an `expect class` beside an `actual typealias` of a class outside the sources (`Charset`): 447 declared relations added; the body relations are the same. What is left unread against the compiler is #10's: types several source sets declare at one id. 0.10.0's note: a star import of a package the tables know comes before the default imports: two `Json` names (`import kotlinx.serialization.json.*`) are no longer unresolved.

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
draftsman: 1578 files, 2137 types, relations: association 1713, dependency 4170, extends 719, implements 742, body dependency 2970, 584 unresolved (49 ambiguous, 535 outside the sources), 0 diagnostics
```

| Files | Types | association | dependency | extends | implements | body dependency | Unresolved | Diagnostics |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1578 | 2137 | 1713 | 4170 | 719 | 742 | 2970 | 584 (49 ambiguous, 535 outside) | 0 |

Types by kind: 1406 classes, 73 abstract classes, 277 interfaces, 266 objects, 69 enums, 46 annotation classes.

The Mermaid and SVG renders of the view draw 39 boxes and 108 relations (`HttpClientCall` and its neighbours one hop away), and the Mermaid file passes `validate.sh`. The HTML viewer carries all 2137 types, as 1688 boxes with 449 nested types folded into their outer types, and 5415 relations (body relations among them) and opens on the same focus. No inferred edges.

## Unresolved

584 references to 251 names, every one with a hint: 49 ambiguous, 535 outside the sources.
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
  JVM (an `actual typealias`), so it stays the uncertain default import below. `Json`, which
  kotlin.js also has as a default import, is taken from a star import of its package, which
  comes first.
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

65 of the 584 are supertypes; the rest are member types and annotation arguments, which
would draw nothing if resolved (fields, signatures and annotations of external types make no
relation).

## What it covers

- Names in bodies (`evidence: "body"`): 3565 names are drawn as 2970 body dependencies. 3497 of them the Kotlin compiler checks, and each matches what it resolves there (`bench/kotlin_oracle`: 1089 compilations of every target a Linux host builds, a file's answer only where all its compilations agree; 0 mismatches). Not checked: the other 68, in modules Ktor's build leaves out (ktor-client-tracing and stetho, not in its settings; ktor-client-webrtc-rs, which needs cargo), which the extractor reads as any other; Apple source sets (`darwin/`, `ios/`, ...) draw nothing, as no Linux host compiles them. Code outside every type draws nothing (3967 of the 7600 project type names the compiler finds in bodies; #8).
- Kotlin Multiplatform: `expect` declarations and their `actual`s in other source sets become one type at the `expect`, every member once (56 types carry `expect`).
- 266 objects, 210 data classes, 59 sealed types, 55 `external` declarations for Kotlin/JS and 46 annotation classes.
- Library supertypes: with `"externals": true` in the view, the 102
  library supertypes (`CoroutineScope`, `AbstractDecoder`, `JsAny`, ...) are drawn as external
  boxes; the numbers above do not count them, as the view leaves externals out.
- Function types (`suspend (HttpResponse) -> Boolean`, `HttpRequestBuilder.() -> Unit`, also in supertypes such as `ClientHook<suspend (HttpResponse) -> HttpResponse?>`): every project type they name is a dependency.
- Annotations: 448 dependencies, mostly opt-in and DSL markers (`InternalAPI` named by 205 types, `KtorDsl` by 119); `"annotations": false` leaves them out of a diagram. `@Serializable(with = X.Companion.Serializer::class)` reaches the serializer nested in a plain companion object.
