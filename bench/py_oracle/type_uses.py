"""The names mypy resolves inside bodies, one JSON object per line: the first of the three
checkers the extractor's Python body relations are compared with (bench/py_oracle/oracle.py,
records as bench/answer_key.py describes them). It runs in an environment of its own
with mypy and nothing else (oracle.py starts it), never in the plugin's.

    python type_uses.py OUT.jsonl SOURCES-FILE PYTHON

SOURCES-FILE lists the source files, one per line as `PATH<TAB>MODULE<TAB>REL`: the file,
the module name the extractor gives it, and its path below the extraction root. Only
they are recorded, and only their classes are the project's. PYTHON is the interpreter
whose site-packages hold the repository's dependencies. mypy runs from the current
directory, which must be where the top package sits. Records:

  {"use": ...}        a name in a body: a class (kind "type"), a class declared in a
                      function ("local"), a module ("module"), a type variable ("tparam"),
                      or, when it starts upper-case or with `_`, anything else ("var") or
                      nothing ("error"). "mypy" says what mypy bound it to (its node type
                      and full name), "annotation" whether it is written in an annotation
  {"declared": ...}   a class the extractor sees as a type: one not inside a function, by
                      its id (module + the classes around it + name)
  {"mypy_error": ...} an error mypy reports, with its code; a name it could not bind is
                      "error" where it stands

A body is a method's body (a function defined in the class, also under an `if` there)
and the value of an assignment directly in a class body, with everything inside them
(functions, lambdas, classes). Decorators, parameters and return types of the method
itself are not read. Of a dotted name (`mod.Foo.Inner()`) each part that is a class is
recorded, "maximal" when no class part follows; modules are passed through. A name in a
binding (`Foo = ...`, `Foo += 1`, `for Foo in`, `except E as Foo`) is no use. Every position is
"receiver": a variable of the name hides a class in an annotation as anywhere else.
Names in string annotations and type comments are not recorded. Lines are 1-based,
columns 0-based in UTF-16 code units.

The names of a class's declarations are recorded too, with "pos" "declared" (issue #7):
its bases, its decorators and its methods', its annotated assignments directly in the
class body (`x: Foo = ...`) and an `__init__`'s annotated `self.x: Foo = ...`, and its
methods' parameter and return annotations; with "role" ("super", "annotation", "field",
"signature") and "in_args" (inside a subscript: `Foo` of `Base[Foo]`, `list[Foo]`). A
class's keywords (`metaclass=`) are not recorded: the extractor draws nothing from them.

mypy binds names in the bodies of functions without annotations too: semantic analysis
runs on every body, and --check-untyped-defs only adds type checking (its answers are the
same with it). Its columns are not UTF-16 ones on a line with other than ASCII before
the name (Source.char reads them back).
"""

from __future__ import annotations

import json
import re
import sys

from mypy import build
from mypy.modulefinder import BuildSource
from mypy.nodes import (
    AssertTypeExpr, AssignmentExpr, AssignmentStmt, Block, CallExpr, CastExpr, ClassDef,
    Decorator, DictionaryComprehension, ForStmt, FuncDef, GeneratorExpr, IfStmt, ListExpr,
    MemberExpr, MypyFile, NameExpr, OperatorAssignmentStmt, OverloadedFuncDef, StarExpr,
    TryStmt, TupleExpr, TypeAliasStmt, TypeApplication, TypeInfo, TypeVarExpr, WhileStmt,
    WithStmt,
)
from mypy.options import Options
from mypy.patterns import AsPattern, MappingPattern, StarredPattern
from mypy.traverser import TraverserVisitor
from mypy.types import (
    AnyType, CallableType, Instance, TypeAliasType, TypeVarType, UnboundType, UnionType,
)
from mypy.typetraverser import TypeTraverserVisitor

out_path, sources_file, python = sys.argv[1:4]
files = [line.split("\t") for line in open(sources_file).read().splitlines() if line]
modules = {mod: (path, rel) for path, mod, rel in files}

