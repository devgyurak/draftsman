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
    # a qualifier's type arguments where the name has its own (`A` of `Outer<A>.Inner<B>`;
    # `Outer<A>.Inner` keeps A in `args`)
    outer_args: tuple = field(default=(), compare=False)


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


@dataclass(frozen=True)
class TypeIntersection(TypeUnion):
    """TypeScript's `A & B`: its items are read as a union's are (each one a type the
    value is)."""


@dataclass(frozen=True)
class TypeMention(FunctionType):
    """TypeScript types a type names without being one of them (`params`): an object type
    literal's members (`{ item: Logger }`), an indexed access (`Foo['bar']`), a
    conditional type, a type predicate (`x is Logger`), a mapped type. Read as a function
    type's are: a dependency on each, never an association."""


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
                if self.peek() == "(" and ref is not None:   # `std::function<Session*(A)>`
                    params, _ = self.param_list()
                    return FunctionType(params, ref)
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
        if tok == "?":  # Java wildcard: `? extends T` and `? super T` both name T
            self.take()
            if self.peek() in ("extends", "super"):
                self.take()
                return self.union()
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
        if self.peek() == "(" and (owner := self._abstract_pointer()) is not None:
            # C++ `R (*)(A)`, `R (C::*)(A)`
            params, _ = self.param_list()
            if owner:
                params = (Named(owner),) + params
            return Pointer(FunctionType(params, Named(name, args, value)), "*")
        if self.peek() == "(":   # C++ std::function<R(A)>
            params, _ = self.param_list()
            return FunctionType(params, Named(name, args, value))
        if name.rsplit(".", 1)[-1] == "Callable" and len(args) == 2 \
                and (isinstance(args[0], _ParamList) or args[0] is None):   # Python
            params = args[0].items if isinstance(args[0], _ParamList) else ()
            return FunctionType(params, args[1])
        outer: tuple = ()
        if self.peek() in (".", "::") and args:
            # Outer<T>.Inner -> treat as Inner nested in Outer
            sep = self.take()
            rest = self.qualified_name()
            name = name + sep + rest
            if self.peek() == "<":
                outer, args = args, self.arg_list(">")
        return Named(name, args, value, subscript, outer)

    def _abstract_pointer(self) -> Optional[str]:
        """`(*)` or `(C::*)` at hand (a C++ pointer to a function or a member function, its
        name left out), taken: "" or the member pointer's class (C, which the function type
        names as its first parameter); None where it is not."""
        j = self.i + 1
        while j + 1 < len(self.toks) and _is_ident(self.toks[j]) and self.toks[j + 1] == "::":
            j += 2
        if j + 1 < len(self.toks) and self.toks[j] == "*" and self.toks[j + 1] == ")":
            owner = "".join(self.toks[self.i + 1:j])[:-2]
            self.i = j + 2
            return owner
        return None

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
        while self.peek() in (".", "::") and (_is_ident(self.peek(1) or "")
                                              or self.peek() == "." and self.peek(1) == "@"):
            sep = self.take()
            while self.peek() == "@":   # Java `Connection.@Nullable Response`
                self.take()
                self.qualified_name()
                if self.peek() == "(":
                    self.skip_balanced("(", ")")
            parts.append(sep)
            parts.append(self.take())
            if not _is_ident(parts[-1]):
                raise _ParseError(f"bad name {parts[-1]!r}")
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


def parse_type(text: Optional[str], dialect: Optional[str] = None) -> Optional[TypeRef]:
    """Parse a type expression; return ``None`` if it has no usable structure.
    ``dialect`` "typescript" reads TypeScript's whole type syntax (_TsParser), which no
    other language's text is read with (LanguageSpec.type_dialect)."""
    if not text:
        return None
    if dialect == "typescript":
        try:
            tokens, breaks = _ts_tokenize(text)
            return _TsParser(tokens, breaks).parse()
        except (_ParseError, RecursionError):
            return None
    if "Annotated" in text:
        text = _strip_annotated(text)
    try:
        return _Parser(_tokenize(text)).parse()
    except _ParseError:
        return None


