# Language notes

Read only the section for the language you are working with. "Not handled" items are
known gaps: expect them in `unresolved` or as missing relations, never as invented ones.

Type aliases (`using Pt = Acme.Point;`, `typealias`, `type X = A | B`, `typedef`, `using X
= ...`, Python `type X = ...`) are not types in the IR, but they are drawn through: a
field of an alias type relates to the project types the alias names, resolved where the
alias is declared, with the multiplicity it implies (`typealias Pts = List<Pt>` is many
`Pt`); a signature that uses it depends on them; a supertype that is an alias of one type
is that type. Aliases of aliases are followed.

## Java

- Types: `class`, `interface`, `enum`, `record`, `@interface` (kind `annotation`).
  `abstract class` becomes `abstract_class`. Nested types get ids like `Outer.Inner`.
- Skipped on purpose: local and anonymous classes, lambda parameters, and the bodies of
  enum constants (`SHIPPED { ... }`).
- Record components are private fields. Visibility default is `package`; interface members
  are `public`, interface fields `static`, interface methods without a body `abstract`.
- Resolution: type parameters → nested types of the type, its enclosing types and their
  supertypes → single-type imports → same package → wildcard imports → `java.lang` and
  common JDK types. Inherited member types are found through project supertypes at
  every level, including a nested type's supertype clause (`class Impl implements
  Listener` where the enclosing class inherits `Listener`). A JDK supertype passes on the
  nested types the JDK declares (`Entry` in a `HashMap` subclass is `java.util.Map.Entry`,
  also over the package's own `Entry`): `langs/java_jdk.json` lists the public and
  protected nested types and fields of the JDK 21 types a class can extend, their
  inherited ones too (`bench/javac_oracle/oracle.py jdk` writes it). A supertype named
  through a wildcard import (`extends HashMap` under `import java.util.*`) stays
  unresolved, but is looked up in the table as each wildcard package's. Names that can only
  come from an external wildcard import or another external supertype (`LayoutParams` in
  a `FrameLayout` subclass) stay unresolved with a hint — they could also be same-package
  generated code outside the sources, so they are not guessed.
- Known limit: a nested type of a supertype outside the JDK (Spring, Android) is not
  known, so it does not hide a project type of the same name: a `Validator` subclass
  writing `Foo` gets the project's `Foo` even if `Validator` declared one. The parser
  cannot tell; javac can. Nor does a JDK type that a JDK after 21 gives a new nested type.
  The other way round, code compiled for an older release loses a relation: `Builder` in
  a `Thread` subclass is Thread.Builder (new in 21) to the table, even where it is the
  project's `Builder` under Java 17.
- Known miss: project types declared in `java.lang` (Netty's stubs of `java.lang.Module`
  and `ProcessHandle` for older JDKs) are not implicitly imported; they stay the JDK's.
- Names in bodies (`evidence: "body"`): a receiver (`Foo.bar()`, `Foo.X`, `Foo::m`) is a
  variable before it is a type, as in javac. It draws nothing when a variable of its
  name may be in scope: one declared anywhere in the member (also after the name, so a
  few are lost), a field of the type, of an enclosing type or of an anonymous or local
  class around it (enum constants and record components too, inherited ones through
  project supertypes and the JDK table), or one `import static` brings in (a single
  import of the name always; `a.B.*` when B is the project's or in the JDK table). After
  a type, a field of the next name ends it (`Util.VALUE.trim()` is `Util`), else a nested
  type continues it (`Util.Helper.run()`). Known limit: fields of other types outside the
  sources (a Spring supertype's, `import static org.lib.Consts.*`) are not known and hide
  nothing, the same rule as for their nested types. Known losses: `Owner::new` is read as
  a receiver, so a field `Owner` hides it although a constructor reference takes only a
  type; `import static p.Sub.Nest` (or `p.Sub.*`) of a nested type Sub inherits draws
  nothing for `Nest.run()`. Nothing is read inside the anonymous class of `o.new Inner()
  { }`, which inherits from a member of o's type.
- Type annotations right before varargs (`X509Certificate @Nullable ... certs`) are valid
  Java 8 that the tree-sitter grammar rejects; they are blanked before parsing (same
  length, so line numbers are exact). Annotations on array levels (`String @A []`) are
  read and ignored.
- `throws E` makes the method depend on `E` (it is not listed in the signature).
- Annotations on the type, its members and their parameters are dependencies of the type
  (`via` `@Name`): on the annotation type when it is the project's (`@Sharable` imported
  from `ChannelHandler`), on class literals in the arguments (`X.class`, `X[].class`),
  and on the type of an enum constant or field written there (`Include.NON_NULL`), when
  that is a project type. A bare name in an argument is a constant and draws nothing.
- Not handled: static imports of nested types, `permits` clauses.

## C#

- Types: `class`, `interface`, `struct`, `record` (also `record struct`), `enum`.
  Properties are kind `property`; positional record parameters are public properties.
- `partial` declarations are merged by full name; members from other files carry `file`.
- Namespaces: block and file-scoped. Types of enclosing namespaces are visible
  (`Shop.Orders` sees `Shop.X`), also those the .NET and ASP.NET table gives a namespace
  outside the sources around the code (`Host` in `namespace Microsoft.Extensions.Hosting`),
  before the file's usings. The first part of a qualified name is looked up as a simple
  name is, from the innermost scope out: `Models.Order` in `namespace App.Web` is
  `App.Models.Order` when the namespace `App.Models` exists, and `Lib.Order` where a class
  `Lib` is nearer than the namespace `Lib` is that class's nested `Order` (a `Lib<T>` is
  passed over, also one a block's using brings in: the arity written must fit). At each level a namespace's members, its
  namespaces among them, come before its usings: `Models.Order.Count` is the global
  namespace `Models`'s, not the class `Models` a file-level `using App.Entities;` brings
  in. `using X;` is a wildcard import, `using A = B;` an alias, whose target is looked up
  where the alias is declared (at the top of the file, also before `namespace X;`: from
  the global namespace; after it, from X).
  `global::A.B` is `A.B`. Primary constructors (C# 12, `class Order(IRepo<Order> repo)`)
  are a public constructor whose parameters are dependencies; records keep their
  parameters as properties. `params Q[] qs` is a parameter. Tuples (`(Person a, Point b)`)
  relate to each element once.
- `: Base, IFoo` cannot be split syntactically: project targets are classified by their
  kind; external ones by the .NET convention (`I` + capital letter = interface).
- Defaults: members `private`, interface members `public`; `const` implies static.
- Because `using` imports whole namespaces, framework types (`PageModel`, `ILogger<T>`)
  appear as unresolved "only explained by wildcard imports". `summary.py` groups them. A
  namespace the project also declares types in (an extension class in
  `Microsoft.AspNetCore.Mvc`) still counts as a possible source of such a name.
- Build imports: each file belongs to the nearest `.csproj` above it, and to every
  `.csproj` below the extraction root that compiles it through `<Compile Include>` (a
  shared file linked into several projects gets only the imports all of them have). With
  `<ImplicitUsings>enable</ImplicitUsings>` (in the project or the nearest
  `Directory.Build.props`) the SDK's documented implicit usings are imports of every file:
  `Microsoft.NET.Sdk`, `.Web`, `.Worker` and the Windows Forms / WPF variants, for every
  SDK the project names (`Sdk="A;B/1.0"`, `<Sdk Name>`); `Aspire.AppHost.Sdk` and
  `MSTest.Sdk` import `Microsoft.NET.Sdk` and get its list (MSTest.Sdk adds
  `Microsoft.VisualStudio.TestTools.UnitTesting` with `UseVSTest`). Other SDKs (Razor,
  BlazorWebAssembly) are not verified and get none. `<Using Include>` adds and
  `<Using Remove>` removes a namespace (`Alias`/`Static` items are skipped). A `global
  using` in any file is an import of every file of the same project, and of no other.
- Conditional compilation: every file is read with the **first branch** of each `#if`
  whose condition is not false whatever the symbols (`#if false ... #else` reads the
  `#else`; `!`, `&&`, `||`, `==` and `!=` of `true` and `false` are worked out); the other branches and the directive lines are blanked before parsing (same
  length, so line numbers are exact). tree-sitter cannot parse `#if` inside a base list,
  a parameter list, an expression or around a second method header, and one
  deterministic configuration avoids reading both. The limit: `#if !FEATURE` keeps the
  side where the feature is off. A `#if` line inside a multi-line string (verbatim, raw)
  or a `/* */` comment is no directive.
