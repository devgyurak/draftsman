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

Known limits (mismatches that stay):

- none

Known limits of declared relations (mismatches that stay):

- none