# ------------------------------------------------------------------ TypeScript

_TS_TOKEN = re.compile(
    r"""(?P<ident>(?:[^\W\d]|\$)[\w$]*)
      | (?P<num>\d[\w.]*)
      | (?P<str>"(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*')
      | (?P<punct>\.\.\.|=>|\+\?|-\?|[<>\[\](){},;?|&*.:=+\-!@`])
    """,
    re.VERBOSE,
)
_TS_TEMPLATE = "#tpl"   # a template literal type: `#tpl` `(` type `,` type `)`


def _ts_tokenize(text: str) -> tuple[list[str], list[bool]]:
    """TypeScript type tokens, and for each whether a line break stands before it (an
    indexed access `A[K]` has none: on a new line `[K]: V` is an index signature). A
    template literal type gives `#tpl ( T1 , T2 )` of the types in its `${...}`."""
    tokens: list[str] = []
    breaks: list[bool] = []
    pos, n, brk = 0, len(text), False
    # the `}` that closes a template's `${`: the template goes on after it
    holes: list[int] = []
    depth = 0

    def template(pos: int) -> int:
        """Scan template text from ``pos`` (after a backtick or a hole's `}`) to the next
        `${` or the closing backtick."""
        nonlocal depth
        i = pos
        while i < n:
            c = text[i]
            if c == "\\":
                i += 2
                continue
            if c == "`":
                tokens.append(")")
                breaks.append(False)
                return i + 1
            if c == "$" and i + 1 < n and text[i + 1] == "{":
                if tokens[-1] != "(":
                    tokens.append(",")
                    breaks.append(False)
                holes.append(depth)
                return i + 2
            i += 1
        raise _ParseError("unterminated template")

    while pos < n:
        c = text[pos]
        if c in " \t\r\n":
            brk = brk or c == "\n"
            pos += 1
            continue
        if text.startswith("//", pos):
            end = text.find("\n", pos)
            pos = n if end < 0 else end
            continue
        if text.startswith("/*", pos):
            end = text.find("*/", pos + 2)
            if end < 0:
                raise _ParseError("unterminated comment")
            brk = brk or "\n" in text[pos:end]
            pos = end + 2
            continue
        if c == "`":
            tokens += [_TS_TEMPLATE, "("]
            breaks += [brk, False]
            brk = False
            pos = template(pos + 1)
            continue
        if c == "}" and holes and holes[-1] == depth:
            holes.pop()
            pos = template(pos + 1)
            continue
        m = _TS_TOKEN.match(text, pos)
        if not m:
            raise _ParseError(text[pos:])
        pos = m.end()
        if m.group("str") or m.group("num"):
            tok = "#lit"
        else:
            tok = m.group("ident") or m.group("punct")
            depth += (tok == "{") - (tok == "}")
        tokens.append(tok)
        breaks.append(brk)
        brk = False
    return tokens, breaks


def _ts_items(*refs) -> tuple:
    return tuple(r for r in refs if r is not None)


def _mention(*refs) -> Optional[TypeRef]:
    items = _ts_items(*refs)
    return TypeMention(items) if items else None


