class Field:
    @classmethod
    def register(cls, f=None, **kw):
        return f if f is not None else (lambda g: g)


class QuerySet: ...


class Item: ...


class content: ...


class BaseManager:
    @classmethod
    def from_queryset(cls, qs, **kw):
        return type("M", (cls,), {})


def make_base(*args, **kw):
    return object


class Response:
    @property
    def content(self):
        return 1

    @content.setter
    def content(self, v): ...
