class Field:
    name = "x"

    @classmethod
    def register(cls, f): return f

    def bound(self, f): return f


class Other: ...
class QuerySet: ...


class BaseManager:
    @classmethod
    def from_queryset(cls, qs, name=None): return cls


class Resp:
    @property
    def content(self): return 1


def make(*a, **k): return object
registry = Field()
