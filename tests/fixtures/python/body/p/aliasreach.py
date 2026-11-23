import p.bare
import p.bare.near as n


class AliasReach:
    def through_the_alias(self):
        return n.Near()                     #> Near=p.bare.near.Near/r

    def through_the_package(self):
        return p.bare.near.Near()           #> Near=disputed/r
