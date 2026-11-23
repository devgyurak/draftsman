from p.bar import Bar, Inner
from p.foo import Foo


class Branch:
    if Bar:                                 #> Bar=-
        Foo = 1
    value = Foo                             #> Foo=var/r


class Tried:
    try:
        Foo = 1
    except Exception:
        pass
    value = Foo                             #> Foo=var/r


class Opened:
    with open("f") as Foo:
        pass
    value = Foo                             #> Foo=var/r


class Looped:
    for Inner in range(2):
        pass
    value = Inner                           #> Inner=var/r


class Unpacked:
    Foo, y = 1, 2
    value = Foo                             #> Foo=var/r


class Chained:
    x = Inner = 1                           #> Inner=-
    value = Inner                           #> Inner=var/r


class Walrus:
    (Foo := 1)
    value = Foo                             #> Foo=var/r


class FromImport:
    from p.bar import Bar as Foo
    value = Foo()                           #> Foo=p.bar.Bar/r

    def method(self):
        return Foo()                        #> Foo=p.foo.Foo/r


class ModuleImport:
    import p.bar as Foo
    value = Foo                             # a module

    def method(self):
        return Foo()                        #> Foo=p.foo.Foo/r


class Plain:
    value = Foo(), Inner()                  #> Foo=p.foo.Foo/r Inner=p.bar.Inner/r
