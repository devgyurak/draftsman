from q.a import Item, Money


class Shadow2:
    # #50: a class body's binding of a name also used in annotations below it
    Item = int
    a: Item
    b: Money

    def f(self, x: Item, y: Money) -> None: ...


class Plain:
    a: Item

    def f(self, x: Item) -> None: ...
