# Changelog

## Unreleased (first release)

Notes for anyone with `view.json` files written against a development build:

- **0.3.0**: the entries below on nested types and annotations change the default
  focus diagram and the relations in `ir.json`; results measured with 0.2.0 (the
  benchmark's runs among them) are not comparable with 0.3.0 ones.
- **One command draws a diagram, and the skill loads in one call** (#1). A run took about
  twice the turns of the same request answered without the plugin (8.1 against 4.0 in the
  benchmark), most of them steps the agent ran one by one. `scripts/draw.py` extracts,
  scopes (`--focus`, `--hops`, `--members`, `--hide`, `--relations`, `--exclude`,
  `--format`, or a `--view`), renders and checks the Mermaid syntax in one call, and prints
  next to the diagram what judging the scope needs: the repository's size, what was drawn,
  what one more hop would add, what was hidden, the unresolved references of the drawn
  types. Test directories are excluded unless `--tests`. Without `--hops` it draws the
  widest neighbourhood within `--max-types` (30), two hops or one, and says what two hops
  would have drawn (Netty's `ChannelPipeline`: 630 types at two hops, 30 at one). Over the
  limit it draws nothing and lists the options with their type counts, the ones that keep
  every relation first (`--max-types N`, fewer hops, then `--relations` without
  `dependency`, which drops the classes related only by use). The `ir.json` it leaves can
  be passed instead of the path to draw again without extracting. Rendering is unchanged: for a given view
  the diagram is the one `render.py` draws. The `/draftsman` command is gone: a plugin
  command named like the skill is what the `Skill` tool loads for that name (reproduced
  with a minimal plugin on Claude Code 2.1.326), so every run got the command's two
  paragraphs, then searched the filesystem for `SKILL.md`. The skill is now the slash
  command itself, `/draftsman` or in full `/draftsman:draftsman`, with the command's
  arguments, and arrives with its directory. `SKILL.md` carries a minimal view, so `view-schema.md` is only read for the
  rarer keys; the install fallbacks moved to `references/setup.md`. `summary.py --focus
  Name` prints the overview and that type's relations in one call.
- **A focus diagram folds nested types into their outer type** (#3). A type related only
  to a nested type of the focus was left out: jsoup's `CookieUtil` uses
  `Connection.Request`, and nesting is no relation. Now `Connection.Request` is drawn as
  part of `Connection`, so `CookieUtil → Connection.Request` is one arrow to `Connection`
  and a relation inside one box draws nothing. A nested type's `extends`/`implements` is
  no inheritance of its outer type: it is drawn as a labelled dependency (`Element ..>
  NodeVisitor : TextAccumulator implements`), unless the outer types inherit themselves
  (jsoup's `NodeVisitor`:
  `W3CDom`, `Element`, `StreamParser`, `Cleaner` and the example `HtmlToPlainText`). The arrow
  keeps its nested source location,
  an association's label names the nested member (`Response.cookies`), and the HTML viewer
  and the SVG title block say that nested types were folded. jsoup's `Connection` at one
  hop: 12 boxes, missing `CookieUtil`, `UrlBuilder` and `StreamParser` -> 11 boxes with all
  three. The new view key `nested` restores one box per nested type (`"boxes"`), and then
  the neighbourhood starts from the focus and its nested types (20 boxes). Without a focus
  nothing is folded unless `"nested": "fold"` is set; a focus on a nested type keeps its
  box. The HTML viewer of a focused view folds as the diagram does (jsoup's 230 types are
  96 boxes); its search still finds nested types, in their box. `summary.py --type` lists
  the relations of a type's nested types too. Every e2e page's render numbers changed
  (jsoup `Element` ±1: 101 -> 39 boxes; 63 of the 101 were nested types, 42 of them
  `Evaluator`'s, now drawn as their outer types).
- **Annotations create relations** (#4). An annotation, attribute or decorator on a type,
  a member or a parameter is a dependency of the type, `via` `@Name`: on the annotation
  type when it is the project's (Netty `@Sharable` -> `ChannelHandler.Sharable`), and on
  the project types named in its arguments: class literals (`@ImportRuntimeHints(
  PetClinicRuntimeHints.class)`, `typeof(X)`, `X::class`, unresolved like a signature
  type when they name nothing known), and names that may be types or values (`E.V`,
  `nameof(X)`, `@admin.register(User)`, `@Module({imports: [UsersModule]})`), drawn only
  when they are project types. Framework annotations stay names. C# `[Marker]` is
  `MarkerAttribute`. A focus area follows an annotation only from the annotated type to
  what it names, so a marker does not pull in every other type that carries it (Netty's
  `channel.unix.Unix` at two hops: 2 types, not 124 through `@UnstableApi`); a focus on
  the annotation type still shows its users (`UnstableApi` ±1: 124 boxes folded, 134 as
  `"boxes"`). `"annotations": false` leaves the arrows
  out (Ktor's `InternalAPI` is named by 203 types).
  Relations: spring-petclinic 73 -> 74, Netty 17600 -> 17812, eShopOnWeb 356 -> 366,
  eShop 924 -> 959, Serilog 560 -> 566, nowinandroid 388 -> 416, Ktor 6451 -> 6897, nest
  2304 -> 2307, Django 1853 -> 1865; jsoup, TypeORM, httpx, leveldb and POCO unchanged.
  Unresolved: eShop 525 -> 526 (`typeof(JsonStringEnumConverter<OrderStatus>)`), Ktor 541
  -> 586 (class literals of opt-in markers from `kotlinx.*` star imports), all outside the
  sources.
- Kotlin: `X.Companion.Inner` names `X.Inner`, the nested type of a plain companion object
  (24 `@Serializable(with = X.Companion.Serializer::class)` in Ktor).

- **Python type ids now carry the package prefix** when the extraction root sits inside a
  package: extracting `django/db/models` gives `django.db.models.query.QuerySet`, not
  `query.QuerySet`. `focus`, `hidden`, `groups`, `notes` and `highlights` that used the
  full old id need the prefix; simple names (`QuerySet`) keep working.
- **Python and TypeScript no longer resolve a supertype's nested type by its simple
  name**, as neither language allows it; such names stay unresolved instead of being
  linked to the base class's member.
- Syntax diagnostics are reported per error span (`line`, `end_line`), not once per file.
- TypeScript: barrel `export *` / `export type *` re-exports are followed, imported type
  aliases are no longer drawn as external types, and a relative import that reaches no
  class is unresolved instead of silently external. On nest `packages/` this corrected 10
  relations that pointed at barrel paths as external types (8 now reach the real
  definition, 2 were type aliases) and found 152 more.
- TypeScript workspaces: imports by package name (`@nestjs/common`, `@acme/core/sub`) are
  linked to the package inside the extraction root, by the exact `name` in its
  package.json. On nest `packages/` the external types dropped from 32 to 9. A package
  name declared by two package.json files is unresolved with both as candidates, never
  picked or treated as external.
- A field whose type is a generic that is not a container (`Repository<User>`,
  `Type<Factory>`, `Observable<Order>` when not configured as a wrapper) keeps its
  association to the outer type and now also depends on the project types among its
  arguments, as method signatures already did. Before, those arguments were dropped,
  which hid the inner class whenever the outer type turned out to be a project type
  (nest's `Type<X>`). Relations grew on every measured project (nest 2086 -> 2103, eShopOnWeb
  +32, leveldb +4, jsoup +3, httpx +1, nowinandroid +1); README numbers are re-measured.
- TypeScript `typeof x` is a dependency when `x` is a class and a value otherwise, never
  an unresolved type (`ReturnType<typeof setTimeout>`).
- C#: SDK implicit usings, `<Using>` items (also from `Directory.Build.props`) and
  `global using` are imports of every file of their `.csproj`. A `global using` of the
  project's own namespace now links names that were unresolved; on eShopOnWeb (none) the
  numbers are unchanged, but `IConfiguration`, `IServiceCollection` and `IUrlHelper` now
  carry the hint that explains them. A namespace the project shares with a library
  (`Microsoft.AspNetCore.Mvc`) counts as a possible source in unresolved hints.
- C#: unresolved hints name where project-wide imports come from
  (`Microsoft.NET.Sdk.Web implicit usings (16 namespaces)`, `1 global using (Acme.Domain.*)`)
  instead of two arbitrary examples.
- C#: every file is read with the first branch of each `#if` (blanked otherwise), so `#if`
  inside a base list, a parameter list, an expression or around a second method header
  no longer breaks the parse (Serilog: 34 diagnostics -> 0, `ILogger` and `PropertyBinder`
  back in the IR; dotnet/eShop: 14 -> 0).
- C#: library type names are no longer turned into `System.X` by name alone. A name is a
  library type, with its real namespace, only when the file imports that namespace
  (`System.Text.Encoding`, `System.Collections.Generic.IEqualityComparer`); `ILogger` is
  `Microsoft.Extensions.Logging`'s, never `System.ILogger`; generic and non-generic
  `IComparer`/`IEqualityComparer` are told apart by their type arguments.
- C#: a file linked into projects with `<Compile Include>` belongs to all of them and gets
  the imports they share; every SDK a project names counts (an extra `<Sdk Name>` no
  longer replaces `Microsoft.NET.Sdk`), and `Aspire.AppHost.Sdk` brings Microsoft.NET.Sdk's
  implicit usings, as does `MSTest.Sdk` (both checked in the SDKs' sources). dotnet/eShop:
  the names its `src/Shared` files, its AppHost and its MSTest project use resolve again.
- Kotlin: `expect`/`actual` declarations merge into one type at the expect, each method
  once (Ktor: 343 duplicated members in 67 types gone); default imports give real ids
  (`kotlin.Exception`, `java.lang.Class`, `kotlin.js.JsAny`), certain unless a star import
  of an outside package could shadow them; `dynamic` is a type keyword; `*.gradle.kts`
  build scripts are not extracted; `vararg` (`String...`), member-extension receivers
  (`Grammar.unaryPlus()`, now also a dependency) and `suspend` stay in signatures.
- A dotted name whose head cannot be found (`Outer.Inner` under a star import) is
  unresolved with the head's hint instead of an external type; only a package head
  (`com.foo.Bar`, C# `System.Text.Encoding`) makes it a qualified external name.
  eShopOnWeb: `EndpointBaseAsync.WithRequest.WithActionResult` is now unresolved.
- Function types are read: Kotlin `(A) -> B`, `R.(A) -> B` and `suspend` forms, TypeScript
  `(a: A) => B`, Python `Callable[[A], B]`, C++ `std::function<R(A)>`. Every project type
  they name is a dependency (a function-typed field is no association). Before, a type
  containing one was unreadable as a whole, so `Map<K, (A) -> B>` lost even its map and a
  supertype like `ClientHook<suspend (HttpResponse) -> Unit>` dropped its relation. Ktor:
  linked references inside function types 69 -> 387, implements +47; nest 2103 -> 2171
  relations, nowinandroid 354 -> 357.
- Kotlin context parameters in function types (`context(Log) () -> Unit`) are dependencies,
  and `suspend`/`context(...)` stay in property and return types too. Container arguments a
  wrapper rule does not follow (the key of `Map<K, V>`) are dependencies of the field,
  in every language: jsoup 1304 -> 1310, nest 2171 -> 2172, httpx 281 -> 283 relations.
- Comments inside a type (a JSDoc block in an inline object type, `/* … */` in a generic
  argument) are no longer part of `type_ref`, in every language.
- **Type aliases are drawn through** to the project types they name, in every language
  (`using Pt = Acme.Point;`, `typealias Pts = List<Pt>`, `type X = A | B`, `typedef
  Circle* CirclePtr;`, Python `type X = ...`): a field of an alias type is an association
  with the multiplicity the alias implies, a signature a dependency, a supertype that is
  an alias of one type an `extends`/`implements`. Before, every alias was a dead end.
- Tuples relate to each element once (`[A, B]`, `(A a, B b)`, `tuple[A, B]`,
  `std::pair`/`std::tuple`); `tuple[P, Q]` and `std::tuple<P, B*>` were read as many `P`.
  Like containers, the tuple names (`Tuple`, `ValueTuple`, ...) and Python `Literal[...]`
  give way to a project class of the same name.
- Wrong facts fixed: C++ `using Base::Base;` inside a class no longer imports `Base::Base`
  (which turned every `Base` of the file into an external type); a Kotlin companion with
  supertypes is its own type `A.Companion`, so `companion object : Creator<A>` no longer
  makes `A implements Creator`.
- Parameters no longer dropped: Python `*args: T`/`**kw: T`, TypeScript `...rest: T[]`,
  C# `params T[]`, C++ parameters with a default value. TypeScript optional parameter
  properties (`protected q?: Q`) are fields. C# 12 primary constructors, and Kotlin ones
  with a plain (non-property) parameter, are listed with all their parameters (a Kotlin
  `vararg val` property is many). Java `throws E` is a dependency.
- No longer unresolved: Python `Literal[...]` (values), `Annotated[X, ...]` (is `X`, also
  with keyword metadata: `Field(gt=0)` made the whole type unreadable), PEP 695 type
  parameters; C# `global::A.B`; C++ in-class `typedef`. C typedefs with several
  declarators (`typedef struct Legacy {…} Legacy_t, *LegacyPtr;`) name the struct, and an
  anonymous `typedef struct {…} Point;` is a type. C++ types in an `inline
  namespace` are found without it (`acme::Versioned`), where they silently vanished.
- Parsing: TypeScript `import("./x").T` types (resolved from that module), Qt's
  statement macros (also `QT_BEGIN_NAMESPACE`, `QML_ELEMENT`, `QML_NAMED_ELEMENT(...)`),
  `Q_INVOKABLE`/`Q_REVISION`/`Q_DECL_...` markers and `signals:`/`slots:` sections, and C++ function-pointer members (now fields, not methods). Kotlin
  `annotation class` has kind `annotation`.
- Measured: nest 2172 -> 2304 relations (aliases, rest parameters, optional parameter
  properties, tuples; `implements` 41 -> 43 through aliases), leveldb 877 -> 885
  (typedefs, `std::pair` elements, default-valued parameters), nowinandroid 357 -> 388
  (dependencies of `@Inject` primary constructors with a plain parameter). Every new
  relation was checked against its source; none were lost.
- **Unresolved references carry a `reason`**: `ambiguous` (project types share the name,
  listed as `candidates`), `outside` (only something outside the sources explains it: a
  wildcard or default import, a nested type of an external supertype) or `unexplained`.
  `extract.py` prints the split (`657 unresolved (72 ambiguous, 585 outside the sources)`)
  and `summary.py` groups by it instead of searching the hint text. Older `ir.json` files
  have no `reason`; `summary.py` then lists every entry in full.
- Wildcard hints name every package outside the sources first and count the ones the
  project also declares after them (`may come from wildcard import kotlinx.coroutines.*;
  or from one of 8 packages the project also declares`); before, the first three star
  imports of the file were shown, project packages among them. A nested class's
  supertype clause now gets the "nested type inherited from" hint of its enclosing type's
  external supertypes too.
- Kotlin: the types of `kotlin.coroutines`, `kotlin.reflect`, `kotlinx.coroutines`,
  `kotlinx.coroutines.channels` and `kotlinx.coroutines.flow` (from their API references)
  get their external id through a star import of their package, when exactly one
  star-imported package has the name and no external supertype could hold a nested type
  of that name. Names whose `actual` is a typealias on some platform (`Runnable`,
  `CloseableCoroutineDispatcher`, `CancellationException`) are left out. Ktor: 931 -> 659
  unresolved, 69 supertypes now drawn as external (`CoroutineScope` 47), 6349 -> 6418
  relations; the other measured projects keep every relation (only hint texts changed, in
  the two eShops).
- Kotlin: kotlinx.serialization (`kotlinx.serialization` and its `descriptors`,
  `encoding`, `modules`, `json` packages) joins the library table; a core type or default
  import of the same name is not overruled by it (`Transient`, kotlin.js `Json`).
  `AutoCloseable` and the common exception classes are known supertypes for the table
  (no nested types). `JsAny` is a core type like `Any`, so `: JsAny` is drawn.
- Candidates of an unresolved name no longer include project types nested in a class the
  reference is not inside, which it cannot mean; the hint names them instead, and the
  reason follows what is left (Netty: 3 `Entry` ambiguous -> outside). TypeScript
  `import Inner = Outer.Inner;` is read as an alias.
- Measured: Ktor 659 -> 541 unresolved (49 ambiguous, 492 outside), 6418 -> 6451
  relations (33 more external supertypes: `AbstractDecoder` 8, `KSerializer` 6, `JsAny`
  12, ...). Every other project keeps its relations and unresolved names.
- C++ macros and directives (POCO, 2ef5cec8a9: 837 -> 2062 types, 2088 -> 9953 relations,
  526 -> 335 unresolved, 3607 -> 389 diagnostics; `Poco::Logger` and `Poco::Channel` were
  missing):
  - an `#if` group is blanked or kept whole, and a directive line (`#define MIN(a, b)
    (...)`, `#pragma pack(push, 1)`) is no code line to judge the next `#if` by. Before,
    the `#endif` after such a line was blanked, which broke the file (leveldb's
    `port/thread_annotations.h`: 10 -> 9 diagnostics; POCO's `String.h`).
  - export macros between `class` and the name by position whatever their name
    (`class Foundation_API Logger :`), and mixed-case ones by name elsewhere, only where a
    declaration goes on (`ACC_PUBLIC` in an expression stays);
  - statement macros on a line of their own (`POCO_CHECK_MINMAX_MACROS`,
    `POCO_DECLARE_EXCEPTION(...)`) and attribute macros before a declaration
    (`POCO_DEPRECATED("...")`, `POCO_NODISCARD_CTOR`) are blanked; a bare upper-case word
    there (`HANDLE Open();`) stays a type.
- C++: a qualified name missing from a namespace the project declares types in is
  unresolved, not external, when the project may declare it out of the parser's sight: it
  is passed to a blanked macro (`POCO_DECLARE_EXCEPTION(API, DataException, Base)`) or named
  in a class head inside a syntax error; the hint says where (POCO: `DataException`,
  `RemoteException` and `XMLException` are no external supertypes, which the classes that
  extend them made them once they parsed). Without such a sign it stays a library's, as a
  project may add to a library's namespace. `std` is never the project's. Java, Kotlin and
  C# packages behave as before (a missing `com.foo.Missing` is still external).
- C++: type aliases of a base class (`using CharacterMap = int[256];`) are found from
  subclasses like its nested types, and so is the base's own name
  (`CodeGenerator::Properties` in a subclass: POCO resolves 31 more references and gains
  115 dependencies on `CodeGenerator`, in 14 classes); a class's own name comes
  before its bases' (POCO: 440 -> 335 unresolved).
- C++ (POCO: 2062 -> 2065 types, 9953 -> 9976 relations, 335 -> 326 unresolved, 389 -> 385
  diagnostics; leveldb unchanged):
  - an attribute macro after a declaration or an enumerator may have a string argument
    with `;` or parentheses (`E POCO_DEPRECATED("since 4.2; use f() instead") = 4,`,
    `void old() POCO_DEPRECATED("use bar() instead");`). Before, it stayed and broke the
    class (`Poco::MongoDB::Database` was missing).
  - value template parameters (`std::size_t N`, with a default, variadic, `auto V`) and
    template template parameters are template parameters: no unresolved `N`, and no
    dependency on a project `struct N` from `Array<P, N>` inside `template <..., std::size_t
    N>`. They are listed with the class (`Array<T, N>`).
  - a name a blanked macro is passed, written without its namespace (`XMLException` in
    `Poco::XML`), gets the "may declare it" hint where that namespace is visible; the
    places are recorded with their namespace, so other namespaces get no such hint. The
    reason is unchanged.
  - every place that passes the name to a macro is kept (bases too: SAXException.h passes
    `XMLException`), and when there are several the hint lists them as mentions, "one of
    them may declare it", a file named after the name first (`XMLException.h`). Before,
    the first in file order was named as the one that may declare it.
- C++: an upper-case name with arguments after a word is an attribute macro only after a
  declarator (`int x_ GUARDED_BY(mu_);`, `VersionSet* const v_ GUARDED_BY(mu_);`), not
  after its type (`const std::string SENTINEL("=?");`, `static const Poco::Timespan
  WAIT(1, 0);`), after a keyword (`explicit URI(const std::string& uri);`: a constructor
  was dropped) or inside a string literal (RemotingNG's code generators). POCO: 385 -> 346
  diagnostics, 8 constructors back, 9976 -> 9978 relations (`URI` -> `Path`, `FIFOIOS` ->
  `BasicFIFOBuffer`); leveldb unchanged.
- End-to-end page for POCO (C++, `2ef5cec8a9`): 2317 files, 2065 types, 9978 relations,
  326 unresolved (system and library headers, POCO's `#define` types, exception classes a
  macro declares, and 20 gaps of Draftsman listed on the page), 346 diagnostics.
- C++ (POCO: 2065 -> 2066 types, 9978 -> 9984 relations, 326 -> 309 unresolved, 346 ->
  333 diagnostics; every other project unchanged):
  - a named union is a type of the new kind `union` (`Poco::Placeholder`); before, its
    members were the enclosing class's and its nested types escaped to the namespace
    (`Poco::Size`, `Poco::Allocation`). The members of an anonymous union still belong to
    the enclosing class.
  - a template specialisation and everything in it are no types; before, its nested
    types came out as types of the namespace (`Poco::NotifyAsyncParams` from
    `AbstractEvent<void, ...>`).
  - a macro call in a class body read as a declarator in parentheses with an error
    inside (`poco_static_assert (offsetof(Header, code) == 0x01);`) is no member, and no
    member is named `sizeof`; 4 `offsetof` members and their dependencies are gone.
  - after `=`, only the first branch of an `#if` group stays (`MAX_ADDRESS_LENGTH =
    #if ... sizeof(struct in6_addr) #else ... #endif`): `IPAddress` and `SocketAddress`
    list `MAX_ADDRESS_LENGTH` instead of `sizeof`, `in6_addr`, ... as enumerators.
  - `typename R::Ptr` (a member of a template parameter) and `Alias::const_iterator`, also
    qualified by the class, are not resolved further; `sizeof(P)`, `alignof(P)` and
    `noexcept(...)` in a template argument are values (no `sizeof` unresolved, no
    dependency on `P`).
- C++: the members of an anonymous struct or union with a variable (`union { char
  buffer[N]; Block* next; } _memory;`) are the variable's, not the enclosing class's; a
  type defined with a variable (`struct Tag { P p; } tagged;`) is the variable's type,
  where before the field's type was the whole body and drew nothing. POCO: 8 members of
  4 classes are no longer listed, 9984 -> 9983 relations (`FastMemoryPool::Block` no
  longer associates with itself through `_memory.next`); leveldb and the other projects
  unchanged.
