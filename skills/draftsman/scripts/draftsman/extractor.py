"""Source file -> raw declarations, driven by queries/<language>.scm.

The query protocol (capture names) is documented in
references/query-protocol.md. This module is language-neutral: everything
language-specific lives in the query file and the LanguageSpec.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
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
    position: str      # "type": only a type can stand there; "receiver": a variable can too
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
    members: list[RawMember] = field(default_factory=list)
    supers: list[RawSuper] = field(default_factory=list)
    annotation_refs: list[RawAnnotation] = field(default_factory=list)
    body_refs: list[RawBodyRef] = field(default_factory=list)


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
def _load(spec_name: str, grammar: str) -> tuple[ts.Parser, ts.Query]:
    try:
        language = tslp.get_language(grammar)
    except Exception as e:   # the pack's DownloadError and its kin
        raise GrammarUnavailable(f"the {grammar} grammar could not be loaded ({e})") from e
    parser = ts.Parser(language)
    source = (QUERY_DIR / f"{spec_name}.scm").read_text(encoding="utf-8")
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
        self.parser, self.query = _load(spec.query or spec.name, spec.grammar)
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
                          sep=sep)
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
        tree = self.parser.parse(src)
        mod_path = self._module_path(root, rel)
        project, build_imports = spec.project_imports(path, root)
        if root not in self._workspaces:
            self._workspaces[root] = spec.workspace_packages(root)
        self._packages = self._workspaces[root]
        scope = FileScope(file=rel, namespace=spec.file_namespace(mod_path), project=project)
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

        for caps in other:
            if (n := _first(caps, "package")) is not None:
                if scope.namespace is None:
                    scope.namespace = _text(n, src)
            elif (n := _first(caps, "typevar")) is not None:
                scope.type_params.add(_text(n, src))
            elif any(k.startswith("import") for k in caps):
                if not spec.is_import(next(n for k, ns in caps.items() if k.startswith("import")
                                           for n in ns)):
                    continue
                imp = self._import(caps, src, mod_path)
                if imp is not None:
                    scope.imports.append(imp)

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
            cur = node.parent
            while cur is not None:
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
            )
            return entry["raw"]

        types_by_node: dict[int, RawType] = {}
        for nid, entry in sorted(type_nodes.items(), key=lambda kv: kv[1]["node"].start_byte):
            rt = build(entry)
            if rt is not None:
                types_by_node[nid] = rt
                raw.types.append(rt)

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
                    if target:
                        scope.alias_targets[q] = spec.normalize_type(target)
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
        self._body_refs(bodies, src, scope, types_by_node, members_by_node)

        # what the build imports into every file (implicit usings), after the file's own
        for ns, origin in build_imports:
            scope.imports.append(Import(ns, wildcard=True, sep=spec.separator, project_wide=True,
                                        origin=origin))

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

    def _body_refs(self, matches, src, scope, types_by_node, members_by_node) -> None:
        """Names written in bodies, each with what may hide it there (query-protocol.md)."""
        regions: set[int] = set()
        inits: dict[int, str] = {}           # initializer block -> its `via`
        classes: dict[int, list[str]] = {}   # body of an anonymous or local class -> supertypes
        refs, declared = [], []
        unread: set[int] = set()   # type nodes that are no name of the scope
        blind: set[int] = set()    # class bodies whose inherited members are not known
        for caps in matches:
            if (n := _first(caps, "body.init")) is not None:
                # only a named type's own: a block in an anonymous class is in a body already
                if self._owner(n, types_by_node)[0] is not None:
                    regions.add(n.id)
                    if (name := _first(caps, "body.init.name")) is not None:
                        inits[n.id] = _text(name, src)   # a compact constructor
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
                    position = cap[len("body.ref."):]
                    if position == "receiver" and any(c.type == "super" for c in n.parent.children):
                        continue   # `X.super.m()`: X is in type position, captured as such
                    refs.append((position, n))
                elif cap == "body.region":
                    regions.add(n.id)
                elif cap == "body.var":
                    declared.append((n, "variables"))
                elif cap == "body.type":
                    declared.append((n, "types"))
                elif cap == "body.unread":
                    unread.add(n.id)
                elif cap == "body.blind":
                    blind.add(n.id)
        if not refs:
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
                if cur.id in inits or members_by_node.get(cur.id):
                    anchors[cur.id] = cur
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
                if cur.id in types_by_node:
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
            members = members_by_node[a.id]
            # several declarators: the one whose name comes last before the name
            rm = max((m for m in members if m.at <= start), key=lambda m: m.at, default=members[0])
            return a.id, rm.member.name, rm

        for node, kind in declared:
            if (a := anchor_of(node.parent)) is not None:
                key = place(a, node.start_byte)[0]
                getattr(names.setdefault(key, BodyNames()), kind).add(_text(node, src))
        # `T` in `<T extends Foo>` is declared there; `Inner` in `o.new Inner()` is o's
        not_refs = {n.id for n, _ in declared} | unread
        # a receiver is a dotted name, not an expression (`this.x.m()`, `a[0].B.m()`)
        refs = [(p, n) for p, n in refs if n.id not in not_refs and (
            p != "receiver" or all(c.type in self.spec.receiver_part_nodes for c in self._parts(n)))]
        whole = {n.id for _, n in refs}
        for position, node in sorted(refs, key=lambda r: r[1].start_byte):
            if node.parent.id in whole:
                continue   # `Foo` in `p.Foo`: the whole name is recorded
            owner, in_body, around = up(node.parent)
            a = anchor_of(node.parent)
            if owner is None or a is None or not in_body:
                continue
            key, via, rm = place(a, node.start_byte)
            parts = self._parts(node)
            types_by_node[owner.id].body_refs.append(RawBodyRef(
                ".".join(_text(n, src) for n in parts), position,
                [(_line(n), _utf16_col(n, src)) for n in parts], via, scope, rm,
                names.setdefault(key, BodyNames()), list(around)))

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
