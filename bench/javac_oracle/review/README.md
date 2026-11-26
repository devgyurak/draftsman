# Review sets: Java sources written by hand

Each directory is a set of sources a review wrote to put the extractor and javac side by
side on forms the end-to-end repositories lack. `oracle.py review` compiles each (its
`.java` files together, Java 21) and compares the body relations the extractor draws from
it, and its declared relations (issue #7), with javac's answers
(bench/review_sets.py); it fails on a mismatch not listed below as a known limit, and on
fewer body names drawn or declared names agreed than the table says.

| Set | Body names drawn | Declared names agreed | What it holds |
|---|---|---|---|
| `jv1` | 7 | 40 | a review's probe of declared names: a superclass's private nested type (`Hidden`, not inherited, #7 case 49) beside the package's and its own class's, protected and public ones (inherited), an interface's nested type, type parameters named like types (`Gen<Money>`, `<Item>`), a JDK superclass's nested type (`Thread.State`), single-type, on-demand and static imports, an annotation's arguments. Before the fix: 2 body mismatches, 1 declared |
| `jv2` | 8 | 24 | a review's probe of inheritance across packages: a superclass's package-private nested type (`a.Base.Pkg`, not inherited by `b.SubB`, nor through `Third extends SubB`, nor in `SubB.In`; inherited by `a.SubA`) beside protected, public and private ones, private nested types of a nested base, a class's own private nested type in its inner class. Before the fix: 3 body mismatches, 3 declared |
| `jv3` | 0 | 22 | a supertype's type arguments (#9, case 24): `extends ArrayList<Node>` beside another package's `Node`, a type parameter `T` beside a class `T`, nested arguments (`HashMap<String, List<Item>>`), the class itself (`Comparable<Nested>`, drawn to nothing), a nested class's supertype (`Base.In<Node>`), arguments over several lines; a project class named like a container (`Provider<Item>`, case 25). Before the fix: 12 agreed, 7 misses |
| `jv4` | 0 | 34 | a review's probe of a supertype's type arguments (#9, case 24): classes named like type parameters, another package's type of the name, nested and annotated arguments. At f5e007a: 34 agreed, no mismatch |
| `jv5` | 5 | 32 | #9 stage 3 and #7's forms found after 0.10.0: `? super X` (beside a type parameter named like a class `T`), `Conn.@Nullable Response` beside a top-level `Response`, annotations on enum constants (`@Other(Item.class) BORING { ... }`), a package-private nested type through a superclass of another package (`a.Leaf extends b.Mid extends a.Base`, beside protected ones), a package-private field of a superclass in another package beside a class of its name. Before the fix (d11e7cc): declared 22 agreed, 1 mismatch, 7 misses; body 4 drawn, 1 mismatch |
| `jv6` | 2 | 26 | a review's probe of #9 cases 26-28 and the package-private chain: `? super X` in parameters, fields, nested arguments, a bound and a function's arguments, `Conn.@Nn Response` also fully qualified and as a type argument, annotations on array levels, annotations on enum constants, also one with a body; a superclass's package-private field `Money` (another package's subclass: the class `b2.Money` in a body), a protected one. The extractor at 973abe2: the same |

Known limits (mismatches that stay):

- none

Known limits of declared relations (mismatches that stay):

- none
