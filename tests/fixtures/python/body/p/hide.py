from p.bar import Bar
from p.foo import Foo


class Hide:
    def parameter(self, Foo):
        return Foo()                        #> Foo=var/r

    def assigned(self):
        Foo = 1
        return Foo                          #> Foo=var/r

    def later(self):
        x = Foo()                           #> Foo=disputed/r
        Foo = 1
        return x, Foo                       #> Foo=var/r

    def loop(self):
        for Foo in range(3):
            print(Foo)                      #> Foo=var/r

    def opened(self):
        with open("f") as Foo:
            return Foo.read()               #> Foo=var/r

    def caught(self):
        try:
            pass
        except ValueError as Foo:
            return Foo                      #> Foo=var/r

    def comprehension(self):
        xs = [Foo for Foo in range(3)]      #> Foo=var/r Foo=-
        return xs, Foo()                    #> Foo=p.foo.Foo/r

    def walrus(self):
        if (Foo := 1):
            return Foo                      #> Foo=var/r

    def imported(self):
        from p.bar import Bar as Foo
        return Foo()                        #> Foo=p.bar.Bar/r

    def function(self):
        def Foo():
            return 1
        return Foo()                        #> Foo=var/r

    def local_class(self):
        class Foo:
            pass
        return Foo()                        #> Foo=local/r

    def lambdas(self):
        f = lambda Foo: Foo()               #> Foo=- Foo=var/r
        return f, Foo()                     #> Foo=p.foo.Foo/r

    def closure(self, Bar):
        def inner():
            return Bar()                    #> Bar=var/r
        return inner

    def outer(self):
        Foo = 1

        def inner():
            nonlocal Foo
            Foo = 2
        return inner, Foo                   #> Foo=var/r
