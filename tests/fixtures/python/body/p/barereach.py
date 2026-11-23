import p.bare.near
from p import bare, pk


class BareReach:
    def through_the_import(self):
        return p.bare.near.Near()           #> Near=p.bare.near.Near/r

    def through_a_name(self):
        return bare.near.Near()             #> Near=disputed/r

    def through_the_package(self):
        return pk.near.Near()               #> Near=p.pk.near.Near/r
