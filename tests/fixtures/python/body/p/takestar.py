from p.one import *  # noqa: F403


class TakeStar:
    def m(self):
        return Both(), OnlyA()              #> Both=disputed/r OnlyA=p.one.a.OnlyA/r
