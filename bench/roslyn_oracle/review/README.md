# Review sets

Sources written by hand in the reviews of C#'s body relations (issue #5), one directory per
set, each with its own projects, kept here so that every change is checked against all of
them:

    uv run bench/roslyn_oracle/oracle.py review [SET ...]

runs each set through Roslyn and the extractor (`key DIR --compare`) and fails on a
mismatch not listed below, or on fewer names drawn than the table gives.

| Set | Names drawn | What it holds |
|---|---:|---|
| `cs1` | 19 | private nested types of a base, Color Color, delegates, `file` types, casts and patterns, block usings, aliases |
| `cs2` | 26 | usings after a file-scoped namespace, `<Using>` items, a partial type's `#else` member, `#if` constants, arity, a BOM |
| `cs3` | 1 | another project's internal types, a Razor component |
| `cs4` | 5 | members of outside base classes (`ControllerBase.User`, `Exception.Data`), aliases |
| `cs5` | 12 | the table's namespaces around the code, bases, block usings, `#if false ... #else` |
| `cs6` | 3 | default accessibility across projects |
| `cs7` | 7 | a package's namespace around the code (CommunityToolkit.Mvvm), qualified names |
| `cs8` | 16 | qualified names through nested and generic types and aliases; aliases and `using static` in outside namespaces |
| `cs9` | 54 | a qualified name's first part in every position, alias targets, arity, `#if` with `==` and `!=` |
| `cs10` | 2 | internal and unreferenced projects' namespaces before a qualified name |
| `dbg` | 9 | a `using` of a namespace of the sources that holds no type itself |

## Known limits

Drawn although no build compiles the place (the parser reads the first branch of an `#if`
whose condition depends on a symbol):

- `cs2/Dead.cs:9:30`
- `cs2/Dead.cs:14:30`
