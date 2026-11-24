# Body references in C++: names whose answer is known

Every name of a type these sources write inside a body (a function's body, also one
defined out of its class, a constructor's initializers, a default argument, a default
member initializer, a static member's initializer, an enumerator's value, and everything
inside them: lambdas, local classes), with the answer Clang gives, written by hand in a
`//>` marker at the end of the line (format: tests/fixtures/java/body/README.md). The
answer is a type's id as ir.json writes it (a type of an anonymous namespace without it:
`shop::State`; an alias is the first type it names, `Feed` answers `lib::AutoPtr`), or what
else the name is: `var` (a parameter or local variable), `member` (a field), `tparam`,
`dependent` (`typename T::Line`: no answer before the template is instantiated), or `-` (no
name in a body: a declaration, a signature, a macro's argument made a string). The
position is `t` where only a type can stand (`Foo x`, `new Foo`, a cast, a template
argument, `Foo::` before a member) and `r` where a value can as well (`Foo(1)`, a base's
initializer `: Base(1)`, the parameter of a block-scope function declaration `Base
b(Base::Tag)`, a name that is no type).

`bench/clang_oracle/oracle.py selftest` checks Clang's answers against these markers. Each
`.cc` file is a translation unit, compiled as C++17 with this directory as include path.
