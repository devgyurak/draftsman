from p.bar import Bar, Inner
from p.foo import Foo


class Matching:
    def match(self, x):
        match x:
            case Foo():                     #> Foo=p.foo.Foo/r
                return 1
            case Bound:                     #> Bound=-
                return Bound                #> Bound=var/r

    def keyword(self, x):
        match x:
            case Bar(Foo=0):                #> Bar=p.bar.Bar/r Foo=-
                return 1
            case Bar(Inner=Inner()):        #> Bar=p.bar.Bar/r Inner=- Inner=p.bar.Inner/r
                return 2

    def keyword_capture(self, x):
        match x:
            case Bar(real=Foo):             #> Bar=p.bar.Bar/r Foo=-
                return Foo                  #> Foo=var/r

    def as_capture(self, x):
        match x:
            case Bar() as Foo:              #> Bar=p.bar.Bar/r Foo=-
                return Foo                  #> Foo=var/r

    def rest(self, x):
        match x:
            case {**Foo}:                   #> Foo=-
                return Foo                  #> Foo=var/r

    def star(self, x):
        match x:
            case [Bar(), *Foo]:             #> Bar=p.bar.Bar/r Foo=-
                return Foo                  #> Foo=var/r

    def nested_as(self, x):
        match x:
            case (Bar() as Foo, _):         #> Bar=p.bar.Bar/r Foo=-
                return Foo                  #> Foo=var/r

    def elsewhere(self, x):
        match x:
            case [Foo]:                     #> Foo=-
                return 1
        return Foo()                        #> Foo=var/r
