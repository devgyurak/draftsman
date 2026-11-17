"""Language-neutral parser for type expressions as written in source.

Handles the shapes shared by the supported languages:

    Name, a.b.Name, ns::Name           named types
    Name<A, B>, list[A], Map~K, V~      generic arguments (<> or [])
    T[], T...                          arrays / varargs
    T?                                 nullable (Kotlin, C#)
    A | B | None                       unions (TypeScript, Python)
    T*, T&, T&&                        C++ pointers / references
    ? extends T, out T, const T        wildcards and qualifiers (dropped)
    (A, B) -> C, R.(A) -> C            function types (Kotlin; `suspend` dropped,
    context(A) () -> C                 context parameters kept as types)
    (a: A) => B                        function types (TypeScript)
    Callable[[A], B], R(A)             Python callables, C++ std::function<R(A)>
    [A, B], (A a, B b), tuple[A, B]    tuples (TS, C#, Python, std::tuple / std::pair)

Anything else (literal types, decltype...) yields ``None``; callers treat that as "no
structural information".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Optional, Union

TypeRef = Union["Named", "Array", "Nullable", "Pointer", "TypeUnion", "FunctionType", "TypeTuple"]


@dataclass(frozen=True)
class Named:
    name: str
    args: tuple = field(default_factory=tuple)
    value: bool = False   # `typeof x`: names a value, which may or may not be a class
    subscript: bool = field(default=False, compare=False)   # arguments in `[...]` (Python)


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


@dataclass(frozen=True)
class FunctionType:
    params: tuple                       # parameter types (unknown ones dropped)
    result: Optional["TypeRef"] = None
    receiver: Optional["TypeRef"] = None  # Kotlin `R.(A) -> C`
    context: tuple = ()                   # Kotlin context parameters: `context(A, B) () -> C`


@dataclass(frozen=True)
class TypeTuple:
    """One value of each item: `[A, B]`, `(A a, B b)`, `tuple[A, B]`."""
    items: tuple


# generic names that are tuples when given two or more element types (unless the project
# defines a class of that name: see special_form)
_TUPLES = frozenset({"tuple", "Tuple", "typing.Tuple", "std::tuple", "std::pair", "ValueTuple",
                     "System.Tuple", "System.ValueTuple"})
# words that combine into one C/C++ builtin type: `unsigned long long`, `long double`
_MULTIWORD = frozenset({"unsigned", "signed", "long", "short", "int", "char", "double", "float"})
# C++ operators that make a value of a type (`std::array<char, sizeof(P)>`): no type
# reference, as a number argument is none
_VALUE_OPERATORS = frozenset({"sizeof", "alignof", "__alignof__", "offsetof", "noexcept"})


@dataclass(frozen=True)
class _ParamList:
    """`[A, B]` inside `Callable[[A, B], R]`."""
    items: tuple


NULL_LIKE = frozenset({"None", "null", "undefined", "nullptr_t", "NoneType"})

# Words that qualify a type without changing which type it is.
_QUALIFIERS = frozenset({
    "const", "volatile", "struct", "class", "enum", "union", "typename", "final",
    "readonly", "in", "out", "ref", "mutable", "constexpr", "static", "inline",
    "extern", "unsafe", "scoped", "params", "keyof", "typeof", "unique", "infer",
    "suspend",
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
        if tok == "context" and self.peek(1) == "(":   # Kotlin context(A, B) () -> C
            self.take()
            context, _ = self.param_list()
            inner = self.primary()
            if not isinstance(inner, FunctionType):
                raise _ParseError("context without a function type")
            return FunctionType(inner.params, inner.result, inner.receiver,
                                context + inner.context)
        if tok == "(":
            params, plain = self.param_list()
            if self.peek() in ("->", "=>"):   # (A, b: B) -> C, (a: A) => B
                self.take()
                return FunctionType(params, self.union())
            if plain and len(params) == 1:   # a parenthesised type: (A | B)[]
                return params[0]
            if len(params) >= 2:   # C# tuple: (Person a, Point b)
                return TypeTuple(params)
            raise _ParseError("parameter list without an arrow")
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
        if tok == "[":   # TypeScript tuple: [A, B], [a: A, b?: B]
            items, _ = self.param_list("[", "]")
            return TypeTuple(items)
        if tok is None or not (tok == "::" or _is_ident(tok)):
            raise _ParseError(f"unexpected {tok!r}")
        name = self.qualified_name()
        if name in _VALUE_OPERATORS and self.peek() == "(":
            depth = 0
            while True:
                tok = self.take()
                depth += (tok == "(") - (tok == ")")
                if depth == 0:
                    return None
        if name.startswith("global::"):   # C# global::Acme.Core.Point
            name = name[len("global::"):]
        # multi-word builtins: `unsigned long long`, `long double`
        while name.rsplit(" ", 1)[-1] in _MULTIWORD and (self.peek() or "") in _MULTIWORD:
            name += " " + self.take()
        args: tuple = ()
        subscript = False   # Python `X[...]`, where Literal and Annotated mean something
        if self.peek() == "<":
            args = self.arg_list(">")
        elif self.peek() == "[" and self.peek(1) != "]":
            args = self.arg_list("]")
            subscript = True
        if self.peek() == "." and self.peek(1) == "(":   # Kotlin R.(A) -> C
            self.take()
            params, _ = self.param_list()
            self.take("->")
            return FunctionType(params, self.union(), Named(name, args, value))
        if self.peek() == "(":   # C++ std::function<R(A)>
            params, _ = self.param_list()
            return FunctionType(params, Named(name, args, value))
        if name.rsplit(".", 1)[-1] == "Callable" and len(args) == 2 \
                and (isinstance(args[0], _ParamList) or args[0] is None):   # Python
            params = args[0].items if isinstance(args[0], _ParamList) else ()
            return FunctionType(params, args[1])
        if self.peek() in (".", "::") and args:
            # Outer<T>.Inner -> treat as Inner nested in Outer
            sep = self.take()
            rest = self.qualified_name()
            name = name + sep + rest
            if self.peek() == "<":
                args = self.arg_list(">")
        return Named(name, args, value, subscript)

    def param_list(self, opener: str = "(", close: str = ")") -> tuple[tuple, bool]:
        """`(A, b: B, ...rest: C[])` -> (types, whether it was a plain `(Type)`)."""
        self.take(opener)
        params: list = []
        plain = True
        while self.peek() != close:
            if self.peek() is None:
                raise _ParseError("unterminated parameter list")
            if self.peek() == "...":       # TS rest parameter
                self.take()
                plain = False
            if _is_ident(self.peek() or "") and (
                    self.peek(1) == ":" or (self.peek(1) == "?" and self.peek(2) == ":")):
                self.take()                # a parameter name: `b: B`, `b?: B`
                if self.peek() == "?":
                    self.take()
                self.take(":")
                plain = False
            ref = self.union()
            if ref is not None:
                params.append(ref)
            if _is_ident(self.peek() or "") and self.peek(1) in (",", close):
                self.take()                # C# tuple element name: (Person a, ...)
                plain = False
            if self.peek() == ",":
                self.take()
                plain = False
            elif self.peek() != close:
                raise _ParseError(f"expected ',' or {close!r}")
        self.take(close)
        return tuple(params), plain and len(params) == 1

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
                items = self.arg_list("]")
                args.append(_ParamList(tuple(i for i in items if i is not None)))
            elif self.peek() == "..." and close == "]":  # Callable[..., R]
                self.take()
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


_ANNOTATED = re.compile(r"\b(?:[A-Za-z_]\w*\.)*Annotated\s*\[(?!\s*\])")   # not Annotated[]


def _strip_annotated(text: str) -> str:
    """`Annotated[Item, Field(gt=0, json_schema_extra={...})]` -> `Annotated[Item]`. The
    metadata is any Python expression, so it is cut out as text before tokenizing."""
    pos = 0
    while (m := _ANNOTATED.search(text, pos)) is not None:
        depth, quote, comma, i = 0, None, None, m.end()
        while i < len(text):
            c = text[i]
            if quote:
                quote = None if c == quote else quote
            elif c in "\"'":
                quote = c
            elif c in "([{":
                depth += 1
            elif c in ")]}":
                if depth == 0:
                    break
                depth -= 1
            elif c == "," and depth == 0 and comma is None:
                comma = i
            i += 1
        else:
            return text   # unbalanced: leave it to the parser
        if comma is not None:
            text = text[:comma] + text[i:]
        pos = m.end()
    return text


def special_form(ref: Named) -> Optional[str]:
    """What a name with a meaning of its own stands for, when no project class of that name
    is meant (the caller checks): "values" for Python `Literal["a"]`, "tuple" for
    `tuple[A, B]`, `Tuple<A, B>`, `std::pair<A, B>`. (`Annotated[X]` is a wrapper in
    config/wrappers.yaml once _strip_annotated has cut its metadata.)"""
    if ref.subscript and ref.name.rsplit(".", 1)[-1] == "Literal":
        return "values"
    if ref.name in _TUPLES and len(ref.args) >= 2 and None not in ref.args:   # not tuple[A, ...]
        return "tuple"
    return None


def parse_type(text: Optional[str]) -> Optional[TypeRef]:
    """Parse a type expression; return ``None`` if it has no usable structure."""
    if not text:
        return None
    if "Annotated" in text:
        text = _strip_annotated(text)
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
        elif isinstance(r, (TypeUnion, TypeTuple)):
            for it in r.items:
                walk(it)
        elif isinstance(r, FunctionType):
            for it in (*r.context, r.receiver, *r.params, r.result):
                walk(it)

    walk(ref)
    return values - types


def named_refs(ref: Optional[TypeRef],
               is_project: Optional[Callable[[str], bool]] = None) -> list[tuple[str, int]]:
    """(name, number of type arguments) of every named type in ``ref``. With ``is_project``,
    the arguments of a `Literal[...]` that is no project class are values and skipped
    (`Literal["Item"]`, whose quotes Python's normalize_type has already removed)."""
    out: list[tuple[str, int]] = []

    def walk(r):
        if isinstance(r, Named):
            if r.name not in NULL_LIKE:
                out.append((r.name, len(r.args)))
            if is_project is not None and special_form(r) == "values" and not is_project(r.name):
                return
            for a in r.args:
                walk(a)
        elif isinstance(r, (Array, Nullable, Pointer)):
            walk(r.elem if isinstance(r, Array) else r.inner)
        elif isinstance(r, (TypeUnion, TypeTuple)):
            for it in r.items:
                walk(it)
        elif isinstance(r, FunctionType):
            for it in (*r.context, r.receiver, *r.params, r.result):
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
        elif isinstance(r, (TypeUnion, TypeTuple)):
            for it in r.items:
                walk(it)
        elif isinstance(r, FunctionType):
            for it in (*r.context, r.receiver, *r.params, r.result):
                walk(it)

    walk(ref)
    return out


def function_types(ref: Optional[TypeRef]) -> list[FunctionType]:
    """Every function type in ``ref``, also inside containers (`Map<K, (A) -> B>`)."""
    out: list[FunctionType] = []

    def walk(r):
        if isinstance(r, FunctionType):
            out.append(r)
        elif isinstance(r, Named):
            for a in r.args:
                walk(a)
        elif isinstance(r, (Array, Nullable, Pointer)):
            walk(r.elem if isinstance(r, Array) else r.inner)
        elif isinstance(r, (TypeUnion, TypeTuple)):
            for it in r.items:
                walk(it)

    walk(ref)
    return out
