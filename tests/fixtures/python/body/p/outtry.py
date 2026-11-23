from p.gui import Button  # noqa: F401

try:
    from tkinter import Button  # noqa: F401,F811
except ImportError:
    pass
