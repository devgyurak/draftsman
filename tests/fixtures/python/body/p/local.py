from p.foo import Foo


class Local:
    def after(self):
        from p.bar import Inner
        return Inner()                      #> Inner=p.bar.Inner/r

    def aliased(self):
        from p.bar import Bar as Foo
        return Foo()                        #> Foo=p.bar.Bar/r

    def before(self):
        x = Foo()                           #> Foo=disputed/r
        from p.bar import Bar as Foo
        return x, Foo()                     #> Foo=p.bar.Bar/r

    def nested(self):
        def inner():
            from p.bar import Bar as Foo
            return Foo()                    #> Foo=p.bar.Bar/r
        return inner, Foo()                 #> Foo=p.foo.Foo/r

    def closure(self):
        from p.bar import Bar as Foo

        def inner():
            return Foo()                    #> Foo=p.bar.Bar/r
        return inner

    def twice(self, flag):
        if flag:
            from p.bar import Bar as Foo
        else:
            from p.foo import Foo
        return Foo()                        #> Foo=disputed/r

    def assigned(self):
        try:
            from p.bar import Bar as Foo
        except ImportError:
            Foo = None
        return Foo                          #> Foo=disputed/r

    def module(self):
        import p.bar
        return p.bar.Bar()                  #> Bar=p.bar.Bar/r
