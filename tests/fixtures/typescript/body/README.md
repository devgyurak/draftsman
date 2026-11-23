# Body references in TypeScript: names whose answer is known

Every name these sources write inside a body (method, constructor and accessor bodies,
field initializers, static blocks, enum members' values, and the functions, classes and
object literals inside them) that names a type, a type parameter, a type alias, a local
class or an upper-case value, with the answer the TypeScript compiler gives, in a `//>`
marker at the end of the line. The format is the Java fixture's
(`tests/fixtures/java/body/README.md`):

    const g: Foo = Foo.create();     //> Foo=p/foo.Foo/t Foo=p/foo.Foo/r

The answer is a type's id as ir.json writes it (module path + namespaces + name), `var`
(a variable, a parameter, a function, a constant), `tparam`, `alias` (a type alias),
`local` (a class declared in a body), or `-` (a declaration, a label in a type as in
`[Foo: string]`, a member after a type as in `Kind.A`, or a namespace before one as in
`Shop.Item`). The position is `t` where only a type can stand (`: Foo`, `as Foo`,
`satisfies Foo`, `implements Foo`, type arguments, `import("./bar").Bar`) or `r` where a
value stands, which a variable may be (`new Foo()`, `Foo.m()`, `Kind.A`,
`x instanceof Foo`, `typeof Foo`, `<Foo />`, `Foo` as an argument or in `{ Foo }`).

`bench/tsc_oracle/oracle.py selftest` checks the compiler against these markers, with
`tsconfig.json` here; the extractor's tests (`tests/test_body_relations_typescript.py`)
check `ir.json` against the same markers.
