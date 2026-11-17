# Recall denominators

Hand-written from the Java sources at the pinned commits of `tasks.yaml`, before any measured
run, following RUBRIC.md ("Edge labels", "Recall denominators"). No Draftsman output was used.
Scope: petclinic and jsoup `src/main` (jsoup without `org/jsoup/examples/**`, with
`src/main/java11`); Netty everything except `**/src/test/**`, `testsuite*/**`, `*-tests/**`,
`microbench/**`, `example/**`.

One row per ordered pair (user, used). `evidence` is `declared` if any declared evidence
exists, else `body_only`; `kind` is `inheritance` only for a direct `extends`/`implements`.
`file_line` is one piece of the strongest evidence; its line contains the target's simple name.

## Counts

| Repo | Focus | Out declared | Out body only | Out total | In declared | In body only | In total |
|---|---|---:|---:|---:|---:|---:|---:|
| spring-petclinic | PetClinicRuntimeHints | 0 | 3 | 3 | 1 | 0 | 1 |
| spring-petclinic | OwnerRepository | 1 | 0 | 1 | 3 | 0 | 3 |
| spring-petclinic | Owner | 3 | 0 | 3 | 4 | 0 | 4 |
| jsoup | Safelist | 7 | 3 | 10 | 2 | 0 | 2 |
| jsoup | NodeInternals | 6 | 2 | 8 | 0 | 6 | 6 |
| jsoup | Connection | 8 | 0 | 8 | 4 | 0 | 4 |
| netty | ChunkedStream | 4 | 1 | 5 | 0 | 3 | 3 |
| netty | Socks4ClientEncoder | 5 | 4 | 9 | 0 | 1 | 1 |
| netty | CleanableDirectBuffer | 0 | 0 | 0 (n/a) | 32 | 0 | 32 |

Of the 32 types that use CleanableDirectBuffer, 6 implement it.

### Collapsed to top-level types (the main scoring)

RUBRIC.md scores on top-level types: both ends of every row are collapsed to the outermost
type that contains them, and a pair that collapses onto itself is dropped. Five rows were
added for this, after review and before any measured run: the four types that use
`Connection` only through its nested types (`CookieUtil`, `UrlBuilder`,
`UrlConnectionExecutor`, `HttpClientExecutor`) and `Connection.Response → StreamParser`.
No other focus has a relation that only its nested types carry.

| Repo | Focus | Out (nested / collapsed) | In (nested / collapsed) |
|---|---|---:|---:|
| spring-petclinic | PetClinicRuntimeHints | 3 / 3 | 1 / 1 |
| spring-petclinic | OwnerRepository | 1 / 1 | 3 / 3 |
| spring-petclinic | Owner | 3 / 3 | 4 / 4 |
| jsoup | Safelist | 10 / 6 | 2 / 2 |
| jsoup | NodeInternals | 8 / 7 | 6 / 6 |
| jsoup | Connection | 8 / 5 | 4 / 8 |
| netty | ChunkedStream | 5 / 5 | 3 / 3 |
| netty | Socks4ClientEncoder | 9 / 9 | 1 / 1 |
| netty | CleanableDirectBuffer | 0 / 0 (n/a) | 32 / 24 |

The nested counts are the focus's own rows; the five rows above count only collapsed.

T1 (`spring-petclinic/_T1_all.csv`): 25 production types, 40 relations: 33 declared (8 of
them inheritance) and 7 body only.

## Decisions applied

- A qualified reference to a nested type (`Connection.Request`, `Range.Spans`,
  `ChannelHandler.Sharable`) is recorded as a relation to the nested type; the main scoring
  collapses it to the outer type (see above).
- A relation needs the type's name in the user's code. Uses without the name are not
  counted: a call on an expression of that type, or a nested class using its outer
  instance's field.
- Anonymous classes and enum-constant bodies belong to the enclosing named type.
- A generic argument in a supertype clause (`JpaRepository<Owner, Integer>`,
  `ChunkedInput<ByteBuf>`) is `declared`, kind `other`.
- An `import` used only by Javadoc is not a relation.

## Uncertain

- **Connection incoming (4).** If a qualified nested-type reference also counted for
  the outer type, 8 more types would use `Connection`: `helper.CookieUtil`
  (`Connection.Request`), `helper.UrlBuilder` (`Connection.KeyVal`),
  `helper.UrlConnectionExecutor` and `helper.HttpClientExecutor` (java11) (`Connection.Method`),
  `HttpConnection.Base`, `HttpConnection.Request`, `HttpConnection.Response` and
  `HttpConnection.KeyVal` (`Connection.Base`/`Request`/`Response`/`KeyVal`). Under the same rule,
  `NodeInternals -> nodes.Range` and `Socks4ClientEncoder -> channel.ChannelHandler` would be added.
- **Imports with no code use.** `helper.DataUtil`, `helper.RequestAuthenticator` and
  `parser.StreamParser` import `org.jsoup.Connection` but use it only in Javadoc.
  They are left out.
- **`Cleaner.CleaningVisitor -> Safelist`.** It calls `safelist.isSafeTag(...)` on the outer
  `Cleaner`'s field (`safety/Cleaner.java:152,166,176`) but never names `Safelist`. It is
  left out. Only `Cleaner` itself is counted.
- **Unnamed return types.** `Socks4ClientEncoder` calls `msg.version()` and `msg.type()`,
  which return `SocksVersion` and `Socks4CommandType`, but never names those types. They
  are left out.
- **`PetClinicApplication -> PetClinicRuntimeHints`.** This is a class literal inside a
  type annotation (`@ImportRuntimeHints(PetClinicRuntimeHints.class)`). It is labelled
  `declared` (annotation). It could be argued to be neither a declaration type nor a body use.
- **`Vet -> NamedEntity`.** The only use is the method reference `NamedEntity::getName`
  (`vet/Vet.java:62`), labelled `body_only`. `Vet` extends `Person`, not `NamedEntity`, so it
  is not indirect.
- **Focus to its own nested types.** These are counted as outgoing: Safelist's 4 value
  classes and Connection's `Method`, `KeyVal`, `Request` and `Response`. `Safelist.TypedValue`
  and `Connection.Base` are used only by other nested types, so they are not counted.
- **Overrides in nested classes.** `UnpooledByteBufAllocator.Instrumented*DirectByteBuf`
  name `CleanableDirectBuffer` in their own override signatures. They are labelled
  `declared`, not indirect.
- **The `focus.yaml` counts differ** from these rows. Those counts came from grep: for
  example, Connection used_by 11 vs 4 here, and CleanableDirectBuffer used_by 24 vs 32 here
  (24 matches its files, not its types).
