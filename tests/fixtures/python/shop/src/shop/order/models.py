from __future__ import annotations

import enum
from dataclasses import dataclass, field

from shop.common.base import BaseEntity
from shop.promo import *


class Status(enum.Enum):
    NEW = 1
    PAID = 2
    SHIPPED = 3


@dataclass
class Product:
    sku: str
    price: float


@dataclass(frozen=True)
class OrderLine:
    product: Product
    quantity: int = 1


class Customer(BaseEntity):
    class Address:
        def __init__(self, street: str) -> None:
            self.street = street

    def __init__(self, name: str, address: Customer.Address | None = None) -> None:
        super().__init__()
        self.name = name
        self.orders: list[Order] = []
        self.address = address
        self.listener: Customer.Listener | None = None   # BaseEntity.Listener, inherited

    def is_new(self) -> bool:
        return self._id is None


class Order(BaseEntity):
    EMPTY: Order | None = None
    __slots__ = ()

    def __init__(self, customer: Customer, coupon: "Coupon | None" = None) -> None:
        super().__init__()
        self.customer = customer
        self.__lines: list[OrderLine] = []
        self.status = Status.NEW
        self.coupon = coupon

        def helper(x: OrderLine) -> None:
            self.hidden = x

    def is_new(self) -> bool:
        return self.status is Status.NEW

    def add_line(self, line: OrderLine) -> None:
        self.__lines.append(line)
        self.last_added = line

    class Audit(BaseEntity.Listener):
        def changed(self, entity: BaseEntity) -> None:
            pass
