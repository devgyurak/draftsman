import functools

import q.a as m
from q.a import BaseManager, Field, Other, QuerySet, Resp, make, registry


@Field.register
class Lookup: ...


@m.Field.register
class Lookup2: ...


@registry.bound
class Lookup3: ...


@functools.lru_cache(maxsize=None)
class Cached: ...


class Manager(BaseManager.from_queryset(QuerySet)): ...


class Manager2(m.BaseManager.from_queryset(m.QuerySet, name="Other")): ...


class Made(make(Other, key=Field.name)): ...


class Plain(make("Field", 1)): ...


class Methods:
    @Field.register
    def m(self): ...

    @property
    def p(self) -> Other: ...

    @p.setter
    def p(self, v: Other) -> None: ...


class Sub(Resp):
    @Resp.content.setter
    def content(self, v): ...