options = Options()
options.preserve_asts = True
options.incremental = False
options.cache_dir = "/dev/null"
options.python_executable = python
options.follow_imports = "silent"
options.ignore_missing_imports = True
options.show_error_codes = True
result = build.build([BuildSource(path, mod) for path, mod, _ in files], options)

out = []
emit = lambda rec: out.append(json.dumps(rec))   # noqa: E731
for msg in result.errors:
    m = re.match(r"(.+?):(\d+): error: (.*?)(?:  \[([\w-]+)\])?$", msg)
    if m:
        rel = next((r for p, _, r in files if p == m.group(1)), m.group(1))
        emit({"mypy_error": m.group(3), "code": m.group(4), "file": rel, "line": int(m.group(2))})

_WORD = re.compile(r"[A-Za-z_]\w*")
_DOTTED = re.compile(r"[A-Za-z_]\w*(?:\s*\.\s*[A-Za-z_]\w*)*")


class Source:
    """A file's lines, and the way from mypy's columns to UTF-16 ones."""

    def __init__(self, path: str):
        self.lines = open(path, encoding="utf-8").read().split("\n")

    def char(self, line: int, col: int, name: str, end: bool = False):
        """The character index of ``name`` that mypy places at ``col`` (its start, or its
        end when ``end``), or None. mypy's column is 2 * characters - UTF-8 bytes on a line
        with other than ASCII before it, the character index on any other; on such a line
        its start columns are sometimes one more than that (after two characters outside
        the BMP, `"😀😀", Foo()`), its end columns never are."""
        text = self.lines[line - 1] if 0 < line <= len(self.lines) else ""
        if text.isascii():
            c = col - len(name) if end else col
            return c if text[c:c + len(name)] == name else None
        nbytes = 0
        for c in range(len(text) + 1):
            if 2 * c - nbytes == col:
                start = c - len(name) if end else c
                if start >= 0 and text[start:start + len(name)] == name:
                    return start
            if c < len(text):
                nbytes += len(text[c].encode())
        return None

    def type_comment(self, f: FuncDef) -> bool:
        """Whether a function's types are written in a `# type:` comment."""
        return any("# type:" in self.lines[i - 1]
                   for i in range(f.line, max(f.line, f.body.line) + 1) if i <= len(self.lines))

    def utf16(self, line: int, c: int) -> int:
        return len(self.lines[line - 1][:c].encode("utf-16-le")) // 2

    def at(self, line: int, c: int) -> str:
        return self.lines[line - 1][c:c + 1] if 0 < line <= len(self.lines) else ""


def walk_classes(stmts, prefix: str, mod: str, src: Source, rel: str) -> None:
    """Every class not inside a function, with the bodies of its members."""
    for s in stmts:
        if isinstance(s, ClassDef):
            cid = f"{prefix}.{s.name}"
            emit({"declared": cid, "file": rel})
            regions(s, cid, src, rel)
            declaration_names(s, cid, src, rel)
            walk_classes(s.defs.body, cid, mod, src, rel)
        elif isinstance(s, (IfStmt, TryStmt, WithStmt, ForStmt, WhileStmt)):
            for b in blocks(s):
                walk_classes(b.body, prefix, mod, src, rel)


def blocks(s) -> list[Block]:
    if isinstance(s, IfStmt):
        return [*s.body, *([s.else_body] if s.else_body else [])]
    if isinstance(s, TryStmt):
        return [s.body, *s.handlers, *(b for b in (s.else_body, s.finally_body) if b)]
    if isinstance(s, (WithStmt, ForStmt, WhileStmt)):
        return [s.body, *([s.else_body] if getattr(s, "else_body", None) else [])]
    return []


def functions(stmts):
    """The functions defined in a class body, also under an `if` or a `try` there."""
    for s in stmts:
        if isinstance(s, FuncDef):
            yield s
        elif isinstance(s, Decorator):
            yield s.func
        elif isinstance(s, OverloadedFuncDef):
            for item in s.items:
                yield item.func if isinstance(item, Decorator) else item
            if s.impl is not None:
                yield s.impl.func if isinstance(s.impl, Decorator) else s.impl
        elif isinstance(s, (IfStmt, TryStmt, WithStmt, ForStmt, WhileStmt)):
            for b in blocks(s):
                yield from functions(b.body)


def regions(cdef: ClassDef, cid: str, src: Source, rel: str) -> None:
    seen: set[int] = set()
    for f in functions(cdef.defs.body):
        if id(f) not in seen:   # an overload's implementation is one of its items too
            seen.add(id(f))
            f.body.accept(Uses(cid, src, rel))
    for s in cdef.defs.body:
        if isinstance(s, AssignmentStmt) and len(s.lvalues) == 1 \
                and isinstance(s.lvalues[0], NameExpr):
            s.rvalue.accept(Uses(cid, src, rel))


def declaration_names(cdef: ClassDef, cid: str, src: Source, rel: str) -> None:
    """The names of a class's declarations (module docstring)."""
    def names(role: str) -> "Declared":
        d = Declared(cid, src, rel, role)
        d.info = cdef.info
        return d
    for e in (*cdef.base_type_exprs, *cdef.removed_base_type_exprs):
        e.accept(names("super"))
    for d in cdef.decorators:
        d.accept(names("annotation"))
    for s in cdef.defs.body:
        if isinstance(s, AssignmentStmt) and s.new_syntax and s.type is not None \
                and len(s.lvalues) == 1 and isinstance(s.lvalues[0], NameExpr):
            names("field").types(s.type, s.unanalyzed_type)
    seen: set[int] = set()
    for d, f in methods(cdef.defs.body):
        if d is not None:
            for dec in d.decorators:
                dec.accept(names("annotation"))
        if id(f) in seen:
            continue
        seen.add(id(f))
        if f.unanalyzed_type is not None and f.type is not None and not src.type_comment(f):
            names("signature").types(f.type, f.unanalyzed_type)
        if f.name == "__init__":
            for a in self_annotations(f.body.body):
                names("field").types(a.type, a.unanalyzed_type)


def methods(stmts):
    """(the Decorator node or None, the function) of each function `functions` yields."""
    for s in stmts:
        if isinstance(s, FuncDef):
            yield None, s
        elif isinstance(s, Decorator):
            yield s, s.func
        elif isinstance(s, OverloadedFuncDef):
            for item in [*s.items, *([s.impl] if s.impl is not None else [])]:
                yield (item, item.func) if isinstance(item, Decorator) else (None, item)
        elif isinstance(s, (IfStmt, TryStmt, WithStmt, ForStmt, WhileStmt)):
            for b in blocks(s):
                yield from methods(b.body)


def self_annotations(stmts):
    """`self.x: Foo = ...` in a method's statements, also in its blocks."""
    for s in stmts:
        if isinstance(s, AssignmentStmt) and s.new_syntax and s.type is not None \
                and len(s.lvalues) == 1 and isinstance(s.lvalues[0], MemberExpr) \
                and isinstance(s.lvalues[0].expr, NameExpr) and s.lvalues[0].expr.name == "self":
            yield s
        elif isinstance(s, (IfStmt, TryStmt, WithStmt, ForStmt, WhileStmt)):
            for b in blocks(s):
                yield from self_annotations(b.body)


def answer(node, name: str):
    """(kind, target, project) for what mypy bound a name to."""
    if isinstance(node, TypeInfo):
        fullname = node.fullname
        if "@" in fullname:   # a class declared in a function: `m.Local@12`
            return ("local" if class_statement(node) else "var"), None, False
        project = node.module_name in modules
        if project and fullname not in declared_all:
            return "var", None, False   # `Point = NamedTuple(...)`: no class statement
        return "type", fullname, project
    if isinstance(node, MypyFile):
        return "module", node.fullname, node.fullname in modules
    if isinstance(node, TypeVarExpr):
        return "tparam", None, False
    if node is None:
        return "error", None, False
    return "var", None, False


def class_statement(info: TypeInfo) -> bool:
    """Whether a class mypy made is written as a class statement, not as a call
    (`RawURL = namedtuple(...)` in a function)."""
    path = modules.get(info.module_name, (None,))[0]
    if path is None:
        return True
    lines = sources_text.setdefault(path, open(path, encoding="utf-8").read().split("\n"))
    line = lines[info.defn.line - 1] if 0 < info.defn.line <= len(lines) else ""
    return re.search(rf"\bclass\s+{re.escape(info.name)}\b", line) is not None


sources_text: dict[str, list[str]] = {}


def described(node) -> str:
    if node is None:
        return "-"
    full = getattr(node, "fullname", "") or ""
    return f"{type(node).__name__} {full}".strip()


class Uses(TraverserVisitor):
    """Records the names written in one body."""

    def __init__(self, cid: str, src: Source, rel: str):
        super().__init__()
        self.cid, self.src, self.rel = cid, src, rel
        self.unreachable = 0   # how many blocks semantic analysis skipped are around

    def record(self, name, line, c, kind, target, project, maximal, node, annotation=False):
        emit({"use": name, "file": self.rel, "line": line, "col": self.src.utf16(line, c),
              "pos": "receiver", "kind": kind, "target": target, "project": project,
              "maximal": maximal, "from": self.cid, "mypy": described(node),
              "annotation": annotation, "unreachable": self.unreachable > 0})

    def visit_block(self, b: Block) -> None:
        # a block semantic analysis skipped (`if TYPE_CHECKING:`'s else, `if PY2:`): mypy
        # binds no name in it and says so (oracle.py: where it abstains)
        self.unreachable += b.is_unreachable
        super().visit_block(b)
        self.unreachable -= b.is_unreachable

    # ------------------------------------------------------------- values

    def chain(self, e):
        """[(name, line, char, node)] of a dotted name `a.B.C`, head first, or None."""
        parts = []
        while isinstance(e, MemberExpr):
            if e.end_line is None or e.end_column is None:
                return None
            c = self.src.char(e.end_line, e.end_column, e.name, end=True)
            if c is None:
                return None
            parts.append((e.name, e.end_line, c, e.node if e.fullname else None))
            e = e.expr
        if not isinstance(e, NameExpr):
            return None
        # by its end, when the span is the name's (mypy gives a name of the length of a
        # whole `from m import Foo` in a function)
        c = self.src.char(e.end_line, e.end_column, e.name, end=True) \
            if e.end_line == e.line and e.end_column is not None \
            and e.end_column - e.column in (len(e.name), len(e.name) - 1) else None
        if c is None:
            c = self.src.char(e.line, e.column, e.name)
        if c is None:
            return None
        parts.append((e.name, e.line, c, e.node))
        return parts[::-1]

    def values(self, parts) -> None:
        got = []
        for name, line, c, node in parts:
            kind, target, project = answer(node, name)
            got.append((kind, target, project))
            if kind not in ("type", "module"):
                break
        for i, (kind, target, project) in enumerate(got):
            name, line, c, node = parts[i]
            if kind == "module":
                continue
            if kind != "type" and (i > 0 or name[:1].islower()):
                continue
            maximal = not (i + 1 < len(got) and got[i + 1][0] == "type")
            self.record(name, line, c, kind, target, project, maximal, node)

    def visit_member_expr(self, e: MemberExpr) -> None:
        parts = self.chain(e)
        if parts is None:
            super().visit_member_expr(e)
        else:
            self.values(parts)

    def visit_name_expr(self, e: NameExpr) -> None:
        if e.name in ("None", "True", "False", "__debug__"):
            return   # keywords, no names
        parts = self.chain(e)
        if parts is not None:
            self.values(parts)

    # ------------------------------------------------------------- bindings

    def targets(self, e) -> None:
        """A binding's target: its names are no uses, what it reads from is (`a.b = `)."""
        if isinstance(e, (TupleExpr, ListExpr)):
            for item in e.items:
                self.targets(item)
        elif isinstance(e, StarExpr):
            self.targets(e.expr)
        elif not isinstance(e, NameExpr):
            e.accept(self)

    def visit_assignment_stmt(self, s: AssignmentStmt) -> None:
        for lv in s.lvalues:
            self.targets(lv)
        s.rvalue.accept(self)
        if s.new_syntax and s.type is not None:   # `x: Foo = ...`, not `# type: Foo`
            self.types(s.type)

    def visit_operator_assignment_stmt(self, s: OperatorAssignmentStmt) -> None:
        self.targets(s.lvalue)
        s.rvalue.accept(self)

    def visit_for_stmt(self, s: ForStmt) -> None:
        self.targets(s.index)
        s.expr.accept(self)
        s.body.accept(self)
        if s.else_body:
            s.else_body.accept(self)

    def visit_with_stmt(self, s: WithStmt) -> None:
        for e, t in zip(s.expr, s.target):
            e.accept(self)
            if t is not None:
                self.targets(t)
        s.body.accept(self)

    def visit_try_stmt(self, s: TryStmt) -> None:
        s.body.accept(self)
        for t, h in zip(s.types, s.handlers):
            if t is not None:
                t.accept(self)
            h.accept(self)
        for b in (s.else_body, s.finally_body):
            if b:
                b.accept(self)

    def visit_assignment_expr(self, e: AssignmentExpr) -> None:
        e.value.accept(self)

    def comprehension(self, e) -> None:
        for index, seq, conds in zip(e.indices, e.sequences, e.condlists):
            seq.accept(self)
            self.targets(index)
            for c in conds:
                c.accept(self)

    def visit_generator_expr(self, e: GeneratorExpr) -> None:
        self.comprehension(e)
        e.left_expr.accept(self)

    def visit_dictionary_comprehension(self, e: DictionaryComprehension) -> None:
        self.comprehension(e)
        e.key.accept(self)
        e.value.accept(self)

    def visit_as_pattern(self, p: AsPattern) -> None:
        if p.pattern is not None:   # `case Foo() as f`, `case Bound`: the name is a binding
            p.pattern.accept(self)

    def visit_starred_pattern(self, p: StarredPattern) -> None:
        pass

    def visit_mapping_pattern(self, p: MappingPattern) -> None:
        for key in p.keys:   # not the binding of `case {**rest}`
            key.accept(self)
        for value in p.values:
            value.accept(self)

    def visit_func_def(self, f: FuncDef) -> None:
        # a function in the body: its defaults, annotations and body; not its name
        for arg in f.arguments:
            if arg.initializer is not None:
                arg.initializer.accept(self)
        if f.unanalyzed_type is not None and f.type is not None and not self.src.type_comment(f):
            self.types(f.type)
        f.body.accept(self)

    def visit_type_application(self, e: TypeApplication) -> None:
        pass   # `Foo[int]`: its name is the index expression's, visited already

    def visit_type_alias_stmt(self, s: TypeAliasStmt) -> None:
        s.value.expr().accept(self)   # `type Pair[T] = ...`: not its name, a binding

    def visit_decorator(self, d: Decorator) -> None:
        for dec in d.decorators:
            dec.accept(self)
        d.func.accept(self)

    def visit_class_def(self, c: ClassDef) -> None:
        # a class in the body: its bases, keywords, decorators and everything in it
        for e in (*c.base_type_exprs, *c.removed_base_type_exprs, *c.decorators,
                  *c.keywords.values()):
            e.accept(self)
        c.defs.accept(self)

    # ------------------------------------------------------------- types

    def visit_call_expr(self, e: CallExpr) -> None:
        # `cast(Foo, x)`: its arguments are left unbound, the type is in the analyzed form
        if isinstance(e.analyzed, (CastExpr, AssertTypeExpr)):
            e.analyzed.accept(self)
        else:
            super().visit_call_expr(e)

    def visit_cast_expr(self, e: CastExpr) -> None:
        e.expr.accept(self)
        self.types(e.type)

    def visit_assert_type_expr(self, e: AssertTypeExpr) -> None:
        e.expr.accept(self)
        self.types(e.type)

    def types(self, t) -> None:
        t.accept(TypeNames(self))


class TypeNames(TypeTraverserVisitor):
    """The classes an analyzed annotation names, at the places they are written."""

    def __init__(self, uses: Uses):
        super().__init__()
        self.uses = uses

    def name(self, t, kind, target, project, node) -> None:
        src, line = self.uses.src, t.line
        if line is None or line < 1 or t.column is None or t.column < 0:
            return
        c = None
        text = src.lines[line - 1] if line <= len(src.lines) else ""
        # mypy's column for the type as written: find the dotted name it starts
        for m in _DOTTED.finditer(text):
            last = m.group(0).rsplit(".", 1)[-1].strip()
            if src.char(line, t.column, m.group(0).split(".")[0].strip()) == m.start() or (
                    t.end_line == line and t.end_column is not None
                    and src.char(line, t.end_column, last, end=True) == m.end() - len(last)):
                c = m
                break
        if c is None or src.at(line, c.start()) in "\"'":
            return   # a string annotation
        parts = [(p.group(0), c.start() + p.start()) for p in _WORD.finditer(c.group(0))]
        written, col = parts[-1]
        # the parts before it, from its full name: classes (`Foo` of `Foo.Inner`) or modules
        for i, (part, pc) in enumerate(parts[:-1]):
            prefix = ".".join(target.split(".")[:-(len(parts) - 1 - i)]) if target else None
            outer = lookup_class(prefix) if prefix else None
            if outer is not None:
                k, tg, pr = answer(outer, part)
                self.uses.record(part, line, pc, k, tg, pr, False, outer, annotation=True)
        self.uses.record(written, line, col, kind, target, project, True, node,
                         annotation=True)

    def visit_instance(self, t: Instance) -> None:
        kind, target, project = answer(t.type, t.type.name)
        self.name(t, kind, target, project, t.type)
        super().visit_instance(t)

    def visit_type_alias_type(self, t: TypeAliasType) -> None:
        # a NamedTuple or TypedDict class is named through an alias mypy makes of it
        info = lookup_class(t.alias.fullname) if t.alias.fullname in declared_all else None
        if info is not None:
            kind, target, project = answer(info, info.name)
            self.name(t, kind, target, project, info)
        else:
            self.name(t, "var", None, False, t.alias)
        super().visit_type_alias_type(t)

    def visit_type_var(self, t: TypeVarType) -> None:
        self.name(t, "tparam", None, False, None)

    def visit_any(self, t: AnyType) -> None:
        pass


class Declared(Uses):
    """Records the names of one declaration of a class, "pos" "declared"."""

    def __init__(self, cid: str, src: Source, rel: str, role: str):
        super().__init__(cid, src, rel)
        self.role, self.args = role, 0
        self.recorded: set[tuple[int, int]] = set()   # (line, character) recorded
        self.info = None   # the class's TypeInfo

    def record(self, name, line, c, kind, target, project, maximal, node, annotation=False):
        self.recorded.add((line, c))
        emit({"use": name, "file": self.rel, "line": line, "col": self.src.utf16(line, c),
              "pos": "declared", "kind": kind, "target": target, "project": project,
              "maximal": maximal, "from": self.cid, "mypy": described(node),
              "annotation": annotation, "unreachable": self.unreachable > 0,
              "role": self.role, "in_args": self.args > 0})

    def visit_index_expr(self, e) -> None:   # `Base[Foo]`
        e.base.accept(self)
        self.args += 1
        e.index.accept(self)
        self.args -= 1

    def types(self, t, written=None) -> None:
        t.accept(DeclaredTypeNames(self))
        if written is not None:
            self.unrecorded(written, t)

    def unrecorded(self, u, t) -> None:
        """A name of the annotation as written (``u``) that the analyzed type ``t`` gave no
        place to: an alias mypy expanded (`Item = int` in the class body, then `a: Item`).
        Its answer is what the analyzed type is there."""
        if isinstance(u, CallableType) and isinstance(t, CallableType):
            for ua, ta in zip(u.arg_types, t.arg_types):
                self.unrecorded(ua, ta)
            self.unrecorded(u.ret_type, t.ret_type)
            return
        if isinstance(u, UnionType) and isinstance(t, UnionType) and len(u.items) == len(t.items):
            for ua, ta in zip(u.items, t.items):
                self.unrecorded(ua, ta)
            return
        if not isinstance(u, UnboundType) or u.line is None or u.line < 1 or u.column is None:
            return
        text = self.src.lines[u.line - 1] if u.line <= len(self.src.lines) else ""
        m = _DOTTED.match(text, u.column) if u.column >= 0 else None
        if m is not None and m.start() == u.column and text[u.column:u.column + 1] not in "\"'":
            last = m.group(0).rsplit(".", 1)[-1].strip()
            c = m.end() - len(last)
            if (u.line, c) not in self.recorded and last == u.name.rsplit(".", 1)[-1]:
                if isinstance(t, Instance):
                    kind, target, project = answer(t.type, last)
                    self.record(last, u.line, c, kind, target, project, True, t.type, True)
                elif isinstance(t, TypeVarType):
                    self.record(last, u.line, c, "tparam", None, False, True, None, True)
                elif isinstance(t, UnboundType) and "." not in u.name and self.info is not None:
                    # mypy left it unanalyzed (`Item = int` in the class body is no alias
                    # to it): what the name is bound to, in the class, then the module
                    sym = self.info.names.get(u.name) or \
                        result.files[self.info.module_name].names.get(u.name)
                    node = sym.node if sym is not None else None
                    kind, target, project = answer(node, last)
                    self.record(last, u.line, c, kind, target, project, True, node, True)
        if isinstance(t, Instance) and len(u.args) == len(t.args):
            self.args += 1
            for ua, ta in zip(u.args, t.args):
                self.unrecorded(ua, ta)
            self.args -= 1


class DeclaredTypeNames(TypeNames):
    def visit_instance(self, t: Instance) -> None:
        kind, target, project = answer(t.type, t.type.name)
        self.name(t, kind, target, project, t.type)
        self.uses.args += 1
        for a in t.args:
            a.accept(self)
        self.uses.args -= 1


def lookup_class(fullname: str):
    """The class of a full name, when there is one (`p.foo.Foo` of `p.foo.Foo.Inner`)."""
    mod, _, rest = fullname.partition(".")
    while True:
        tree = result.files.get(mod)
        if tree is not None and rest:
            names = tree.names
            node = None
            for part in rest.split("."):
                sym = names.get(part) if names is not None else None
                node = sym.node if sym is not None else None
                if not isinstance(node, TypeInfo):
                    node = None
                    break
                names = node.names
            if node is not None:
                return node
        if not rest:
            return None
        head, _, rest = rest.partition(".")
        mod = f"{mod}.{head}"


# every class statement of the sources, before any body is read (a body may name one
# declared further down)
declared_all: set[str] = set()


def collect(stmts, prefix: str) -> None:
    for s in stmts:
        if isinstance(s, ClassDef):
            declared_all.add(f"{prefix}.{s.name}")
            collect(s.defs.body, f"{prefix}.{s.name}")
        elif isinstance(s, (IfStmt, TryStmt, WithStmt, ForStmt, WhileStmt)):
            for b in blocks(s):
                collect(b.body, prefix)


for path, mod, rel in files:
    state = result.graph.get(mod)
    if state is not None and state.tree is not None:
        collect(state.tree.defs, mod)
for path, mod, rel in files:
    state = result.graph.get(mod)
    if state is None or state.tree is None:
        emit({"mypy_error": "not analyzed", "code": None, "file": rel, "line": 1})
        continue
    walk_classes(state.tree.defs, mod, mod, Source(path), rel)

with open(out_path, "w") as f:
    f.write("".join(line + "\n" for line in out))
