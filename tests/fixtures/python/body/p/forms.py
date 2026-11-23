from typing import Optional, cast

import p.foo
from p import foo as foomod
from p.bar import Bar, Sub
from p.foo import Foo, FooError


class Forms:
    made = Foo()                            #> Foo=p.foo.Foo/r
    kind = Bar                              #> Bar=p.bar.Bar/r

    def __init__(self) -> None:
        self.held: Foo = Foo()              #> Foo=p.foo.Foo/r Foo=p.foo.Foo/r

    def forms(self, x):
        a = Foo()                           #> Foo=p.foo.Foo/r
        b = Foo.create()                    #> Foo=p.foo.Foo/r
        if isinstance(x, (Foo, Bar)):       #> Foo=p.foo.Foo/r Bar=p.bar.Bar/r
            pass
        try:
            pass
        except FooError:                    #> FooError=p.foo.FooError/r
            pass
        c: Foo = a                          #> Foo=p.foo.Foo/r
        d: list[Foo] | None = None          #> Foo=p.foo.Foo/r
        e: Optional[Bar] = None             #> Bar=p.bar.Bar/r
        f = foomod.Foo.Inner()              #> Foo=p.foo.Foo/r Inner=p.foo.Foo.Inner/r
        g = p.foo.Foo()                     #> Foo=p.foo.Foo/r
        h = cast(Foo, x)                    #> Foo=p.foo.Foo/r
        i = f"{Foo.create()}"               #> Foo=p.foo.Foo/r
        j: "Foo" = a                        #> Foo=-
        k = Sub.Listener()                  #> Sub=p.bar.Sub/r Listener=-
        m: type[Bar] = Bar                  #> Bar=p.bar.Bar/r Bar=p.bar.Bar/r
        return a, b, c, d, e, f, g, h, i, j, k, m, Foo  #> Foo=p.foo.Foo/r

    def nested(self):
        def inner(y: Foo = Foo()) -> Bar:   #> Foo=p.foo.Foo/r Foo=p.foo.Foo/r Bar=p.bar.Bar/r
            return Bar()                    #> Bar=p.bar.Bar/r

        class Local(Foo):                   #> Local=- Foo=p.foo.Foo/r
            def k(self) -> Bar:             #> Bar=p.bar.Bar/r
                return Bar()                #> Bar=p.bar.Bar/r

        return inner, Local()               #> Local=local/r

    @staticmethod
    def signature(x: Foo = Foo()) -> Bar:   #> Foo=- Foo=- Bar=-
        return Bar()                        #> Bar=p.bar.Bar/r
