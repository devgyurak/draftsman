"""Source file -> raw declarations, driven by queries/<language>.scm.

The query protocol (capture names) is documented in
references/query-protocol.md. This module is language-neutral: everything
language-specific lives in the query file and the LanguageSpec.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path
from typing import Optional

import tree_sitter as ts
import tree_sitter_language_pack as tslp

from .langs import FileScope, Import, LanguageSpec, Unseen
from .langs.base import annotation_name
from .model import Diagnostic, Location, Member, Param

QUERY_DIR = Path(__file__).resolve().parents[2] / "queries"


@dataclass
class RawSuper:
    kind: str        # extends | implements | inherits
    text: str
    line: int
    scope: Optional[FileScope] = None   # file it was written in (partial types)


@dataclass
class RawMember:
    member: Member
    tparams: set[str] = field(default_factory=set)
    has_body: bool = False
    flags: set[str] = field(default_factory=set)   # capture names present in the match
    value: Optional[str] = None                     # initialiser text, if captured
    scope: Optional[FileScope] = None               # file it was written in (partial types)
    throws: list[str] = field(default_factory=list)  # Java `throws E`: used, not drawn as a member
    at: int = 0   # start byte of its name: tells the declarators of `int a = x, b = y;` apart
    # the receiver types of extension functions and properties in it, its own too
    # (Kotlin's `fun Ctx.ext()`, `@body.receiver`): their members are names in its body
    receivers: list[str] = field(default_factory=list)


@dataclass
class RawAnnotation:
    """An annotation, decorator or attribute written on a type, a member or a parameter,
    with the names in its arguments that may be types: (name, certainly a type, line)."""

    name: str
    line: int
    scope: FileScope
    args: list[tuple[str, bool, int]] = field(default_factory=list)


@dataclass
class BodyNames:
    """Names declared inside one member (its parameters included), wherever in it: those
    that may hide a type of the same name in it."""

    variables: set[str] = field(default_factory=set)   # locals, parameters, fields of local classes
    types: set[str] = field(default_factory=set)       # local classes, type parameters


@dataclass
class RawBodyRef:
    """A name written in a body (`new Foo()`, `Foo.bar()`), recorded on the nearest named
    type around it."""

    text: str          # a dotted name (`Util.Helper`), type arguments and comments left out
    position: str      # "type": only a type can stand there; "receiver": a variable can
    # too; "call": what is called (Kotlin's `Foo(1)`), which a function may be as well
    # (line, column) of each part of the name: 1-based lines, 0-based columns in UTF-16 code
    # units (javac's)
    places: list[tuple[int, int]]
    via: str           # the member the body belongs to, or the initializer (`static {}`)
    scope: FileScope
    member: Optional[RawMember]   # None in an initializer block
    names: BodyNames   # shared by every reference of the member
    # supertypes of the anonymous and local classes around the name, innermost first:
    # their members are in scope before the named type's
    classes: list[list[str]] = field(default_factory=list)
    # how many type arguments each part is written with (LanguageSpec.arity), or None
    arities: list[Optional[int]] = field(default_factory=list)
    # a receiver's member after it (`Create` in `Order.Create()`; LanguageSpec.color_color)
    next: Optional[str] = None

    @property
    def line(self) -> int:
        return self.places[0][0]


@dataclass
class RawType:
    qualified_name: str
    name: str
    kind: str
    location: Location
    scope: FileScope
    language: str
    namespace: Optional[str] = None
    outer: Optional[str] = None
    modifiers: list[str] = field(default_factory=list)
    annotations: list[str] = field(default_factory=list)
    generics: list[str] = field(default_factory=list)
    # the generics count of each declaration merged into it (`Repo` and `Repo<T>`)
    arities: set[int] = field(default_factory=set)
    members: list[RawMember] = field(default_factory=list)
    supers: list[RawSuper] = field(default_factory=list)
    annotation_refs: list[RawAnnotation] = field(default_factory=list)
    body_refs: list[RawBodyRef] = field(default_factory=list)
    # variables in scope in every body of the type, and of its subtypes, that are no
    # member of ir.json (C#'s primary constructor parameters, event fields, generated
    # members: `@body.field`, `@body.generated`)
    body_fields: set[str] = field(default_factory=set)
    # declared in code a build may leave out (LanguageSpec.conditional_ranges)
    conditional: bool = False
    # names of types the type declares that ir.json does not record (C#'s nested delegates:
    # "type"; an extension block's type parameters: "tparam"; `@body.hidden_type`)
    hidden_types: dict[str, str] = field(default_factory=dict)
    # names a build may declare in the type's #elif/#else branches, in any of its files
    # (LanguageSpec.left_out_names)
    left_out: set[str] = field(default_factory=set)
    # declared in a static scope of its outer type that is no type itself (Kotlin's
    # companion object without supertypes), whose id leaves the scope out
    static_scope: bool = False
    # seen in its file only (LanguageSpec.file_local_node: C++'s anonymous namespace)
    file_local: bool = False
    # the `#if` branches declaring it, (file, first line, last line) each, or None when a
    # declaration stands outside every one (LanguageSpec.branch_ranges)
    branches: Optional[list[tuple[str, int, int, str]]] = None
    # an enum whose constants are no names of the scope around it (C++'s `enum class`)
    scoped: bool = False


@dataclass
class RawFile:
    path: str
    scope: FileScope
    types: list[RawType] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)


class GrammarUnavailable(RuntimeError):
    """The language pack could not provide a grammar: it downloads each on first use."""

    HELP = ("tree-sitter-language-pack downloads each grammar on first use and keeps it in "
            "its cache, so without network access, or while its server fails, nothing can be "
            "extracted. Try again in a minute, or tell the user. Do not draw the diagram by "
            "hand from reading the code: its relations would not come from a parser.")


@lru_cache(maxsize=None)
def _load(spec_name: str, grammar: str, extra: tuple[str, ...] = ()) -> tuple[ts.Parser, ts.Query]:
    try:
        language = tslp.get_language(grammar)
    except Exception as e:   # the pack's DownloadError and its kin
        raise GrammarUnavailable(f"the {grammar} grammar could not be loaded ({e})") from e
    parser = ts.Parser(language)
    source = "\n".join((QUERY_DIR / f"{name}.scm").read_text(encoding="utf-8")
                       for name in (spec_name, *extra))
    return parser, ts.Query(language, source)


def _text(node: ts.Node, src: bytes) -> str:
    """Source text of ``node`` on one line, without the comments inside it (a JSDoc
    block in an inline object type, `/* nullable */` in a signature)."""
    raw = src[node.start_byte:node.end_byte]
    if b"/" in raw or b"#" in raw:   # cheap test before walking the subtree
        cuts = _comment_spans(node)
        if cuts:
            parts, pos = [], node.start_byte
            for start, end in cuts:
                parts += [src[pos:start], b" "]
                pos = end
            parts.append(src[pos:node.end_byte])
            text = " ".join(b"".join(parts).decode("utf-8", "replace").split())
            return _BRACKET_SPACE.sub("", text)   # `List< Line>` where a comment was
    return " ".join(raw.decode("utf-8", "replace").split())


_BRACKET_SPACE = re.compile(r"(?<=[<(\[]) | (?=[>)\],])")


def _comment_spans(node: ts.Node) -> list[tuple[int, int]]:
    # comment node types differ per grammar: comment, line_comment, block_comment,
    # multiline_comment; string contents are other nodes and stay untouched
    spans = []
    stack = [node]
    while stack:
        n = stack.pop()
        if "comment" in n.type:
            spans.append((n.start_byte, n.end_byte))
        elif n.child_count:
            stack.extend(n.children)
    return sorted(spans)


def _inside(node: ts.Node, ids: set[int]) -> bool:
    """Whether one of the nodes ``ids`` is at or above ``node``."""
    while node is not None:
        if node.id in ids:
            return True
        node = node.parent
    return False


def _string(node: ts.Node, src: bytes) -> Optional[str]:
    """The text of a string literal without interpolations (`"Foo"`), else None."""
    if node.type != "string" or any(c.type == "interpolation" for c in node.children):
        return None
    return "".join(_text(c, src) for c in node.children if c.type == "string_content")


def _line(node: ts.Node) -> int:
    return node.start_point[0] + 1


def _utf16_col(node: ts.Node, src: bytes) -> int:
    line_start = node.start_byte - node.start_point[1]
    return len(src[line_start:node.start_byte].decode("utf-8", "replace").encode("utf-16-le")) // 2


def _first(caps: dict, name: str) -> Optional[ts.Node]:
    nodes = caps.get(name)
    return nodes[0] if nodes else None


def _root(caps: dict, prefix: str) -> Optional[tuple[str, ts.Node]]:
    for cap, nodes in caps.items():
        if cap.startswith(prefix):
            return cap[len(prefix):], nodes[0]
    return None


class Extractor:
    def __init__(self, spec: LanguageSpec):
        self.spec = spec
        self.parser, self.query = _load(spec.query or spec.name, spec.grammar,
                                        spec.extra_queries)
        self._package_roots: dict[Path, str] = {}
        self._workspaces: dict[Path, dict[str, list[tuple[str, str]]]] = {}
        self._packages: dict[str, list[tuple[str, str]]] = {}   # of the current root

    def _module_path(self, root: Path, rel: str) -> str:
        """``rel`` below the package the extraction root sits in (see package_root)."""
        if root not in self._package_roots:
            self._package_roots[root] = self.spec.package_root(root)
        prefix = self._package_roots[root]
        return f"{prefix}/{rel}" if prefix else rel

    # ------------------------------------------------------------ modifiers

    def _modifiers(self, nodes: list[ts.Node], decl: ts.Node,
                   src: bytes) -> tuple[list[str], list[str]]:
        """(keywords, annotation names) from modifier captures and the declaration."""
        keywords: list[str] = []
        annotations: list[str] = []

        def walk(n: ts.Node) -> None:
            if n.type in self.spec.annotation_nodes:
                name = n.child_by_field_name(self.spec.annotation_name_field)
                annotations.append(_text(name, src) if name is not None
                                   else annotation_name(_text(n, src)))
            elif n.child_count == 0:
                keywords.append(_text(n, src))
            else:
                for c in n.children:
                    walk(c)

        for n in nodes:
            walk(n)
        if self.spec.modifier_node_types or self.spec.modifier_keywords:
            for c in decl.children:
                if c.type in self.spec.modifier_node_types:
                    keywords.extend(_text(c, src).split())
                elif not c.is_named and c.type in self.spec.modifier_keywords:
                    keywords.append(c.type)
        return keywords, annotations

    # ------------------------------------------------------------ ownership

    def _owner(self, start: Optional[ts.Node], targets: dict[int, object],
               stops: dict[int, object] = None) -> tuple[Optional[object], bool]:
        """Nearest strict ancestor of ``start`` registered in ``targets``.

        Returns (None, _) if an opaque node or a node in ``stops`` is hit first.
        The flag tells whether a static scope (companion object) was crossed.
        """
        static = False
        cur = start.parent if start is not None else None
        while cur is not None:
            if cur.id in targets:
                return targets[cur.id], static
            if stops and cur.id in stops:
                return None, False
            if self.spec.is_opaque(cur):
                return None, False
            if cur.type in self.spec.static_scope_nodes:
                static = True
            cur = cur.parent
        return None, False

    # ------------------------------------------------------------ imports

    def _module_target(self, text: str, rel: str) -> tuple[Optional[str], bool, tuple]:
        """(module id or None for a package outside the sources; whether the import
        points inside the sources by its form, relative or a workspace package; the
        modules it may name when the workspace package name is declared twice)."""
        if self._packages:
            mods = self.spec.workspace_modules(text, self._packages)
            if len(mods) == 1:
                return mods[0], True, ()
            if mods:
                return None, True, tuple(mods)
        return self.spec.module_id(text, rel), text.startswith("."), ()

    def _import(self, caps: dict, src: bytes, rel: str) -> Optional[Import]:
        spec, sep = self.spec, self.spec.separator
        alias_node = _first(caps, "import.alias")
        alias = _text(alias_node, src) if alias_node is not None else None
        static = _first(caps, "import.static") is not None   # Java `import static`
        if (n := _first(caps, "import")) is not None:
            return Import(_text(n, src), alias=alias, sep=sep, static=static)
        if (n := _first(caps, "import.wildcard")) is not None:
            text = _text(n, src).strip("'\"")
            target, inside, alts = self._module_target(text, rel)
            return Import(target or text, wildcard=True, external=target is None and not alts,
                          local=inside, ambiguous=alts, sep=sep, static=static,
                          project_wide=spec.is_project_wide(n),
                          origin="global using" if spec.is_project_wide(n) else None)
        if (n := _first(caps, "import.module")) is not None:
            text = _text(n, src)
            target, inside, alts = self._module_target(text, rel)
            local = alias or text.rsplit(".", 1)[-1].rsplit("/", 1)[-1]
            return Import(target or text, alias=local, module=True,
                          external=target is None and not alts, local=inside, ambiguous=alts,
                          sep=sep, aliased=alias is not None)
        if (n := _first(caps, "import.from")) is not None:
            mod_text = _text(n, src).strip("'\"")
            target, inside, alts = self._module_target(mod_text, rel)
            name_node = _first(caps, "import.name")
            if name_node is None:
                return None
            name = _text(name_node, src)
            base = target if target is not None else mod_text
            return Import(f"{base}{sep}{name}" if base else name, alias=alias,
                          external=target is None and not alts, local=inside,
                          ambiguous=alts, sep=sep)
        return None

    # ------------------------------------------------------------ main

    def extract(self, path: Path, rel: str, root: Path) -> RawFile:
        """Parse one file; ``rel`` is its path below ``root``, the directory extracted."""
        spec = self.spec
        original = path.read_bytes()
        src = spec.preprocess(original)
        conditional = spec.conditional_ranges(original)
        branch_ranges = spec.branch_ranges(original)
        tree = self.parser.parse(src)
        mod_path = self._module_path(root, rel)
        project, build_imports = spec.project_imports(path, root)
        if root not in self._workspaces:
            self._workspaces[root] = spec.workspace_packages(root)
        self._packages = self._workspaces[root]
        scope = FileScope(file=rel, namespace=spec.file_namespace(mod_path), project=project,
                          left_out_types=spec.left_out_types(original),
                          left_out_names=spec.left_out_names(original),
                          implicit_types=spec.implicit_types(tree.root_node),
                          build_types=spec.build_types(path, root))
        scope.branches = [(first, last, cond) for _, _, first, last, cond in branch_ranges]
        raw = RawFile(path=rel, scope=scope)
        unseen: list[tuple[str, Unseen]] = [
            (name, Unseen(rel, line, line, macro))
            for name, line, macro in spec.macro_declared_names(original)]
        if tree.root_node.has_error:
            spans = _error_spans(tree.root_node)
            lines = src.split(b"\n")
            for start, end in spans:
                for name in _CLASS_HEAD.findall(b"\n".join(lines[start - 1:end])):
                    unseen.append((name.decode(), Unseen(rel, start, end)))
            for start, end in spans[:MAX_ERROR_SPANS]:
                raw.diagnostics.append(Diagnostic(
                    rel, start, "syntax error; declarations in these lines may be missing",
                    end_line=end))
            if len(spans) > MAX_ERROR_SPANS:
                raw.diagnostics.append(Diagnostic(
                    rel, spans[MAX_ERROR_SPANS][0],
                    f"{len(spans) - MAX_ERROR_SPANS} more syntax errors after this line",
                    end_line=spans[-1][1]))

        type_matches, member_matches, other, bodies = [], [], [], []
        namespaces: dict[int, str] = {}
        inline: list = []
        ns_nodes: list = []
        for _, caps in ts.QueryCursor(self.query).matches(tree.root_node):
            if any(k.startswith("body.") for k in caps):
                bodies.append(caps)   # most matches of a file: read apart (_body_refs)
            elif _root(caps, "type."):
                type_matches.append(caps)
            elif _root(caps, "member."):
                member_matches.append(caps)
            elif (n := _first(caps, "namespace")) is not None:
                name = _first(caps, "namespace.name")
                if name is not None:
                    namespaces[n.id] = _text(name, src)
                    ns_nodes.append(n)
                    if n.child_count and n.children[0].type == "inline":
                        inline.append(n)
            else:
                other.append(caps)
        # by the namespace around the line, for references that see that namespace
        for name, place in unseen:
            point = (place.line - 1, 0)
            cur = tree.root_node.descendant_for_point_range(point, point)
            parts = []
            while cur is not None:
                if cur.id in namespaces:
                    parts.insert(0, namespaces[cur.id])
                cur = cur.parent
            places = scope.unseen_types.setdefault(name, {}).setdefault(
                spec.separator.join(parts), [])
            if place not in places:
                places.append(place)
        # every namespace a block opens, by its full name (also one declaring no type)
        for n in ns_nodes:
            parts, cur = [], n
            while cur is not None:
                if cur.id in namespaces:
                    parts.insert(0, namespaces[cur.id])
                cur = cur.parent
            scope.declared_namespaces.add(spec.separator.join(
                p for p in [scope.namespace, *parts] if p))
        # C++ `inline namespace v1`: its types are also named without it (acme::Versioned)
        for n in inline:
            parts, cur = [], n
            while cur is not None:
                if cur.id in namespaces:
                    parts.insert(0, namespaces[cur.id])
                cur = cur.parent
            scope.inline_namespaces.add(spec.separator.join(parts))
        # parameters must be appended in source order
        other.sort(key=lambda c: min(n.start_byte for nodes in c.values() for n in nodes))

        imports_by_node: dict[int, Import] = {}   # by the nodes of its captures
        type_ids = {_root(caps, "type.")[1].id for caps in type_matches}
        class_imports: dict[int, list[Import]] = {}   # LanguageSpec.local_imports
        listed: Optional[set[str]] = None   # the names the file lists as its exports
        package_at: Optional[int] = None    # where a file-wide namespace is declared
        readable = True
        for caps in other:
            if (n := _first(caps, "package")) is not None:
                if scope.namespace is None:
                    scope.namespace = _text(n, src)
                    package_at = n.start_byte
            elif (n := _first(caps, "exports")) is not None:
                # a list or tuple of plain strings; anything else cannot be read
                names = [_string(c, src) for c in n.named_children if "comment" not in c.type] \
                    if n.type in ("list", "tuple") else [None]
                if None in names:
                    readable = False
                else:
                    listed = (listed or set()) | set(names)
            elif (n := _first(caps, "typevar")) is not None:
                scope.type_params.add(_text(n, src))
            elif any(k.startswith("import") for k in caps):
                node = next(n for k, ns in caps.items() if k.startswith("import") for n in ns)
                if not spec.is_import(node):
                    continue
                imp = self._import(caps, src, mod_path)
                if imp is not None and any(a <= node.start_byte < b for a, b in conditional):
                    imp.conditional = True
                if imp is not None and spec.block_imports:
                    parts, cur = [], node.parent
                    while cur is not None:
                        if cur.id in namespaces:
                            parts.insert(0, namespaces[cur.id])
                        cur = cur.parent
                    if parts:
                        imp.block = spec.separator.join(p for p in [scope.namespace, *parts] if p)
                    elif package_at is not None and node.start_byte > package_at:
                        imp.block = scope.namespace   # after C#'s `namespace A;`: A's
                if imp is not None and spec.include_visibility and not imp.wildcard:
                    parts, cur = [], node.parent
                    while cur is not None and cur.type not in (
                            "compound_statement", "field_declaration_list"):
                        if cur.id in namespaces:
                            parts.insert(0, namespaces[cur.id])
                        cur = cur.parent
                    if cur is None:   # at a namespace's scope or the file's
                        imp.namespace = spec.separator.join(p for p in [scope.namespace, *parts] if p)
                if imp is not None:
                    around = self._enclosing(node, type_ids) if spec.local_imports else None
                    if around is None:
                        scope.imports.append(imp)
                    elif around.id in type_ids:   # the class's (its declarations' names)
                        class_imports.setdefault(around.id, []).append(imp)
                    for nodes in caps.values():   # for an import in a member (@body.import)
                        for n in nodes:
                            imports_by_node[n.id] = imp

        scope.exports = listed if readable else None
        scope.exports_unread = not readable

        # --- types: register every declaration node, then compute names
        type_nodes: dict[int, dict] = {}
        for caps in type_matches:
            kind, node = _root(caps, "type.")
            prev = type_nodes.get(node.id)
            # several patterns may match one node; a specific kind beats "class"
            if prev is not None and (prev["kind"] != "class" or kind == "class"):
                continue
            type_nodes[node.id] = {"node": node, "kind": kind, "caps": caps, "raw": None}

        sep = spec.separator

        def build(entry) -> Optional[RawType]:
            if entry["raw"] is not None or entry.get("skip"):
                return entry["raw"]
            node, caps = entry["node"], entry["caps"]
            name_node = _first(caps, "name")
            if name_node is None:
                entry["skip"] = True
                return None
            # walk up: enclosing type, enclosing namespaces, or an opaque node
            outer_raw = None
            ns_parts: list[str] = []
            in_static = False
            cur = node.parent
            while cur is not None:
                if cur.type in spec.static_scope_nodes and cur.id not in type_nodes:
                    in_static = True
                if cur.id in type_nodes:
                    outer_raw = build(type_nodes[cur.id])
                    if outer_raw is None:
                        entry["skip"] = True
                        return None
                    break
                if cur.id in namespaces:
                    ns_parts.insert(0, namespaces[cur.id])
                elif spec.is_opaque(cur):
                    entry["skip"] = True
                    return None
                cur = cur.parent
            name = spec.type_name(node, _text(name_node, src))
            prefix = None
            if sep in name:  # an out-of-class definition such as `struct Table::Rep`
                written = re.sub(r"<[^<>]*>", "", re.sub(r"<[^<>]*>", "", name)).replace(" ", "")
                prefix, name = written.rsplit(sep, 1)
            if outer_raw is not None:
                namespace = outer_raw.namespace
                qname = outer_raw.qualified_name + sep + name
            else:
                namespace = sep.join(p for p in [scope.namespace, *ns_parts] if p) or None
                if prefix:
                    owner_q = f"{namespace}{sep}{prefix}" if namespace else prefix
                    qname = owner_q + sep + name
                else:
                    owner_q = None
                    qname = f"{namespace}{sep}{name}" if namespace else name
                if ns_parts and (block := spec.local_block(node)) is not None:
                    scope.block_local[qname] = (_line(block), block.end_point[0] + 1)
            mods, annos = self._modifiers(caps.get("modifiers", []), node, src)
            entry["raw"] = RawType(
                qualified_name=qname,
                name=name,
                kind=spec.type_kind(entry["kind"], mods),
                location=Location(rel, _line(node)),
                scope=scope,
                language=spec.name,
                namespace=namespace,
                outer=outer_raw.qualified_name if outer_raw else (owner_q if prefix else None),
                modifiers=mods,
                annotations=annos + [annotation_name(_text(a, src))
                                     for a in caps.get("annotation", [])],
                conditional=any(a <= node.start_byte < b for a, b in conditional),
                left_out=set(scope.left_out_names),
                static_scope=in_static and outer_raw is not None,
                file_local=spec.file_local_node(node),
                scoped=spec.scoped_enum(node),
                branches=next(([(rel, first, last, cond)] for a, b, first, last, cond
                               in branch_ranges if a <= node.start_byte < b), None),
            )
            return entry["raw"]

        types_by_node: dict[int, RawType] = {}
        for nid, entry in sorted(type_nodes.items(), key=lambda kv: kv[1]["node"].start_byte):
            rt = build(entry)
            if rt is not None:
                types_by_node[nid] = rt
                raw.types.append(rt)
        for name, fields in spec.companion_fields(path).items():
            for rt in raw.types:
                if rt.name == name:
                    rt.body_fields |= fields

        # --- members
        members_by_node: dict[int, list[RawMember]] = {}
        seen_members: dict[tuple[int, str], RawMember] = {}
        for caps in sorted(member_matches, key=lambda c: _root(c, "member.")[1].start_byte):
            self._member(caps, src, scope, types_by_node, members_by_node, seen_members)

        # --- parameters, type parameters, supertypes, annotations
        decls: dict[int, object] = {**types_by_node,
                                    **{k: v[0] for k, v in members_by_node.items()}}
        callables = {k: v[0] for k, v in members_by_node.items()
                     if v[0].member.kind in ("method", "constructor")}
        # annotations, by node: a pattern naming the declaration they apply to wins over
        # one that does not (TS `export @Dec() class`)
        annotation_refs: dict[int, dict] = {}
        for caps in other:
            if (n := _first(caps, "annotation.ref")) is not None:
                if n.id not in annotation_refs or "annotation.ref.target" in caps:
                    annotation_refs[n.id] = caps
        for caps in other:
            if (n := _first(caps, "param")) is not None:
                owner, _ = self._owner(n, callables, stops=types_by_node)
                if owner is None:
                    continue
                pname, ptype = _first(caps, "param.name"), _first(caps, "param.type")
                name = _text(pname, src) if pname is not None else ""
                tref = spec.normalize_type(spec.type_text(ptype, _text(ptype, src), src)) \
                    if ptype is not None else None
                if (d := _first(caps, "param.declarator")) is not None:
                    dname, suffix, _ = spec.declarator(d, src)
                    name = dname or name
                    tref = (tref or "") + suffix if tref else tref
                if tref is not None and (_first(caps, "param.varargs") is not None
                                         or spec.is_varargs(n)):
                    tref += "..."
                owner.member.params.append(Param(name, tref))
            elif (n := _first(caps, "throws")) is not None:
                owner, _ = self._owner(n, callables, stops=types_by_node)
                if owner is not None:
                    owner.throws.append(spec.normalize_type(_text(n, src)))
            elif (n := _first(caps, "tparam")) is not None:
                target = _first(caps, "tparam.target")
                if target is not None:
                    owner = decls.get(target.id)
                else:
                    owner, _ = self._owner(n, decls)
                if isinstance(owner, RawType):
                    owner.generics.append(_text(n, src))
                elif isinstance(owner, RawMember):
                    owner.tparams.add(_text(n, src))
            elif (n := _first(caps, "alias")) is not None:
                t = _first(caps, "alias.type")
                target = spec.alias_target(n, t, _text(t, src)) if t is not None else ""
                if target is None:
                    continue   # the declaration names a type, it is no alias of one
                q = self._qualify(n, _text(n, src), types_by_node, namespaces, scope)
                if q is not None:
                    scope.aliases.add(q)
                    if (block := spec.local_block(n.parent)) is not None:
                        scope.block_local[q] = (_line(block), block.end_point[0] + 1)
                    if target:
                        scope.alias_targets[q] = spec.normalize_type(target)
                    if params := spec.alias_params(n):
                        scope.alias_tparams[q] = set(params)
                    if spec.block_imports:
                        parts, cur = [], n.parent
                        while cur is not None:
                            if cur.id in namespaces:
                                parts.insert(0, namespaces[cur.id])
                            cur = cur.parent
                        scope.alias_blocks[q] = spec.separator.join(
                            p for p in [scope.namespace, *parts] if p) if parts \
                            else scope.namespace if package_at is not None \
                            and n.start_byte > package_at else ""
                    if any(a <= n.start_byte < b for a, b in conditional):
                        scope.conditional_aliases.add(q)
            elif (n := _first(caps, "annotation")) is not None:
                target = _first(caps, "annotation.target")
                if target is None:
                    continue
                name = annotation_name(_text(n, src))
                if target.id in types_by_node:
                    types_by_node[target.id].annotations.append(name)
                for rm in members_by_node.get(target.id, []):
                    rm.member.annotations.append(name)
            else:
                sup = _root(caps, "super.")
                if sup is None:
                    continue
                kind, n = sup
                owner, _ = self._owner(n, types_by_node)
                if owner is not None:
                    owner.supers.append(RawSuper(kind, _text(n, src), _line(n), scope))

        for nid in sorted(annotation_refs, key=lambda i: annotation_refs[i]["annotation.ref"][0].start_byte):
            self._annotation_ref(annotation_refs[nid], src, scope, types_by_node,
                                 set(annotation_refs))
        self._body_refs(bodies, src, scope, types_by_node, members_by_node, namespaces,
                        imports_by_node, spec.unbuilt_ranges(original, path, root))

        # what the build imports into every file (implicit usings), after the file's own
        # (a C# <Using Alias> is looked at after the namespaces around, as a file's alias at
        # its top is: its block is the global namespace's)
        for ns, origin, *kind in build_imports:
            kind = kind[0] if kind else ""
            if kind.startswith("alias="):
                scope.imports.append(Import(ns, alias=kind[len("alias="):], sep=spec.separator,
                                            project_wide=True, origin=origin, block=""))
            else:
                scope.imports.append(Import(ns, wildcard=True, sep=spec.separator,
                                            project_wide=True, origin=origin,
                                            static=kind == "static"))

        # an import in a class body names a class in that class's own declarations (its
        # fields' and methods' annotations), not in its methods' bodies nor its nested classes
        for nid, imps in class_imports.items():
            if (rt := types_by_node.get(nid)) is not None:
                rt.scope = replace(scope, imports=[*imps, *scope.imports])
                for rm in rt.members:
                    if rm.scope is scope:
                        rm.scope = rt.scope

        for rt in raw.types:
            spec.finalize_type(rt)
        return raw

    def _annotation_ref(self, caps, src, scope, types_by_node, refs: set[int]) -> None:
        """An annotation on a declaration: its type name and the names in its arguments,
        recorded on the nearest enclosing type (the type itself for its own annotations)."""
        node, name_node = _first(caps, "annotation.ref"), _first(caps, "annotation.ref.name")
        if name_node is None:
            return
        target = _first(caps, "annotation.ref.target")
        owner = types_by_node.get(target.id) if target is not None else None
        if owner is None:
            owner, _ = self._owner(node, types_by_node)
        if owner is None:
            return   # in a body, a lambda or a local type: not the declaration's
        ann = RawAnnotation(annotation_name(_text(name_node, src)), _line(node), scope)
        args = _first(caps, "annotation.ref.args")
        if args is not None:
            text = lambda n: _text(n, src)   # noqa: E731
            stack = [args]
            while stack:
                n = stack.pop()
                found = []
                for i, c in enumerate(n.children):
                    if not c.is_named or "comment" in c.type or c.id in refs:
                        continue   # a nested annotation is an entry of its own
                    if n.field_name_for_child(i) in ("name", "key"):
                        continue   # `using = X.class`: the argument's name, not a value
                    hit = self.spec.annotation_arg(c, text)
                    if hit is not None:
                        if hit[0]:
                            ann.args.append((hit[0], hit[1], _line(c)))
                    else:
                        found.append(c)
                stack.extend(reversed(found))
        owner.annotation_refs.append(ann)

    def _body_refs(self, matches, src, scope, types_by_node, members_by_node,
                   namespaces, imports_by_node, unread_ranges=()) -> None:
        """Names written in bodies, each with what may hide it there (query-protocol.md);
        none in ``unread_ranges`` (LanguageSpec.unbuilt_ranges)."""
        regions: set[int] = set()
        inits: dict[int, str] = {}           # initializer block -> its `via`
        classes: dict[int, list[str]] = {}   # body of an anonymous or local class -> supertypes
        refs, declared, receivers = [], [], []
        unread: set[int] = set()   # type nodes that are no name of the scope
        blind: set[int] = set()    # class bodies whose inherited members are not known
        guarded: set[int] = set()  # blocks only some checkers read (a platform's branch)
        # members defined outside their type -> (the type as written, name, type parameters)
        detached: dict[int, tuple[str, str, list[str]]] = {}
        for caps in matches:
            if (n := _first(caps, "body.detached")) is not None:
                if (got := self.spec.detached_owner(n, src)) is not None:
                    detached[n.id] = got
                continue
            if (n := _first(caps, "body.init")) is not None:
                # only a named type's own: a block in an anonymous class is in a body already
                if self._owner(n, types_by_node)[0] is not None:
                    # the body alone when the init is its declaration (whose parameters
                    # are the body's names, and whose signature is no body)
                    regions.add((_first(caps, "body.init.region") or n).id)
                    if (name := _first(caps, "body.init.name")) is not None:
                        inits[n.id] = _text(name, src)   # a compact constructor
                    elif (via := self.spec.init_via(n, src)) is not None:
                        inits[n.id] = via
                    else:
                        head = _text(n, src).split("{", 1)[0].strip()
                        inits[n.id] = f"{head} {{}}" if head else "{}"
                continue
            if (n := _first(caps, "body.class")) is not None:
                sup = _first(caps, "body.class.super")
                if sup is not None:
                    classes.setdefault(n.id, []).append(_text(sup, src))
                continue
            # the rest capture one node each (a type name in a body is one match of many)
            for cap, nodes in caps.items():
                n = nodes[0]
                if cap.startswith("body.ref."):
                    position = self.spec.ref_position(n, cap[len("body.ref."):])
                    if position == "receiver" and any(c.type == "super" for c in n.parent.children):
                        continue   # `X.super.m()`: X is in type position, captured as such
                    refs.append((position, n))
                elif cap == "body.region":
                    regions.add(n.id)
                elif cap == "body.var":
                    declared.append((n, "variables"))
                elif cap == "body.var.enum":
                    if not self.spec.scoped_enum(n.parent.parent.parent):
                        declared.append((n, "variables"))
                elif cap == "body.field":
                    if (owner := self._owner(n, types_by_node)[0]) is not None:
                        owner.body_fields.add(self.spec.body_name_text(_text(n, src)))
                elif cap == "body.generated":
                    if (owner := self._owner(n, types_by_node)[0]) is not None:
                        owner.body_fields.update(self.spec.generated_fields(n, src))
                elif cap == "body.extension":
                    scope.extension_methods.add(_text(n, src))
                elif cap == "body.receiver":
                    receivers.append(n)
                elif cap == "body.function":
                    if self.spec.top_function(n):
                        scope.top_functions.add(self.spec.body_name_text(_text(n, src)))
                elif cap == "body.value":
                    scope.top_values.add(self.spec.body_name_text(_text(n, src)))
                elif cap in ("body.hidden_type", "body.hidden_tparam"):
                    kind = "type" if cap == "body.hidden_type" else "tparam"
                    if (owner := self._owner(n, types_by_node)[0]) is not None:
                        owner.hidden_types[_text(n, src)] = kind
                    elif kind == "type":   # a delegate of a namespace: no type of ir.json
                        parts, cur = [], n.parent
                        while cur is not None:
                            if cur.id in namespaces:
                                parts.insert(0, namespaces[cur.id])
                            cur = cur.parent
                        ns = self.spec.separator.join(p for p in [scope.namespace, *parts] if p)
                        scope.build_types.setdefault(ns, set()).add(_text(n, src))
                elif cap == "body.type":
                    declared.append((n, "types"))
                elif cap == "body.import":
                    declared.append((n, "imports"))
                elif cap == "body.global":
                    declared.append((n, "globals"))
                elif cap == "body.unread":
                    unread.add(n.id)
                elif cap == "body.declared_type":
                    # a declaration's type where the language reads no declaration (C#'s
                    # `F(Order < b, Customer > d)`, two comparisons): none of its names
                    if not self.spec.declaration_read(n.parent):
                        stack = [n]
                        while stack:
                            cur = stack.pop()
                            unread.add(cur.id)
                            stack.extend(cur.children)
                elif cap == "body.blind":
                    blind.add(n.id)
                elif cap == "body.include":
                    scope.includes.append(_text(n, src))
                elif cap == "body.include_unknown":
                    scope.unknown_include = True
                elif cap == "body.nsalias":
                    target = _text(n.parent, src).split("=", 1)[-1].strip().rstrip(";").strip()
                    scope.namespace_aliases[_text(n, src)] = target.lstrip(":").replace(" ", "")
                elif cap == "body.forward":
                    parts, cur = [_text(n, src)], n.parent
                    while cur is not None:
                        if cur.id in namespaces:
                            parts.insert(0, namespaces[cur.id])
                        cur = cur.parent
                    scope.forward_types.add(self.spec.separator.join(
                        p for p in [scope.namespace, *parts] if p))
                elif cap == "body.guarded":
                    blind.add(n.id)
                    guarded.add(n.id)
        if not refs and not (declared and self.spec.rebinding_hides):
            return
        names: dict[int, BodyNames] = {}   # by the node of the member or initializer

        # what every node lies in, worked out once per node: names in one member share
        # their way up. anchors: the member or initializer node at or above a node, None at
        # the named type; ups: (the named type, whether a body is on the way, the
        # supertypes of the anonymous and local classes below the member, innermost first),
        # or no type when an annotation or a blind class body is on the way
        anchors: dict[int, Optional[ts.Node]] = {}
        ups: dict[int, tuple] = {}
        no_type = (None, False, ())

        def anchor_of(cur: ts.Node) -> Optional[ts.Node]:
            chain = []
            while cur is not None and cur.id not in anchors:
                if cur.id in types_by_node:
                    anchors[cur.id] = None
                    break
                if cur.id in inits or cur.id in detached or members_by_node.get(cur.id):
                    anchors[cur.id] = cur
                    break
                if (decl := self.spec.member_of(cur)) is not None and members_by_node.get(decl.id):
                    anchors[cur.id] = decl   # a getter on the line after its property
                    break
                chain.append(cur)
                cur = cur.parent
            found = anchors.get(cur.id) if cur is not None else None
            for c in chain:
                anchors[c.id] = found
            return found

        def up(cur: ts.Node) -> tuple:
            chain = []
            while cur is not None and cur.id not in ups:
                if cur.type in self.spec.annotation_nodes or cur.id in blind:
                    ups[cur.id] = no_type   # an annotation's arguments are no body, even inside one
                    break
                if cur.id in types_by_node or cur.id in detached:
                    ups[cur.id] = (cur, False, ())
                    break
                chain.append(cur)
                cur = cur.parent
            got = ups[cur.id] if cur is not None else no_type
            for c in reversed(chain):
                owner, in_body, around = got
                if owner is not None:
                    a = anchor_of(c)
                    around = () if a is None or a.id == c.id else (
                        ((classes[c.id],) if c.id in classes else ()) + around)
                    got = (owner, in_body or c.id in regions, around)
                ups[c.id] = got
            return got

        def place(a: ts.Node, start: int) -> tuple:
            """(node id, via, member) of the member or initializer node ``a``."""
            if a.id in inits:
                return a.id, inits[a.id], None
            if a.id in detached:
                return a.id, detached[a.id][1], None
            members = members_by_node[a.id]
            # several declarators: the one whose name comes last before the name
            rm = max((m for m in members if m.at <= start), key=lambda m: m.at, default=members[0])
            return a.id, rm.member.name, rm

        def namespace_path(cur: Optional[ts.Node]) -> Optional[tuple[str, ...]]:
            """The names of the namespaces around ``cur``, outermost first (`namespace A.B`
            is A, B), or None inside a type or an opaque node (a function)."""
            path: list[str] = []
            while cur is not None:
                if cur.id in types_by_node or self.spec.is_opaque(cur):
                    return None
                if cur.id in namespaces:
                    path[:0] = namespaces[cur.id].split(self.spec.separator)
                cur = cur.parent
            return tuple(path)

        # variables a namespace block declares, by the namespace's path in the file: every
        # block of one namespace shares them, so as not to miss an exported one
        in_namespace: dict[tuple[str, ...], set[str]] = {}
        bound: dict[tuple[str, ...], Counter] = {}
        top_classes: set[str] = set()   # the class statements at the top of the file
        # class -> what the statements of its body bind outside its members
        # (LanguageSpec.initializers_in_class_scope)
        in_class: dict[int, set[str]] = {}
        nested: Counter = Counter()   # (class, the name of a class statement in its body)

        def class_around(cur: Optional[ts.Node]) -> Optional[ts.Node]:
            """The type whose body ``cur`` stands in, with no function between."""
            while cur is not None and not self.spec.is_opaque(cur):
                if cur.id in types_by_node:
                    return cur
                cur = cur.parent
            return None

        # member -> (name, the function it is imported in, where, the import)
        local_imports: dict[int, list[tuple[str, int, int, Import]]] = {}
        scopes: dict[int, FileScope] = {}   # the file's, with an import of a member first
        for node, kind in declared:
            if kind == "globals":   # Python's `global Foo`: the module's, wherever it stands
                in_namespace.setdefault((), set()).add(_text(node, src))
            elif (a := anchor_of(node.parent)) is not None:
                # a member inside a member is the outer one's: TypeScript's parameter
                # property `constructor(private x)` is a parameter in the body
                while (outer := anchor_of(a.parent)) is not None:
                    a = outer
                key = place(a, node.start_byte)[0]
                if kind == "imports":
                    # one name from a module (`from x import Foo`): read through it after
                    # it, in the function it stands in; elsewhere in the member it hides
                    imp = imports_by_node.get(node.id) or imports_by_node.get(node.parent.id)
                    fn = node.parent
                    while fn is not None and not self.spec.is_opaque(fn):
                        fn = fn.parent
                    if imp is not None and not imp.module and not imp.wildcard \
                            and fn is not None:
                        local_imports.setdefault(key, []).append(
                            (_text(node, src), fn.id, node.start_byte, imp))
                        continue
                    kind = "variables"
                getattr(names.setdefault(key, BodyNames()), kind).add(
                    self.spec.body_name_text(_text(node, src)))
            elif self.spec.initializers_in_class_scope and kind in ("variables", "imports") \
                    and (cls := class_around(node.parent)) is not None:
                in_class.setdefault(cls.id, set()).add(_text(node, src))
            elif self.spec.rebinding_hides and kind == "types" and node.parent.id in types_by_node \
                    and (cls := class_around(node.parent.parent)) is not None:
                nested[(cls.id, _text(node, src))] += 1
            elif (kind == "variables" or self.spec.rebinding_hides) and (path := namespace_path(
                    # a function's or a class's name is the scope's around it
                    node.parent.parent if node.parent.child_by_field_name("name") == node
                    else node.parent)) is not None:
                if kind == "variables":
                    in_namespace.setdefault(path, set()).add(_text(node, src))
                else:   # a class statement or an import of the namespace's top
                    bound.setdefault(path, Counter())[_text(node, src)] += 1
                    if kind == "types" and not path:
                        top_classes.add(_text(node, src))
                        if _inside(node, guarded):   # no one class for every checker
                            in_namespace.setdefault((), set()).add(_text(node, src))
        scope.variables = set(in_namespace.get((), ()))   # before the names bound twice
        # a name bound twice there (two class statements, a class and an import) is no
        # one type (LanguageSpec.rebinding_hides), here and where it is imported
        for path, counts in bound.items():
            in_namespace.setdefault(path, set()).update(n for n, k in counts.items() if k > 1)
        scope.rebound = {n for n in top_classes if n in in_namespace.get((), ())}
        # the same in a class body: `if x: class Cond` / `else: class Cond` in Foo is no one
        # `Foo.Cond`, nor is a nested class the body also binds as a variable
        for (cid, name), k in nested.items():
            if k > 1 or name in in_class.get(cid, ()):
                outer = types_by_node[cid].qualified_name
                if scope.namespace and outer.startswith(scope.namespace + self.spec.separator):
                    outer = outer[len(scope.namespace) + len(self.spec.separator):]
                scope.rebound.add(outer + self.spec.separator + name)
        if not refs:
            return
        seeded: set[int] = set()   # members given the variables of the namespaces around
        # `T` in `<T extends Foo>` is declared there; `Inner` in `o.new Inner()` is o's
        not_refs = {n.id for n, _ in declared} | unread
        # a receiver is a dotted name, not an expression (`this.x.m()`, `a[0].B.m()`)
        refs = [(p, n) for p, n in refs if n.id not in not_refs and (
            p == "type" or self._dotted(n))
            and not any(a <= n.start_byte < b for a, b in unread_ranges)
            and not self.spec.unreadable(n)]
        if self.spec.ref_priority:   # one node, one name: the position the language puts first
            rank = {p: i for i, p in enumerate(self.spec.ref_priority)}
            best: dict[int, tuple[str, ts.Node]] = {}
            for p, n in refs:
                if n.id not in best or rank.get(p, len(rank)) < rank.get(best[n.id][0], len(rank)):
                    best[n.id] = (p, n)
            refs = list(best.values())
        whole = {n.id for _, n in refs}
        for n in receivers:   # an extension's receiver: in the member it stands in
            if (a := anchor_of(n.parent)) is not None and a.id not in inits:
                rm = place(a, n.start_byte)[2]
                if rm is not None:
                    rm.receivers.extend(self.spec.receiver_types(n, _text(n, src), src))
        for position, node in sorted(refs, key=lambda r: r[1].start_byte):
            if node.parent.id in whole:
                continue   # `Foo` in `p.Foo`: the whole name is recorded
            owner, in_body, around = up(node.parent)
            # the name may be the initializer itself: Kotlin's `: Face by Proxy`
            a = anchor_of(node if node.id in inits else node.parent)
            # the name may be the whole body: `X = Foo.BAR` (TypeScript's field initializer)
            if owner is None or a is None or not (in_body or node.id in regions):
                continue
            _, via, rm = place(a, node.start_byte)
            # a member inside a member (Python's `self.x = ...` in `__init__`) sees the outer
            # one's names, under which they are kept
            top_a = a
            while (outer := anchor_of(top_a.parent)) is not None:
                top_a = outer
            key = top_a.id
            member_names = names.setdefault(key, BodyNames())
            if key not in seeded:
                seeded.add(key)
                if key in detached:   # a definition's own type parameters
                    member_names.types |= set(detached[key][2])
                # the namespaces around the outermost type: a nested type's bodies see them
                top, cur = owner, owner.parent
                while cur is not None:
                    if cur.id in types_by_node:
                        top = cur
                    cur = cur.parent
                if in_namespace and (path := namespace_path(top.parent)) is not None:
                    for k in range(len(path) + 1):
                        member_names.variables |= in_namespace.get(path[:k], set())
                # a field's initializer, in the class body: what the body binds
                if in_class and rm is not None and rm.member.kind in ("field", "enum_constant") \
                        and (cls := class_around(a.parent)) is not None:
                    member_names.variables |= in_class.get(cls.id, set())
            parts = self._parts(node)
            ref_scope, ref_names = scope, member_names
            head = _text(parts[0], src)
            imported = [imp for name, fn, at, imp in local_imports.get(key, ())
                        if name == head and at < node.start_byte and _inside(node, {fn})]
            if len({imp.path for imp in imported}) == 1:
                imp = imported[0]
                if id(imp) not in scopes:
                    scopes[id(imp)] = replace(scope, imports=[imp, *scope.imports])
                ref_scope = scopes[id(imp)]
            elif any(name == head for name, *_ in local_imports.get(key, ())):
                # before the import, outside its function, or two imports of the name
                ref_names = BodyNames(member_names.variables | {head}, member_names.types)
            if implicit := self.spec.implicit_variables(node):   # C#'s `value` in a setter
                ref_names = BodyNames(ref_names.variables | implicit, ref_names.types)
            after = node.parent.child_by_field_name("name") if position == "receiver" else None
            ref = RawBodyRef(
                self.spec.ref_text(node, self.spec.separator.join(
                    self.spec.body_name_text(_text(n, src)) for n in parts)),
                position,
                [(_line(n), _utf16_col(n, src)) for n in parts], via, ref_scope, rm,
                ref_names, list(around), [self.spec.arity(n) for n in parts],
                _text(self._parts(after)[0], src) if after is not None and after.id != node.id
                else None)
            if owner.id in detached:
                # the type is found once every file is read (_Builder): written in the
                # namespaces around the definition
                path = namespace_path(owner.parent) or ()
                scope.detached_refs.append((detached[owner.id][0], self.spec.separator.join(
                    p for p in [scope.namespace, *path] if p), ref))
            else:
                types_by_node[owner.id].body_refs.append(ref)

    def _enclosing(self, node: ts.Node, type_ids: set[int]) -> Optional[ts.Node]:
        """The function or the type whose body ``node`` stands in, or None."""
        cur = node.parent
        while cur is not None:
            if cur.id in type_ids or self.spec.is_opaque(cur):
                return cur
            cur = cur.parent
        return None

    def _dotted(self, node: ts.Node) -> bool:
        """Whether a receiver is a dotted name: every node of it one of
        LanguageSpec.receiver_part_nodes (no call in `new Foo(x).m`), type arguments
        aside (`Repo<int>.Make()`)."""
        return node.type in self.spec.receiver_part_nodes and all(
            self._dotted(c) for c in node.named_children
            if not (c.is_extra or c.type in self.spec.type_argument_nodes))

    def _parts(self, node: ts.Node) -> list[ts.Node]:
        """The identifiers of a dotted name, without the annotations, type arguments and
        comments inside it (`Outer<T>.Inner`, `java.lang.@A String`)."""
        if node.named_child_count == 0:
            return [node]
        out: list[ts.Node] = []
        for c in node.named_children:
            if not (c.is_extra or c.type in self.spec.annotation_nodes
                    or c.type in self.spec.type_argument_nodes):
                out += self._parts(c)
        return out

    def _qualify(self, node, name, types_by_node, namespaces, scope) -> Optional[str]:
        """Qualified name for a declaration that is not a type (aliases)."""
        sep = self.spec.separator
        parts: list[str] = []
        cur = node.parent
        while cur is not None:
            if cur.id in types_by_node:
                return types_by_node[cur.id].qualified_name + sep + name
            if cur.id in namespaces:
                parts.insert(0, namespaces[cur.id])
            elif self.spec.is_opaque(cur):
                return None
            cur = cur.parent
        ns = sep.join(p for p in [scope.namespace, *parts] if p)
        return f"{ns}{sep}{name}" if ns else name

    def _member(self, caps, src, scope, types_by_node, members_by_node, seen_members) -> None:
        spec = self.spec
        kind, node = _root(caps, "member.")
        owner, static_scope = self._owner(spec.ownership_start(caps, node), types_by_node)
        if owner is None:
            return
        name_node = _first(caps, "name")
        type_node = _first(caps, "type")
        type_ref = (spec.normalize_type(spec.type_text(type_node, _text(type_node, src), src))
                    if type_node is not None else None)
        name = _text(name_node, src) if name_node is not None else None
        if (d := _first(caps, "declarator")) is not None:
            dname, suffix, is_function = spec.declarator(d, src)
            name = dname or name
            if type_ref is not None and suffix:
                type_ref += suffix
            if is_function and kind == "field":
                kind = "method"
            elif not is_function and kind != "field":
                return  # a method pattern matched a non-function declarator
        if not name:
            return
        if kind == "method" and type_node is None and name == owner.name:
            kind = "constructor"
        name = spec.member_name(kind, name)
        if not name:
            return

        key = (node.id, name)
        if key in seen_members:  # several patterns matched one declaration
            existing = seen_members[key]
            if existing.member.type_ref is None:
                existing.member.type_ref = type_ref
            if (recv := _first(caps, "receiver")) is not None and existing.member.receiver is None:
                existing.member.receiver = spec.normalize_type(_text(recv, src))
            if _first(caps, "body") is not None and not existing.has_body:
                existing.has_body = True
                existing.member.abstract = spec.is_abstract(
                    owner.kind, existing.member.kind, existing.member.modifiers, True)
            existing.flags |= set(caps)
            return

        mods, annos = self._modifiers(caps.get("modifiers", []), node, src)
        has_body = _first(caps, "body") is not None
        marker = _first(caps, "abstract")
        member = Member(
            name=name,
            kind=kind,
            visibility=spec.visibility(owner.kind, kind, mods, name, node),
            type_ref=type_ref,
            static=static_scope or spec.is_static(owner.kind, kind, mods),
            abstract=spec.is_abstract(owner.kind, kind, mods, has_body,
                                      _text(marker, src) if marker is not None else None),
            modifiers=mods,
            annotations=annos,
            line=_line(node),
            receiver=(spec.normalize_type(_text(_first(caps, "receiver"), src))
                      if _first(caps, "receiver") is not None else None),
        )
        value = _first(caps, "value")
        rm = RawMember(member, has_body=has_body, flags=set(caps),
                       value=_text(value, src) if value is not None else None, scope=scope,
                       at=name_node.start_byte if name_node is not None else node.start_byte)

        # the same field declared twice (partial classes, self.x in several places)
        if kind in ("field", "property"):
            for other in owner.members:
                if other.member.name == name and other.member.kind == kind:
                    if other.member.type_ref is None:
                        other.member.type_ref = type_ref
                    seen_members[key] = other
                    return
        owner.members.append(rm)
        seen_members[key] = rm
        members_by_node.setdefault(node.id, []).append(rm)


MAX_ERROR_SPANS = 20  # per file; the rest are summarised in one diagnostic


_CLASS_HEAD = re.compile(rb"\b(?:class|struct)\s+(?:[A-Za-z_]\w*\s+)*?([A-Za-z_]\w*)\s*(?:final\s*)?(?::(?!:)|\{)")


def _error_spans(root: ts.Node) -> list[tuple[int, int]]:
    """Line spans of every ERROR/MISSING node, outermost only, merged when they
    touch, so a reader can tell which declarations of a file are trustworthy."""
    spans: list[tuple[int, int]] = []
    stack = [root]
    while stack:
        node = stack.pop()
        if node.is_error or node.is_missing:
            spans.append((node.start_point[0] + 1, node.end_point[0] + 1))
        elif node.has_error:
            stack.extend(reversed(node.children))
    spans.sort()
    merged: list[tuple[int, int]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged
