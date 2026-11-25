import q.a as m
from q.a import Money as Cash, Item, Base, deco
from q.b import Money, In, In2, Tag
from . import b as bmod


@deco
class Use(Base):
    a: Cash
    b: Money
    c: m.Item
    d: In
    e: bmod.In

    class In2: ...

    g: In2

    def f(self, x: Item, y: m.Money) -> In: ...
    def h(self, x: In2) -> None: ...


class Shadow:
    Item = int
    a: Item

    def f(self, x: Item) -> None: ...


class Late(m.Base):
    x: Base.In

    def g(self, y: "Money", z: list[Cash]) -> dict[str, bmod.Money]: ...


class Gen(bmod.Tag):
    def __init__(self, a: Money) -> None:
        self.a: Cash = Cash()
        self.b = a
