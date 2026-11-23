from collections import namedtuple
from typing import NamedTuple


class Pt(NamedTuple):
    x: int


class Records:
    def annotated(self):
        p: Pt = Pt(1)                       #> Pt=p.records.Pt/r Pt=p.records.Pt/r
        return p

    def local(self):
        Raw = namedtuple("Raw", ["a"])
        return Raw(1)                       #> Raw=var/r

    def commented(self):
        x = []  # type: list[Pt]            #> Pt=-
        return x
