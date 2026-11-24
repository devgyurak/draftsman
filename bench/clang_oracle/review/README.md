# Review sets: C++ sources written by hand

Each directory is a set of sources a review wrote to put the extractor and Clang side by
side on forms the end-to-end repositories lack. `oracle.py review` compiles each (every
`.cc` file a translation unit, C++17, the directory as include path, and each header no
unit includes a unit of its own) and compares the body relations the extractor draws from
it with Clang's answers; it fails on a mismatch not listed below as a known limit, and on
fewer names drawn than the table says. The sets compile without errors: a wrong candidate
has a real rival, so that a wrong draw is a mismatch.

| Set | Names drawn | What it holds |
|---|---|---|
| `cpp1` | 0 | the pre-check's probe of name lookup: `using namespace` (a namespace's own name is nearer), a block's `using a::B;`, a namespace alias, a call `Make(s)` that is the type (no argument-dependent lookup past a type) and `Tag(s)` that is a function of an argument's namespace, a vexing parse |

Known limits (mismatches that stay):

Names Clang finds that are not drawn (misses, no failure):