class _TsParser(_Parser):
    """TypeScript's type syntax (parse_type's dialect "typescript"). What the type is made
    of is kept as the other languages' shapes: a union's and an intersection's items
    (TypeUnion, TypeIntersection), arrays and tuples, function types, generic names. The
    types a type only names (an object type literal's members, an indexed access, a
    conditional type, a mapped type, a type predicate) are a TypeMention. What is no name
    of a type gives nothing: a literal, a property's or a parameter's name, a tuple's
    label, a type parameter declared in the text (`<T>() => T`, `infer U`, a mapped
    type's key), `this`, the key of an indexed access written as a literal."""

    def __init__(self, tokens: list[str], breaks: list[bool]):
        super().__init__(tokens)
        self.breaks = breaks
        self.bound: list[set[str]] = []   # type parameters the text declares, innermost last
        self.infer: Optional[set[str]] = None   # `infer U` names of a conditional's extends

    def broken(self) -> bool:
        """Whether a line break stands before the next token."""
        return self.i < len(self.breaks) and self.breaks[self.i]

    def is_bound(self, name: str) -> bool:
        return any(name in b for b in self.bound)

    def parse(self) -> Optional[TypeRef]:
        ref = self.type()
        if self.peek() is not None:
            raise _ParseError(f"trailing {self.peek()!r}")
        return ref

    # a type: a predicate, a function or constructor type, a conditional type
    def type(self) -> Optional[TypeRef]:
        tok = self.peek()
        if tok == "asserts" and (_is_ident(self.peek(1) or "")) and self.peek(1) != "is":
            self.take()
            self.take()
            if self.peek() == "is":
                self.take()
                return _mention(self.type())
            return None
        if _is_ident(tok or "") and self.peek(1) == "is":   # `x is Logger`, `this is Foo`
            self.take()
            self.take()
            return _mention(self.type())
        if tok == "abstract" and self.peek(1) == "new":
            self.take()
            tok = "new"
        if tok == "new" and self.peek(1) in ("(", "<"):   # a constructor type
            self.take()
            return self.function_type()
        if tok == "<" or tok == "(" and self.arrow_ahead():
            return self.function_type()
        checked = self.union()
        if self.peek() != "extends":
            return checked
        self.take()   # `C extends E ? T : F`
        was, self.infer = self.infer, set()
        try:
            extends = self.union()
            inferred = self.infer
        finally:
            self.infer = was
        self.take("?")
        self.bound.append(inferred)
        try:
            yes = self.type()
        finally:
            self.bound.pop()
        self.take(":")
        no = self.type()
        return _mention(checked, extends, yes, no)

    def arrow_ahead(self) -> bool:
        """Whether the `(` at hand opens a function type's parameters (a `=>` follows its
        closing parenthesis)."""
        depth, j = 0, self.i
        while j < len(self.toks):
            t = self.toks[j]
            if t in ("(", "[", "{"):
                depth += 1
            elif t in (")", "]", "}"):
                depth -= 1
                if depth == 0:
                    return j + 1 < len(self.toks) and self.toks[j + 1] == "=>"
            j += 1
        return False

    def function_type(self) -> FunctionType:
        """`<T>(a: A, b?: B) => R`, the parameters' names left out."""
        bound, named = self.type_params() if self.peek() == "<" else (set(), [])
        self.bound.append(bound)
        try:
            params = self.params()
            self.take("=>")
            return FunctionType(params + tuple(named), self.type())
        finally:
            self.bound.pop()

    def type_params(self) -> tuple[set[str], list]:
        """`<T extends A = B, U>`: the names (bound from here on), and the types the
        constraints and defaults name."""
        self.take("<")
        names: set[str] = set()
        named: list = []
        self.bound.append(names)   # (the earlier ones are names in the later ones)
        try:
            while self.peek() != ">":
                if self.peek() in ("const", "in", "out") and _is_ident(self.peek(1) or ""):
                    self.take()
                name = self.take()
                if not _is_ident(name):
                    raise _ParseError(f"bad type parameter {name!r}")
                names.add(name)
                if self.peek() == "extends":
                    self.take()
                    named += _ts_items(self.type())
                if self.peek() == "=":
                    self.take()
                    named += _ts_items(self.type())
                if self.peek() == ",":
                    self.take()
                elif self.peek() != ">":
                    raise _ParseError("expected ',' or '>'")
        finally:
            self.bound.pop()
        self.take(">")
        return names, named

    def params(self) -> tuple:
        """`(a: A, b?: B, ...c: C[], { d }: D, this: E)`: the parameters' types."""
        self.take("(")
        out: list = []
        while self.peek() != ")":
            while self.peek() in ("public", "private", "protected", "readonly") \
                    and self.peek(1) not in (":", "?", ",", ")"):
                self.take()
            if self.peek() == "...":
                self.take()
            if self.peek() in ("{", "["):   # a destructured parameter
                self.skip_balanced(self.peek(), "}" if self.peek() == "{" else "]")
            else:
                name = self.take()
                if not _is_ident(name):
                    raise _ParseError(f"bad parameter {name!r}")
            if self.peek() == "?":
                self.take()
            if self.peek() == ":":
                self.take()
                ref = self.type()
                if ref is not None:
                    out.append(ref)
            if self.peek() == ",":
                self.take()
            elif self.peek() != ")":
                raise _ParseError("expected ',' or ')'")
        self.take(")")
        return tuple(out)

    def union(self) -> Optional[TypeRef]:
        if self.peek() == "|":   # prettier's multi-line `| A | B`
            self.take()
        items = [self.intersection()]
        while self.peek() == "|":
            self.take()
            items.append(self.intersection())
        items = [x for x in items if x is not None]
        if not items:
            return None
        return items[0] if len(items) == 1 else TypeUnion(tuple(items))

    def intersection(self) -> Optional[TypeRef]:
        if self.peek() == "&":
            self.take()
        items = [self.operator()]
        while self.peek() == "&":
            self.take()
            items.append(self.operator())
        items = [x for x in items if x is not None]
        if not items:
            return None
        return items[0] if len(items) == 1 else TypeIntersection(tuple(items))

    def operator(self) -> Optional[TypeRef]:
        tok = self.peek()
        if tok == "infer" and _is_ident(self.peek(1) or ""):
            self.take()
            name = self.take()
            if self.infer is not None:
                self.infer.add(name)
            if self.peek() == "extends" and self.infer is not None:
                # `infer U extends C ? ...`: a constraint only where a `?` does not follow
                self.take()
                return _mention(self.operator())
            return None
        if tok in ("keyof", "readonly", "unique"):   # (as the other languages: dropped)
            self.take()
            return self.operator()
        if tok == "typeof":
            self.take()
            if self.peek() == "import":
                return self.primary_ts()
            name = self.qualified_name()
            args = self.arg_list(">") if self.peek() == "<" and not self.broken() else ()
            return self.postfix_ts(Named(name, args, True))
        if tok in ("+", "-") and self.peek(1) == "#lit":   # `-1`
            self.take()
        return self.postfix_ts(self.primary_ts())

    def postfix_ts(self, ref: Optional[TypeRef]) -> Optional[TypeRef]:
        while self.peek() == "[" and not self.broken():
            self.take()
            if self.peek() == "]":
                self.take()
                ref = Array(ref) if ref is not None else None
                continue
            key = self.type()   # `Foo['bar']`, `T[number]`, `Foo[K]`
            self.take("]")
            ref = _mention(ref, key)
        return ref

    def primary_ts(self) -> Optional[TypeRef]:
        tok = self.peek()
        if tok is None:
            raise _ParseError("type expected")
        if tok == "(" and self.arrow_ahead():
            return self.function_type()
        if tok == "(":
            self.take()
            ref = self.type()
            self.take(")")
            return ref
        if tok == "{":
            return self.object_type()
        if tok == "[":
            return self.tuple_type()
        if tok == "#lit":
            self.take()
            return None
        if tok == _TS_TEMPLATE:
            self.take()
            self.take("(")
            items = []
            while self.peek() != ")":
                items.append(self.type())
                if self.peek() == ",":
                    self.take()
            self.take(")")
            return _mention(*items)
        if tok == "this":
            self.take()
            return None
        if tok == "import" and self.peek(1) == "(":   # `import('x')` (a module's type)
            self.take()
            self.skip_balanced("(", ")")
            if self.peek() == ".":
                self.take()
                self.qualified_name()
            if self.peek() == "<":
                self.arg_list(">")
            return None
        if not _is_ident(tok):
            raise _ParseError(f"unexpected {tok!r}")
        name = self.qualified_name()
        args: tuple = ()
        if self.peek() == "<" and not self.broken():
            args = self.arg_list(">")
        if "." not in name and self.is_bound(name):
            return None
        return Named(name, args)

    def arg_list(self, close: str) -> tuple:
        self.take("<")
        args = []
        while self.peek() != ">":
            args.append(self.type())
            if self.peek() == ",":
                self.take()
            elif self.peek() != ">":
                raise _ParseError("expected ',' or '>'")
        self.take(">")
        return tuple(args)

    def tuple_type(self) -> TypeTuple:
        """`[A, B?, ...C[]]`, `[a: A, b?: B, ...rest: C[]]`."""
        self.take("[")
        items: list = []
        while self.peek() != "]":
            if self.peek() == "...":
                self.take()
            if _is_ident(self.peek() or "") and (
                    self.peek(1) == ":" or self.peek(1) == "?" and self.peek(2) == ":"):
                self.take()   # a label
                if self.peek() == "?":
                    self.take()
                self.take(":")
            ref = self.type()
            if self.peek() == "?":
                self.take()
            if ref is not None:
                items.append(ref)
            if self.peek() == ",":
                self.take()
            elif self.peek() != "]":
                raise _ParseError("expected ',' or ']'")
        self.take("]")
        return TypeTuple(tuple(items))

    def object_type(self) -> Optional[TypeRef]:
        """An object type literal or a mapped type: the types of its members."""
        self.take("{")
        items: list = []
        while self.peek() != "}":
            if self.peek() is None:
                raise _ParseError("unterminated object type")
            if self.peek() in (";", ","):
                self.take()
                continue
            items += self.object_member()
        self.take("}")
        return _mention(*items)

    def object_member(self) -> list:
        while True:   # `readonly`, `-readonly`, `get`, unless it is the member's name
            tok = self.peek()
            if tok in ("+", "-") and self.peek(1) == "readonly" or tok in (
                    "readonly", "get", "set") and self.peek(1) not in (
                    ":", "?", "(", ";", ",", "}", "<", None):
                self.take()
                continue
            break
        if tok == "[":
            # a mapped type's `[K in T as N]`, an index signature's `[key: K]`, or a
            # computed property name `[Symbol.iterator]`
            if _is_ident(self.peek(1) or "") and self.peek(2) == "in":
                self.take()
                key = self.take()
                self.take("in")
                self.bound.append({key})
                try:
                    over = self.type()
                    named = None
                    if self.peek() == "as":
                        self.take()
                        named = self.type()
                    self.take("]")
                    if self.peek() in ("?", "+?", "-?"):
                        self.take()
                    value = None
                    if self.peek() == ":":
                        self.take()
                        value = self.type()
                    return list(_ts_items(over, named, value))
                finally:
                    self.bound.pop()
            if _is_ident(self.peek(1) or "") and self.peek(2) == ":":
                self.take()
                self.take()
                self.take(":")
                index = self.type()
                self.take("]")
                self.take(":")
                return list(_ts_items(index, self.type()))
            self.skip_balanced("[", "]")
        elif tok == "new" and self.peek(1) in ("(", "<"):   # a construct signature
            self.take()
        elif tok in ("(", "<"):   # a call signature
            pass
        elif tok == "#lit" or _is_ident(tok or ""):
            self.take()   # the member's name
        else:
            raise _ParseError(f"unexpected {tok!r} in an object type")
        if self.peek() == "?":
            self.take()
        if self.peek() in ("(", "<"):   # a method: `m<T>(a: A): R`
            bound, out = self.type_params() if self.peek() == "<" else (set(), [])
            self.bound.append(bound)
            try:
                out += self.params()
                if self.peek() == ":":
                    self.take()
                    out += _ts_items(self.type())
                return out
            finally:
                self.bound.pop()
        if self.peek() == ":":
            self.take()
            return list(_ts_items(self.type()))
        return []


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
