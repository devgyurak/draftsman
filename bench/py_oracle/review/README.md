# Review sets: Python sources written by hand

Each directory is a set of sources a review wrote to put the extractor and the three
checkers (mypy, pyright, ty) side by side on forms the end-to-end repositories lack.
`oracle.py review` runs them over each (no dependencies) and compares the body relations
the extractor draws from it, and its declared relations (issue #7), with the checkers'
answers (bench/review_sets.py); it fails on a mismatch not listed below as a known limit,
and on fewer body names drawn or declared names agreed than the table says. Where the
checkers disagree ("disputed") nothing may be drawn; such a place is counted apart.

| Set | Body names drawn | Declared names agreed | What it holds |
|---|---|---|---|
| `py1` | 2 | 32 | declared names (#7, cases 6, 7, 50): a member's decorator the class body binds (`Other = print`), annotations beside a class body's binding and beside a nested class the module also binds (the checkers disagree: drawn nothing), a name bound twice (`try: from q.x.foo import Foo` / `except: class Foo`) in a base and an annotation, imports under another name, module aliases, nested classes, string annotations, generics. Before the fix: 1 declared mismatch, 8 drawn where the checkers disagree |

Known limits (mismatches that stay):

- none

Known limits of declared relations (mismatches that stay):

- none
