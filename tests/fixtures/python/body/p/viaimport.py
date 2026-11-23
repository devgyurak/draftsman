from p import outside, relay, relay2
from p.outside import Label


class ViaImport:
    def named(self):
        return Label()                      #> Label=disputed/r

    def module(self):
        return outside.Button()             #> Button=disputed/r

    def relayed(self):
        return relay.Button()               #> Button=disputed/r

    def relayed_by_star(self):
        return relay2.Button()              #> Button=disputed/r


class ViaName:
    def m(self):
        from p.relay2 import Button
        return Button()                     #> Button=disputed/r
