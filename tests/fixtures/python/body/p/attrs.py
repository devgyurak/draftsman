from p.bar import Bar, Inner
from p.foo import Foo


class Attrs(Bar):
    def make(self):
        return self

    def after_values(self, xs, a, b):
        r = super().Foo                     #> Foo=-
        s = xs[0].Foo()                     #> Foo=-
        t = self.make().Foo                 #> Foo=-
        u = (a or b).Foo                    #> Foo=-
        v = "".Foo                          #> Foo=-
        w = Foo().Inner                     #> Foo=p.foo.Foo/r Inner=-
        x = Foo.create().Inner()            #> Foo=p.foo.Foo/r Inner=-
        y = a(b).Foo.Inner                  #> Foo=- Inner=-
        return r, s, t, u, v, w, x, y

    def named(self):
        return Inner()                      #> Inner=p.bar.Inner/r
