from p.bar import Bar, Inner
from p.foo import *
from p.foo import FooError

for Bar in range(3):
    pass

with open("f") as Inner:
    pass

FooError: type = ValueError

type Alias = Bar                            #> Bar=-


class Foo:
    pass


class Top:
    def loop(self):
        return Bar                          #> Bar=disputed/r

    def opened(self):
        return Inner                        #> Inner=disputed/r

    def annotated(self):
        return FooError                     #> FooError=disputed/r

    def shadowed(self):
        return Foo()                        #> Foo=disputed/r

    def alias(self):
        return Alias                        #> Alias=var/r
