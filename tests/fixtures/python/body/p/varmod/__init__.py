from p.foo import Foo, FooError  # noqa: F401

if Foo:
    FooError = None
