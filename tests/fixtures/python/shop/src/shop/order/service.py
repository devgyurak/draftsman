from __future__ import annotations

import typing as t
from typing import TypeVar

from shop.pay import gateway as gw
from shop.pay import PaymentGateway   # re-exported by `from .gateway import *`
from sqlalchemy.orm import Session

from . import models
from .models import Customer, Order

T = TypeVar("T", bound=Order)


class OrderRepository(t.Protocol):
    def find_by_customer(self, customer: Customer) -> list[Order]: ...


class OrderService:
    instance: t.ClassVar[OrderService | None] = None

    def __init__(self, repository: OrderRepository, gateway: PaymentGateway, session: Session):
        self._repository = repository
        self._gateway = gateway
        self._session = session

    def place(self, customer: Customer, lines: list[models.OrderLine]) -> Order:
        return Order(customer)

    async def pay(self, order: Order) -> gw.Receipt:
        return await self._gateway.charge(order)

    def reload(self, order: T) -> T:
        return order

    @staticmethod
    def create() -> OrderService:
        raise NotImplementedError
