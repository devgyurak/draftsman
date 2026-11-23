from typing import TYPE_CHECKING

from p.foo import *

if TYPE_CHECKING:
    from p.bar import Bar

try:
    from p.bar import Inner
except ImportError:
    Inner = None


class Module:
    def star(self):
        return Foo()                        #> Foo=p.foo.Foo/r

    def checking(self) -> None:
        x: Bar = self.make()                #> Bar=p.bar.Bar/r
        print(isinstance(x, Bar))           #> Bar=p.bar.Bar/r

    def conditional(self):
        return Inner                        #> Inner=disputed/r

    def make(self):
        return None
