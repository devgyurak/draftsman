from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import TYPE_CHECKING

from stripe import *

if TYPE_CHECKING:
    from shop.order import Order  # re-exported by shop/order/__init__.py


@dataclass
class Receipt:
    id: str
    amount: Receipt.Money

    @dataclass
    class Money:
        cents: int
        currency: str


class PaymentGateway(abc.ABC):
    @abc.abstractmethod
    async def charge(self, order: Order) -> Receipt: ...

    def supports_refund(self) -> bool:
        return False


class StripeGateway(PaymentGateway):
    def __init__(self, client: StripeClient) -> None:
        self._client = client
        self._fee: Receipt.Money | None = None

    async def charge(self, order: Order) -> Receipt:
        return Receipt("x", Receipt.Money(0, "usd"))
