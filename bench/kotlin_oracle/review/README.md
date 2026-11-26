# Review sets: Kotlin sources written by hand

Each directory is a set of sources a review wrote to put the extractor and the compiler
side by side on forms the end-to-end repositories lack. `oracle.py review` compiles each
(its `.kt` files together, for the JVM, with the standard library) and compares the body
relations the extractor draws from it, and its declared relations (issue #7), with the
compiler's answers; it fails on a mismatch not listed below as a known limit, and on fewer
body names drawn or declared names agreed than the table says.

| Set | Body names drawn | Declared names agreed | What it holds |
|---|---|---|---|
| `kt1` | 33 | 19 | the pre-check review's probe of name lookup: nested types and companion members inherited from a superclass (not from an interface, nor through an extension receiver), a class and a function of one name (`Money(1)`, `Money(1, 2)`, `Money("s")`), an import alias hiding the name from a star import, a star import before the default imports (`Result`), receiver lambdas, `vararg`, annotations on types. Its compile errors are meant: they show what Kotlin does not find |
| `kt2` | 73 | 25 | typealiases (of an alias, generic, of a function type, of an outer class, of a nested type), companion objects (named, with supertypes, types nested in them), `from` of nested types, accessors, secondary constructors, member extensions, delegation `by`, annotations on local declarations, `when`, `$Registry` in a string, names qualified with their package, backticks. Its 4 compile errors are meant (an alias import in the same package, a type parameter's bound) |
| `kt4` | 30 | 4 | a typealias as a type argument, also of a local class's or an anonymous object's supertype (the plugin said no class for it there). Its compile error is meant (`is` with an erased type) |
| `kt6` | 0 | 5 | an import alias hides the original name from a star import and from the file's own package (the compiler: unresolved); the declared relations draw nothing there either (#7, case 9) |
| `kt7` | 56 | 41 | the first review of the extractor: an import alias hiding the name in the file's own package, nested types of an interface and of a superclass's companion (not seen in a subclass), a class and a function of one name in calls, member extensions' receivers, receiver lambdas, shadowing locals, type parameters, imports of nested types and enum entries. No compile errors: each wrong candidate has a real rival, so a wrong draw is a mismatch |
| `kt8` | 20 | 57 | the implementation's own probe after the table: library supertypes the table knows (Thread's nested `State` and static `MAX_PRIORITY`, CoroutineScope's `coroutineContext`, Exception's `message`), extensions of library types (members only, no nested type or static), a method or a companion's function of a class's name, private classes, values (named arguments, inherited and interface properties, a top-level extension property, explicit imports of an enum entry and an object's property, lambda and destructured names). No compile errors |

| `kt9` | 58 | 100 | the review of the extractor's last round: values (enum entries, objects and companions in arguments, operators, `when`, templates, `by`, `throw`), imports of enum entries and objects, receivers of extensions (a type parameter's bounds, `where`, an alias, a nullable or generic receiver, a project type under a library supertype, local extensions), interface companions. No compile errors |
| `kt10` | 10 | 11 | a constructor parameter's default value (`class Z(val p: Any = Registry)`), which hid the name in the whole class |
| `kt11` | 9 | 15 | accessors on the line after their property (`val b: Any` / `get() = ...`), block getters, setters, `override` properties |
| `kt12` | 7 | 11 | a class's delegate `: Face by Proxy`, after a superclass's constructor call, in an object, through a constructor parameter |
| `kt13` | 10 | 14 | a library supertype's private and package-private names (Thread's `Caches`, `eetop`, `holder`, ArrayList's `Itr`, `elementData`), which hide nothing, beside its protected and public static ones (`modCount`, `MAX_PRIORITY`), which do |
| `kt14` | 13 | 33 | accessors of extension properties, a comment between a property and its getter, `field` and `value`, receivers: an alias of a library type (`typealias T2 = Thread`), a qualified, parenthesized or annotated one (`@receiver:Suppress("x") Ctx`), an anonymous function's (`fun Ctx.(): Int = Money(2)`), class type parameters as receivers. No compile errors |
| `kt15` | 6 | 49 | declared relations (issue #7, cases 8 to 12), each beside a rival type: a star import of a package of the sources before the default imports (`Result`, `Pair`) and after the file's own package; an import alias hiding the name from the file's own package and from a star import (`r.Money` through `import r.*`); a nested type of a library superclass (`Thread.State`) before the package's; nested types of an interface and of a superclass's companion, not inherited, beside a superclass's, which is; the same names in bodies. The extractor before the fix: 16 declared mismatches, 2 body names drawn |
| `kt16` | 11 | 80 | a review's probe of the fix: nested types through a project superclass of a library one (`MyThread : Thread`), a library interface's (`Map`'s `Entry`, not seen) beside a Java class's own (`AbstractMap`'s `SimpleEntry`), an import under its own name beside an alias of it (`import p.Money` and `import p.Money as Coin`), an alias of a nested type, companions and interfaces of several levels, rivals in the file's own package. Declared: 80 names of the key, no mismatch (4 outside types in supertypes' type arguments read since #9, case 24) |
| `kt17` | 0 | 19 | a supertype's type arguments (#9, case 24): `ArrayList<Node>()` beside another package's `Node`, a type parameter `T` beside a class `T`, nested arguments, `Comparable<Nested>` naming the class itself, a delegation `List<Item> by d`; typealiases named like containers (`Vector`, `Provider`, case 25). Before the fix: 11 agreed, 6 misses |
| `kt18` | 0 | 21 | #9 stage 3: an alias of a suspend function type (36; a function type's parameter named like a class), an expect class beside an actual typealias of an outside class (37; its 4 compile errors are meant: one module compiles no expect/actual pair), context parameters (39; one named like a class), function types in parentheses (40), annotations on an accessor and on enum entries (41), an extension property's receiver (42), an import of a function named like the package's class (55). Before the fix (d11e7cc): 6 agreed, 13 misses |
| `kt19` | 0 | 34 | a review's probe of #9 stage 3: aliases of suspend function types with a receiver, a field of an alias of a function type, a receiver function type in parentheses, a nullable parenthesized function type, annotations on a setter and a getter and on an enum entry, extension properties' receivers (`Box<out Job?>.done`), context parameters, also one named like a class (`context(Ctx: Cfg)`), parameters and function type labels named like classes, an import of a function named like the package's class (55). The extractor at 973abe2: the same |

A mismatch in a file with compile errors counts as one here: the sets compile with errors on
purpose.

Known limits (mismatches that stay):

- `kt7/shop/Recv.kt:4:31` a lambda with a receiver (`with(c) { Money(1) }`): which lambda has
  one, and of what type, is the called function's, not the syntax's
- `kt7/shop/Recv.kt:5:29` the same (`c.run { Order.toString() }`)
- `kt1/q/Use.kt:42:25` the same (`dsl { Widget(); Registry }`: the value `Registry` is the
  receiver's property)
- `kt14/shop/A.kt:34:30` the same, where the lambda's type is written beside it
  (`val e: Ctx.() -> Int = { Money(1) }`): the type a lambda takes is its context's

Names the compiler finds that are not drawn (misses, no failure):

- `kt9/q/ImportsV.kt:8:28` an imported enum entry (`import shop.Kind.A`) is taken to hide
  the name in type positions too, where Kotlin looks for a class (`q.A`)
- `kt9/shop/Recv2.kt:25:30` a local extension's receiver (`fun Ctx.loc()` in `g`) is taken
  for the whole member's
- `kt9/shop/Recv2.kt:31:25` a superclass's companion member is taken to be a receiver's
  (`fun Sub2.k() = Flag`), and `kt9/shop/Vals.kt:15:20`, `16:20` an interface's companion
  members an implementing class's (`Flag2`, `Helper2()`)
- `kt9/shop/Vals.kt:34:26`, `35:26` `Order.Companion` answers at both names: `Order` is drawn

Declared names the compiler finds that are not drawn (misses, no failure):

- `kt14/shop/A.kt:38:33` the receiver of an extension written with an annotation
  (`@receiver:Suppress("x") Ctx`): not read (#9, case 60)

Known limits of declared relations (mismatches that stay):

- none
