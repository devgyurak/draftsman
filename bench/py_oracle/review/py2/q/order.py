from q.a import Other, Item, Money, deco


class Late:
    @Other
    def m(self): ...

    Other = print


class Meth:
    def Other(f): return f

    @Other
    def m(self): ...


@Other
class OnClass:
    Other = print


class Dotted:
    Item = deco

    @Item
    def m(self): ...

    @deco
    def n(self, x: Money) -> Money: ...


class AnnOnly:
    Item: Item
    Money: "Money"

    def f(self, x: Item) -> None: ...


class AnnValue:
    Item: Item = Item()
