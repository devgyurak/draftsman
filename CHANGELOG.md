# Changelog

## Unreleased (first release)

Notes for anyone with `view.json` files written against a development build:

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
