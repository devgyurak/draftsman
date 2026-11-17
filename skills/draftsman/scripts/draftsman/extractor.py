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

from .langs import FileScope, Import, LanguageSpec
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


@dataclass
class RawFile:
    path: str
    scope: FileScope
    types: list[RawType] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)


@lru_cache(maxsize=None)
def _load(spec_name: str, grammar: str) -> tuple[ts.Parser, ts.Query]:
    language = tslp.get_language(grammar)
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
        if (n := _first(caps, "import")) is not None:
            return Import(_text(n, src), alias=alias, sep=sep)
        if (n := _first(caps, "import.wildcard")) is not None:
            text = _text(n, src).strip("'\"")
            target, inside, alts = self._module_target(text, rel)
            return Import(target or text, wildcard=True, external=target is None and not alts,
                          local=inside, ambiguous=alts, sep=sep,
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
        src = spec.preprocess(path.read_bytes())
        tree = self.parser.parse(src)
        mod_path = self._module_path(root, rel)
        project, build_imports = spec.project_imports(path, root)
        if root not in self._workspaces:
            self._workspaces[root] = spec.workspace_packages(root)
        self._packages = self._workspaces[root]
        scope = FileScope(file=rel, namespace=spec.file_namespace(mod_path), project=project)
        raw = RawFile(path=rel, scope=scope)
        if tree.root_node.has_error:
            spans = _error_spans(tree.root_node)
            for start, end in spans[:MAX_ERROR_SPANS]:
                raw.diagnostics.append(Diagnostic(
                    rel, start, "syntax error; declarations in these lines may be missing",
                    end_line=end))
            if len(spans) > MAX_ERROR_SPANS:
                raw.diagnostics.append(Diagnostic(
                    rel, spans[MAX_ERROR_SPANS][0],
                    f"{len(spans) - MAX_ERROR_SPANS} more syntax errors after this line",
                    end_line=spans[-1][1]))

        type_matches, member_matches, other = [], [], []
        namespaces: dict[int, str] = {}
        for _, caps in ts.QueryCursor(self.query).matches(tree.root_node):
            if _root(caps, "type."):
                type_matches.append(caps)
            elif _root(caps, "member."):
                member_matches.append(caps)
            elif (n := _first(caps, "namespace")) is not None:
                name = _first(caps, "namespace.name")
                if name is not None:
                    namespaces[n.id] = _text(name, src)
            else:
                other.append(caps)
        # parameters must be appended in source order
        other.sort(key=lambda c: min(n.start_byte for nodes in c.values() for n in nodes))

        for caps in other:
            if (n := _first(caps, "package")) is not None:
                if scope.namespace is None:
                    scope.namespace = _text(n, src)
            elif (n := _first(caps, "typevar")) is not None:
                scope.type_params.add(_text(n, src))
            elif any(k.startswith("import") for k in caps):
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
            name = _text(name_node, src)
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
        for caps in other:
            if (n := _first(caps, "param")) is not None:
                owner, _ = self._owner(n, callables, stops=types_by_node)
                if owner is None:
                    continue
                pname, ptype = _first(caps, "param.name"), _first(caps, "param.type")
                name = _text(pname, src) if pname is not None else ""
                tref = spec.normalize_type(_text(ptype, src)) if ptype is not None else None
                if (d := _first(caps, "param.declarator")) is not None:
                    dname, suffix, _ = spec.declarator(d, src)
                    name = dname or name
                    tref = (tref or "") + suffix if tref else tref
                if tref is not None and _first(caps, "param.varargs") is not None:
                    tref += "..."
                owner.member.params.append(Param(name, tref))
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
                q = self._qualify(n, _text(n, src), types_by_node, namespaces, scope)
                if q is not None:
                    scope.aliases.add(q)
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

        # what the build imports into every file (implicit usings), after the file's own
        for ns, origin in build_imports:
            scope.imports.append(Import(ns, wildcard=True, sep=spec.separator, project_wide=True,
                                        origin=origin))

        for rt in raw.types:
            spec.finalize_type(rt)
        return raw

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
        type_ref = spec.normalize_type(_text(type_node, src)) if type_node is not None else None
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

        key = (node.id, name)
        if key in seen_members:  # several patterns matched one declaration
            existing = seen_members[key]
            if existing.member.type_ref is None:
                existing.member.type_ref = type_ref
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
        )
        value = _first(caps, "value")
        rm = RawMember(member, has_body=has_body, flags=set(caps),
                       value=_text(value, src) if value is not None else None, scope=scope)

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
