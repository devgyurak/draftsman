# Review sets: Kotlin sources written by hand

Each directory is a set of sources a review wrote to put the extractor and the compiler
side by side on forms the end-to-end repositories lack. `oracle.py review` compiles each
(its `.kt` files together, for the JVM, with the standard library) and compares the body
relations the extractor draws from it with the compiler's answers; it fails on a mismatch
not listed below as a known limit, and on fewer names drawn than the table says.

| Set | Names drawn | What it holds |
|---|---|---|
| `kt1` | 0 | the pre-check review's probe of name lookup: nested types and companion members inherited from a superclass (not from an interface, nor through an extension receiver), a class and a function of one name (`Money(1)`, `Money(1, 2)`, `Money("s")`), an import alias hiding the name from a star import, a star import before the default imports (`Result`), receiver lambdas, `vararg`, annotations on types. Its compile errors are meant: they show what Kotlin does not find |

Known limits (mismatches that stay):
