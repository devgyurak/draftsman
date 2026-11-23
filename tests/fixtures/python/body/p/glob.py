from p.foo import Foo


class Writes:
    def rebind(self):
        global Foo
        Foo = 1


class Reads:
    def use(self):
        return Foo()                        #> Foo=disputed/r
