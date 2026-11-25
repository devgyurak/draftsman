import sys

try:
    from q.a import Foo
except ImportError:
    Foo = None

if sys.version_info >= (3, 9):
    from q.a import Money
else:
    from q.b import Money

from q.a import Item
from q.a import Item


class T(Foo):
    x: Money
    y: Item

    def f(self, a: Foo) -> None: ...
