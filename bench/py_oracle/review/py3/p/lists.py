from typing import Dict, Generic, List, TypeVar

import b.models
from a.models import Item, Node

T = TypeVar("T")


class NodeList(List[Node]): ...


class Gen(Generic[T]): ...


class Nested(Dict[str, List[Item]]): ...


class UsesB(List[b.models.Node]): ...


class Base(Generic[T]): ...


class Sub(Base[Item]): ...


class SubSelf(Base["SubSelf"]): ...


type Vector = list[Item]


class Holder:
    items: Vector
