import bar
import p.sub.deep
from p import sub
from p.compat import Shim, Twin
from p.listing import *


class Reach:
    def rebound(self):
        return Shim(), Twin()               #> Shim=disputed/r Twin=disputed/r

    def submodule(self):
        return sub.deep.Deep()              #> Deep=p.sub.deep.Deep/r

    def imported(self):
        return p.sub.deep.Deep()            #> Deep=p.sub.deep.Deep/r

    def package(self):
        return sub.Deep()                   #> Deep=p.sub.deep.Deep/r

    def listed(self):
        return Extra(), Shown()             #> Extra=disputed/r Shown=disputed/r

    def external(self):
        # an outside module named like the project's p.bar: no marker, nothing is drawn
        return bar.Bar()
