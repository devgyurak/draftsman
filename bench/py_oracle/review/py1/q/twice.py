try:
    from q.x.foo import Foo
except ImportError:
    # #7: which Foo the name is depends on what ran
    class Foo: ...

from q.x.foo import Bar


class X(Foo): ...


class Y(Bar):
    f: Foo
    b: Bar
