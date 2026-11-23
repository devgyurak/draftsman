from p.foo import Foo


class Holder:
    class Twin:
        pass

    class Twin:  # noqa: F811
        pass

    if Foo:                                 #> Foo=-
        class Cond:
            pass
    else:
        class Cond:
            pass

    class Kept:
        pass


class UseHolder:
    def conditional(self):
        return Holder.Cond()                #> Holder=p.twice.Holder/r Cond=disputed/r

    def repeated(self):
        return Holder.Twin()                #> Holder=p.twice.Holder/r Twin=p.twice.Holder.Twin/r

    def once(self):
        return Holder.Kept()                #> Holder=p.twice.Holder/r Kept=p.twice.Holder.Kept/r
