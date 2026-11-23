class Label:
    pass


from tkinter import *  # noqa: E402


class Button:
    pass


class Outside:
    def after(self):
        return Button()                     #> Button=disputed/r

    def before(self):
        return Label()                      #> Label=disputed/r
