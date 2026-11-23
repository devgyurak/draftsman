from p.foo import *
from p.limited import *


class Starred:
    def listed(self):
        return Shown()                      #> Shown=p.limited.Shown/r

    def unlisted(self):
        return Unlisted()                   #> Unlisted=error/r

    def private(self):
        return _Hidden()                    #> _Hidden=error/r

    def public(self):
        return FooError()                   #> FooError=p.foo.FooError/r