- Library types: type keywords (`int`, `string`, ...) are builtins. Well-known library
  types (`IDisposable`, `CancellationToken`, `Encoding`, `IEqualityComparer`, `ILogger`)
  are external with their real namespace (`System.Threading.CancellationToken`) only when
  the file imports exactly one namespace that holds them; otherwise they are unresolved
  with the usual hint. `IComparer<T>`/`IEqualityComparer<T>` and their non-generic
  versions are told apart by their type arguments. A project type of the same name
  always wins.
- Attributes on the type, its members and their parameters are dependencies of the type
  (`via` `@Name`): `[Marker]` names `MarkerAttribute` (a project class without the
  `Attribute` suffix is not taken for one), `typeof(X)` in the arguments is a type
  reference, and `E.V`, `nameof(X)` and bare names are drawn when they are project types.
  `[assembly: ...]` attributes belong to no type.
- Names in bodies (`evidence: "body"`; method, constructor, accessor, operator, indexer
  and local function bodies, constructor initializers, field, property and enum member
  initializers, a primary constructor's base arguments, a record's too; not attributes, parameter
  defaults or top-level statements): a name where only a type stands (a local's type,
  `new Foo()`, a cast, `typeof`, `default`, `as`, a pattern's or a `catch`'s type, type
  arguments, a lambda's or local function's parameter types, and `is Foo` alone, which C#
  reads as a type before a constant) is looked up among types; the head of a member
  access (`Foo.Create()`, `Foo.Line.Make()`, `Repo<int>.Make()`), `nameof(Foo)` and a
  constant pattern (`case Status.Open:`, a switch arm's `Foo =>`, `is not Foo`, `is A or
  B`, the head of `is Status.Closed`) may be a variable, and draws nothing where one of
  the name is in scope: a parameter, a local, a pattern, `out`, `foreach`, `catch`,
  deconstruction, lambda or LINQ variable anywhere in the member (also after the name, so
  a few are lost), a field, property, event or primary constructor parameter of the type,
  of the types around it and of their project supertypes, a static field `using static`
  brings in, or a member generated code declares (Razor's `@inject` and `@code` members of
  `X.razor` for `X.razor.cs`, also from `_Imports.razor`; XAML's `x:Name` of `X.xaml` for
  `X.xaml.cs`; CommunityToolkit.Mvvm's `[ObservableProperty]` and `[RelayCommand]`;
  `[JsonSerializable(typeof(T))]`), a C# 14 extension block's receiver parameter, or a
  member of a base class outside the sources: one the .NET and ASP.NET table gives
  (`ControllerBase.User`, `Exception.Data`; `langs/csharp_framework.json`, made by
  `bench/roslyn_oracle/oracle.py framework` from the reference assemblies), and any name
  under a base the table does not know (a package's, MAUI's; a name `I` + a capital is
  taken for an interface, which passes on none). A private field or nested type of a
  project base class is no member of its subclass. A field or property whose type has its
  name (`OrderStatus OrderStatus`) leaves the name the type before a nested type or a
  member that is static wherever it is declared (C#'s "Color Color") when the field's type,
  resolved where the field is declared, is that type (not `Lib.Order Order` in Shop, an
  array, a generic or a struct's `Spot? Spot`) and no extension method of the sources has
  the member's name; the field before any other. A delegate, and an extension block's type
  parameter, hide a type of their name. A `using` in a namespace block or after a
  file-scoped namespace comes before the namespaces around it: a namespace outside the
  sources declares what the table says (System's `Task`), and one the table does not know
  may declare any name the block's project namespaces do not; an alias the file declares
  of one project type (`using O = Shop.Order;`) names that type, unless a namespace around
  declares a type of the name; `<Using Include Alias>` and `<Using Static="true">` items of
  the project file are global usings. A namespace around the code that is a package's
  the project references (the `<PackageReference Include>` id, in the project or its
  `Directory.Build.props`, or in a project its `<ProjectReference>`s reach unless
  `PrivateAssets="all"`, or a namespace below it, case aside: `namespace
  CommunityToolkit.Mvvm.Input.Mine` with CommunityToolkit.Mvvm) and that the table does
  not know may hold any type, which hides a name found further out: such a name draws
  nothing, also where the sources declare types in that namespace. A Razor component (`X.razor`) is a type of its
  `@namespace`, else the nearest `_Imports.razor`'s plus the folders below it, else the
  root namespace plus folders. A `file` type is seen in its file only; a type `internal`
  in another project (or nested in one) only where that project's `InternalsVisibleTo`
  (item or attribute) names the file's assembly. A name the written arity does not fit
  (`Box` where the nearest Box is `Box<T>`) draws nothing; nor does `(Foo) - 1` or
  `(Foo)[0]`, which C# reads as a parenthesized name (an element access before `[`, which
  tree-sitter takes for a cast of a collection expression; `(Foo[])[]` stays a cast), a
  property pattern's path (`{ Customer.Name: "x" }`), or a declaration where C# reads none:
  tree-sitter reads `F(Order < b, Customer > d)`, `[Order < b, Customer > d]` and
  `this[...]` alike as `Order<b, Customer> d`, two comparisons to C#, which declares only
  in an `out` (`ref`, `in`) argument and a deconstruction's tuple (left of `=` or of a
  `foreach`). `value` in a setter (and `init`, `add`, `remove`) and C# 14's `field`
  in a property's accessor are variables, which hide a type of the name. On the three e2e
  repositories tree-sitter's parse of the (preprocessed) sources has no ERROR or MISSING
  node.
- Where a build may resolve a body's name differently, nothing is drawn: a type declared
  in the `#if` branch the parser reads (Serilog's `System.TimeProvider` for older
  targets), a name a type, field or alias of an `#elif`/`#else` branch has (in any file
  of the type), a name the
  file resolves through a `using` in an `#if` branch, an id two build projects declare
  (two projects' `partial class Program`, the implicit `Program` of top-level
  statements), a type of a project the file's project does not reference
  (`<ProjectReference>`, followed through), and in a .NET MAUI app code only a platform's
  build compiles (`Platforms/<platform>/`, `#if ANDROID`, `#if IOS || MACCATALYST`); no
  build compiles `#if false` (nor the `#else` of `#if true`), and its names hide nothing. A
  type gRPC generates from the project's `<Protobuf Include>` (each .proto's messages,
  enums and services, in its `csharp_namespace`) hides a type of the name a `using`
  brings in, also for declared relations. Checked against Roslyn (`bench/roslyn_oracle`,
  each file's compilations joined; a place they resolve differently is no answer): 0
  mismatches on eShopOnWeb, eShop and Serilog, and on the reviews' sets of sources written
  by hand but for two known limits (`bench/roslyn_oracle/review`, `oracle.py review`).
- Known limits of bodies: an `#if` the parser reads takes its first branch, so a symbol no
  build defines (`#if NEVER_DEFINED`) and `#if !DEBUG` (the key builds Debug) draw where
  no build compiles. Lost: under a base class outside .NET and ASP.NET, every name where a
  variable may stand (7 on eShop's MAUI app); behind a namespace the table does not know
  in a nearer using (2 on eShop); found further out than a package's namespace around the
  code (the rule above), also an alias's target there: a project that puts its own code
  below a package's namespace loses the names its usings, the namespaces around and
  qualified names give (eShopOnWeb 1, in `namespace Ardalis.GuardClauses`;
  serilog-sinks-file's `src` at `4c8e677`, in `namespace Serilog` and
  `Serilog.Sinks.File` of the Serilog package, 13 body dependencies instead of 20); a qualified name whose first part another project's internal
  type or a project the file's does not reference takes (`Models.Order` where `App.Models`
  is such a class or namespace), or that starts with `global::`; a receiver whose head a
  field of the file's `using static` shares while a namespace of the name comes first, and
  one whose name another member of the type binds as a variable; a name of the table's ASP.NET
  namespaces around the code where the project does not reference ASP.NET (the table is
  one for every project); a name through a namespace alias or an alias of a generic
  (`M.Order` with `using M = Shop.Models;`); a `file` type's name, and in another file a name it
  shares; a Color Color name before a member an extension method shares (`Of`); names in
  top-level statements
  (no type the extractor sees holds them), after `global::`, through an alias another
  file declares, a parameter or a local of its type's name (Color Color, whose type is
  not kept), a static member beside an instance overload of its name, a name a file's
  `using static` brings a field of (C# looks at the namespaces around first), a type of
  another arity further out (`Lib.Box` beyond `Box<T>`), and a name a switch arm's
  pattern variable shares elsewhere in the member, a local function's type parameter's
  (`typeof(Money)` elsewhere in a method whose local function is `M<Money>()`), a type
  named as a pointer's (`Point* p`), and a type named `var` or `nameof` where a declaration
  or a call would be read. Drawn where it may be wrong: a
  namespace around the code of a package the project does not reference itself (one that
  comes through another package or the SDK) is taken for the project's.
- Not handled: extension methods (they stay members of their static class, which is
  correct but not linked to the extended type), the .NET 8 rule that drops `System.Net.Http` for .NET Framework targets.
  Declared relations ignore project references and the arity written (`Repo<int>` may
  resolve to a `Repo` of the namespace around), take types of one id from two projects
  for one (`Program`), see the `using X = ...` alias of a file without a namespace in
  every file, and in a file-scoped namespace look at the file's aliases before the
  namespaces around it (C# after).

## Kotlin

- `class`, `interface`, `enum class`, `object` (kind `object`), data/value/sealed classes
  (modifiers). Properties are kind `property`; `val`/`var` primary-constructor parameters
  are properties, plain constructor parameters are not.
- Companion object members become `static` members of the enclosing class. A companion
  with supertypes (`companion object : Parcelable.Creator<A>`) is the object that
  implements them, so it is a nested type `A.Companion` (or its own name,
  `A.Factory`) of kind `object`, and the supertypes are its relations, not `A`'s.
- `annotation class` has kind `annotation`, as in Java.
- Supertypes: `Base()` (constructor call) is a superclass; a bare type in a class's list is
  an interface (Kotlin requires the call for classes), so external ones are `implements`.
- Visibility default `public`. Top-level extension functions belong to no class; a member
  extension keeps its receiver (`+ Grammar.unaryPlus()`), and the receiver type is a
  dependency. `vararg` parameters read as `String...`, `suspend` stays in function types.
- The primary constructor is listed as `constructor(...)` with all its parameters when one
  of them is plain (no `val`/`var`), and its parameters are dependencies. When all are
  properties (`data class Point(val x: Int, val y: Int)`) it is not listed: the properties
  already say it. A `vararg val` property is `items: Item...` (multiplicity `*`).
- Properties without a written type (`val state = MutableStateFlow(...)`) have no type:
  the initialiser is not evaluated, so no relation.
- `expect`/`actual`: the expect class and its actuals are one type, located at the expect
  declaration. A method or constructor declared again in another file with the same
  receiver, name and parameter types is one member (the expect's is kept); look-alikes
  within one file are overloads and all stay.
- Default imports (kotlinlang.org/docs/packages.html#default-imports: `kotlin.*` and its
  `annotation`, `collections`, `comparisons`, `io`, `ranges`, `sequences`, `text`, `math`
  subpackages, plus `java.lang.*`/`kotlin.jvm.*` on the JVM and `kotlin.js.*` on JS, used
  together) give external ids with their package: `kotlin.Exception`, `java.lang.Class`,
  `kotlin.js.JsAny`. The core types (`String`, `Int`, `Exception`, and Kotlin/Wasm's
  `JsAny`, written where `Any` would be) are always taken;
  the others only when no star import of an outside package could also provide the name
  (the documentation gives no priority between star and default imports), else they stay
  unresolved with "may be the default import ..." in the hint. A project type of the name
  wins. `dynamic` (Kotlin/JS) is a type keyword: nothing to draw, nothing unresolved.
- Library types through star imports: the types (classes, interfaces, objects, enums,
  annotation classes; no functions, no typealiases) of `kotlin.coroutines`,
  `kotlin.reflect`, `kotlinx.coroutines`, `kotlinx.coroutines.channels`,
  `kotlinx.coroutines.flow` and of kotlinx.serialization (`kotlinx.serialization`, its
  `descriptors`, `encoding`, `modules` and `json` packages), as their API references on
  kotlinlang.org list them and the sources of the versions Ktor builds with confirm
  (kotlinx.coroutines 1.11.0, kotlinx.serialization 1.11.0), get their external id
  (`kotlinx.coroutines.CoroutineScope`) when the file star-imports the package and exactly
  one of the star-imported packages has the name (two would be an ambiguity error in
  Kotlin). The project's own types, explicit imports and the file's own package come
  first; a core type or default import of the same name is not overruled (`Transient`,
  and `Json`, which kotlin.js also has, stay as they are). `CoroutineContext.Key` follows its head. The table is not used where a
  nested type of an external supertype could have the name, as Kotlin would take that
  first: under a supertype whose nested types are not known (Netty, `java.io`), the name
  stays unresolved with both hints. Known: the common supertypes of those libraries, and
  `kotlin.AutoCloseable`, `Throwable`, `Exception`, `RuntimeException`,
  `IllegalStateException`, `IllegalArgumentException` (none declares a nested type, nor do
  their java.lang classes on the JVM). Names whose
  `actual` is a typealias on some platform are left out: `Runnable` (`java.lang.Runnable`
  on the JVM, so still the uncertain default import), `CloseableCoroutineDispatcher`, and
  `CancellationException` (also in `kotlin.coroutines.cancellation`). Other libraries (kotlinx.serialization, kotlinx.io,
  Netty, servlet) have no table: their names stay unresolved with a hint.
- Gradle build and settings scripts (`*.gradle.kts`) are not extracted; other `.kts`
  scripts are.
- Function types (`Route.() -> Unit`, `suspend (Call) -> Unit`, `context(Log) () -> Unit`,
  also inside containers) make a dependency on every project type they name; a field of such a type is no
  association. Supertypes with a function type among their arguments are read too.
- Annotations on the type, its members, constructor properties and parameters are
  dependencies of the type (`via` `@Name`): on the annotation class when it is the
  project's (`@OptIn(InternalAPI::class)` depends on `InternalAPI` twice over: `@OptIn`
  is Kotlin's, the class literal is the project's), on `X::class` and `Outer.Inner::class`
  in the arguments, and on `E.V` when `E` is a project type. Opt-in markers make some
  annotation classes hubs (Ktor's `InternalAPI` is named by 203 types); a focus area does
  not spread through them, and `"annotations": false` in the view leaves those arrows out.
- A plain `companion object`'s types are recorded as the class's (`Receipt.Parser`), so
  `Receipt.Companion.Parser` is read as `Receipt.Parser`.
- `typealias` is an alias (see the note on aliases below). Not handled: delegation targets
  (`by x`).
- Names in bodies (`evidence: "body"`; function bodies, property initializers, getters
  and setters (also on the lines after their property) and delegates, default arguments, `init` blocks, secondary constructors and
  their delegation, a superclass's constructor arguments, a class's delegate `by x`, an
  enum entry's arguments and body, and what is inside them: lambdas, anonymous objects,
  local classes and functions): a name where only a type stands (a local's or a
  parameter's type, `is`, `as`, type arguments, `catch`, a local class's or an anonymous
  object's supertypes, `super<Foo>`) is looked up among types; the head of a member access
  (`Foo.x`, `Foo.Line.x`, `Foo::class`, `Foo::bar`), what is called (`Foo(1)`,
  `Outer.Inner()`, `::Foo`) and a name standing alone where a value does (an object or a
  companion: `listOf(Registry)`, `val x = Loading`, `when (s) { Loading -> }`,
  `"$Registry"`, `Cause.Missing`) may be something else, and draws nothing where a
  variable of the name is in scope (a parameter, a local, a lambda's, `for`, `catch` or
  destructured name, a local function, anywhere in the member), a property or enum entry
  of the type, of the types around it and of their project supertypes, a constructor
  parameter (its name, not a name in its default value), a property declared at any
  file's top in the sources (`val ContentNegotiation`), a member of an extension's
  receiver (`fun Ctx.ext()`: its instance properties and functions, also those of its
  supertypes outside the sources as far as the table knows them, not its nested types;
  a receiver that is a type parameter is its bounds, `<T : Ctx>`, `where T : Ctx`, an
  alias the class it names, also a library one; an anonymous function's receiver, `fun
  Ctx.() = ...`, is one too, and its simple name a type in the body), or, for a call, a function of
  the name declared at any file's top or a method of the types around (`Money(1, 2)`
  beside `class Money`: which one is called depends on the arguments). A typealias draws
  the class it names directly (`typealias Cash = Money`), wherever it is declared; one of a
  generic or a function type draws nothing in a body (declared relations draw the types
  inside it: `val c: Cashes` with `typealias Cashes = List<Money>` depends on `Money`).
  What a build decides, read from the sources: a platform source set (Ktor's
  `<module>/jvm/src`, Gradle's `src/jvmMain/kotlin`; the module is the nearest directory
  with a build script) sees its own types and the common ones (`common`, `commonMain`,
  `main`), not another platform's; a type of the file's package in another module only is
  taken only where no star or default import could bring in the name (the module's
  dependencies are the build's); a private top-level class only in its file (each
  platform's own private class of one id is that id there); an Apple source set (`ios`,
  `macos`, `tvos`, `watchos`, `darwin`, `apple`) draws nothing, as no answer key here
  compiles it; in a file that star-imports a Kotlin/Native platform library
  (`platform.posix.*`), whose C functions take any name, a call of a class's name draws
  nothing (`WinHttpConnect(...)`). Kotlin's lookup: a class sees its superclasses' nested
  types by simple name, not an interface's, nor those of a superclass's companion object
  (its own, and those of the types around it, it sees); `import p.Money as Coin` hides
  `Money` in the file, also through a star import and the file's package. Supertypes
  outside the sources: under one `kotlin_outside.json` knows (the standard library,
  kotlinx coroutines, serialization and io, the JDK's common packages, as the Kotlin
  compiler sees them: `bench/kotlin_oracle/oracle.py table`), a name draws nothing where
  the supertype has a member of it a subclass sees (public and protected properties and
  functions, its companion's and Java's static members, nested types through
  superclasses only; a private or package-private one hides nothing); under one it does
  not know, nothing is hidden, as in Java. Checked against the Kotlin compiler
  (`bench/kotlin_oracle`): nowinandroid 150 names, Ktor 3,497, no mismatch.
- Known limits of bodies. Drawn where it may be wrong: a member or nested type of a
  supertype the table does not know (Android, Gradle, Netty) that shares a project type's
  name the file sees (androidx.work's `CoroutineWorker` passes on `Result`: e2e 0); a
  lambda with a receiver (`with(c) { Money(1) }`, `routing { }`, also beside its written
  type, `val e: Ctx.() -> Int = { Money(1) }`): which lambda has one, and of what type, is
  its context's, not the syntax's; a module the build leaves
  out (Ktor's ktor-client-tracing and stetho, not in its settings, and webrtc-rs, which
  needs cargo: 68 names), as the extractor does not read Gradle's settings; a platform
  source set's types are taken as the common ones' where the sources lay them out
  otherwise. Lost: everything in code outside every type, top-level functions and
  properties (no type in ir.json to draw from: nowinandroid 300 names of 454, Ktor 3,967
  of 7,600; #8); annotations in a body; a call of a class's name beside a function of the
  name anywhere in the sources (Ktor 15, for 125 wrong ones kept out), in a file
  star-importing a native platform library (Ktor 36, for 1), a name beside a top-level
  property of it anywhere (Ktor 3), a class of an id another platform's file declares
  private (Ktor's `DatagramSendChannel`, private in `web/`, internal in `jvm/`: 2), a type of another platform's source set a platform one
  depends on (`jvmAndPosix` from `jvm`: Ktor 12); a type a name finds through a star
  import or a nested type of an interface or a companion when another type of the name
  comes first; in type positions, a name an import of an enum entry or an object's
  member brings in (`import shop.Kind.A`, where Kotlin looks for a class `A`); in a
  member with a local extension or an anonymous function with a receiver, its receiver's
  members everywhere in the member; a qualified or generic anonymous function's receiver
  type (`fun shop.Ctx.()`); a
  superclass's or an interface's companion members taken for a receiver's or an
  implementing class's; `o.Part()` (an inner class's constructor after a value). Declared relations follow none of the lookup rules above
  (#7): they take an interface's or a superclass's companion's nested type for inherited,
  a project type for one an outside superclass nests (`Thread`'s `State`), and see a name
  an import alias hides.

## TypeScript / TSX

- `class`, `abstract class`, `interface`, `enum`; `namespace` blocks nest their types
  (`Customer.Address` through declaration merging works). `type X = ...` is an alias.
- Tuples (`[Point, Circle]`, `[a: Point, b?: Circle]`) relate to each element once.
  Rest parameters read as `...rest: P[]`. `import("./other").Foo` (an import type, not
  in the grammar) is read as `other.Foo` from that module, never a `Foo` of the file:
  before parsing, the module part becomes a namespace alias of the same length and
  `import * as other from "./other";` is appended after the last line.
- Ids are module path + name: `src/order/order.Order`; `index.ts` is its directory.
- Scopes: a `namespace` block sees the module around it (`namespace Order { … Order … }`),
  and its own types and aliases (`class Foo`, `import Foo = Lib.Foo`) come before an
  import of the same name. One the block does not export is seen in that block alone
  (another block of the namespace sees the import), as is everything in a namespace the
  block does not export; in a `declare namespace` every member is exported. Members of a
  merged namespace are not inherited: a subclass of `Base` must write `Base.Listener`.
- Imports: named, aliased (`{ A as B }`), namespace (`* as pay` then `pay.Receipt`), and
  barrel re-exports: `export { X } from`, `export * from` and `export type * from` (TS 5.0;
  `type` is blanked before parsing, same length). Relative paths resolve exactly, and a
  name a relative import does not reach is unresolved, not external — unless the barrel
  re-exports it from a package (`export { EventEmitter } from "events"`), which then is
  the external id. Non-relative paths (`@/x`, `~/x`, `src/x`) are matched against project
  modules by unique suffix, otherwise they are external packages (no relation).
- Workspaces (nx, turborepo, the nest monorepo): every `package.json` below the extraction
  root maps its exact `"name"` to its directory. `@acme/core` is the package's entry —
  the `types`/`main`/`module`/`source` file when that is a `.ts` source in the package,
  else its `index.ts` — and `@acme/core/sub` is `sub` below the package. A package name
  declared by two package.json files is unresolved with both packages as candidates; a
  name the package does not contain is unresolved, like a relative import. Extract from
  the workspace root so every package is inside it.
- Imported type aliases (`import { Options } from "./x"` where `type Options = …`) are
  aliases, drawn through to the project types they name. Standard-library globals (`Partial`, `Required`,
  `Float32Array`, `AsyncDisposable`, ...) are builtins.
- Not handled: `exports` subpath maps in package.json, tsconfig `paths` aliases
  (`@app/*`), `export * as ns from`, a default export re-exported by name (`export {
  default as X } from`: X is unresolved where a member's type names it, and draws
  nothing in a body).
- Constructor parameter properties (`constructor(private repo: Repo)`, also optional
  ones: `protected q?: Q`) are fields;
  `#private` names are private. Properties of inline object types are not members, and
  the types inside them produce no relations (`options: { socketClass?: Type<X> }`).
  Fields without a written type (`reg = new Registry()`) have no type and no association:
  initialisers are not evaluated, though the names they write are body dependencies.
- Default imports are resolved by the local name. Not handled: `declare module`,
  `declare global` blocks (`declare global { namespace JSX { ... } }`: their types are not
  extracted), global scripts without imports/exports, mixins built with functions.
- Decorators on a class, its members and parameters: the names their arguments pass are
  dependencies of the class (`via` `@Name`) when they are project classes,
  `@Module({imports: [UsersModule]})`, `@Type(() => Foo)`, `@InjectRepository(User)`,
  `pay.Receipt`; constants (`@Inject(TOKEN)`) draw nothing. A decorator is a function, so
  its own name draws nothing unless it is a project class.
- Names in bodies (`evidence: "body"`; methods, accessors, field initializers, static
  blocks, enum members' values): a type name (`: Foo`, `as Foo`, `satisfies Foo`, type
  arguments, a local class's `implements`) looks the name up among types; any other name
  is a value (`new Foo()`, `Foo.m()`, `Kind.A`, `x instanceof Foo`, `typeof Foo`, `<Foo />`,
  `register(Foo)`, `{ Foo }`, a local class's `extends Foo`), which draws nothing when the
  member declares a variable, function or class of the name anywhere (also after the
  name, so a few are lost), and nothing when the name is an interface (the value of
  `Token` is the `const Token` beside `interface Token`). A constructor's parameter
  properties (`constructor(private Foo)`) are its parameters; an enum's members, also
  those written as strings (`"Foo" = 1`), are names in its members' values (`B = Foo`); a
  namespace block's variables and functions are names in the bodies of its classes and of
  the namespaces inside it, and hide them even where a type of an inner namespace is
  nearer (that one is missed). A label in a type is no name (`[Foo: string]`, `{ [Key:
  string]: T }`); an import type names the module's type (`import("./m").Foo`). Fields
  hide nothing, as a body reaches them through `this`; a class does not see the types of
  a namespace merged with it by their simple names. A dotted value goes through what the
  file imports or a namespace around it (`ns.Foo.m()`, `Shop.Item`), never through a
  variable. Checked
  against the TypeScript compiler (`bench/tsc_oracle`): 0 mismatches on nest and TypeORM.
  Known limits: a value whose name starts lower-case is not read (a class named so is
  missed); a type alias draws nothing in a body.

## Python

- Ids are dotted module paths, named the way Python names modules: from the extraction
  root, prefixed by the packages the root sits in (extracting `django/db/models` gives
  `django.db.models.query.QuerySet`, because each directory up to `django/` has an
  `__init__.py`); a root outside any package gives `src.shop.order.models.Order`.
  Namespace packages (PEP 420, no `__init__.py`) cannot be detected: extract from their
  top. If you do not, an import that ends with exactly one project id
  (`nspkg.sub.mod.X` for `mod.X`) is left unresolved with that id as candidate rather
  than treated as external.
  Absolute imports are matched by unique suffix, so `from shop.order import X` works with
  a `src/` layout, but a match never drops a package of the sources: `import jinja2` in
  `django/template/backends/` is the outside package, not that directory's `jinja2.py`.
  Package re-exports in `__init__.py` are followed — named ones first,
  then `from .sub import *`, each by its exact module path (`forms.Form` is
  `django.forms.forms.Form`, never another `Form`). A star import brings in what the
  module's `__all__` lists (a list or tuple of strings, `+=` too), else every name not
  starting with `_`. Classes of the `builtins` module (`dict`, `LookupError`) are builtins.
- Fields: class-level assignments (unannotated or `ClassVar` = static), dataclass-style
  annotations, and `self.x = ...` directly inside `__init__` (not other methods, not nested
  functions). `self.x = param` takes the annotation of that `__init__` parameter.
- Kinds: `Protocol` → interface, `ABC` → abstract_class (also any `@abstractmethod`),
  `Enum` family → enum (class attributes become constants), `NamedTuple`/`TypedDict` →
  record. These marker bases (and `Generic`, `object`) produce no relation.
- Names in a class body: a base class's nested class is *not* in scope (class bodies are
  not scopes), so `class Sub(Base)` must say `Base.Listener`; a bare `Listener` resolves
  to a module-level `Listener` or stays unresolved — never to `Base.Listener`. Through a
  subclass it works, as attributes are inherited: `Sub.Listener` is `Base.Listener`.
- Visibility by naming: `__x` private, `_x` protected. `@staticmethod`/`@classmethod` are
  static, `@property` methods are properties. `self`/`cls` are dropped from parameters.
- Module-level `T = TypeVar(...)` and other module-level assignments (type aliases) are
  never unresolved, and draw nothing (an assignment may be a value). `type X = A | B`
  (PEP 695) is an alias drawn through to `A` and `B`; PEP 695 type parameters
  (`class New[K: Item]`, `def f[T]`) are type parameters. String annotations (`"Order"`)
  are read as types. `Literal[...]` holds values, no types; `Annotated[X, ...]` is `X`,
  whatever the metadata (`Field(gt=0)`, `Depends(get_db)`). `Literal` needs the
  subscript: a class called `Literal` in another language (`Literal l;`, `Literal[]`) is a
  type. `tuple[P, Q]` relates to `P` and `Q` once each, `tuple[P, ...]` to many `P`.
  `*args: Item` and `**kw: Status` are parameters.
- Decorators on a class and its methods: a decorator that is a project class
  (`@classproperty`) and the project classes passed in its arguments (`@admin.register(User)`)
  are dependencies of the class (`via` `@Name`); other names draw nothing.
- Names in bodies (`evidence: "body"`; method bodies, the values of assignments directly
  in a class body, and the functions, lambdas and classes inside them): every name is a
  value, in an annotation too, so a variable of the name hides a class wherever it stands:
  `Foo()`, `Foo.create()`, `isinstance(x, Foo)`, `except Foo`, `x: Foo`,
  `models.Model()`. What hides one: the member's parameters and every name its statements
  bind, anywhere in it (also after the name, and a comprehension's or a lambda's variable
  outside them, so a few are lost): assignment and `for` targets, `with`/`except ... as`,
  `:=`, `del`, `nonlocal`, a `case` capture (`case Foo`, `case Bar(real=Foo)`, `case Bar()
  as Foo`, `case [*Foo]`, `case {**Foo}`), a function, class, `type Pair[T]` statement or
  PEP 695 type parameter it declares. `self.x = Foo` in `__init__`, a field written in a
  method, sees the method's names. An attribute's name is no name of the scope
  (`super().Foo`, `xs[0].Foo()`, `Foo().Inner`, `case Bar(Foo=0)`). An import in the
  member (`from x import Foo`) names x's Foo after it, in the
  function it stands in and those inside it; elsewhere in the member, before it, or where
  two imports of the name may run, it hides the name, as `import a.b` hides `a`. An
  import in a function or a class body is never the file's: not in another method, nor in
  a declaration (`class C(Bar)` beside `def helper(): from x import Bar`); one in a class
  body names a class in that class's annotations and signatures. The
  module's variables (assignments, `for` and
  `with` targets, functions and `type X = ...` at its top, under `if`/`try` too: `try:
  from x import Foo` / `except ImportError: Foo = None`) and every name a `global`
  statement names hide it in every class of the file. In a class-level value, the class's
  own names do (fields, methods, nested classes, and what its statements bind: `value =
  Foo` after `Foo = 1`, `if x: Foo = 1`, `for Foo in ...`, `Foo, y = 1, 2`, an import in
  the class body; its nested class there is missed). A method does not see its class body: not its
  attributes, nor its nested classes by their simple names (`Outer.Inner()` is drawn, a
  bare `Inner()` is the module's). A name the module binds twice at its top (two class
  statements, a class and an import of its name, a class and a star import that brings
  in another one of that name) is no one class, there or where another file imports it,
  and so is a nested class its class body binds twice (`if x: class Cond` / `else: class
  Cond`, two `class Twin` statements, a class and a variable): `Foo.Cond()` draws Foo;
  beside a star import of a module outside the sources (`from tkinter import *`), whose
  names are not known, no name of the file is drawn, nor where another file takes the
  name from it: by importing the name (`from q.outside import Button`, re-exported too),
  through the module (`outside.Button()`), or by a star import of a project module that
  brings such a star in (`from q.gui import *`, one step away or more). The same goes
  for a name a module binds to two classes (`from .a import Foo` and `from .b import Foo`
  in `dup/__init__.py`, two star imports that bring in two, a name and a star import, a
  class and a star import, a project class and something outside the sources: `from
  tkinter import Button` beside `from q.w import Button`, in either order or under `try:`,
  `import tkinter as Button`) or as a variable (`if x: Foo = None`): another file's `from
  q.dup import Foo`, `dup.Foo()` or `from q.dup import *` draws nothing; one class
  reached by two paths is one class. Declarations do not follow these rules yet: `class
  X(Foo)` there is drawn to the first import's class.
  A dotted value goes through what the file imports (`models.Model()` after `from
  django.db import models`, `p.foo.Foo()` after `import p.foo`), never a variable, and
  reaches a submodule only through the name a module import binds, or one its package's
  `__init__` imports relatively: `p.sub.near.Near()` after `import p.sub.near`, or after
  `from . import near` (or `from .near import Near`) in `p/sub/__init__.py`, but not
  `sub.near.Near()` after `from p import sub` and `import p.sub.near`, nor
  `p.sub.near.Near()` after `import p.sub.near as n` or an absolute import in the
  `__init__`, where pyright finds nothing (`models.base.ModelBase()` draws nothing after
  `from django.db import models` alone; `p.bar.Bar()` nothing after `from p.bar import
  Bar`). In a body nothing comes through a
  star import whose `__all__` cannot be read (`__all__ = a_all + b_all`). No name in a
  branch of a `sys.platform` or `sys.version_info` test is read, and a class declared in
  one draws nothing, in its file or where another imports it; nor is one in code only run
  outside type checking (after `if TYPE_CHECKING:` or `typing.TYPE_CHECKING`, under `if`
  or `elif not TYPE_CHECKING:`, the running value of `Foo() if TYPE_CHECKING else Bar()`),
  where mypy and pyright see nothing and only ty answers. Checked against mypy, pyright
  and ty together (`bench/py_oracle`): the key is where they name the same declaration, and
  a place where they differ (15 in Django, none in httpx) is to draw nothing. A checker
  that gives no definition where it marks the code unreachable itself abstains (mypy in a
  block its semantic analysis skips, pyright in the range of its hint of unreachable code,
  ty there too or where its hover says `Never`), and the others decide, two or more of
  them; after `return`, under `if False:` or `if PY2:`, after a false `assert` on the
  version, one checker abstains and the other two agree. Django: ty abstains at 8 places
  (`elif db_field.name in self.raw_id_fields:`, which it takes for never true since the
  class sets `raw_id_fields = ()`), mypy and pyright at none; httpx: none. httpx: 186
  names, 0 mismatches; Django: 4,065 names, 0 mismatches. The key is the name as static
  analysis sees it: monkeypatching, a name another module rebinds later, and code only
  another platform runs are in none of the three. Known limits: a plain name that starts
  lower-case is not read (a class named so is missed); a nested class reached through a
  subclass (`Sub.Listener()`) draws only `Sub`; a name an import in the class body binds
  is not read in the class's values; after two imports of one package's modules (`import
  p.foo`, `import p.bar`) `p.foo.Foo()` draws nothing, as `p` counts as bound twice;
  names in string annotations and type comments are not read. In a declaration, a nested
  class's annotation sees the outer class's nested classes (`class Outer: class Sub: x:
  Inner` is `Outer.Inner`), which Python's scoping does not (the module's `Inner`), and a
  method's decorator does not see the class body (`Other = print` there, then `@Other`,
  draws the module's class `Other`).
- Not handled: `__all__` written as anything but a list or tuple of strings
  (`a_all + b_all`, `__all__.extend(...)`; a star import is then taken to bring in every
  name not starting with `_`, except in a body), attributes created outside `__init__`,
  untyped values (no association without a type hint), `__getattr__` magic.

## C++

- `class`, `struct` and `union` (default `public`; a named union is kind `union`),
  `enum`/`enum class`; forward declarations are ignored. A template specialisation
  (`template <class S> class Ev<void, S> {...}`, `template <> class Ev<int> {...}`) is no
  type, and neither is anything inside it, nested types included. Out-of-class definitions of nested types (`struct Table::Rep { ... }`) attach
  to their owner. Ids use `::`; types of enclosing namespaces are visible.
- Visibility follows `public:`/`protected:`/`private:` sections. Pure virtual methods
  (`= 0`) are abstract; a class with only pure virtual methods and no data members is
  classified `interface`, otherwise `abstract_class`. Destructors and operators are not
  listed. Out-of-class method definitions in `.cpp` files add nothing (the declaration in
  the class is the fact).
- Associations carry `ownership`: value members and `unique_ptr` are `owned`
  (composition, drawn with a diamond); pointers, references, `shared_ptr`/`weak_ptr` are
  `shared`.
- Macros are blanked before parsing (same length, so line numbers are exact), never
  expanded; a class a macro declares (`POCO_DECLARE_EXCEPTION(API, E, Base)`) is not drawn.
  - Export macros: between `class`/`struct` and the name, by position whatever the
    name (`class Foundation_API Logger :`, `class MACRO(x) Name {`; not a lower-case word,
    so `struct sockaddr_in addr{};` stays, nor `class Name final`); elsewhere by name,
    upper or mixed case, when a declaration goes on after them (`FOO_EXPORT`, `Net_API
    std::ostream& operator<<(...)`, `std::string Util_API replace(...)`; not
    `x == ACC_PUBLIC`).
  - Statement macros on a line of their own without `;` (`POCO_CHECK_MINMAX_MACROS`,
    `POCO_DECLARE_EXCEPTION(...)`), where a declaration may start: after `;`, `{`, `}` or
    the start of the file, not before a `{` (`TEST(A, B)` then a body), not after `,` or
    `:` (an initializer list), not as an enum's only constant, and without arguments not
    before `name(` (`MY_TYPE` alone on its line, then `compute(P p);`: a return type).
  - Attribute macros before a declaration: with arguments (`POCO_DEPRECATED("...")`,
    also after `[[nodiscard]]`, an access specifier or a `template <...>` head); without
    arguments only before a constructor of a class in the file (`POCO_NODISCARD_CTOR
    Request(int)`) or when the name says `_NODISCARD`, `_DEPRECATED`, `_INLINE`,
    `_CONSTEXPR`, `_NOEXCEPT`, `_EXPLICIT` - a bare `HANDLE` or `DWORD` there is a type.
  - Attribute macros after a declaration or an enumerator (`GUARDED_BY(mu)`,
    `E_OLD POCO_DEPRECATED("since 4.2; use f() instead") = 4,`: a string argument may
    hold `;` and parentheses), after a declarator or `)` only: `const std::string
    SENTINEL("=?");` declares `SENTINEL`, `explicit URI(...)` is a constructor, and text
    inside a string literal stays. Also `#if` groups inside an expression (an
    initializer list), blanked with their `#elif`/`#else`/`#endif`; after `=` the
    branches are alternative values and only the first stays (`MAX = #if V6
    sizeof(struct in6_addr) #else sizeof(struct in_addr) #endif`).
  Other macros may still cause syntax errors; they are reported as diagnostics and only
  affect nearby declarations. A macro call in a class body that the grammar reads as a
  declarator in parentheses with an error inside (`poco_static_assert (offsetof(Hdr,
  code) == 0x01);`) is no member, nor is a name no member can have (`sizeof`); a
  pointer-to-member field (`void (P::*method)(int);`), also with an error inside, is
  kept.
- `typedef`/`using X = ...` are aliases, also inside a class (`typedef Circle* CirclePtr;`
  makes a field of type `CirclePtr` a shared association to `Circle`), also with several
  declarators (`typedef struct Legacy {…} Legacy_t, *LegacyPtr;` names `Legacy`). C's
  `typedef struct {…} Point;` (an anonymous struct or enum) is a type called `Point`; an
  anonymous union is no type, so `typedef union {…} U_t;` is an alias with nothing to draw.
  `using namespace X;` is a wildcard import, and `using a::B;` imports `B` (also inside an
  include guard); inside a class (`using Base::Base;`, `using Base::f;`) it is a member
  declaration and imports nothing. Qualified names into namespaces outside the sources
  (`std::`, `boost::`) are external, also in a namespace the project adds to
  (`Poco::Util::ServerApplication` next to the project's `Poco::Util::MyExtension`). A name
  the project may declare where the parser could not see it is unresolved instead, with
  where: an argument of a blanked statement macro (`POCO_DECLARE_EXCEPTION(API,
  DataException, Base)` for `Poco::Data::DataException`) or a class head inside a syntax
  error. `std` is never the project's: a project may only specialise templates there.
  Written without its namespace (`XMLException`), such a name gets the same "may declare
  it" hint where that namespace is visible (the reference's own or an enclosing one); the
  reason does not change, as a macro argument may be anything (`DEFINE_GUARD(Lock, ...)`).
  A name several macros mention (as a base too) is listed with each place, "one of them
  may declare it", a file named after the name first (`XMLException.h`).
- Template parameters of every kind are no types to resolve: types (`class T`), values
  (`std::size_t N`, `int N = 8`, `int... Is`, `auto V`) and templates (`template <class>
  class C`). Inside the template they hide a project type of the same name (`Array<P, N>`
  does not depend on a `struct N`), and they are listed with the class (`Array<T, N>`).
  A member of one (`typename R::Ptr`) is unknown and not resolved. `sizeof(P)`,
  `alignof(P)` and `noexcept(...)` in a template argument are values
  (`std::array<char, sizeof(P)>` depends on nothing).
- Class scope: nested types and type aliases of a base class (`using CharacterMap =
  int[256];`) are inherited, and so is the base's own name (`CodeGenerator::Properties` in
  a subclass of `Poco::CodeGeneration::CodeGenerator`); a class's own name comes first
  (`Listener` inside `tcp::Listener`, which derives from another `Listener`). A member of
  what an alias names (`NamespaceMap::const_iterator`, also `NamespaceManager::NamespaceMap::const_iterator`)
  is not resolved further, as the alias's target is not read. Types in an `inline namespace` are found with or without it
  (`acme::Versioned` is `acme::v1::Versioned`).
- Parameters with a default value (`P p = P()`) are parameters. A function-pointer member
  (`void (*cb)(int)`) is a field of type `void(int)*`. Members of an anonymous union or
  struct are members of the enclosing class, as in C++; with a variable (`union { int i;
  float f; } u;`) they are the variable's (`u.i`), so the class lists only `u`, without a
  type. A type defined with a variable (`struct Tag { P p; } tagged;`, `enum Mode { A, B }
  mode;`) gives the field that type: `tagged` is a `Tag`. `std::tuple<P, B*>` and
  `std::pair` relate to each element once.
- Qt: Qt's statement macros (`Q_OBJECT`, `Q_GADGET`, `Q_PROPERTY(...)`, `Q_ENUM(...)`,
  `Q_DISABLE_COPY(...)`, `Q_DECLARE_...`, `QT_BEGIN_NAMESPACE`/`QT_END_NAMESPACE`,
  `QML_ELEMENT`, `QML_NAMED_ELEMENT(...)`, ...) when only a comment follows on their line,
  the markers around a declaration (`Q_INVOKABLE`, `Q_SIGNAL`, `Q_SLOT`, `Q_REVISION(n)`,
  `Q_DECL_...`), and the `signals:` / `public slots:` sections are blanked or read as access
  sections before parsing (signals are public). Other `Q_` names (`Q_FIRST = 1,`) are left
  alone.
- Names in bodies (`evidence: "body"`; a member function's body, also one defined out of
  its class (`void Foo::bar() {}`, `Foo::Foo() : Base(1) {}`, `int Foo::x = ...;`: the
  class's, looked up in the class, its bases, the namespaces around the class, then the
  file's `using`s), a constructor's initializers, a default argument or member
  initializer, an enumerator's value, a friend function, an operator or a destructor
  defined in the class, and what is inside them: lambdas and local classes, which are the
  function's around them). Where only a type stands (a declaration's type, `new`, a cast,
  a template argument) the name is looked up among types; a variable, a parameter, a
  field or a method of the classes around hides a type of its name there too, as C++ has
  one scope for both. A qualified name's parts are types or namespaces (no variable is
  looked up before `::`): the longest prefix that is a project type is drawn
  (`Order::Status::Paid` draws Order::Status, `A::B::c()` A::B), the head looked up in
  the classes around first (`Mutex::ScopedLock` after `using Mutex = FastMutex;`), and a
  head that a namespace around may be draws nothing (`Keywords::now()` beside a type
  `Keywords`); `::Foo` is the global one. What is called (`Money(1)`, `ns::Money(1)`,
  `AutoPtr<X>(p)`), a base's initializer (`: Base(1)`), `sizeof(X)`, `typeid(X)` and a
  block-scope function declaration's parameter (`Guard g(Tag);`, a variable Tag when
  one is in scope) may be a value too; there, an enumerator of an unscoped enum of the
  classes around, their bases or the namespaces around hides the type (`sizeof(Paid)`,
  `Lock l(Paid);` beside `enum Kind { Paid };`; not an `enum class`'s). A call draws
  nothing where a function of the name is declared at a namespace's scope anywhere in the
  sources (with a return type: a constructor an error leaves at a namespace's scope is
  none) or a method of the classes around. Inside a template, a base written with its
  parameters (`Vec<T> : TBase<T>`) is not looked into: its member types and fields are
  found once T is known, so they neither are candidates nor hide one (`TBase<int>` is
  looked into). A namespace alias of the file's scope (`namespace fs = a::inner;`) is
  read: `fs::D` is `a::inner::D`. An alias stands for every project type its written type names, as a declared
  relation's (`typedef AutoPtr<Channel> Ptr;`), but an alias template's own parameters
  and a dependent `typename X<T>::Y` name none. What a build decides, read from the
  sources: a type of an anonymous namespace is a candidate in its file only; a type is a
  candidate only where its file is included by the body's file, directly or through
  others (a quoted path from the file's directory first, else every file whose path ends
  with the one written), and lookup goes on past one that is not (another program's
  global `Utility` is none of RemoteGen's, whose `Poco::CodeGeneration::Utility` is meant);
  where an included file declares the type without defining it (`struct Fwd;`), the name
  is that type and lookup stops there. A type declared in an `#if` branch is drawn in
  that branch and in branches of the same condition, in any file (`#if defined(POCO_HAVE_IPv6)`
  around `IPv6AddressImpl` and its uses; POCO's `ip_mreq` for HP-UX beside the system's
  is not). Bases outside the sources: under a class of `std` that
  `cpp_std.json` knows (libstdc++'s, as Clang reads it: `bench/clang_oracle/oracle.py
  table`; also through its typedefs, `std::ostream`), a name draws nothing where the base
  has a public or protected member of it (before `::` a member type only); under one it
  does not know, or one written with the class's template parameters (`std::vector<T>`,
  looked into once T is known), nothing is hidden. C++ and the other languages name none
  of each other's types. Checked against Clang (`bench/clang_oracle`): leveldb 877 names,
  POCO 21,908, no mismatch; review sets cpp2 to cpp4 pin the forms
  (`bench/clang_oracle/review/README.md`).
- Known limits of bodies. Not drawn: code outside every type (free functions, a
  namespace's variables; #8) and template specialisations (`template <> struct X<int>
  {...}`, `template <> void X<int>::f() {}`), as declared relations skip them; the part of
  a longer name (`Order` in `Order::Line`); a member access's member (`x.Foo`); a macro's
  argument the preprocessing blanks (`POCO_IMPLEMENT_EXCEPTION(E, Base, ...)`); what
  follows an `#if` that opens a block in each branch (`#if A if (x) { #else if (y) {
  #endif }`), which the grammar takes for one function holding the next ones; a type
  outside the include graph a path written with a macro or a build's include directory
  makes; a qualified name in a macro's argument the macro makes a string
  (`STR(Money::Zero)`), read as an expression, and a macro's argument that is an
  identifier alone (`DECL(Money, d)`, `NEWOF(Money)`), where the parser sees no type; an
  elaborated name (`struct Channel c`); a member defined out of a class named by a
  typedef (`int Ord::look()`); a namespace alias of a block (`namespace al = a::inner;`); a
  type the sources only declare (`struct Fwd;` with no definition); a header with no
  include of its own, which relies on what its includer included first. Includes are read
  as a whole: a name above the `#include` of its file counts as included. An include path
  is matched by its suffix where the quoted path from the file's directory fails, which
  may take another directory's file of the name (`"sub/deep.h"` for `one/sub/deep.h`
  besides `sub/deep.h`). Lost to a rule: a type of an `#if` branch named outside every
  branch of its condition (POCO 3); a type of a file the body's file includes through a
  path the suffix match misses (1). A local variable hides its name in the whole member,
  also before it is declared, and a `using namespace` in a function counts for the file.
- Not handled in declared relations: `#include` graphs (resolution is by name and
  namespace, not by includes; bodies use them, above), template specialisations
  (skipped, see above), private/protected inheritance (drawn as plain `extends`).
