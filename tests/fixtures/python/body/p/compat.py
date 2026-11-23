import os

try:
    from p.bar import Bar as Shim
except ImportError:
    class Shim:
        pass

if os.environ.get("TWIN"):
    class Twin:
        pass
else:
    class Twin:
        pass
