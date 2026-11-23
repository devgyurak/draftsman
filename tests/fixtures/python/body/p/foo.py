class Foo:
    class Inner:
        pass

    @classmethod
    def create(cls) -> "Foo":
        return cls()


class FooError(Exception):
    pass


class _Hidden:
    pass
