from p.foo import Foo


class Marked:
    pass


class Reads:
    def m(self):
        return Marked(), Foo()             #> Marked=p.bom.Marked/r Foo=p.foo.Foo/r
