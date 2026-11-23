import p.foo
from p.far.deep import Far
from p.sub import deep


class FromReach:
    def through_a_name(self):
        return p.far.deep.Far()             # mypy binds no p.far: no name in the key

    def name(self):
        return Far()                        #> Far=p.far.deep.Far/r

    def through_a_module(self):
        return p.sub.deep.Deep()            #> Deep=disputed/r

    def module(self):
        return deep.Deep()                  #> Deep=p.sub.deep.Deep/r
