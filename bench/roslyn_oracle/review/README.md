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
| `cs19` | 8 | 32 | a review's probe of the fix: a `global using` alias in every file of its project, aliases of a file in two namespaces of it, a namespace block's alias beside another block of the namespace, a namespace alias (`L.Order`, `L::Order`), an alias of a generic, `InternalsVisibleTo`, an unreferenced project's public type, arity of two type arguments, `nameof` and `typeof` beside members and nested types, `Kind.A` beside `public Kind Kind`, a namespace of the shared framework around the code |

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
- `cs19/P/Aliases.cs:10:18`, `11:19` a type through a namespace alias (`using L = Lib;`:
  `L.Order`, `L::Order`): not read (#9)

## Known limits of declared relations (mismatches that stay)

- none
