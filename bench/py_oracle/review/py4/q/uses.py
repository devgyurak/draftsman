import functools

from q.fields import BaseManager, Field, Item, QuerySet, Response, make_base


# #33: a class's attribute as a decorator is the class's
@Field.register
class Lookup: ...


@Field.register(name="Item")
class Named: ...


# #34: a base made by a call names the classes in it; a keyword's name, a string and a
# function name no class
class Manager(BaseManager.from_queryset(QuerySet, Item=1)): ...


class Made(make_base(QuerySet, "Item", kind=None)): ...


class Sub(Response):
    # a property of the class (`content`), beside a module class `content`
    @property
    def content(self):
        return 2

    @content.setter
    def content(self, v): ...

    @functools.lru_cache
    def cached(self) -> int:
        return 1
