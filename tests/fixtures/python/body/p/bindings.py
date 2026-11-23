from p.bar import Bar, Inner
from p.foo import Foo


class Bindings:
    def unpacked(self, pair):
        Foo, x = pair
        return Foo                          #> Foo=var/r

    def starred(self, items):
        *Foo, x = items
        return Foo                          #> Foo=var/r

    def augmented(self):
        Foo = 0
        Foo += 1
        return Foo                          #> Foo=var/r

    def listed(self, pair):
        [Foo, x] = pair
        return Foo                          #> Foo=var/r

    def loop_pairs(self, pairs):
        for Foo, x in pairs:
            return Foo                      #> Foo=var/r

    def opened_pair(self):
        with open("a") as (Foo):
            return Foo                      #> Foo=var/r

    def args(self, *Foo, **Bar):
        return Foo, Bar                     #> Foo=var/r Bar=var/r

    def typed(self, Foo: int, Bar: int = 1):
        return Foo, Bar                     #> Foo=var/r Bar=var/r

    def default(self, Foo=1, /, *, Bar=2):
        return Foo, Bar                     #> Foo=var/r Bar=var/r

    def generic(self):
        def inner[Foo](x: Foo) -> Foo:      #> Foo=- Foo=tparam/r Foo=tparam/r
            return x
        return inner, Foo()                 #> Foo=p.foo.Foo/r

    def deleted(self):
        Foo = 1
        del Foo                             #> Foo=var/r
        return 0

    def pattern(self, x):
        match x:
            case Bar.Inner:                 #> Bar=p.bar.Bar/r Inner=-
                return 1
            case [Foo, *rest]:              #> Foo=-
                return Foo                  #> Foo=var/r
        return Inner()                      #> Inner=p.bar.Inner/r

    def generic_alias(self):
        type Pair[Foo] = tuple[Foo, Foo]    #> Pair=- Foo=- Foo=tparam/r Foo=tparam/r
        return Pair                         #> Pair=var/r

    def deleted_many(self, flag):
        Foo = Bar = Inner = 1
        del (Foo, Bar), [Inner]             #> Foo=var/r Bar=var/r Inner=var/r
        return 0
