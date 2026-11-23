import sys
import typing
from typing import TYPE_CHECKING

from p.bar import Bar
from p.foo import Foo

PY2 = False


class Unreachable:
    def after_return(self):
        return 1
        return Foo()                        #> Foo=p.foo.Foo/r

    def never(self):
        if False:
            return Foo()                    #> Foo=p.foo.Foo/r
        if 0:
            return Bar()                    #> Bar=p.bar.Bar/r
        return None

    def forever(self):
        while True:
            pass
        return Foo()                        #> Foo=p.foo.Foo/r

    def version(self):
        assert sys.version_info >= (3, 99)
        return Foo()                        #> Foo=p.foo.Foo/r

    def py2(self):
        if PY2:                             #> PY2=var/r
            return Foo()                    #> Foo=p.foo.Foo/r
        return None

    def checking(self):
        if TYPE_CHECKING:                   #> TYPE_CHECKING=var/r
            return Foo()                    #> Foo=p.foo.Foo/r
        else:
            return Bar()                    #> Bar=disputed/r

    def not_checking(self):
        if not TYPE_CHECKING:               #> TYPE_CHECKING=var/r
            return Bar()                    #> Bar=disputed/r
        return None

    def typing_attribute(self):
        if typing.TYPE_CHECKING:
            return 1
        else:
            return Foo()                    #> Foo=disputed/r

    def elif_not_checking(self, x):
        if x:
            return 1
        elif not TYPE_CHECKING:             #> TYPE_CHECKING=var/r
            return Foo()                    #> Foo=disputed/r
        return 2

    def conditional(self):
        return Foo() if TYPE_CHECKING else Bar()  #> Foo=p.foo.Foo/r TYPE_CHECKING=var/r Bar=disputed/r


class Narrowed:
    names = ()

    def m(self, name):
        if name in self.names:
            return Foo()                    #> Foo=p.foo.Foo/r
        return None
