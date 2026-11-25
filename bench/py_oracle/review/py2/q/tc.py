from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from q.a import Item


class U:
    def f(self, x: Item) -> Item: ...
