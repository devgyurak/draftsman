class Other: ...


class A:
    # #6: the class body's binding is the decorator, not the module's class
    Other = print

    @Other
    def m(self): ...


class B:
    # no binding in the class body: the module's class
    @Other
    def m(self): ...
