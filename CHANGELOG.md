# Changelog

## Unreleased (first release)

Notes for anyone with `view.json` files written against a development build:

- **0.3.0**: the entries below on nested types and annotations change the default
  focus diagram and the relations in `ir.json`; results measured with 0.2.0 (the
  benchmark's runs among them) are not comparable with 0.3.0 ones.
- **After 0.6.0**: C#'s `ir.json` gains the relations read from names in bodies (below);
  results measured with 0.6.0 are not comparable on what C# bodies relate. One declared
  relation changes: eShop's `BasketService` extends the gRPC-generated
  `Basket.BasketBase`, an external type now; and two of eShop's dependencies go to the type
  the file's own `using` names (`OrderingContextSeed`'s `CardType`,
  `CreateOrderDraftCommandHandler`'s `Order`: the domain's, not `Application.Queries`').
  The other languages' `ir.json` are the same.
- **0.6.0**: Python's `ir.json` gains the relations read from names in bodies (below);
  results measured with 0.5.0 are not comparable with 0.6.0 ones on what Python bodies
  relate, and a few Python declarations change (an import in a function or a class body
  is no longer the file's; a suffix match of an import no longer drops a package).
  TypeScript's changes where a namespace's own type shares the name of an import (below);
  nest's and TypeORM's `ir.json` are the same.
- **0.5.0**: TypeScript's `ir.json` gains the relations read from names in bodies
  (below); results measured with 0.4.x are not comparable with 0.5.0 ones on what
  TypeScript bodies relate. Nothing changes for the other languages.
- **0.4.1**: `draw.py` warns when a focus diagram is drawn from part of a project (below);
  the benchmark's v3 and v3-haiku measured 0.4.0 (`7d2358a`), without the warning.
- **0.4.0**: Java's `ir.json` gains the relations read from names in method bodies, and a
  focus diagram draws those that touch the focus; results measured with 0.3.0 (the
  benchmark's two rounds among them) are not comparable with 0.4.0 ones on what bodies
  relate.
- **A grammar the language pack cannot download is exit 2, not a traceback.**
  `tree-sitter-language-pack` fetches each grammar from GitHub on first use; in the
  benchmark that fetch failed twice (HTTP 500), `draw.py` ended in a traceback, and one
  run drew its diagram by hand from `grep`. `draw.py` and `extract.py` now exit 2 with
  what failed and what to do: try again or tell the user, and not draw by hand. It
  changes only that failure, which the benchmark's images no longer meet: they fetch the
  grammar when built.
- **`draw.py` warns when a focus diagram is drawn from part of a project.** Run on Haiku,
  the benchmark's Draftsman arm extracted one module of Netty in two of six runs
  (`handler/src/main/java`, `codec-socks`) and so missed the focus's relations to the
  other modules' types (recall out of the focus 0.66, 1.00 on Opus). With a focus, when
  the path lies in a larger project (the run of directories with a `pom.xml`, a
  `build.gradle`, a `package.json`, ... above it, or `.git`; never the home directory or
  above) whose other sources of the languages extracted were not read, the report says
  how many (counting stops at 1000: "at least") and gives the command that draws from
  the project's root. It never widens the scope itself: one module may be what the user
  wants, and without a focus it is more likely to be.
- **Names in Java method bodies are relations** (#2). A project type a body names, in
  type position (`new Foo()`, a cast, `instanceof`, a local variable's type, `X.class`,
  type arguments, the header and members of a local or anonymous class) or as a receiver
  (`Foo.bar()`, `Foo.X`, `Foo::bar`), is a dependency marked `evidence: "body"`, `via` the
  member. Citing the line proves nothing for such a relation, since the line always names
  the target, so javac is the answer key: `bench/javac_oracle` records what javac resolves
  at every place, and every name drawn on spring-petclinic, jsoup and Netty matches it (37,
  2524 and 21324 names, 0 mismatches; Netty's io_uring classes compile at their own
  release for that). A hand-written fixture of 126 names, checked against javac too, pins
  the forms these projects lack (records, `o.new Inner()`, `java.*` wildcard imports,
  shadowing fields). A name that may mean something else draws nothing and is never
  unresolved: a variable of the name for a receiver (a local, a field of any class around
  it, inherited ones too, a static import), a type the member declares, a nested type an
  outside supertype passes on, a name two wildcard imports provide. What JDK supertypes
  pass on comes from a table of the JDK 21 types (`langs/java_jdk.json`, written by
  `oracle.py jdk`); supertypes outside the JDK are not known and hide nothing, the
  assumption declarations already made. The table resolves declarations too: `Entry` in a
  `HashMap` subclass is `java.util.Map.Entry` (jsoup 2 → 0 unresolved, Netty 6 → 3);
  declared relations are otherwise unchanged. Drawing: the view's `body` (`draw.py --body`)
  is `"focus"` with a focus and in the viewer, `"none"` otherwise; the class at the other
  end of a focus's body relation is drawn but leads nowhere, a signature's or annotation's
  arrow wins over a body's, and body arrows are dotted more finely (`body` in Mermaid). The
  e2e focus diagrams: petclinic's `Owner` unchanged, jsoup's `Element` 39 → 52 types,
  Netty's `DefaultChannelPipeline` 22 → 37, which can take a diagram over `--max-types`
  (`draw.py` then offers `--body none`). `summary.py` counts them apart, and the most
  connected types and the viewer's cycles stay on declarations. Netty extracts in about
  4.0 s instead of 2.4 s. The other languages read no bodies yet (#5); Django's and
  TypeORM's `ir.json` are byte for byte the same, the other e2e projects were not run again.
- **Names in Python method bodies are relations** (#5, 0.6.0). As in Java and
  TypeScript, a project class a method body or a class-level value names is a dependency
  marked `evidence: "body"`; every name is a value, in an annotation too (`Foo()`,
  `Foo.create()`, `isinstance(x, Foo)`, `except Foo`, `x: Foo`, `models.Model()`). Python
  has no compiler, so the answer key is where three checkers name the same declaration:
  `bench/py_oracle` walks mypy's tree after semantic analysis (it binds names in
  unannotated functions too) and asks pyright's and ty's language servers for the
  definition at each place; where they differ, nothing may be drawn. httpx: 186 names
  drawn, 0 mismatches (529 places checked, none disputed, none left undrawn); Django: 4065
  names, 0 mismatches since a checker that marks a place unreachable and names nothing
  there abstains (below; before, 3 were drawn where ty alone gave no definition), none at
  the 15 places the checkers dispute, 18 of the key's names left undrawn. A
  fixture of 120 names, which the three agree with, pins every form that binds a name,
  each written by hand; three drew a class before they were closed (`with f as (Foo)`,
  `case Bar.Inner:`, a class beside a star import of its name). Python scopes names
  unlike Java and TypeScript, and `LanguageSpec` settings say so: a method does not see
  its class body (`nested_types_in_bodies`), a class-level value does
  (`initializers_in_class_scope`); the module's variables and `global` names hide a class
  in every class of the file; an import in a method names its class after it, in its
  function; a name the module binds twice (a class and an import of it, two class
  statements) is no one class, also where it is imported (`rebinding_hides`); `import
  a.b` binds `a`, a submodule is reached only when the file imports it, and a star import
  brings in what `__all__` lists (else no `_` name, and in a body nothing through an
  `__all__` that cannot be read); a branch of a `sys.platform` or `sys.version_info` test
  is not read. Turned off one at a time, the rules keep these wrong names out of Django:
  a member's variables 1 (at a cost of 6 right ones), the module's variables 3,
  rebinding 6, `__all__` 8, submodules 6, suffix matching 2 (at no cost); the others only
  the fixture's; each also fails a test. Reading an import in a method draws 118 more of
  Django's names, going through `from p import mod` 711, none wrong. One declared
  relation changes with them: Django's `LimitedStream` and `FakePayload` extend
  `io.IOBase`, not `django.contrib.gis.geos.prototypes.io.IOBase` (a suffix match of an
  import no longer drops a package). httpx gains 152 body dependencies and Django 3203;
  the e2e focus diagrams grow from 11 to 16 types (`Client`) and from 30 to 56
  (`Field`). Django extracts in about 2.5 s instead of 1.0 s. jsoup's, petclinic's,
  Netty's, TypeORM's and nest's `ir.json` are byte for byte the same; the C#, Kotlin and
  C++ e2e projects were not run again.
- **Names in C# method bodies are relations** (#5, after 0.6.0). As in Java, a project
  type a body names where only a type stands (a local's type, `new Foo()`, a cast,
  `typeof`, `as`, a pattern's type, type arguments, `is Foo` alone) or where an expression
  does (`Foo.Create()`, `nameof(Foo)`, `case Status.Open:`) is a dependency marked
  `evidence: "body"`. Roslyn is the answer key: `bench/roslyn_oracle` loads each
  repository with the .NET SDK its `global.json` pins (8.0, 10.0, 11.0, in one container
  image pinned by digest; nothing installed on the host but Docker), lowers `latest` to
  that SDK's C# version, compiles every project in Debug, and records what each
  compilation resolves at each name; a file several compilations compile (target
  frameworks, `<Compile Include>` links) has an answer only where they all agree, and a
  place none compiles has none. eShopOnWeb: 251 names drawn, Serilog 655 (5 target
  frameworks), eShop 560 (eShop's MAUI apps compiled for plain `net11.0`), 0 mismatches.
  The key also answers for any directory with a `.csproj` (`oracle.py key DIR
  --compare`), which four rounds of sources written by hand ran through: they drew a
  wrong type in operator and indexer bodies (their parameters hid nothing), through
  `var @Order`, a type of another arity (`Box` beside `Box<T>`), an event field, a
  `using static` in a namespace block, a type of a project the file's project does not
  reference, a `using`, a field or an alias only some build has, and a member generated
  code declares (Razor `@inject`, XAML `x:Name`, `[ObservableProperty]`,
  `[JsonSerializable]`), all now closed and pinned in a fixture of 236 names compiled for
  net11.0 and net10.0. The rules turned off one at a time keep these wrong names out of the
  e2e projects: fields and properties 3, 35 and 4 (eShop at a cost of 16 right ones, which
  C#'s Color Color rule, also followed, recovers), a type declared in an `#if` 1 (Serilog,
  at a cost of 8), one id of two projects 2, gRPC's generated types 1, MAUI's platform
  code 13; the others only the fixture's. eShopOnWeb gains 206 body dependencies, Serilog 363, eShop 442; the
  e2e focus diagrams grow from 5 to 7 types (`BasketService`), 13 to 22 (`Logger`) and 20
  to 27 (`OrderingContext`). jsoup's, petclinic's, Netty's, nest's, TypeORM's, httpx's and
  Django's `ir.json` are byte for byte the same.
- **More C# forms that drew a wrong type in a body** (#5, after 0.6.0). A review's four
  sets of sources written by hand drew 23, 11, 4 and 4 wrong names, now closed: a base
  class's private nested type or field, a member of a base class outside the sources
  (`ControllerBase.User`, `Exception.Data`, from a table of .NET's and ASP.NET Core's
  reference assemblies that `bench/roslyn_oracle/oracle.py framework` writes; under a base
  the table does not know, a name where a variable may stand draws nothing), a delegate,
  a C# 14 extension block's receiver and type parameters, `(Order) - 1`, a property
  pattern's path, Color Color where the field's type only shares the name (`Lib.Order
  Order`, `Spot? Spot` of a struct) or an extension method shares the member's name, a
  `using` after a file-scoped namespace or of a namespace outside the sources in a block
  (System's `Task` before the project's around it; one the table does not know hides any
  name), `<Using Alias>` and `<Using Static>` items, Razor components' namespaces, `file`
  types, another project's internal types (`InternalsVisibleTo`), `#if false`, and an
  `#else` member in another file of a partial type. On the e2e projects nothing was drawn
  wrong before or after; eShop draws 551 names instead of 555: 5 more through usings after
  a file-scoped namespace, 7 fewer under MAUI's base classes, which the table does not
  know, and 2 fewer behind OpenTelemetry's and Polly's namespaces.
  Lost and documented: a symbol no build defines and `#if !DEBUG` read as compiled.
- **C# namespaces around the code, and a qualified name's first part** (#5, after 0.6.0).
  Two more reviews' sets of sources written by hand drew wrong forms, now closed. A
  namespace outside the sources around the code is looked in before the file's usings, as
  C# does: `Host` in `namespace Microsoft.Extensions.Hosting` and `Random` in `namespace
  System.Mine` are the framework's (the .NET table's); a namespace around the code that is
  the id of a package the project references, or a project it references passes on, or
  below it (`namespace CommunityToolkit.Mvvm.Input.Mine`), is the package's, and a name
  found further out than it draws nothing. A qualified name's first part is looked up as a simple name: `Models.Order`
  in `namespace App.Web` is `App.Models.Order` where that namespace exists, a class `Lib`
  around comes before a namespace `Lib` (not a `Lib<T>`, which the written arity does not
  fit, also through a block's using), and at each level a namespace before the types of
  the level's usings; an alias's target is looked up where the alias is declared (before
  `namespace X;`: the global namespace). `#if false ... #else` reads the
  `#else`, and `==` and `!=` in an `#if` are worked out. The reviews' sources are kept in
  `bench/roslyn_oracle/review/` and `oracle.py review` checks all of them: 0 mismatches
  but for the two `#if` limits below. eShop draws 560 names instead of 551, 9 receivers
  written partly qualified (`Services.Common.Common.X`), and eShopOnWeb 251 instead of 252,
  one in its `namespace Ardalis.GuardClauses`; nothing was drawn wrong before or after.
  Declared relations do not change; eShop's unresolved go from 517 to 513 and
  eShopOnWeb's from 195 to 194 (files declared in a `Microsoft.*` namespace find
  `IServiceCollection`, `IHostEnvironment`, `IUrlHelper` there). Lost and documented:
  names past a package's namespace, which a project that puts its own code below one
  loses (serilog-sinks-file's `src`: 13 body dependencies instead of 20), a name of the
  table's ASP.NET namespaces around code
  whose project does not reference ASP.NET, and a first part another project's internal
  type or an unreferenced project's namespace takes; drawn where it may be wrong: a
  namespace of a package the project does not reference itself.
- **More Python forms that drew a wrong class in a body** (#5, 0.6.0). Sources
  written by hand for review, run through the extractor and the three checkers together,
  drew a class where the checkers name something else: 21, 15 and 2 names in three sets,
  now 0. An attribute's name after a value was read as a name of the scope
  (`super().Foo`, `xs[0].Foo()`, `Foo().Inner`); a pattern's keyword was read and its
  captures did not hide (`case Bar(Foo=0)`, `case Bar(real=Foo)`, `as Foo`, `*Foo`,
  `**Foo`); what a class body's statements bind did not hide a name in its values (`if x:
  Foo = 1`, `for Foo in ...`, `Foo, y = 1, 2`, `(Foo := 1)`, an import there); an import in
  a function or a class body was the whole file's (`def helper(): from gui import
  TimeoutError` made every `except TimeoutError:` the project's, and an import in one
  method reached the others), declared relations included, before #5 too; `self.x = Foo`
  in `__init__` missed the method's names. Listing where tree-sitter-python puts an
  identifier in Django, httpx and the standard library found `del Foo` and `type Pair[T] =
  ...`, which bind names, and checking more forms by hand found two more: `p.bar.Bar()`
  after `from p.bar import Bar` (pyright and ty find no `p.bar`: only `import p.bar`
  reaches it now) and a class beside a star import of an outside module (`from tkinter
  import *`: no name of the file is drawn). An import in a class body names a class in
  that class's annotations, which also corrects `y: Foo` after `from m import Bar as Foo`
  there (the module's Foo before). The key gained four fixes: a name after characters
  outside the BMP on its line (`"😀😀", Foo()`, where mypy's start column is off by one,
  its end column not), `case {**rest}`, a `type` statement's name, `Foo[int]` read once.
  The fixture grows to 185 names and 38 non-names; each fix fails a test when turned off.
  Django's and httpx's `ir.json` are byte for byte the same (none of these forms occurs
  there in a way that changes a relation: still 4065 and 186 names, 3 and 0 mismatches,
  the same keys), and so are jsoup's, petclinic's, Netty's, TypeORM's and nest's.
- **A Python checker that marks code unreachable and names nothing there abstains** (#5,
  0.6.0). The answer key's rule changes, and with it the pass condition of #5: a
  checker that gives no definition at a place and marks the place unreachable itself
  abstains (mypy: a block its semantic analysis skips; pyright: the range of its hint of
  unreachable code, pulled with `textDocument/diagnostic`, which it sends only to a client
  that declares the Unnecessary tag; ty: that hint, or a `Never` hover); the others
  decide, and only two or more of them giving the same is agreement. A definition given
  in code marked unreachable is an answer, and no definition without the mark is one too
  (a submodule the file does not import). Records keep `abstained`; `oracle.py run` and
  `checkers` count it per checker. Django: ty abstains at 8 places, mypy and pyright at
  none; the 3 places drawn where ty alone gave no definition (`elif db_field.name in
  self.raw_id_fields:` with `raw_id_fields = ()`) are agreed now, so Django has 0
  mismatches and 15 disputed places instead of 18 (the entries below say 3, measured
  with the earlier key); httpx: no abstention, unchanged. In the fixture, after
  `return`, `if False:`, `if 0:`, `while True:` and a false version assert pyright
  abstains and mypy and ty agree; under `if PY2:` mypy abstains; mypy on this machine
  abstains in a branch of a platform test, so pyright and ty decide there. Where mypy and
  pyright both abstain, only ty is left and the place is disputed: code only run outside
  type checking (`else:` after `if TYPE_CHECKING:`, `typing.TYPE_CHECKING` too, `if` and
  `elif not TYPE_CHECKING:`, and the running value of `Foo() if TYPE_CHECKING else
  Bar()`, where pyright gives no definition), whose names the extractor no longer reads,
  as for a platform test; a branch of a version test is another such place, already not
  read. The fixture grows to 251 names; turning abstention off fails the key's selftest
  at 6 places, turning the extractor's rule off fails both tests. Neither changes
  Django's or httpx's `ir.json`, nor the other e2e projects'.
- **A nested Python class its class body binds twice is no one class** (#5, after
  0.5.0). `if x: class Cond` / `else: class Cond` in Foo made `Foo.Cond()` a relation to
  Foo.Cond, where ty answers both statements and `object.__init__` (the call of their
  union) and the checkers disagree. The rule for a name the module binds twice now holds
  in a class body: two class statements of one name, or a class and a variable, and
  `Foo.Cond()` draws Foo alone. Two `class Twin` statements one after the other are
  hidden too, as at the top of a module, though the checkers agree there. Fixture: 232
  names; Django and httpx unchanged (each `ir.json` byte for byte the same, also the
  other e2e projects').
- **A Python name a module imports from outside and from the project is no class where it
  is taken** (#5, 0.6.0). A fourth set of hand-written sources found 4 and 2 wrong
  names, now 0: `from q.w import Button` and `from tkinter import Button` in one module
  (in either order, the outside one under `try:` too) made another file's `from
  q.out_last import Button` and `out_last.Button()` q.w's class, where it is tkinter's at
  run time and the checkers disagree. An import that names no project class (a package
  outside the sources, a function) now counts among a module's bindings of the name, and
  so does a module import (`import tkinter as Button`); the module's own class and a
  project star import beside an outside import are caught the same way, and an outside
  import of another name changes nothing. The fixture grows to 226 names; each part fails
  a test when turned off. Turned off on Django and httpx, the rule changes no name: every
  e2e `ir.json` is byte for byte the same.
- **A Python name a module binds to two classes, or as a variable, is no class where it
  is taken** (#5, 0.6.0). A third set of hand-written sources found 3 and 4 wrong
  names, now 0: `from .a import Foo` and `from .b import Foo` in `dup/__init__.py` (or two
  star imports that both bring in `Both`, a name and a star import, a class and a star
  import), and another file's `from q.dup import Foo`, `dup.Foo()` or `from q.one import
  *` drew a's class, where it is b's at run time and mypy, pyright and ty answer a, b and
  both. A name the module binds as a variable (`if x: FooError = None` after importing it)
  was drawn the same way; `FileScope.variables` keeps the module's variables for that. One
  class reached by two paths is still drawn. Declared relations (`class X(Foo)`) still
  take the first import's class, as for every rule of names in bodies. The fixture grows
  to 218 names; each rule fails a test when turned off. Turned off on Django and httpx,
  neither rule changes a name: their `ir.json` are byte for byte the same (4065 and 186
  names, 3 and 0 mismatches), and so are jsoup's, petclinic's, Netty's, TypeORM's and
  nest's.
- **Three more Python forms drawn where the checkers disagree, and a BOM in the key** (#5,
  0.6.0). A second set of hand-written sources found 6, 2 and 1 wrong names, now 0;
  the earlier sets stay at 0. A star import from outside the sources hid the names of its
  own file only: a name is as uncertain where another file takes it, through a project
  module's star import that brings one in (`from q.gui import *`, gui.py importing
  tkinter's, one step away or more), through an import of the name (`from q.outside
  import Button`, re-exported too) or through the module (`outside.Button()`). A
  submodule was reached through any name for its package: it is reached through the name
  its import binds (`import q.sub.near` binds `q`, not the `sub` of `from q import sub`;
  `import q.sub.near as n` binds only `n`; `Import.aliased` tells that apart), or through a
  package whose `__init__` imports it relatively (`from . import near`, which all three
  checkers follow; not an absolute import). The key read no class of a file that starts
  with a UTF-8 BOM (`ast.parse` rejects U+FEFF), so pyright's and ty's answers there were
  "var" and every name of its classes was disputed. The fixture grows to 199 names; each
  part of the rules fails a test when turned off. Turned off one at a time on Django and
  httpx, no part changes a name (none hidden right, none kept out wrong): their `ir.json`
  are byte for byte the same, 4065 and 186 names, 3 and 0 mismatches, and no file of
  either starts with a BOM. The shop fixture's Python witness of a name in a body moves
  to `isinstance(self, Auditable)` in common/base.py, as its other bodies name classes
  from files with `from stripe import *` or `from shop.promo import *`. jsoup's,
  petclinic's, Netty's, TypeORM's and nest's `ir.json` are byte for byte the same.
- **A TypeScript namespace's own type comes before an import of its name** (0.6.0).
  In `import { Foo } from "./foo"; namespace N2 { class Foo {} export class A { f: Foo |
  null = null } }`, A's Foo is N2's, as the compiler says, but the extractor checked the
  file's imports first, as Java does, and drew `foo.Foo`, in declared and body relations
  alike; an `import Foo = Lib.Foo` alias in the namespace lost the same way. A
  `LanguageSpec` setting, `namespaces_before_imports`, puts the namespaces around a type
  first in TypeScript. A member the block does not export stays in that block
  (`LanguageSpec.local_block`): another block of the same namespace in the file sees the
  import, as the compiler does, where the first version of this change drew the other
  block's class. The fixture gains both, now 86 names; nest's and TypeORM's `ir.json` are
  byte for byte the same (0 mismatches with the compiler), and so are jsoup's, Netty's,
  petclinic's and Django's.
- **Labels in TypeScript types are no names; an enum member written as a string hides
  one** (#5). A tuple member's label and an index signature's parameter (`[Foo: string]`,
  `{ [Kind: string]: number }`) were read as values and drew the class the file imports,
  where the compiler sees no name; `"Foo" = 1` in an enum did not hide `Foo` in `B = Foo`,
  as `Foo = 1` does. The answer key (`bench/tsc_oracle/type_uses.mjs`) now records the
  type an import type names (`import("./m").Foo`), which the extractor drew right but
  `compare` counted as a mismatch. All are in the fixture, now 74 names. Run again on nest
  and TypeORM, the compiler's records are the same, and so is `ir.json` (1432 and 3406
  names, 0 mismatches), as are jsoup's, Netty's, petclinic's and Django's.
- **Three more TypeScript names that hide a class in a body** (#5). Where the compiler
  reads a variable, the extractor drew the class the file imports: a constructor's
  parameter property (`constructor(private Foo: any) { Foo.make(); }`; elsewhere it is
  `this.Foo`), an enum's member in its members' values (`enum E { Foo = 1, B = Foo }`) and
  a namespace block's variable or function in the bodies of its classes (`namespace NS {
  const Foo = ...; export class A { m() { Foo.make(); } } }`), which `lang-notes.md` listed
  as a limit. Each is in the fixture, now 69 names, which the compiler agrees with. None
  changes a relation in nest or TypeORM: their `ir.json` is byte for byte the same (1432
  and 3406 names, 0 mismatches), and so are jsoup's, Netty's, petclinic's and Django's.
- **Names in TypeScript method bodies are relations** (#5). As in Java, a project type a
  body names is a dependency marked `evidence: "body"`: in type position (`: Foo`, `as
  Foo`, `satisfies Foo`, type arguments) or as a value, where a variable may stand too
  (`new Foo()`, `Foo.m()`, `Kind.A`, `typeof Foo`, `<Foo />` in TSX, `Foo` as an argument
  or in `{ Foo }`). The answer key is the TypeScript compiler: `bench/tsc_oracle` records
  what its TypeChecker resolves at every place, and every name drawn on nest and TypeORM
  matches it (1432 and 3406 names, 0 mismatches, and no project type it resolved is left
  undrawn), with a fixture of 54 names checked against it too. TypeScript scopes names
  unlike Java, and the rules say so (`LanguageSpec` settings, `lang-notes.md`): a variable,
  function or class the member declares hides a value of the name, never a type; fields
  hide nothing (a body reaches them through `this`); an interface is no value (`Token`
  beside `const Token`); a class does not see its merged namespace's types by their simple
  names; a dotted value goes through an import or a namespace, never a variable. Turned
  off one at a time, the rules cost no relation on the two repositories; variable hiding
  keeps out 5 wrong ones in TypeORM (`create(dataSource: dataSource)` under `import type
  { DataSource as dataSource }`). A value whose name starts lower-case is not read, which
  saves about a third of the time it adds to extraction. nest gains 1117 body dependencies and
  TypeORM 2076; their declared relations, types and unresolved names are unchanged, and
  the e2e focus diagrams grow from 41 to 51 types (`NestContainer`) and from 23 to 32
  (`EntityManager`). nest extracts in about 1.06 s instead of 0.69 s, TypeORM in 1.07 s
  instead of 0.55 s. Java's and Python's `ir.json` (petclinic, jsoup, Netty, Django) are
  byte for byte the same; the C#, Kotlin, C++ and httpx e2e projects were not run again.
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
