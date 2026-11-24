# Review sets: Kotlin sources written by hand

Each directory is a set of sources a review wrote to put the extractor and the compiler
side by side on forms the end-to-end repositories lack. `oracle.py review` compiles each
(its `.kt` files together, for the JVM, with the standard library) and compares the body
relations the extractor draws from it with the compiler's answers; it fails on a mismatch
not listed below as a known limit, and on fewer names drawn than the table says.

| Set | Names drawn | What it holds |
|---|---|---|
| `kt1` | 33 | the pre-check review's probe of name lookup: nested types and companion members inherited from a superclass (not from an interface, nor through an extension receiver), a class and a function of one name (`Money(1)`, `Money(1, 2)`, `Money("s")`), an import alias hiding the name from a star import, a star import before the default imports (`Result`), receiver lambdas, `vararg`, annotations on types. Its compile errors are meant: they show what Kotlin does not find |
| `kt2` | 73 | typealiases (of an alias, generic, of a function type, of an outer class, of a nested type), companion objects (named, with supertypes, types nested in them), `from` of nested types, accessors, secondary constructors, member extensions, delegation `by`, annotations on local declarations, `when`, `$Registry` in a string, names qualified with their package, backticks. Its 4 compile errors are meant (an alias import in the same package, a type parameter's bound) |
| `kt4` | 30 | a typealias as a type argument, also of a local class's or an anonymous object's supertype (the plugin said no class for it there). Its compile error is meant (`is` with an erased type) |
| `kt6` | 0 | an import alias hides the original name from a star import and from the file's own package (the compiler: unresolved), where the declared relations still draw `p.Money` (#7) |
| `kt7` | 43 | the first review of the extractor: an import alias hiding the name in the file's own package, nested types of an interface and of a superclass's companion (not seen in a subclass), a class and a function of one name in calls, member extensions' receivers, receiver lambdas, shadowing locals, type parameters, imports of nested types and enum entries. No compile errors: each wrong candidate has a real rival, so a wrong draw is a mismatch |
| `kt8` | 20 | the implementation's own probe after the table: library supertypes the table knows (Thread's nested `State` and static `MAX_PRIORITY`, CoroutineScope's `coroutineContext`, Exception's `message`), extensions of library types (members only, no nested type or static), a method or a companion's function of a class's name, private classes, values (named arguments, inherited and interface properties, a top-level extension property, explicit imports of an enum entry and an object's property, lambda and destructured names). No compile errors |

| `kt9` | 58 | the review of the extractor's last round: values (enum entries, objects and companions in arguments, operators, `when`, templates, `by`, `throw`), imports of enum entries and objects, receivers of extensions (a type parameter's bounds, `where`, an alias, a nullable or generic receiver, a project type under a library supertype, local extensions), interface companions. No compile errors |
| `kt10` | 10 | a constructor parameter's default value (`class Z(val p: Any = Registry)`), which hid the name in the whole class |
| `kt11` | 9 | accessors on the line after their property (`val b: Any` / `get() = ...`), block getters, setters, `override` properties |
| `kt12` | 7 | a class's delegate `: Face by Proxy`, after a superclass's constructor call, in an object, through a constructor parameter |
| `kt13` | 10 | a library supertype's private and package-private names (Thread's `Caches`, `eetop`, `holder`, ArrayList's `Itr`, `elementData`), which hide nothing, beside its protected and public static ones (`modCount`, `MAX_PRIORITY`), which do |

A mismatch in a file with compile errors counts as one here: the sets compile with errors on
purpose.

Known limits (mismatches that stay):

- `kt7/shop/Recv.kt:4:31` a lambda with a receiver (`with(c) { Money(1) }`): which lambda has
  one, and of what type, is the called function's, not the syntax's
- `kt7/shop/Recv.kt:5:29` the same (`c.run { Order.toString() }`)
- `kt1/q/Use.kt:42:25` the same (`dsl { Widget(); Registry }`: the value `Registry` is the
  receiver's property)

Names the compiler finds that are not drawn (misses, no failure):

- `kt9/q/ImportsV.kt:8:28` an imported enum entry (`import shop.Kind.A`) is taken to hide
  the name in type positions too, where Kotlin looks for a class (`q.A`)
- `kt9/shop/Recv2.kt:25:30` a local extension's receiver (`fun Ctx.loc()` in `g`) is taken
  for the whole member's
- `kt9/shop/Recv2.kt:31:25` a superclass's companion member is taken to be a receiver's
  (`fun Sub2.k() = Flag`), and `kt9/shop/Vals.kt:15:20`, `16:20` an interface's companion
  members an implementing class's (`Flag2`, `Helper2()`)
- `kt9/shop/Vals.kt:34:26`, `35:26` `Order.Companion` answers at both names: `Order` is drawn
