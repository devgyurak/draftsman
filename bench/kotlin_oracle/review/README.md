# Review sets: Kotlin sources written by hand

Each directory is a set of sources a review wrote to put the extractor and the compiler
side by side on forms the end-to-end repositories lack. `oracle.py review` compiles each
(its `.kt` files together, for the JVM, with the standard library) and compares the body
relations the extractor draws from it with the compiler's answers; it fails on a mismatch
not listed below as a known limit, and on fewer names drawn than the table says.

| Set | Names drawn | What it holds |
|---|---|---|
| `kt1` | 30 | the pre-check review's probe of name lookup: nested types and companion members inherited from a superclass (not from an interface, nor through an extension receiver), a class and a function of one name (`Money(1)`, `Money(1, 2)`, `Money("s")`), an import alias hiding the name from a star import, a star import before the default imports (`Result`), receiver lambdas, `vararg`, annotations on types. Its compile errors are meant: they show what Kotlin does not find |
| `kt2` | 71 | typealiases (of an alias, generic, of a function type, of an outer class, of a nested type), companion objects (named, with supertypes, types nested in them), `from` of nested types, accessors, secondary constructors, member extensions, delegation `by`, annotations on local declarations, `when`, `$Registry` in a string, names qualified with their package, backticks. Its 4 compile errors are meant (an alias import in the same package, a type parameter's bound) |
| `kt4` | 30 | a typealias as a type argument, also of a local class's or an anonymous object's supertype (the plugin said no class for it there). Its compile error is meant (`is` with an erased type) |
| `kt6` | 0 | an import alias hides the original name from a star import and from the file's own package (the compiler: unresolved), where the declared relations still draw `p.Money` (#7) |

Known limits (mismatches that stay):
