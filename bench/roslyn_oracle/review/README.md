# Review sets

Sources written by hand in the reviews of C#'s body relations (issue #5), one directory per
set, each with its own projects, kept here so that every change is checked against all of
them:

    uv run bench/roslyn_oracle/oracle.py review [SET ...]

runs each set through Roslyn and the extractor (`key DIR --compare`, and `--declared` for
declared relations, issue #7) and fails on a mismatch not listed below, or on fewer body
names drawn or declared names agreed than the table gives.

| Set | Body names drawn | Declared names agreed | What it holds |
|---|---:|---:|---|
| `cs1` | 19 | 16 | private nested types of a base, Color Color, delegates, `file` types, casts and patterns, block usings, aliases |
| `cs2` | 26 | 9 | usings after a file-scoped namespace, `<Using>` items, a partial type's `#else` member, `#if` constants, arity, a BOM |
| `cs3` | 3 | 0 | another project's internal types, a Razor component |
| `cs4` | 5 | 3 | members of outside base classes (`ControllerBase.User`, `Exception.Data`), aliases |
| `cs5` | 12 | 10 | the table's namespaces around the code, bases, block usings, `#if false ... #else` |
| `cs6` | 5 | 2 | default accessibility across projects |
| `cs7` | 7 | 1 | a package's namespace around the code (CommunityToolkit.Mvvm), qualified names |
| `cs8` | 16 | 0 | qualified names through nested and generic types and aliases; aliases and `using static` in outside namespaces |
| `cs9` | 54 | 6 | a qualified name's first part in every position, alias targets, arity, `#if` with `==` and `!=` |
| `cs10` | 2 | 0 | internal and unreferenced projects' namespaces before a qualified name |
| `dbg` | 9 | 0 | a `using` of a namespace of the sources that holds no type itself |
| `cs11` | 18 | 9 | an alias before and after a file-scoped namespace, a block using's generic type before a qualified name, `using static` fields and variables of other members before a receiver |
| `cs12` | 0 | 0 | a package a referenced project references; a project's own code below a package's namespace |
| `cs13` | 12 | 0 | global, csproj and nested-block aliases, an alias of a generic type, arity through block, file, global and static usings |
| `cs14` | 22 | 23 | a parenthesized name before an operator or `[`, patterns, lambdas, attributes, strings, a local function's type parameter |
| `cs15` | 6 | 0 | a package through two project references, an alias hiding a type |
| `cs16` | 31 | 2 | forms tree-sitter and Roslyn may read apart: `F(a < b, c > d)`, `x is T ? a : b`, pointers, `(A)(b)`, `(A)!b`, `(A)~b`, collection expressions and ranges, types named `var`, `dynamic`, `nameof`, `value`, `field` |
| `cs17` | 73 | 7 | the rest of tree-sitter's declarations in a collection expression and an indexer, type positions (async lambdas, `await foreach`, LINQ with types, combined patterns), array, tuple and generic aliases, where nested and odd members' bodies belong, a record's base arguments, `#if` lines in strings and comments |
| `cs18` | 5 | 27 | declared relations (issue #7: cases 2, 3, 4, 5, 35), each beside a rival type: a namespace-less file's alias (`using Order = Lib.Order;`) and a file without it, an alias before a file-scoped namespace beside the namespace's type, another project's `internal` type before a using's, the arity written (`Repo<int>`), a package's namespace around the code (CommunityToolkit.Mvvm.Input), `nameof(Order)` beside a base's property, the same names in bodies. The extractor before the fix: 19 declared mismatches, 1 body name |
| `cs19` | 8 | 34 | a review's probe of the fix: a `global using` alias in every file of its project, aliases of a file in two namespaces of it, a namespace block's alias beside another block of the namespace, a namespace alias (`L.Order`, `L::Order`), an alias of a generic, `InternalsVisibleTo`, an unreferenced project's public type, arity of two type arguments, `nameof` and `typeof` beside members and nested types, `Kind.A` beside `public Kind Kind`, a namespace of the shared framework around the code |
| `cs20` | 1 | 16 | a review's probe of the fix: a global using's alias of a generic (`Safe`), aliases in nested namespace blocks, `Kind.A` and `nameof(Kind)` beside `public Kind Kind`, `typeof` beside nested types |
| `cs21` | 0 | 15 | a supertype's type arguments (#9, case 24): `List<Node>` beside another namespace's `Node`, a type parameter `T` beside a class `T`, nested arguments, `IComparable<Nested>` naming the class itself, a qualifier's arguments (`Outer<Item>.Inner<Node>`); aliases named like containers (`using Vector = ...List<A.Item>;`, `using Provider = A.Node;`, case 25). Before the fix: 7 agreed, 7 misses |
| `cs22` | 0 | 9 | #9 case 57: types through aliases of namespaces (`L2.Order`, `L2::Order`, `S2.Item`, `L2.Sub.Item`), in fields and parameters; an alias in a namespace block whose target is read from that namespace outward (`using B2 = Lib.Sub;` in `namespace Shop` is Shop.Lib.Sub), beside Shop.Order, Shop.Lib.Order and a class `L`. Before the fix (d11e7cc): 1 agreed, 8 misses |
| `cs23` | 2 | 13 | a review's probe of #9 case 57: aliases of a namespace and of a nested namespace, `L.Order` and `L::Order` in fields, a return type, a parameter's type arguments, a base and a body, in a namespace of their own and in `namespace Shop.Inner` beside a class `Shop.L` with a nested `Order` (`L.Order` is Shop.L.Order there, `L::Order` the alias's Lib.Order). The extractor at 973abe2: 12 agreed, 1 mismatch (`L::Order` drawn as Shop.L.Order) |
| `cs24` | 9 | 27 | a review's probe of `::` after 0.11.0 (#11, cases 64-66): `L::Order`, `L::Sub.Deep`, `L::Box<L::Order>`, `L::Order.Line`, a global using's `G::Order`, a block alias's `M::Deep`, beside classes `Shop.L`, `Shop.G`, `Shop.M` with the same members, in fields, parameters, an attribute and bodies (`new`, `typeof`, a cast, `is`, receivers `L::Order.Make()` and `L::Util.Run()`), bases `: L::Order` and `: L::Box<M::Deep>`, an alias whose target is `L::Sub` (`LS::Deep`, `LS.Deep` beside a class `Shop.LS`). The extractor at 9d7fc36: 22 agreed, 5 misses (the bases, the alias's target); 5 body names drawn, 5 mismatches |
| `cs25` | 27 | 17 | a review's probe of `::` in 22 kinds of body place beside classes named like the aliases: arrays, `default`, `as`, `is` with a designation, `nameof`, generic receivers (`L::Box<int>.Make()`), type arguments of a call, locals, lambdas' parameters, nested receivers, enum members, a switch's patterns, `with`, `foreach`, `typeof(L::Box<>)`, a local named like the alias; bases with arguments, a record's, a struct's and an interface's, `global::Lib.Order` as a base and in bodies, an attribute's `typeof`, a type parameter's constraint. The extractor at 7c60e09: 22 body names drawn, 17 agreed; the 5 names after a `global::` alias's target or `global::` itself not drawn |
| `cs26` | 6 | 12 | #11 case 67: aliases whose target is written from the global namespace (`using N = global::Lib;`, a block's `using M = global::Lib.Sub;`) beside a class `Shop.Lib` with the same members, in fields, parameters, bases and bodies. The extractor at 7c60e09: 1 agreed, 7 mismatches (`Shop.Lib.Sub.Deep`), 4 misses; 3 body mismatches |
| `cs27` | 5 | 12 | the same without the rival class: the extractor at 7c60e09 took the targets for namespaces outside the sources (9 misses, and 3 bases whose external ids were the project's `Lib.Order` and `Lib.Box`); no body name drawn |
| `cs28` | 5 | 2 | `global::Shop.Order` in bodies beside a nearer namespace `App.Shop` (#11 case 68): receivers, `new`, `typeof`; `Shop.Status.Open` alone is App.Shop's. The extractor at 7c60e09: 1 body name drawn, the 4 after `global::` not |

## Known limits

Drawn although no build compiles the place (the parser reads the first branch of an `#if`
whose condition depends on a symbol):

- `cs2/Dead.cs:9:30`
- `cs2/Dead.cs:14:30`

## Not drawn by design

Below a namespace of a package the project references (the package's id or a namespace
under it), the package may declare any type, so a name found further out draws nothing,
although Roslyn finds a type of the sources there:

- cs12/B/Mine.cs line 7 (`Order.Count`, Shop's through `using Shop;`)
- cs12/E/Use.cs lines 6 to 10: in `namespace CommunityToolkit.Mvvm.Extras.Views` of a project
  that references CommunityToolkit.Mvvm, a type `using` brings in (`Item`), one of a
  namespace around (`Helper`), a fully qualified and a partly qualified name (`Box`)

- cs19/P/Block.cs line 8: a namespace block's alias (`using Order = Lib.Order;` in
  `namespace Shop.Sub4 { }`) where a namespace around declares a type of the name
  (Shop.Order): a body draws nothing, though the block's alias is nearer (Roslyn: Lib.Order;
  declared relations draw it)

## Declared names Roslyn finds that are not drawn (misses, no failure)

- `cs18/P/Pkg.cs:10:16` in a namespace of a package the project references
  (`namespace CommunityToolkit.Mvvm.Input.Mine`), `Order`, which `using Shop;` brings in:
  the package may declare any type, so the name is unresolved with that reason, as a body
  draws nothing there (Roslyn: Shop.Order, the package has none)
- `cs20/P/Attr.cs:7:14` `Kind` of `[Tag(Kind.A)]`: the extractor draws `Shop.Kind` there
  (Roslyn's answer), but the comparison does not pair its name `Kind.A` with Roslyn's record
  of `Kind` (a limit of bench/declared.py's matching, not of the extractor)

## Known limits of declared relations (mismatches that stay)

- `cs20/P/Nested.cs:34:16` `Safe`, a global using's alias of `Lib.Box<Lib.Order>`: the
  extractor draws both types the alias names, Roslyn's key gives only the generic's
  definition (`Lib.Box`): a limit of the key's reading of aliases, not of the extractor
- `cs19/P/Aliases.cs:12:16` `Map`, `using Map = System.Collections.Generic.Dictionary<string,
  Lib.Order>;` (a name of a container, no longer passed over: #9, case 25): the same
- `cs21/P/Supers.cs:19:16` `Vector`, `using Vector = System.Collections.Generic.List<A.Item>;`
  (the same case): the same
