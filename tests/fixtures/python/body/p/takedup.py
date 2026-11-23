from p import dup, mix, one, own, same
from p.dup import Foo, OnlyA
from p.mix import Both as Mixed
from p.one import Both
from p.own import Both as Owned
from p.same import Foo as Same


class TakeDup:
    def named(self):
        return Foo(), OnlyA()               #> Foo=disputed/r OnlyA=p.dup.a.OnlyA/r

    def through_the_module(self):
        return dup.Foo(), dup.OnlyA()       #> Foo=disputed/r OnlyA=p.dup.a.OnlyA/r

    def by_stars(self):
        return Both(), one.Both(), one.OnlyA()  #> Both=disputed/r Both=disputed/r OnlyA=p.one.a.OnlyA/r

    def name_and_star(self):
        return Mixed(), mix.Both()          #> Mixed=disputed/r Both=disputed/r

    def one_class_twice(self):
        return Same(), same.Foo()           #> Same=p.dup.a.Foo/r Foo=p.dup.a.Foo/r

    def class_and_star(self):
        return Owned(), own.Both()          #> Owned=disputed/r Both=disputed/r
