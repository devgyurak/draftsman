from __future__ import annotations

from p.foo import Foo


class Future:
    def method(self):
        x: Foo = Foo()                      #> Foo=p.foo.Foo/r Foo=p.foo.Foo/r
        return x
