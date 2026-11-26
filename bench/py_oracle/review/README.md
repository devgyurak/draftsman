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
| `py2` | 0 | 12 | a review's probe of the fix: names bound twice through imports and `TYPE_CHECKING`, a class body's bindings of several kinds, forward references, aliases of imports |
| `py3` | 0 | 10 | a base's type arguments (#9, case 24): `List[Node]` beside another package's `Node`, `Generic[T]` with a `TypeVar` beside a class `T`, nested arguments, a module-qualified `b.models.Node`, the class itself as a string; an alias named like a container (`type Vector = list[Item]`, case 25). Before the fix: 5 agreed, 4 misses |
| `py4` | 0 | 7 | #9 cases 33, 34: a class's attribute as a decorator (`@Field.register`, with arguments), bases made by calls (`BaseManager.from_queryset(QuerySet, Item=1)`, a function's `make_base(QuerySet, "Item", kind=None)`), each beside a class named like a keyword or a string there; a property's `@content.setter` beside a module class `content`. Before the fix (d11e7cc): 2 agreed, 5 misses |
| `py5` | 0 | 13 | a review's probe of #9 cases 33, 34: a class's attribute as a decorator, also through a module alias (`@m.Field.register`) and on a method, a value's attribute (`@registry.bound`: no class), a call decorator with keyword arguments, bases made by calls with a keyword argument whose string names a class (`name="Other"`) and a string argument (`make("Field", 1)`), a property's setter, `@Resp.content.setter` beside a base's property. The extractor at 973abe2: the same |

Known limits (mismatches that stay):

- none

Known limits of declared relations (mismatches that stay):

- `py3/p/lists.py:34:12` `Vector`, a `type` statement's alias of `list[Item]`: the
  extractor draws `Item`, the alias names it; the key records a type alias as a variable
  with no types it names (a limit of the key: `type Items = list[Item]` compares so too)
