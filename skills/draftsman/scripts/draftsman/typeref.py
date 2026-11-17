"""Language-neutral parser for type expressions as written in source.

Handles the shapes shared by the supported languages:

    Name, a.b.Name, ns::Name           named types
    Name<A, B>, list[A], Map~K, V~      generic arguments (<> or [])
    T[], T...                          arrays / varargs
    T?                                 nullable (Kotlin, C#)
    A | B | None                       unions (TypeScript, Python)
    T*, T&, T&&                        C++ pointers / references
    ? extends T, out T, const T        wildcards and qualifiers (dropped)

Anything else (function types, literal types, decltype...) yields ``None``;
callers treat that as "no structural information".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional, Union

TypeRef = Union["Named", "Array", "Nullable", "Pointer", "TypeUnion"]


@dataclass(frozen=True)
class Named:
    name: str
    args: tuple = field(default_factory=tuple)
    value: bool = False   # `typeof x`: names a value, which may or may not be a class


@dataclass(frozen=True)
class Array:
    elem: "TypeRef"


@dataclass(frozen=True)
class Nullable:
    inner: "TypeRef"


@dataclass(frozen=True)
class Pointer:
    inner: "TypeRef"
    sigil: str  # '*', '&', '&&'


@dataclass(frozen=True)
class TypeUnion:
    items: tuple


NULL_LIKE = frozenset({"None", "null", "undefined", "nullptr_t", "NoneType"})

# Words that qualify a type without changing which type it is.
_QUALIFIERS = frozenset({
    "const", "volatile", "struct", "class", "enum", "union", "typename", "final",
    "readonly", "in", "out", "ref", "mutable", "constexpr", "static", "inline",
    "extern", "unsafe", "scoped", "params", "keyof", "typeof", "unique", "infer",
})

_TOKEN = re.compile(
    r"""\s*(?:
        (?P<ident>[^\W\d][\w$]*)
      | (?P<num>\d+)
      | (?P<str>"[^"]*"|'[^']*')
      | (?P<punct>\.\.\.|::|&&|=>|->|[<>\[\](),?|*&@.:=])
    )""",
    re.VERBOSE,
)


class _ParseError(Exception):
    pass


def _tokenize(text: str) -> list[str]:
    tokens = []
    pos = 0
    text = text.strip()
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m or m.end() == pos:
            raise _ParseError(text[pos:])
        pos = m.end()
        if m.group("str") or m.group("num"):
            tokens.append("#lit")
        else:
            tokens.append(m.group("ident") or m.group("punct"))
    return tokens


class _Parser:
    def __init__(self, tokens: list[str]):
        self.toks = tokens
        self.i = 0

    def peek(self, k: int = 0) -> Optional[str]:
        j = self.i + k
        return self.toks[j] if j < len(self.toks) else None

    def take(self, expected: Optional[str] = None) -> str:
        tok = self.peek()
        if tok is None or (expected is not None and tok != expected):
            raise _ParseError(f"expected {expected!r}, got {tok!r}")
        self.i += 1
        return tok

    def parse(self) -> Optional[TypeRef]:
        ref = self.union()
        if self.peek() is not None:
            raise _ParseError(f"trailing {self.peek()!r}")
        return ref

    def union(self) -> Optional[TypeRef]:
        items = [self.postfix()]
        while self.peek() == "|":
            self.take()
            items.append(self.postfix())
        items = [x for x in items if x is not None]
        if not items:
            return None
        return items[0] if len(items) == 1 else TypeUnion(tuple(items))

    def postfix(self) -> Optional[TypeRef]:
        ref = self.primary()
        while True:
            tok = self.peek()
            if tok == "[" and self.peek(1) == "]":
                self.take(), self.take()
                ref = Array(ref) if ref is not None else None
            elif tok == "...":
                self.take()
                ref = Array(ref) if ref is not None else None
            elif tok == "?":
                self.take()
                ref = Nullable(ref) if ref is not None else None
            elif tok in ("*", "&", "&&"):
                self.take()
                ref = Pointer(ref, tok) if ref is not None else None
            elif tok in _QUALIFIERS:  # C++ east const: `Foo const*`
                self.take()
            elif tok == "@":  # Java type annotation on an array level: `String @Nullable []`
                self.take()
                self.qualified_name()
                if self.peek() == "(":
                    self.skip_balanced("(", ")")
            else:
                return ref

    def primary(self) -> Optional[TypeRef]:
        tok = self.peek()
        while tok == "@":  # annotations: @NonNull Foo
            self.take()
            self.qualified_name()
            if self.peek() == "(":
                self.skip_balanced("(", ")")
            tok = self.peek()
        value = False
        while tok in _QUALIFIERS:
            value = value or tok == "typeof"
            self.take()
            tok = self.peek()
        if tok == "(":
            self.take()
            inner = self.union()
            self.take(")")
            if self.peek() in ("->", "=>"):
                raise _ParseError("function type")
            return inner
        if tok == "?":  # Java wildcard
            self.take()
            if self.peek() in ("extends", "super"):
                kw = self.take()
                bound = self.union()
                return bound if kw == "extends" else None
            return None
        if tok == "*" and self.peek(1) in (">", ",", "]"):  # Kotlin star projection
            self.take()
            return None
        if tok == "#lit":
            self.take()
            return None
        if tok is None or not (tok == "::" or _is_ident(tok)):
            raise _ParseError(f"unexpected {tok!r}")
        name = self.qualified_name()
        # multi-word builtins: `unsigned long long`, `long double`
        while _is_ident(self.peek() or "") and self.peek() not in _QUALIFIERS:
            name += " " + self.take()
        args: tuple = ()
        if self.peek() == "<":
            args = self.arg_list(">")
        elif self.peek() == "[" and self.peek(1) != "]":
            args = self.arg_list("]")
        if self.peek() in (".", "::") and args:
            # Outer<T>.Inner -> treat as Inner nested in Outer
            sep = self.take()
            rest = self.qualified_name()
            name = name + sep + rest
            if self.peek() == "<":
                args = self.arg_list(">")
        return Named(name, args, value)

    def qualified_name(self) -> str:
        parts = []
        if self.peek() == "::":
            self.take()
        parts.append(self.take())
        if not _is_ident(parts[0]):
            raise _ParseError(f"bad name {parts[0]!r}")
        while self.peek() in (".", "::") and _is_ident(self.peek(1) or ""):
            sep = self.take()
            parts.append(sep)
            parts.append(self.take())
        return "".join(parts)

    def arg_list(self, close: str) -> tuple:
        self.take()  # opener
        args = []
        while self.peek() != close:
            if self.peek() is None:
                raise _ParseError("unterminated argument list")
            if self.peek() == "[" and close == "]":  # Callable[[A, B], R]
                self.skip_balanced("[", "]")
                args.append(None)
            else:
                args.append(self.union())
            if self.peek() == ",":
                self.take()
            elif self.peek() != close:
                raise _ParseError(f"expected ',' or {close!r}")
        self.take(close)
        return tuple(args)

    def skip_balanced(self, opener: str, close: str) -> None:
        depth = 0
        while True:
            tok = self.take()
            if tok == opener:
                depth += 1
            elif tok == close:
                depth -= 1
                if depth == 0:
                    return


def _is_ident(tok: str) -> bool:
    return bool(tok) and (tok[0].isalpha() or tok[0] in "_$")


def parse_type(text: Optional[str]) -> Optional[TypeRef]:
    """Parse a type expression; return ``None`` if it has no usable structure."""
    if not text:
        return None
    try:
        return _Parser(_tokenize(text)).parse()
    except _ParseError:
        return None


def value_names(ref: Optional[TypeRef]) -> set[str]:
    """Names written only as `typeof x` in ``ref``: values, unless they are classes."""
    values: set[str] = set()
    types: set[str] = set()

    def walk(r):
        if isinstance(r, Named):
            (values if r.value else types).add(r.name)
            for a in r.args:
                walk(a)
        elif isinstance(r, (Array, Nullable, Pointer)):
            walk(r.elem if isinstance(r, Array) else r.inner)
        elif isinstance(r, TypeUnion):
            for it in r.items:
                walk(it)

    walk(ref)
    return values - types


def named_refs(ref: Optional[TypeRef]) -> list[tuple[str, int]]:
    """(name, number of type arguments) of every named type in ``ref``."""
    out: list[tuple[str, int]] = []

    def walk(r):
        if isinstance(r, Named):
            if r.name not in NULL_LIKE:
                out.append((r.name, len(r.args)))
            for a in r.args:
                walk(a)
        elif isinstance(r, (Array, Nullable, Pointer)):
            walk(r.elem if isinstance(r, Array) else r.inner)
        elif isinstance(r, TypeUnion):
            for it in r.items:
                walk(it)

    walk(ref)
    return out


def all_names(ref: Optional[TypeRef]) -> list[str]:
    """Every named type mentioned anywhere in ``ref`` (outer types and arguments)."""
    out: list[str] = []

    def walk(r):
        if r is None:
            return
        if isinstance(r, Named):
            if r.name not in NULL_LIKE:
                out.append(r.name)
            for a in r.args:
                walk(a)
        elif isinstance(r, (Array, Nullable, Pointer)):
            walk(r.elem if isinstance(r, Array) else r.inner)
        elif isinstance(r, TypeUnion):
            for it in r.items:
                walk(it)

    walk(ref)
    return out
