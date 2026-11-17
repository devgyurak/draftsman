# Ktor — Kotlin

An asynchronous client and server framework, Kotlin Multiplatform: common code with `expect` declarations and `actual`s for JVM, native, JS and Wasm, across about 140 Gradle modules.

| | |
|---|---|
| Repository | [github.com/ktorio/ktor](https://github.com/ktorio/ktor) |
| Commit | `cc3d345bc2` (2026-11-16) |
| Extracted | the whole repository without test source sets (`<module>/<platform>/test`), test-support modules (`ktor-server-test-host`, `ktor-client-tests`, ...), the compiler plugin's test data and the Gradle build logic |

Measured on 2026-11-17 with Draftsman `3a4f253`.

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
draftsman: 1578 files, 2137 types, relations: association 1686, dependency 3329, extends 691, implements 712, 659 unresolved (72 ambiguous, 587 outside the sources), 0 diagnostics
```

| Files | Types | association | dependency | extends | implements | Unresolved | Diagnostics |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1578 | 2137 | 1686 | 3329 | 691 | 712 | 659 (72 ambiguous, 587 outside) | 0 |

Types by kind: 1406 classes, 73 abstract classes, 277 interfaces, 266 objects, 69 enums, 46 annotation classes.

The Mermaid and SVG renders of the view draw 34 types and 73 relations (`HttpClientCall` and its neighbours one hop away), and the Mermaid file passes `validate.sh`. The HTML viewer carries all 2137 types and 4577 relations and opens on the same focus. No inferred edges.

## Unresolved

659 references to 262 names, every one with a hint: 72 ambiguous, 587 outside the sources.
Ktor imports almost everything with star imports (`import kotlinx.coroutines.*`):

- Coroutine and reflection types are resolved through the Kotlin library table when the
  file star-imports their package (see [lang-notes](../../../skills/draftsman/references/lang-notes.md#kotlin)):
  272 references that were unresolved before, 69 of them supertypes, now `implements` and
  `extends` relations to external ids (`class X : CoroutineScope` 47 times,
  `CoroutineDispatcher`, `CopyableThrowable`, `CoroutineContext.Key`, `SendChannel`).
- 13 names of that table stay unresolved on purpose: they are written in a class whose
  external supertype may declare a nested type of the same name, which Kotlin would pick
  first (`kotlin.AutoCloseable`, `kotlin.Exception`, Netty handlers, `java.io` streams).
- `Runnable` is not in the table: in kotlinx.coroutines it is `java.lang.Runnable` on the
  JVM (an `actual typealias`), so it stays the uncertain default import below.
- The other library types have no table: servlet (`HttpServletRequest` 28,
  `HttpServletResponse` 22), kotlinx.serialization (`SerialDescriptor` 23, `KSerializer`
  20), `java.nio.ByteBuffer` 24, Netty (`ChannelHandlerContext` 17), kotlinx.io (`Source`),
  Apple's `platform.Foundation` (`NSURLSession`) and `kotlinx.cinterop` (`COpaquePointer`).
- 42 are default imports that a star import of an outside package could shadow, so they
  are not certain (*may be the default import java.lang.ClassLoader*): `JsAny`,
  `ClassLoader`, `Runnable`, `Class`.
- 72 are ambiguous: they share a simple name with a project type (`Callback`, `Request`,
  `Logger`, `HttpRequest`, `Map.Entry`); the project types are listed as candidates and
  none is picked.
- 32 are dotted names whose head is itself one of the above (`Map.Entry`,
  `Flow.Subscription`).

## What it covers

- Kotlin Multiplatform: `expect` declarations and their `actual`s in other source sets become one type at the `expect`, every member once (56 types carry `expect`).
- 266 objects, 210 data classes, 59 sealed types, 55 `external` declarations for Kotlin/JS and 46 annotation classes.
- Library supertypes through star imports: with `"externals": true` in the view, the 69
  coroutine supertypes (`CoroutineScope`, `CoroutineDispatcher`, ...) are drawn as external
  boxes; the numbers above do not count them, as the view leaves externals out.
- Function types (`suspend (HttpResponse) -> Boolean`, `HttpRequestBuilder.() -> Unit`, also in supertypes such as `ClientHook<suspend (HttpResponse) -> HttpResponse?>`): every project type they name is a dependency.
