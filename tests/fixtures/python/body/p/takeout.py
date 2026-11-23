from p import outlast
from p.outclass import Button as Classed
from p.outfirst import Button as First
from p.outlast import Button as Last
from p.outmod import Button as Moduled
from p.outother import Button as Kept
from p.outstar import Button as Starred
from p.outtry import Button as Tried


class TakeOut:
    def named(self):
        return Last(), First(), Tried()     #> Last=disputed/r First=disputed/r Tried=disputed/r

    def through_the_module(self):
        return outlast.Button()             #> Button=disputed/r

    def other_bindings(self):
        return Moduled(), Classed(), Starred()  #> Moduled=disputed/r Classed=disputed/r Starred=disputed/r

    def another_name(self):
        return Kept()                       #> Kept=p.gui.Button/r
