import os
import sys

from p.foo import Foo

if sys.platform == "win32":
    class Windows:
        pass

if os.name == "nt":
    class Nt:
        pass


class Platform:
    def guarded(self):
        if sys.platform == "win32":
            return Foo()                    #> Foo=p.foo.Foo/r
        return Foo()                        #> Foo=p.foo.Foo/r

    def declared(self):
        return Windows, Nt                  #> Windows=disputed/r Nt=p.platform.Nt/r
