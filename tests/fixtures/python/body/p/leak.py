import p.foo
from p.gui import Button as Knob


def helper():
    from p.gui import Button, TimeoutError
    from p.bar import Bar
    return Button, TimeoutError, Bar


class Leak:
    def caught(self):
        try:
            pass
        except TimeoutError:                #> TimeoutError=builtins.TimeoutError/r
            pass

    def unbound(self):
        return Button()                     #> Button=error/r

    def first(self):
        from p import bar
        return bar.Bar()                    #> Bar=p.bar.Bar/r

    def second(self):
        return bar.Bar()                    # bar is unbound

    def imports(self):
        import p.bar
        return p.bar.Bar()                  #> Bar=p.bar.Bar/r

    def submodule(self):
        return p.bar.Bar()                  #> Bar=disputed/r

    def kept(self):
        return p.foo.Foo(), Knob()          #> Foo=p.foo.Foo/r Knob=p.gui.Button/r


class Declared(Bar):                        #> Declared=- Bar=-
    pass
