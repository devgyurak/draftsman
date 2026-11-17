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
  Listener` where the enclosing class inherits `Listener`). Names that can only come from
  an external wildcard import or an external supertype (`LayoutParams` in a `FrameLayout`
  subclass) stay unresolved with a hint — they could also be same-package generated code
  outside the sources, so they are not guessed.
- Type annotations right before varargs (`X509Certificate @Nullable ... certs`) are valid
  Java 8 that the tree-sitter grammar rejects; they are blanked before parsing (same
  length, so line numbers are exact). Annotations on array levels (`String @A []`) are
  read and ignored.
- `throws E` makes the method depend on `E` (it is not listed in the signature).
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
- The primary constructor is listed as `constructor(...)` with all its parameters when it
  has any; its plain parameters are dependencies. A `vararg val` property is
  `items: Item...` (multiplicity `*`).
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
  `kotlin.js.JsAny`. The core types (`String`, `Int`, `Exception`, ...) are always taken;
  the others only when no star import of an outside package could also provide the name
  (the documentation gives no priority between star and default imports), else they stay
  unresolved with "may be the default import ..." in the hint. A project type of the name
  wins. `dynamic` (Kotlin/JS) is a type keyword: nothing to draw, nothing unresolved.
- Gradle build and settings scripts (`*.gradle.kts`) are not extracted; other `.kts`
  scripts are.
- Function types (`Route.() -> Unit`, `suspend (Call) -> Unit`, `context(Log) () -> Unit`,
  also inside containers) make a dependency on every project type they name; a field of such a type is no
  association. Supertypes with a function type among their arguments are read too.
- `typealias` is an alias (see the note on aliases below). Not handled: delegation targets
  (`by x`).

## TypeScript / TSX

- `class`, `abstract class`, `interface`, `enum`; `namespace` blocks nest their types
  (`Customer.Address` through declaration merging works). `type X = ...` is an alias.
- Tuples (`[Point, Circle]`, `[a: Point, b?: Circle]`) relate to each element once.
  Rest parameters read as `...rest: P[]`. `import("rxjs").Observable<P>` (an import
  type, not in the grammar) is read as `Observable<P>`: the module part is blanked
  before parsing, same length.
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
  (`@app/*`), `export * as ns from`.
- Constructor parameter properties (`constructor(private repo: Repo)`, also optional
  ones: `protected q?: Q`) are fields;
  `#private` names are private. Properties of inline object types are not members, and
  the types inside them produce no relations (`options: { socketClass?: Type<X> }`).
  Fields without a written type (`reg = new Registry()`) have no type and no relation:
  initialisers are not evaluated.
- Default imports are resolved by the local name. Not handled: `declare module`, global
  scripts without imports/exports, mixins built with functions.

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
  are read as types. `Literal[...]` holds values, no types; `Annotated[X, ...]` is `X`.
  `tuple[P, Q]` relates to `P` and `Q` once each, `tuple[P, ...]` to many `P`.
  `*args: Item` and `**kw: Status` are parameters.
- Not handled: `__all__` (a `*` re-export is taken to expose every name the module
  defines), attributes created outside `__init__`, untyped values (no association
  without a type hint), `__getattr__` magic.

## C++

- `class`, `struct` (default `public`), `enum`/`enum class`; forward declarations are
  ignored. Out-of-class definitions of nested types (`struct Table::Rep { ... }`) attach
  to their owner. Ids use `::`; types of enclosing namespaces are visible.
- Visibility follows `public:`/`protected:`/`private:` sections. Pure virtual methods
  (`= 0`) are abstract; a class with only pure virtual methods and no data members is
  classified `interface`, otherwise `abstract_class`. Destructors and operators are not
  listed. Out-of-class method definitions in `.cpp` files add nothing (the declaration in
  the class is the fact).
- Associations carry `ownership`: value members and `unique_ptr` are `owned`
  (composition, drawn with a diamond); pointers, references, `shared_ptr`/`weak_ptr` are
  `shared`.
- Macros: export/visibility macros (`class FOO_EXPORT Bar`, `FOO_API`), thread-safety
  attributes (`GUARDED_BY(mu)`), and `#if` lines inside initializer lists are blanked
  before parsing (same length, so line numbers are exact). Other macros may still cause
  syntax errors; they are reported as diagnostics and only affect nearby declarations.
- `typedef`/`using X = ...` are aliases, also inside a class (`typedef Circle* CirclePtr;`
  makes a field of type `CirclePtr` a shared association to `Circle`). `using namespace
  X;` is a wildcard import, and `using a::B;` imports `B` at file or namespace level; inside
  a class (`using Base::Base;`, `using Base::f;`) it is a member declaration and imports
  nothing. Qualified names into namespaces outside the sources (`std::`, `boost::`) are
  external. Types in an `inline namespace` are found with or without it
  (`acme::Versioned` is `acme::v1::Versioned`).
- Parameters with a default value (`P p = P()`) are parameters. A function-pointer member
  (`void (*cb)(int)`) is a field of type `void(int)*`. Members of an anonymous union or
  struct are members of the enclosing class, as in C++. `std::tuple<P, B*>` and
  `std::pair` relate to each element once.
- Qt: `Q_OBJECT`, `Q_PROPERTY(...)` and other `Q_...` statements on a line of their own,
  `Q_INVOKABLE`/`Q_SIGNAL`/`Q_SLOT`, and the `signals:` / `public slots:` sections are
  blanked or read as access sections before parsing (signals are public).
- Not handled: `#include` graphs (resolution is by name and namespace, not by includes),
  template specialisations as separate types, private/protected inheritance (drawn as
  plain `extends`).
