from p.foo import Foo


class Matching:
    def match(self, x):
        match x:
            case Foo():                     #> Foo=p.foo.Foo/r
                return 1
            case Bound:                     #> Bound=-
                return Bound                #> Bound=var/r
