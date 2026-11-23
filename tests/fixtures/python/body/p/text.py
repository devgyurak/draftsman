from p.foo import Foo


class Text:
    def wide(self):
        s = "한글", Foo()                      #> Foo=p.foo.Foo/r
        t = "😀😀", Foo(), Foo.Inner()         #> Foo=p.foo.Foo/r Foo=p.foo.Foo/r Inner=p.foo.Foo.Inner/r
        u = "😀😀😀"; v: Foo = Foo()           #> Foo=p.foo.Foo/r Foo=p.foo.Foo/r
        w = "😀😀"; x: Foo.Inner = Foo.Inner()  #> Foo=p.foo.Foo/r Inner=p.foo.Foo.Inner/r Foo=p.foo.Foo/r Inner=p.foo.Foo.Inner/r
        return s, t, u, v, w, x, f"😀{Foo()!r:>{Foo.create()}}"  #> Foo=p.foo.Foo/r Foo=p.foo.Foo/r
