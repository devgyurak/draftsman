from enum import Enum

from p.bar import Inner
from p.foo import Foo


class Outer:
    class Inner:
        pass

    made = Inner()                          #> Inner=p.scopes.Outer.Inner/r
    lazy = lambda self: Inner()             #> Inner=p.bar.Inner/r

    def method(self):
        return Inner()                      #> Inner=p.bar.Inner/r

    def qualified(self):
        return Outer.Inner()                #> Outer=p.scopes.Outer/r Inner=p.scopes.Outer.Inner/r


class Config:
    Foo = 1
    value = Foo                             #> Foo=var/r

    def method(self):
        return Foo()                        #> Foo=p.foo.Foo/r


class Kind(Enum):
    A = 1
    B = A                                   #> A=var/r

    def method(self):
        return Kind.A                       #> Kind=p.scopes.Kind/r A=-
