# Body references in C#: names whose answer is known

Every name these sources write inside a body (method, constructor, accessor, operator and
local function bodies, constructor initializers, field, property and enum member
initializers, a primary constructor's base arguments, top-level statements, and the
lambdas inside them) that names a type, a type parameter or an upper-case variable, with
the answer Roslyn gives, in a `//>` marker at the end of the line. The format is the Java
fixture's (`tests/fixtures/java/body/README.md`):

    Order o = Order.Create();     //> Order=Shop.Order/t Order=Shop.Order/r

The answer is a type's id as ir.json writes it (namespaces and outer types by `.`, no type
arguments: `Repo` and `Repo<T>` are both `Shop.Repo`), `var` (a local, a parameter, a
field, a property, a range variable), `tparam`, `split` (the two target frameworks
resolve it differently), or `-` (a declaration, a signature, an attribute, a parameter
default, a member after a dot, a named argument, an initializer's, a pattern's or a tuple
element's member name, a label, or a namespace before a type as in `Shop.Order`). The
position is `t` where only a type can stand (`new Foo()`, `Foo x`, `(Foo)x`, `typeof(Foo)`,
`default(Foo)`, type arguments, `catch (Foo)`, `is Foo f`, and `is Foo` when Foo is a type)
or `r` where an expression does, which a variable may be (`Foo.M()`, `Foo.X`,
`nameof(Foo)`, `case Foo:`, a switch arm's `Foo =>`, `is not Foo`, `is A or B`, the head of
`is Status.Closed`).

`bench/roslyn_oracle/oracle.py selftest` checks Roslyn against these markers, compiling
`Body.csproj` for net11.0 and net10.0 in Debug; the extractor's tests
(`tests/test_body_relations_csharp.py`) check `ir.json` against the same markers.
