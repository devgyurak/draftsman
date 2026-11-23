from p.bar import Bar
from p.foo import Foo

Alias = Bar


def Foo():
    return 1


class Rebind:
    def function(self):
        return Foo()                        #> Foo=disputed/r

    def alias(self):
        return Alias()                      #> Alias=var/r
