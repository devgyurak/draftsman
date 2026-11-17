from __future__ import annotations

import builtins
from typing import Optional

from .base import LanguageSpec

# every class of the builtins module (dict, LookupError, classmethod, ...) is in scope
# in every module without an import
_BUILTIN_CLASSES = {name for name, value in vars(builtins).items()
                    if isinstance(value, type) and not name.startswith("_")}

_BUILTINS = _BUILTIN_CLASSES | {
    "int", "float", "complex", "str", "bytes", "bytearray", "bool", "object", "None",
    "type", "slice", "range", "memoryview", "Exception", "BaseException", "ValueError",
    "TypeError", "KeyError", "RuntimeError", "NotImplementedError", "Any", "Self",
    "NoReturn", "Never", "Callable", "Hashable", "Sized", "Literal", "TypeVar", "Generic",
    "Protocol", "ABC", "Enum", "IntEnum", "StrEnum", "Flag", "IntFlag", "NamedTuple",
    "TypedDict", "datetime", "date", "time", "timedelta", "timezone", "Decimal", "Fraction",
    "UUID", "Path", "PurePath", "Pattern", "Match", "Logger", "Lock", "Event", "Thread",
}

# supertypes that only say what kind of type this is
_KIND_BASES = {
    "Protocol": "interface", "ABC": "abstract_class", "Enum": "enum", "IntEnum": "enum",
    "StrEnum": "enum", "Flag": "enum", "IntFlag": "enum", "NamedTuple": "record",
    "TypedDict": "record",
}
_MARKER_BASES = set(_KIND_BASES) | {"object", "Generic", "ABCMeta"}


def _last(name: str) -> str:
    return name.split("[", 1)[0].rsplit(".", 1)[-1]


def _strip_quotes(text: str) -> str:
    return text.replace('"', "").replace("'", "")


class PythonSpec(LanguageSpec):
    name = "python"
    grammar = "python"
    extensions = (".py", ".pyi")
    separator = "."
    opaque_nodes = frozenset({"function_definition", "lambda"})
    builtins = frozenset(_BUILTINS)
    import_suffix_match = True
    inherited_member_types = False

    def package_root(self, root):
        # the way Python names modules: a root inside packages (django/db/models with
        # __init__.py up to django/) is the module django.db.models, not ""
        parts = []
        d = root.resolve()
        while d != d.parent and ((d / "__init__.py").exists() or (d / "__init__.pyi").exists()):
            parts.append(d.name)
            d = d.parent
        return "/".join(reversed(parts))

    def file_namespace(self, rel):
        mod = rel.rsplit(".", 1)[0].replace("/", ".")
        return mod[: -len(".__init__")] if mod.endswith(".__init__") else mod

    def module_id(self, text, rel):
        if not text.startswith("."):
            return text
        dots = len(text) - len(text.lstrip("."))
        package = self.file_namespace(rel).split(".")
        if not rel.endswith("__init__.py") and not rel.endswith("__init__.pyi"):
            package = package[:-1]
        base = package[: len(package) - (dots - 1)] if dots > 1 else package
        rest = text[dots:]
        return ".".join([*base, rest] if rest else base)

    def normalize_type(self, text):
        return _strip_quotes(text) if text else text

    def ownership_start(self, caps, root):
        if "_self" not in caps:
            return root
        # self.x = ... counts only directly inside __init__ (not nested functions)
        cur = root.parent
        while cur is not None and cur.type != "function_definition":
            cur = cur.parent
        if cur is None:
            return None
        name = cur.child_by_field_name("name")
        if name is None or name.text != b"__init__":
            return None
        start = cur.parent
        return start.parent if start is not None and start.type == "decorated_definition" \
            else start

    def visibility(self, owner_kind, member_kind, modifiers, name, node):
        if name.startswith("__") and not name.endswith("__"):
            return "private"
        if name.startswith("_") and not name.startswith("__"):
            return "protected"
        return "public"

    def is_static(self, owner_kind, member_kind, modifiers):
        return False  # decided in finalize_type, once decorators are known

    def is_abstract(self, owner_kind, member_kind, modifiers, has_body, marker=None):
        return False

    def finalize_type(self, raw):
        kept = []
        for sup in raw.supers:
            base = _last(sup.text)
            if base in _KIND_BASES and raw.kind == "class":
                raw.kind = _KIND_BASES[base]
            if base not in _MARKER_BASES:
                kept.append(sup)
        raw.supers = kept

        init_params: dict[str, Optional[str]] = {}
        members = []
        for rm in raw.members:
            m = rm.member
            decos = {_last(a) for a in m.annotations}
            if m.kind == "method":
                if "staticmethod" in decos or "classmethod" in decos:
                    m.static = True
                if "abstractmethod" in decos:
                    m.abstract = True
                if m.params and m.params[0].name in ("self", "cls") and "staticmethod" not in decos:
                    m.params = m.params[1:]
                if m.name == "__init__":
                    m.kind = "constructor"
                    init_params = {p.name: p.type_ref for p in m.params}
                elif "property" in decos:
                    m.kind, m.params = "property", []
            elif m.kind == "field":
                if m.name.startswith("__") and m.name.endswith("__"):
                    continue  # __slots__, __all__, ...
                is_self = "_self" in rm.flags
                if raw.kind == "enum" and not is_self and not m.name.startswith("_"):
                    m.kind, m.type_ref, m.static = "enum_constant", None, True
                elif not is_self:
                    # class-level: unannotated or ClassVar[...] means a class variable
                    t = m.type_ref or ""
                    m.static = not t or _last(t) == "ClassVar"
            members.append(rm)
        raw.members = members

        # self.x = param  ->  x has the annotated type of that __init__ parameter
        for rm in raw.members:
            m = rm.member
            if m.kind == "field" and m.type_ref is None and "_self" in rm.flags \
                    and rm.value in init_params:
                m.type_ref = init_params[rm.value]

        if raw.kind == "class" and any(rm.member.abstract for rm in raw.members):
            raw.kind = "abstract_class"
        if raw.kind == "interface":
            for rm in raw.members:
                if rm.member.kind == "method":
                    rm.member.abstract = True
