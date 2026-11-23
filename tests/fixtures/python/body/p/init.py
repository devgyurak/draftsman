from p.bar import Bar
from p.foo import Foo


class Init:
    def __init__(self, Bar):
        Foo = 1
        self.x = Foo                        #> Foo=var/r
        self.y = Bar                        #> Bar=var/r

    def method(self):
        self.z = Foo(), Bar()               #> Foo=p.foo.Foo/r Bar=p.bar.Bar/r


class Imported:
    def __init__(self):
        from p.bar import Bar as Foo
        self.x = Foo()                      #> Foo=p.bar.Bar/r
