# Body references in Python: names whose answer is known

Every name these sources write inside a body (a method's body, the value of an
assignment directly in a class body, and the functions, lambdas and classes inside them)
that names a class, or that starts upper-case or with `_`, with the answer of the three
checkers, in a `#>` marker at the end of the line. The format is the Java fixture's
(`tests/fixtures/java/body/README.md`):

    a = Foo()                           #> Foo=p.foo.Foo/r

The answer is a class's id as ir.json writes it (module + the classes around it + name),
`var` (a variable, a parameter, a function, a class attribute, an alias), `local` (a
class declared in a function), `error` (a name nothing binds), `disputed` (mypy, pyright
and ty do not give the same: nothing may be drawn there), or `-` (a binding such as
`case Bound:`, a name in a string annotation or a type comment, a name in the method's
own signature, or a nested class reached through a subclass, `Sub.Listener`, which mypy
does not bind). The
position is always `r`: a variable of the name hides a class in an annotation as
anywhere else.

`bench/py_oracle/oracle.py selftest` checks the three checkers against these markers;
the extractor's tests (`tests/test_body_relations_python.py`) check `ir.json` against the
same markers.
