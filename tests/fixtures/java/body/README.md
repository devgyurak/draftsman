# Body references: names whose answer is known

Every type name these sources write inside a body (method, constructor, initializer,
field initializer, enum constant argument, lambda, anonymous or local class), with the
answer javac gives, written by hand in a `//>` marker at the end of the line:

    Owner a = new Owner();     //> Owner=p.Owner/t Owner=p.Owner/t

Each item is `Name=answer/position`. Items go left to right; the n-th item named `Owner`
is the n-th whole-word `Owner` in the code before the marker. The answer is a type's
qualified name, `var` (a variable), `tparam` (a type parameter), `local` (a local class),
or `-` (not a name in a body: a declaration, or a plain expression). The position is `t`
(a type name: `new`, a cast, a local variable's type, `X.class`, ...) or `r` (a receiver:
`X.m()`, `X.F`, `X::m`), where a variable would win over a type.

`bench/javac_oracle/oracle.py selftest` checks the oracle against these markers; the
extractor's tests check `ir.json` against the same markers. The sources compile with
`javac --release 21` and nothing on the classpath. Names no compiler accepts (one simple
name from two star imports) are in the extractor's tests, not here.
