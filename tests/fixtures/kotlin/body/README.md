# Body references in Kotlin: names whose answer is known

Every name these sources write inside a body (a function's body, a property's initializer,
getter and delegate, an `init` block, a default argument, a superclass's constructor
arguments, an enum entry's arguments and body, and everything inside them: lambdas,
anonymous objects, local classes and functions), with the answer the Kotlin compiler gives,
written by hand in a `//>` marker at the end of the line (format:
tests/fixtures/java/body/README.md). The answer is a type's id as ir.json writes it (a
typealias's is the class it stands for: `Cash(2)` answers `shop.Money`),
or what else the name is: `var` (a parameter or local variable), `function`, `property`,
`enumEntry`, `local` (a local class), `package`, `label` (`this@Uses`), or `-` (no name in a
body: a declaration). The position is `t` where only a type can stand (`val x: Foo`,
`is Foo`, `<Foo>`, a supertype) and `r` where a value can as well (`Foo(...)`, `Foo.x`,
`Foo::class`, a name alone).

`bench/kotlin_oracle/oracle.py selftest` checks the compiler's answers against these
markers. The sources compile with the Kotlin compiler (JVM) and the standard library alone.
A name after a `.` is not listed: no type is named there, but a nested class's
constructor (`Order.Line()`). A string template's names are written `${Plugin}` here, as
the marker parser takes `$` for a part of a name.
