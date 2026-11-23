from p import varmod
from p.varmod import Foo, FooError


class TakeVar:
    def named(self):
        return Foo(), FooError()            #> Foo=p.foo.Foo/r FooError=disputed/r

    def through_the_module(self):
        return varmod.Foo(), varmod.FooError()  #> Foo=p.foo.Foo/r FooError=disputed/r
