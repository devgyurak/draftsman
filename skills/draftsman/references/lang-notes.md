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
  (`Shop.Orders` sees `Shop.X`). `using X;` is a wildcard import, `using A = B;` an alias.
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
- Conditional compilation: every file is read with the **first branch** of each `#if`;
  `#elif`/`#else` branches and the directive lines are blanked before parsing (same
  length, so line numbers are exact). tree-sitter cannot parse `#if` inside a base list,
  a parameter list, an expression or around a second method header, and one
  deterministic configuration avoids reading both. The limit: `#if !FEATURE` keeps the
  side where the feature is off. A `#if` line inside a multi-line string would be
  blanked too.
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
- Not handled: extension methods (they stay members of their static class, which is
  correct but not linked to the extended type), alias and static `<Using>` items in the
  project file, the .NET 8 rule that drops `System.Net.Http` for .NET Framework targets.

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

## TypeScript / TSX

- `class`, `abstract class`, `interface`, `enum`; `namespace` blocks nest their types
  (`Customer.Address` through declaration merging works). `type X = ...` is an alias.
- Tuples (`[Point, Circle]`, `[a: Point, b?: Circle]`) relate to each element once.
  Rest parameters read as `...rest: P[]`. `import("./other").Foo` (an import type, not
  in the grammar) is read as `other.Foo` from that module, never a `Foo` of the file:
  before parsing, the module part becomes a namespace alias of the same length and
  `import * as other from "./other";` is appended after the last line.
- Ids are module path + name: `src/order/order.Order`; `index.ts` is its directory.
- Scopes: a `namespace` block sees the module around it (`namespace Order { … Order … }`).
  Members of a merged namespace are not inherited: a subclass of `Base` must write
  `Base.Listener`.
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
  a `src/` layout, and package re-exports in `__init__.py` are followed — named ones first,
  then `from .sub import *`, each by its exact module path (`forms.Form` is
  `django.forms.forms.Form`, never another `Form`). Classes of the `builtins` module
  (`dict`, `LookupError`) are builtins.
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
- Not handled: `__all__` (a `*` re-export is taken to expose every name the module
  defines), attributes created outside `__init__`, untyped values (no association
  without a type hint), `__getattr__` magic.

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
- Not handled: `#include` graphs (resolution is by name and namespace, not by includes),
  template specialisations (skipped, see above), private/protected inheritance (drawn as
  plain `extends`).
