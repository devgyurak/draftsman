"""Raw declarations -> IR: name resolution and relation building.

Every relation produced here comes from a written type reference: a
supertype clause, a field type, or a method/constructor signature. Names
that cannot be tied to a project type, a builtin, or an explicitly imported
external type end up in ``IR.unresolved`` for Claude to judge.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Optional

from .extractor import RawBodyRef, RawFile, RawMember, RawType
from .langs import LANGUAGES, FileScope, Import, Unseen, spec_for_path
from .model import IR, External, Location, Relation, Type, Unresolved
from .typeref import Named, function_types, named_refs, parse_type, value_names
from .wrappers import Wrappers, combine

PROJECT, EXTERNAL, BUILTIN, TPARAM, ALIAS, UNRESOLVED = (
    "project", "external", "builtin", "tparam", "alias", "unresolved")

_KIND_STRENGTH = {"interface": 0, "annotation": 0, "class": 1}


@dataclass
class Resolution:
    status: str
    target: Optional[str] = None      # project type id or external qualified name
    hint: Optional[str] = None
    candidates: list[str] = field(default_factory=list)
    outside: bool = False   # unresolved, and only something outside the sources explains it


class Resolver:
    def __init__(self, types: dict[str, RawType], scopes: list[FileScope]):
        self.index = types
        self.inline_names: dict[str, str] = {}
        self.by_simple: dict[str, list[str]] = {}
        for qname, t in types.items():
            self.by_simple.setdefault(t.name, []).append(qname)
        self.namespaces = {t.namespace for t in types.values() if t.namespace}
        self.type_namespaces = set(self.namespaces)   # namespaces with a type declared in them
        self.unseen_types: dict[str, dict[str, list[Unseen]]] = {}   # name -> namespace -> places
        for s in scopes:
            for n, by_ns in s.unseen_types.items():
                for ns, places in by_ns.items():
                    self.unseen_types.setdefault(n, {}).setdefault(ns, []).extend(places)
        self.scopes_by_ns: dict[str, list[FileScope]] = {}
        self._uncertain_names: dict[tuple[int, str], bool] = {}   # _uncertain
        for s in scopes:
            if s.namespace:
                self.scopes_by_ns.setdefault(s.namespace, []).append(s)
                self.namespaces.add(s.namespace)
        self.aliases: set[str] = set().union(*(s.aliases for s in scopes)) if scopes else set()
        # namespace -> types the build generates outside the sources (LanguageSpec.build_types)
        self.build_types: dict[str, set[str]] = {}
        for s in scopes:
            for ns, names in s.build_types.items():
                self.build_types.setdefault(ns, set()).update(names)
        # a type or alias seen only inside its namespace block -> (file, first, last line)
        self.block_local: dict[str, tuple[str, int, int]] = {
            q: (s.file, *lines) for s in scopes for q, lines in s.block_local.items()}
        # alias -> (the type text it names, the file scope that text is resolved in)
        self.alias_targets: dict[str, tuple[str, FileScope]] = {
            a: (text, s) for s in scopes for a, text in s.alias_targets.items()}
        # C++ inline namespaces: acme::v1::Versioned is also acme::Versioned
        inline = set().union(*(s.inline_namespaces for s in scopes)) if scopes else set()
        if inline:
            for qname in types:
                parts = qname.split("::")
                short = "::".join(p for i, p in enumerate(parts)
                                  if "::".join(parts[:i + 1]) not in inline)
                if short != qname and short not in types:
                    self.inline_names.setdefault(short, qname)
        # what an import can name: a class or a type alias (`export type X = ...`)
        self._targets = set(self.index) | self.aliases
        self._supers_cache: dict[str, list[Resolution]] = {}
        self._resolving_supers: set[str] = set()
        self._suffix_cache: dict[tuple[str, bool], Optional[str]] = {}
        self._tail_cache: dict[str, Optional[str]] = {}
        self._field_cache: dict[tuple[str, str], bool] = {}
        self._ancestors_cache: dict[tuple[str, bool], list[str]] = {}

    # ------------------------------------------------------------ helpers

    def _type_params(self, rtype: RawType, member: Optional[RawMember]) -> set[str]:
        names = set(member.tparams) if member else set()
        names |= rtype.scope.type_params
        cur: Optional[RawType] = rtype
        while cur is not None:
            names.update(cur.generics)
            cur = self.index.get(cur.outer) if cur.outer else None
        return names

    def _by_suffix(self, path: str, pool, spec=None) -> Optional[str]:
        """The unique entry of ``pool`` that ends with ``path`` on a segment boundary; with
        LanguageSpec.suffix_skips_no_package, not one whose dropped part is a module or a
        package of the sources (whose __init__ is one)."""
        hits = [p for p in pool if p == path or p.endswith("." + path) or p.endswith("/" + path)]
        if spec is not None and spec.suffix_skips_no_package:
            hits = [p for p in hits if p == path
                    or p[:-len(path) - 1] not in self.scopes_by_ns]
        return hits[0] if len(hits) == 1 else None

    def _exports(self, module: str, name: str, spec, certain: bool = False) -> bool:
        """Whether a wildcard import of the project module ``module`` brings in ``name``."""
        scopes = self.scopes_by_ns.get(module) or self.scopes_by_ns.get(
            self._by_suffix(module, self.scopes_by_ns, spec) or "", [])
        return all(spec.star_exports(name, s, certain) for s in scopes)

    def _rebound(self, target: str) -> bool:
        """Whether the module of a project type binds its name (or an outer type's) more
        than once at its top, or the class body around it does (FileScope.rebound: `Foo`,
        `Foo.Cond`)."""
        t = self.index[target]
        names = [t.name]
        while t.outer and t.outer in self.index:
            t = self.index[t.outer]
            names.insert(0, t.name)
        sep = LANGUAGES[t.language].separator
        return any(sep.join(names[:k]) in t.scope.rebound for k in range(1, len(names) + 1))

    def lookup(self, path: str, spec, depth: int = 0, certain: bool = False) -> Optional[str]:
        """Project type or alias id for a fully written path, following re-exports;
        ``certain``: only through wildcard imports known to bring the name in."""
        if path in self._targets:
            return path
        if not spec.import_suffix_match:
            return None
        # only top-level answers are cached: a nested call can stop at the depth limit,
        # and caching that None would make results depend on file order
        if depth == 0 and (path, certain) in self._suffix_cache:
            return self._suffix_cache[(path, certain)]
        found = self._by_suffix(path, self._targets, spec)
        if found is None and depth < 4:
            # `from pkg import Name` where pkg/__init__ re-exports Name
            sep = spec.separator
            if sep in path:
                mod, name = path.rsplit(sep, 1)
                ns = mod if mod in self.scopes_by_ns else self._by_suffix(mod, self.scopes_by_ns,
                                                                           spec)
                scopes = self.scopes_by_ns.get(ns, []) if ns else []
                for scope in scopes:
                    for imp in scope.imports:
                        if not imp.wildcard and not imp.module and imp.local_name == name:
                            found = self.lookup(imp.path, spec, depth + 1, certain)
                            if found:
                                break
                    if found:
                        break
                # then `from pkg.sub import *` in pkg/__init__, followed by its exact path:
                # the same simple name can live in several packages (Field)
                for scope in scopes if not found else []:
                    for imp in scope.imports:
                        if imp.wildcard and not imp.external and \
                                self._exports(imp.path, name, spec, certain):
                            found = self.lookup(imp.path + sep + name, spec, depth + 1, certain)
                            if found:
                                break
                    if found:
                        break
        if depth == 0:
            self._suffix_cache[(path, certain)] = found
        return found

    def _reexported_from(self, path: str, spec, depth: int = 0) -> Optional[str]:
        """The package path a project module re-exports ``path`` from, if the re-export
        chain leaves the sources (`export { EventEmitter } from "events"`)."""
        sep = spec.separator
        if depth >= 4 or sep not in path:
            return None
        mod, name = path.rsplit(sep, 1)
        ns = mod if mod in self.scopes_by_ns else self._by_suffix(mod, self.scopes_by_ns, spec)
        for scope in self.scopes_by_ns.get(ns, []) if ns else []:
            for imp in scope.imports:
                if imp.wildcard or imp.module or imp.local_name != name:
                    continue
                if not imp.local:
                    return imp.path
                found = self._reexported_from(imp.path, spec, depth + 1)
                if found:
                    return found
        return None

    def _ambiguous_package(self, imp, rest: str, spec) -> Resolution:
        """Several workspace packages share the imported package name: never pick one."""
        sep = spec.separator
        cands = [f for m in imp.ambiguous if (f := self.lookup(m + sep + rest, spec))]
        package = imp.path if imp.module else imp.path.rsplit(sep, 1)[0]
        return Resolution(UNRESOLVED, candidates=cands or list(imp.ambiguous), hint=(
            f"package name {package} is declared by {len(imp.ambiguous)} package.json "
            f"files ({', '.join(imp.ambiguous)}); which one is meant is not known"))

    def _found(self, target: str) -> Resolution:
        return Resolution(ALIAS, target) if target in self.aliases else Resolution(PROJECT, target)

    def _not_found(self, path: str, spec) -> Resolution:
        """An import path that names no project type. External, unless it ends with
        exactly one project id: then the root is probably inside a package Python names
        differently (a namespace package without __init__.py), so leave it unresolved
        with that id as a candidate instead of drawing nothing silently."""
        if spec.import_suffix_match:
            if path not in self._tail_cache:
                tails = [t for t in self.index if path.endswith(spec.separator + t)]
                self._tail_cache[path] = tails[0] if len(tails) == 1 else None
            near = self._tail_cache[path]
            if near:
                return Resolution(UNRESOLVED, candidates=[near], hint=(
                    f"import path {path} ends with project type {near}; is the extraction "
                    "root inside a package without __init__.py? Extract from its top"))
        return Resolution(EXTERNAL, path)

    def _sees(self, rtype: RawType, qname: str) -> bool:
        """Whether a type or alias is in scope by its simple name where ``rtype`` is
        declared: one a namespace block keeps to itself (FileScope.block_local) only inside
        that block."""
        local = self.block_local.get(qname)
        return local is None or (rtype.location.file == local[0]
                                 and local[1] <= rtype.location.line <= local[2])

    def _namespace_chain(self, ns: Optional[str], sep: str, parents: bool,
                         floor: Optional[str] = None) -> list[str]:
        if not ns:
            return [""]
        if parents:
            parts = ns.split(sep)
            return [sep.join(parts[:i]) for i in range(len(parts), 0, -1)] + [""]
        # namespace blocks inside a file see the blocks around them, down to the
        # file's own namespace (TS `namespace X {}` sees the module)
        chain = [ns]
        while floor and ns != floor and ns.startswith(floor + sep):
            ns = ns.rsplit(sep, 1)[0]
            chain.append(ns)
        return chain

    def supertypes(self, rtype: RawType) -> list[Resolution]:
        """Resolutions of the supertype clauses of ``rtype`` (cached)."""
        qname = rtype.qualified_name
        cached = self._supers_cache.get(qname)
        if cached is not None:
            return cached
        if qname in self._resolving_supers:
            return []  # asked again while resolving them (cyclic declarations)
        self._resolving_supers.add(qname)
        try:
            cached = []
            for sup in rtype.supers:
                ref = parse_type(sup.text)
                if isinstance(ref, Named):
                    # a supertype clause cannot see the type's *own* inherited member
                    # types, but it does see those of its enclosing types
                    cached.append(self.resolve(ref.name, rtype, inherit=False, scope=sup.scope,
                                               arity=len(ref.args)))
                else:
                    cached.append(Resolution(UNRESOLVED))
        finally:
            self._resolving_supers.discard(qname)
        self._supers_cache[qname] = cached
        return cached

    def _member_type(self, owner: RawType, name: str, sep: str, inherit: bool,
                     seen: set[str]) -> Optional[str]:
        """A nested type or member type alias ``name`` declared in ``owner`` or inherited from
        its supertypes (`using CharacterMap = int[256];` in a base class)."""
        if owner.qualified_name in seen:
            return None
        seen.add(owner.qualified_name)
        cand = owner.qualified_name + sep + name
        if cand in self.index or cand in self.aliases:
            return cand
        if inherit:
            for sup in self.supertypes(owner):
                if sup.status == PROJECT:
                    found = self._member_type(self.index[sup.target], name, sep, inherit, seen)
                    if found:
                        return found
        return None

    def _external_supers(self, rtype: RawType) -> list[str]:
        """External ancestors of the type and its enclosing types, also those reached
        through project superclasses (B extends FrameLayout; A extends B)."""
        out: list[str] = []
        seen: set[str] = set()
        cur: Optional[RawType] = rtype
        while cur is not None:
            for target in self._external_ancestors(cur, seen):
                if target not in out:
                    out.append(target)
            cur = self.index.get(cur.outer) if cur.outer else None
        return out

    def _external_ancestors(self, rtype: RawType, seen: Optional[set[str]] = None,
                            starred: bool = False) -> list[str]:
        """External supertypes of the type, also those reached through project ones;
        ``starred`` adds what a supertype left unresolved may be through each wildcard
        import of its file (`HashMap` under `import java.util.*`)."""
        if seen is None:   # asked for the type alone: the same answer every time
            key = (rtype.qualified_name, starred)
            if key not in self._ancestors_cache:
                self._ancestors_cache[key] = self._external_ancestors(rtype, set(), starred)
            return self._ancestors_cache[key]
        out: list[str] = []
        stack = [rtype]
        while stack:
            t = stack.pop()
            if t.qualified_name in seen:
                continue
            seen.add(t.qualified_name)
            for written, sup in zip(t.supers, self.supertypes(t)):
                if sup.status == PROJECT:
                    stack.append(self.index[sup.target])
                    continue
                ref = parse_type(written.text)
                name = ref.name if isinstance(ref, Named) else ""
                for target in self._outside(name, sup, written.scope or t.scope, t, starred):
                    if target not in out:
                        out.append(target)
        return out

    def _outside(self, name: str, res: Resolution, scope: FileScope, rtype: RawType,
                 starred: bool) -> list[str]:
        """The external types a name resolved as ``res`` may be: its target, or with
        ``starred`` the type of its name in each wildcard import outside the sources."""
        if res.status in (EXTERNAL, BUILTIN):
            return [res.target] if res.target else []
        if not (starred and res.status == UNRESOLVED and res.outside and name):
            return []
        sep = LANGUAGES[rtype.language].separator
        return [i.path + sep + name for i in scope.imports
                if i.wildcard and (i.external or i.path not in self.namespaces)]

    def _inherited_external(self, supers: list[str], name: str, spec) -> Optional[str]:
        """The nested type ``name`` one of the external ``supers`` passes on, as far as the
        language knows the library (LanguageSpec.inherited_type)."""
        return next((t for s in supers if (t := spec.inherited_type(s, name))), None)

    def _closed_namespace(self, name: str, chain: list, sep: str, spec) -> Optional[str]:
        """The project namespace a qualified name points into (`Poco::Data` for
        `Poco::Data::Missing`, also relative to the enclosing namespaces), for languages that
        check them (LanguageSpec.owns_namespace)."""
        parts = name.split(sep)[:-1]
        for i in range(len(parts), 0, -1):
            prefix = sep.join(parts[:i])
            for ns in chain:
                cand = f"{ns}{sep}{prefix}" if ns else prefix
                if cand in self.type_namespaces and spec.owns_namespace(cand):
                    return cand
        return None

    def _unseen(self, name: str, namespaces: list[str]) -> Optional[str]:
        """Where ``name`` may be declared out of the parser's sight, in the first of
        ``namespaces`` that has it (FileScope.unseen_types). Several places are all
        mentions, and at most one declares it: a file named after the name comes first
        (`XMLException.h`, not `SAXException.h` that passes it as a base), then the rest
        in file order."""
        by_ns = self.unseen_types.get(name, {})
        places = next((by_ns[ns] for ns in namespaces if ns in by_ns), None)
        if not places:
            return None
        places = sorted(places, key=lambda p: Path(p.file).stem != name)   # stable
        if len(places) == 1:
            (p,) = places
            if p.macro is None:
                return f"its declaration in {p.file}:{p.line}-{p.end_line} did not parse"
            return f"{p.macro}(...) at {p.file}:{p.line} may declare it"
        shown = ", ".join(
            f"{p.macro}(...) at {p.file}:{p.line}" if p.macro
            else f"a class head that did not parse at {p.file}:{p.line}-{p.end_line}"
            for p in places[:3])
        more = f" (+{len(places) - 3} more)" if len(places) > 3 else ""
        return f"mentioned by {shown}{more}; one of them may declare it"

    def _base_named(self, rtype: RawType, name: str, sep: str) -> Optional[Resolution]:
        """A base class of ``rtype`` (also through project bases) whose own name is
        ``name``: in C++ it is in the scope of its derived classes."""
        seen: set[str] = set()
        stack = [rtype]
        while stack:
            t = stack.pop()
            if t.qualified_name in seen:
                continue
            seen.add(t.qualified_name)
            for sup in self.supertypes(t):
                if not sup.target:
                    continue
                if sup.target.rsplit(sep, 1)[-1] == name and sup.status in (PROJECT, EXTERNAL):
                    return Resolution(sup.status, sup.target)
                if sup.status == PROJECT:
                    stack.append(self.index[sup.target])
        return None

    def _scope_supers(self, rtype: RawType, inherit: bool) -> list[str]:
        """External supertypes whose nested types are in scope where a name is written:
        those of the type and its enclosing types, or only the enclosing types' in the
        type's own supertype clause."""
        if inherit:
            return self._external_supers(rtype)
        outer = self.index.get(rtype.outer) if rtype.outer else None
        return self._external_supers(outer) if outer else []

    def _nested_path(self, target: str, rest: str, sep: str, inherit: bool,
                     spec=None) -> Optional[Resolution]:
        for part in rest.split(sep):
            if target not in self.index:
                # `NamespaceManager::NamespaceMap::const_iterator`: a member of what the
                # alias names, as `NamespaceMap::const_iterator` inside the class
                return Resolution(ALIAS)
            found = self._member_type(self.index[target], part, sep, inherit, set())
            if found is None and spec is not None and part in spec.static_scope_names:
                continue   # `X.Companion.Serializer`: the companion's types are X's
            target = found
            if target is None:
                return None
        return self._found(target)

    # ------------------------------------------------------------ resolve

    def resolve(self, name: str, rtype: RawType, member: Optional[RawMember] = None,
                inherit: bool = True, scope: Optional[FileScope] = None,
                arity: Optional[int] = None, strict: bool = False,
                nested: bool = True) -> Resolution:
        """What ``name`` written in ``rtype`` stands for. ``strict``: a name more than one
        wildcard import provides is unresolved, not the first one's. ``nested``: whether
        the nested types of ``rtype`` and the types around it are in scope (in a body,
        LanguageSpec.nested_types_in_bodies)."""
        spec = LANGUAGES[rtype.language]
        sep = spec.separator
        scope = scope or (member.scope if member and member.scope else None) or rtype.scope
        chain = self._namespace_chain(rtype.namespace, sep, spec.parent_namespace_lookup,
                                      scope.namespace)

        if name in self._type_params(rtype, member):
            return Resolution(TPARAM)

        if sep in name:
            if name in self.index:
                return Resolution(PROJECT, name)
            if name in self.inline_names:
                return Resolution(PROJECT, self.inline_names[name])
            if name in self.aliases:   # n::Legacy_t
                return Resolution(ALIAS, name)
            for ns in chain:  # partially qualified: pay::Receipt inside namespace shop
                if ns and ns + sep + name in self.index:
                    return Resolution(PROJECT, ns + sep + name)
                if ns and ns + sep + name in self.inline_names:
                    return Resolution(PROJECT, self.inline_names[ns + sep + name])
                if ns and ns + sep + name in self.aliases:
                    return Resolution(ALIAS, ns + sep + name)
            head, rest = name.split(sep, 1)
            for imp in scope.imports:  # module alias: pay.Receipt, models.OrderLine
                if not imp.wildcard and imp.module and imp.ambiguous and imp.local_name == head:
                    return self._ambiguous_package(imp, rest, spec)
                if not imp.wildcard and imp.local_name == head:
                    found = None if imp.external else self.lookup(imp.path + sep + rest, spec,
                                                                  certain=strict)
                    if found:
                        return self._found(found)
                    if imp.module:
                        return (Resolution(EXTERNAL, imp.path + sep + rest) if imp.external
                                else self._not_found(imp.path + sep + rest, spec))
            first = self.resolve(head, rtype, member, inherit, scope, strict=strict,
                                 nested=nested)
            if first.status == PROJECT:
                found = self._nested_path(first.target, rest, sep, inherit, spec)
                if found:
                    return found
                target = self.index[first.target]
                if target.kind == "enum" and any(
                        rm.member.name == rest for rm in target.members):
                    return Resolution(PROJECT, first.target)  # enum member as a type
                cands, unreachable = self._candidates(name, sep, rtype)
                hint = f"{first.target} has no nested type {rest}"
                if unreachable:
                    hint += "; " + _unreachable_hint(unreachable)
                return Resolution(UNRESOLVED, hint=hint, candidates=cands)
            if first.status == EXTERNAL and first.target:
                return self._not_found(first.target + sep + rest, spec)
            if first.status in (EXTERNAL, BUILTIN):
                return Resolution(EXTERNAL, (first.target or head) + sep + rest)
            if first.status == ALIAS:
                return Resolution(ALIAS)
            if first.status == TPARAM:   # `typename R::Ptr`: a member of whatever R is
                return Resolution(TPARAM)
            # a fully qualified name outside the project, when its head is a package
            # (com.foo.Bar, System.Text.Encoding); otherwise a type this file could not
            # find (`Outer.Inner` under a star import), which stays unresolved
            owner = self._closed_namespace(name, chain, sep, spec)
            prefix, last = name.rsplit(sep, 1)
            where = self._unseen(last, [f"{ns}{sep}{prefix}" if ns else prefix for ns in chain])
            if owner and where:
                # Poco::Data::DataException, declared by a macro the parser never saw:
                # the project's, not a library's
                return Resolution(UNRESOLVED, candidates=first.candidates, hint=(
                    f"the project's namespace {owner} declares no type {last} the parser "
                    f"saw; {where}"))
            heads = {i.path.split(sep, 1)[0] for i in scope.imports}
            heads |= {ns.split(sep, 1)[0] for ns in self.namespaces}
            if scope.namespace:
                heads.add(scope.namespace.split(sep, 1)[0])
            if spec.is_package_head(head, heads):
                return Resolution(EXTERNAL, name)
            return Resolution(UNRESOLVED, hint=first.hint, candidates=first.candidates,
                              outside=first.outside)

        # nested types of this type and its enclosing types, including inherited ones
        cur: Optional[RawType] = rtype
        while cur is not None:
            inherited = spec.inherited_member_types and (inherit or cur is not rtype)
            found = spec.nested_types_in_scope and nested and self._member_type(
                cur, name, sep, inherited, set())
            if found:
                return self._found(found)
            if spec.base_names_in_scope and cur.name == name and cur.kind != "alias":
                return Resolution(PROJECT, cur.qualified_name)   # a class's own name first
            if inherited and spec.base_names_in_scope:
                base = self._base_named(cur, name, sep)
                if base is not None:   # `CodeGenerator::Properties` in a CodeGenerator subclass
                    return base
            if inherited:   # `Entry` in a HashMap subclass is Map.Entry, not the package's
                outside = self._inherited_external(
                    self._external_ancestors(cur, starred=True), name, spec)
                if outside:
                    return Resolution(EXTERNAL, outside)
            cur = self.index.get(cur.outer) if cur.outer else None

        def in_namespaces() -> Optional[Resolution]:
            for ns in chain:
                cand = ns + sep + name if ns else name
                if not self._sees(rtype, cand):
                    pass
                elif cand in self.index:
                    return Resolution(PROJECT, cand)
                elif cand in self.inline_names:
                    return Resolution(PROJECT, self.inline_names[cand])
                elif cand in self.aliases:
                    return Resolution(ALIAS, cand)  # a type alias: drawn through to its target
                elif name in self.build_types.get(ns, ()):
                    return Resolution(EXTERNAL, cand)   # generated by the build (gRPC)
                if (found := self._block_import(name, ns, scope, spec, strict)) is not None:
                    return found
            return None

        if spec.namespaces_before_imports and (found := in_namespaces()):
            return found
        for imp in scope.imports:
            if not imp.wildcard and not imp.module and imp.local_name == name \
                    and imp.block is None:
                if imp.ambiguous:
                    return self._ambiguous_package(imp, imp.path.rsplit(sep, 1)[-1], spec)
                if not imp.external:
                    found = self.lookup(imp.path, spec, certain=strict)
                    if found:
                        return self._found(found)
                    outside = self._reexported_from(imp.path, spec)
                    if outside:
                        return Resolution(EXTERNAL, outside)
                    if imp.local:
                        # a relative or workspace-package import points into the sources
                        return Resolution(UNRESOLVED, hint=(
                            f"imported from inside the sources (a relative path or a workspace "
                            f"package), but {imp.path} is no class or type alias there "
                            "(a value, or a re-export not followed?)"))
                    return self._not_found(imp.path, spec)
                return Resolution(EXTERNAL, imp.path)

        if not spec.namespaces_before_imports and (found := in_namespaces()):
            return found

        external_wildcards: list[Import] = []
        shared_wildcards: list[Import] = []   # declared in the project too, but not this name
        provided: list[str] = []
        for imp in scope.imports:
            if imp.wildcard and imp.block is None:
                found = None if imp.external or not self._exports(imp.path, name, spec, strict) \
                    else self.lookup(imp.path + sep + name, spec, certain=strict)
                if found and not strict:
                    return self._found(found)
                if found:
                    provided.append(found)
                    continue
                for ns in chain:  # C#/C++: `using Orders;` relative to the namespace
                    if ns and f"{ns}{sep}{imp.path}{sep}{name}" in self.index:
                        return Resolution(PROJECT, f"{ns}{sep}{imp.path}{sep}{name}")
                if imp.external or (imp.path not in self.namespaces
                                    and imp.path not in self.index):
                    external_wildcards.append(imp)
                elif imp.path not in self.index:
                    # eShopOnWeb declares an extension class in Microsoft.AspNetCore.Mvc;
                    # the rest of that namespace is still ASP.NET
                    shared_wildcards.append(imp)
        if provided:
            hits = list(dict.fromkeys(provided))
            if len(hits) == 1:
                return self._found(hits[0])
            return Resolution(UNRESOLVED, candidates=hits,
                              hint=f"{len(hits)} wildcard imports provide the name")

        library = spec.library_type(name, {i.path for i in scope.imports if i.wildcard}, arity,
                                    lambda: self._scope_supers(rtype, inherit))
        if library:
            return Resolution(EXTERNAL, library)
        if spec.is_builtin(name):
            return Resolution(BUILTIN, spec.builtin_id(name))
        # a default import is certain only when no star import of an outside package
        # could provide the same name
        default = spec.default_import(name)
        if default and not external_wildcards:
            return Resolution(EXTERNAL, default)

        hints = []
        candidates = external_wildcards + shared_wildcards
        # the file's own imports first, as a reader sees them: every package outside the
        # sources by name, then those the project declares too (a library may share one)
        # by count, as they rarely are the source
        outside = list(dict.fromkeys(i.path for i in external_wildcards if not i.project_wide))
        shared = list(dict.fromkeys(i.path for i in shared_wildcards
                                    if not i.project_wide and i.path not in outside))
        own = outside + shared
        if outside:
            hint = "may come from wildcard import " + ", ".join(f"{w}{sep}*" for w in outside)
            if len(shared) == 1:
                hint += f"; or from {shared[0]}{sep}*, a package the project also declares"
            elif shared:
                hint += f"; or from one of {len(shared)} packages the project also declares"
            hints.append(hint)
        elif shared:
            shown = ", ".join(f"{w}{sep}*" for w in shared[:3])
            more = f" (+{len(shared) - 3} more)" if len(shared) > 3 else ""
            also = "a package" if len(shared) == 1 else "packages"
            hints.append(f"may come from wildcard import {shown}{more} ({also} the project "
                         "also declares)")
        # project-wide ones by where they come from, not by example: any one of them may
        # be the source, and naming two at random misleads
        origins: dict[str, list[str]] = {}
        for i in candidates:
            if i.project_wide and i.path not in own:
                paths = origins.setdefault(i.origin or "project-wide imports", [])
                if i.path not in paths:
                    paths.append(i.path)
        if origins:
            parts = []
            for origin, paths in origins.items():
                if origin == "global using":   # written in the sources: name them
                    names = ", ".join(f"{p}{sep}*" for p in paths[:3])
                    parts.append(f"{len(paths)} global using{'s' if len(paths) > 1 else ''} "
                                 f"({names}{', ...' if len(paths) > 3 else ''})")
                else:
                    parts.append(f"{origin} ({len(paths)} namespace{'s' if len(paths) > 1 else ''})")
            hints.append("may come from a project-wide wildcard import: " + ", ".join(parts))
        if default:
            hints.append(f"may be the default import {default}")
        ext = self._scope_supers(rtype, inherit)
        if ext:
            hints.append("may be a nested type inherited from " + ", ".join(ext))
        outside = bool(hints)   # what explains it so far is all outside the sources
        cands, unreachable = self._candidates(name, sep, rtype)
        if unreachable:
            hints.append(_unreachable_hint(unreachable))
        # `XMLException` in Poco::XML, where POCO_DECLARE_EXCEPTION(..., XMLException, ...)
        # stands: maybe the project's, maybe not (`DEFINE_GUARD(HANDLE, CloseHandle)`)
        where = self._unseen(name, chain) if sep not in name else None
        if where:
            hints.append(where)
        return Resolution(UNRESOLVED, hint="; ".join(hints) or None,
                          candidates=cands, outside=outside)

    def body_type(self, name: str, rtype: RawType, ref: RawBodyRef) -> Optional[str]:
        """The project type a name in type position stands for where ``ref`` is written,
        or None: also when a type of the name is declared anywhere in the member."""
        res = self._in_body(name, rtype, ref, 0)
        if res.status == ALIAS and res.target:
            return self._alias_type(res.target, name, rtype, ref)
        return res.target if res.status == PROJECT else None

    def body_receiver(self, ref: RawBodyRef, rtype: RawType) -> Optional[tuple[str, int]]:
        """(project type, how many parts of the name it covers) a receiver starts with
        (`Util.Helper` in `Util.Helper.run()`, `Util` in `Util.VALUE.trim()`), or None. A
        variable wins over a type, and a type over a package (JLS 6.5.2): a head that may be
        a variable draws nothing, and after a type a field of the name ends it."""
        spec = LANGUAGES[rtype.language]
        sep = spec.separator
        parts = ref.text.split(sep)
        # a type the member declares (a local class) is no package either
        if parts[0] in ref.names.types or self._is_variable(parts[0], rtype, ref):
            return None
        res = self._in_body(parts[0], rtype, ref, 0)
        if res.status == ALIAS and res.target:
            aliased = self._alias_type(res.target, parts[0], rtype, ref)
            res = Resolution(PROJECT, aliased) if aliased else Resolution(UNRESOLVED)
        if res.status == EXTERNAL and res.target in self.scopes_by_ns:
            res = Resolution(UNRESOLVED)   # Python's `from p import mod`: a module, no type
        if res.status == PROJECT:
            target, n = res.target, 1
        elif res.status != UNRESOLVED or len(parts) == 1:
            return None
        elif spec.receiver_package_heads:
            if parts[0] in self.index:
                # a type of the default package is no package head, and only the default
                # package sees that type, where it is resolved already
                return None
            # a package: the first prefix that is a project type (`io.netty.Foo.X`)
            n = next((k for k in range(2, len(parts) + 1)
                      if sep.join(parts[:k]) in self.index), 0)
            if not n:
                return None
            target = sep.join(parts[:n])
        else:
            # a module or namespace the scope binds the head to (`ns.Foo.m()`): the first
            # prefix it resolves to a project type
            if not self._binds(parts[0], rtype, ref):
                return None
            found = next(((k, r.target) for k in range(2, len(parts) + 1)
                          if (r := self._in_body(sep.join(parts[:k]), rtype, ref, 0)).status
                          == PROJECT), None)
            if found is None:
                return None
            n, target = found
            if n > 2 and spec.submodules_need_import and not self._imports_module(
                    parts[:n - 1], ref.scope, spec):
                return None   # `models.base.ModelBase`: a submodule the file did not import
        if self.index[target].kind in spec.type_only_kinds:
            return None   # the value of the name is another declaration's
        while n < len(parts) and not self._has_field(self.index[target], parts[n]):
            nested = self._member_type(self.index[target], parts[n], sep,
                                       spec.inherited_member_types, set())
            if nested is None or self.index[nested].kind in spec.type_only_kinds or (
                    spec.rebinding_hides and self._rebound(nested)):
                break   # `Foo.Cond` where Foo's body binds Cond twice: Foo alone
            target, n = nested, n + 1
        return target, n

    def _alias_type(self, alias: str, name: str, rtype: RawType,
                    ref: RawBodyRef) -> Optional[str]:
        """The project type an alias the file declares names as a whole (C#'s `using O =
        Shop.Order;`, not `using Orders = List<Order>;`; LanguageSpec.body_aliases), or
        None; also None for one in code a build may leave out, and where a namespace
        around declares a type of the name, which C# looks at before the file's aliases."""
        spec = LANGUAGES[rtype.language]
        entry = self.alias_targets.get(alias)
        if not spec.body_aliases or entry is None or entry[1].file != ref.scope.file \
                or alias in entry[1].conditional_aliases or not isinstance(
                    written := parse_type(entry[0]), Named) or written.args:
            return None
        chain = self._namespace_chain(rtype.namespace, spec.separator,
                                      spec.parent_namespace_lookup, ref.scope.namespace)
        if any((ns + spec.separator + name if ns else name) in self.index for ns in chain):
            return None
        res = self.resolve(written.name, rtype, None, scope=entry[1], strict=True)
        return res.target if res.status == PROJECT else None

    def _binds(self, head: str, rtype: RawType, ref: RawBodyRef) -> bool:
        """Whether ``head`` is a name the file imports or a namespace around ``rtype``."""
        spec = LANGUAGES[rtype.language]
        if any(imp.local_name == head for imp in ref.scope.imports if not imp.wildcard):
            return True
        if spec.module_imports_bind_heads and any(
                imp.module and imp.path.split(spec.separator, 1)[0] == head
                for imp in ref.scope.imports):
            return True
        chain = self._namespace_chain(rtype.namespace, spec.separator,
                                      spec.parent_namespace_lookup, ref.scope.namespace)
        return any((ns + spec.separator + head if ns else head) in self.namespaces
                   for ns in chain)

    def _head_module(self, head: str, scope: FileScope, spec) -> Optional[tuple[str, list[str]]]:
        """(the module a dotted name's head names, the modules the file's module imports
        load through it), or None: `from p import sub` and `import p.sub as sub` name p.sub
        and load nothing through it, `import p.sub.near` names p and loads p.sub.near."""
        sep = spec.separator
        named = {imp.path for imp in scope.imports if not imp.wildcard
                 and (imp.aliased or not imp.module) and imp.local_name == head}
        if named:
            return (named.pop(), []) if len(named) == 1 else None
        loaded = [imp.path for imp in scope.imports if imp.module and not imp.aliased
                  and imp.path.split(sep, 1)[0] == head]
        return (head, loaded) if spec.module_imports_bind_heads and loaded else None

    def _imports_module(self, parts: list[str], scope: FileScope, spec) -> bool:
        """Whether a dotted name's parts reach a module as attributes, one part after the
        other (`models.base` after `from django.db import models`): from the module the head
        names, a part is a submodule that a module import of the file loads through that
        head (`import p.sub.near` binds `p`, with `p.sub` and `p.sub.near` on it; not the
        `sub` of `from p import sub`, after which pyright finds no `sub.near`, nor `p` after
        `import p.sub.near as n`), or one its package imports from by a relative import
        (`from . import near`, `from .near import Near` in `p/sub/__init__.py`; not `from
        p.sub.near import Near`, which pyright and ty do not take to bind it there)."""
        sep = spec.separator
        got = self._head_module(parts[0], scope, spec)
        if got is None:
            return False
        module, loaded = got
        for part in parts[1:]:
            sub = module + sep + part
            if not (any(p == sub or p.startswith(sub + sep) for p in loaded) or any(
                    imp.local and (imp.path == sub or imp.path.startswith(sub + sep))
                    for s in self._module_scopes(module, spec) for imp in s.imports)):
                return False
            module = sub
        return True

    def _around(self, rtype: RawType, ref: RawBodyRef, depth: int):
        """For each anonymous or local class around ``ref`` from ``depth`` levels out,
        innermost first: (its project supertypes, the types outside the sources it
        inherits from, as far as they are known)."""
        for i, supers in enumerate(ref.classes[depth:], depth + 1):
            project, outside = [], []
            for sup in supers:
                written = parse_type(sup)
                if not isinstance(written, Named):
                    continue
                owner = self._in_body(written.name, rtype, ref, i)
                outside += self._outside(written.name, owner, ref.scope, rtype, True)
                if owner.status == PROJECT:
                    project.append(self.index[owner.target])
                    outside += self._external_ancestors(self.index[owner.target], starred=True)
            yield project, outside

    def _in_body(self, name: str, rtype: RawType, ref: RawBodyRef, depth: int) -> Resolution:
        """``name`` as seen from the anonymous or local class ``depth`` levels out from
        ``ref`` (ref.classes): the nested types each inherits come first, then the member's
        and the named type's scopes."""
        spec = LANGUAGES[rtype.language]
        sep = spec.separator
        head, _, rest = name.partition(sep)
        if head in ref.names.types:
            return Resolution(UNRESOLVED)
        for project, outside in self._around(rtype, ref, depth):
            for owner in project:
                found = self._member_type(owner, head, sep, True, set())
                if found:
                    return (self._nested_path(found, rest, sep, True) or Resolution(UNRESOLVED)) \
                        if rest else self._found(found)
            found = self._inherited_external(outside, head, spec)
            if found:   # `State` in `new Thread() { ... }`
                return Resolution(EXTERNAL, found + sep + rest if rest else found)
        res = self.resolve(name, rtype, ref.member, scope=ref.scope, strict=True,
                           nested=spec.nested_types_in_bodies)
        if res.status == PROJECT and spec.rebinding_hides and (
                self._rebound(res.target) or self._uncertain_path(name, ref.scope, spec)
                or sep not in name and any(
                    found != res.target for found in self._star_provides(name, ref.scope, spec))):
            # `try: from x import Foo` / `except: class Foo`; `class Foo` beside a star
            # import that brings in another Foo, or beside one that may bring in anything
            # (from outside the sources), here or in a module the name comes through
            return Resolution(UNRESOLVED)
        return res

    def _block_import(self, name: str, ns: str, scope: FileScope, spec,
                      strict: bool) -> Optional[Resolution]:
        """``name`` through the imports of the namespace block ``ns`` (Import.block), or
        None: an alias of the name, else the one project type its wildcard imports provide
        (two: unresolved)."""
        sep = spec.separator
        block = [imp for imp in scope.imports if imp.block is not None and imp.block == ns]
        for imp in block:
            if not imp.wildcard and imp.local_name == name:
                found = None if imp.external else self.lookup(imp.path, spec, certain=strict)
                return self._found(found) if found else Resolution(EXTERNAL, imp.path)
        hits = list(dict.fromkeys(
            found for imp in block if imp.wildcard and not imp.external
            and self._exports(imp.path, name, spec, strict)
            and (found := self.lookup(imp.path + sep + name, spec, certain=strict))))
        if len(hits) > 1:
            return Resolution(UNRESOLVED, candidates=hits,
                              hint=f"{len(hits)} wildcard imports provide the name")
        return self._found(hits[0]) if hits else None

    def _module_scopes(self, module: str, spec) -> list[FileScope]:
        return self.scopes_by_ns.get(module) or self.scopes_by_ns.get(
            self._by_suffix(module, self.scopes_by_ns, spec) or "", [])

    def _uncertain_path(self, name: str, scope: FileScope, spec) -> bool:
        """_uncertain for a dotted name: its head in the file, then each part in the module
        the parts before it name (`relay.Button` after `from p import relay`)."""
        sep = spec.separator
        parts = name.split(sep)
        if self._uncertain(scope, parts[0], spec):
            return True
        got = self._head_module(parts[0], scope, spec)
        if got is None:
            return False
        module = got[0]
        for part in parts[1:]:
            scopes = self._module_scopes(module, spec)
            if not scopes:
                return False
            if any(self._uncertain(s, part, spec) for s in scopes):
                return True
            module = module + sep + part
        return False

    def _uncertain(self, scope: FileScope, name: str, spec) -> bool:
        """Whether a file's ``name`` may be another class than the one it resolves to: bound
        by a wildcard import of a module outside the sources (`from tkinter import *`),
        whose names are not known, bound to two things at the top of the file (`from .a
        import Foo` and `from .b import Foo`, two star imports that bring in two, an import
        and a class, a project class and `from tkinter import Foo` or `import tkinter as
        Foo`), or bound as a variable there (FileScope.variables); in the file, or
        in a project module the file takes the name from, by
        its name or by a wildcard import that brings it in (`from q.gui import *`, `gui.py`
        importing tkinter's *; `from q.dup import Foo`)."""
        key = (id(scope), name)
        if key in self._uncertain_names:
            return self._uncertain_names[key]
        self._uncertain_names[key] = False   # a cycle of imports adds nothing
        sep = spec.separator
        found = False
        if name in scope.variables:   # `if x: Foo = None` in the module the name comes from
            self._uncertain_names[key] = True
            return True
        own = f"{scope.namespace}{sep}{name}" if scope.namespace else name
        targets = {own} if own in self.index and self.index[own].location.file == scope.file \
            else set()
        for imp in scope.imports:
            if imp.wildcard:
                scopes = [] if imp.external else self._module_scopes(imp.path, spec)
                brings = [s for s in scopes if spec.star_exports(name, s)]
                found = not scopes or any(self._uncertain(s, name, spec) for s in brings)
                if brings and (target := self.lookup(imp.path + sep + name, spec, certain=True)):
                    targets.add(target)
            elif not imp.module and imp.local_name == name:
                module, _, original = imp.path.rpartition(sep)
                found = any(self._uncertain(s, original, spec)
                            for s in self._module_scopes(module, spec))
                # what is no project class (`from tkinter import Button`, a function) is
                # still another binding of the name
                targets.add(self.lookup(imp.path, spec) or "?" + imp.path)
            elif imp.module and (imp.local_name == name if imp.aliased
                                 else imp.path.split(sep, 1)[0] == name):
                targets.add("?" + imp.path)   # `import tkinter as Button`
            # not in a scope made for one name (an import in a function before the file's,
            # a class body's imports before the file's): there the first import wins
            if found or len(targets) > 1 and any(
                    f is scope for f in self.scopes_by_ns.get(scope.namespace, ())):
                found = True
                break
        self._uncertain_names[key] = found
        return found

    def _star_provides(self, name: str, scope: FileScope, spec) -> list[str]:
        """The project types the file's wildcard imports are known to bring in as ``name``."""
        sep = spec.separator
        return [found for imp in scope.imports if imp.wildcard and not imp.external
                and self._exports(imp.path, name, spec, True)
                and (found := self.lookup(imp.path + sep + name, spec, certain=True))]

    def _is_variable(self, name: str, rtype: RawType, ref: RawBodyRef) -> bool:
        """Whether a variable of the name may be in scope where ``ref`` is written: one the
        member declares, a field of a class around it (inherited ones too, from the JDK as
        far as its table tells), or one a static import brings in. Fields of other types
        outside the sources are not known (lang-notes.md)."""
        if name in ref.names.variables:
            return True
        spec = LANGUAGES[rtype.language]
        if spec.initializers_in_class_scope and ref.member is not None \
                and ref.member.member.kind in ("field", "enum_constant") and (
                    any(rm.member.name == name for rm in rtype.members)
                    or self._member_type(rtype, name, spec.separator, False, set())):
            return True   # in the class body: its own names first (`value = Foo`)
        if not spec.fields_in_scope:
            # an enum's constants are names in its own bodies (`B = A` in an enum)
            return any(rm.member.kind == "enum_constant" and spec.body_name(rm.member.name) == name
                       for rm in rtype.members)
        for project, outside in self._around(rtype, ref, 0):
            if any(self._has_field(t, name) for t in project) or \
                    any(spec.inherited_field(o, name) for o in outside):
                return True
        cur: Optional[RawType] = rtype
        while cur is not None:
            if self._has_field(cur, name):
                return True
            cur = self.index.get(cur.outer) if cur.outer else None
        sep = spec.separator
        for imp in ref.scope.imports:
            if not imp.static:
                continue
            if imp.wildcard:   # `import static a.B.*`: B's static fields
                owner = self.index.get(imp.path)
                if owner is not None and self._has_field(owner, name) or \
                        owner is None and spec.inherited_field(imp.path, name, static=True):
                    return True
            elif imp.local_name == name:
                # `import static a.B.N` brings in every static member named N: a type only
                # when B is the project's, with no field N
                owner = self.index.get(imp.path.rsplit(sep, 1)[0])
                if owner is None or self._has_field(owner, name) or \
                        self._member_type(owner, name, sep, True, set()) is None:
                    return True
        return False

    def _has_field(self, rtype: RawType, name: str) -> bool:
        """Whether the project type has a field ``name``, also an enum constant, a record
        component or one of its RawType.body_fields, its own or inherited (through the JDK
        table for JDK supertypes)."""
        key = (rtype.qualified_name, name)
        if key not in self._field_cache:
            self._field_cache[key] = False   # a cycle of supertypes has no field
            spec = LANGUAGES[rtype.language]
            self._field_cache[key] = any(
                rm.member.name == name and rm.member.kind in ("field", "enum_constant", "property")
                for rm in rtype.members) or name in rtype.body_fields or any(
                self._has_field(self.index[s.target], name)
                for s in self.supertypes(rtype) if s.status == PROJECT) or any(
                spec.inherited_field(o, name)
                for o in self._external_ancestors(rtype, starred=True))
        return self._field_cache[key]

    def _candidates(self, name: str, sep: str, rtype: RawType) -> tuple[list[str], list[str]]:
        """Project types with the simple name: (those the reference could mean, nested
        types it cannot reach). A nested type is reachable by its simple name only from
        inside its outer type; every other way in (imports, inheritance, aliases) is
        resolved before candidates are looked for."""
        enclosing = set()
        cur: Optional[RawType] = rtype
        while cur is not None:
            enclosing.add(cur.qualified_name)
            cur = self.index.get(cur.outer) if cur.outer else None
        cands, unreachable = [], []
        for c in sorted(self.by_simple.get(name.rsplit(sep, 1)[-1], [])):
            outer = self.index[c].outer
            (cands if outer is None or outer in enclosing else unreachable).append(c)
        return cands, unreachable


def _unreachable_hint(nested: list[str]) -> str:
    shown = ", ".join(nested[:3]) + (f" (+{len(nested) - 3} more)" if len(nested) > 3 else "")
    return (f"project nested type{'s' if len(nested) > 1 else ''} of the name, out of scope "
            f"here: {shown}")


def _share_project_imports(scopes: list[FileScope]) -> None:
    """A `global using` in one file is an import of every file of its project; a file
    linked into several projects gets the ones they all have."""
    key = lambda i: (i.path, i.alias, i.wildcard)   # noqa: E731
    by_project: dict[str, list[FileScope]] = {}
    for s in scopes:
        if s.project is not None and ";" not in s.project:
            by_project.setdefault(s.project, []).append(s)
    shared: dict[str, list[Import]] = {
        p: [i for s in members for i in s.imports if i.project_wide and i.origin == "global using"]
        for p, members in by_project.items()}
    for s in scopes:
        if s.project is None:
            continue
        projects = s.project.split(";")
        lists = [shared.get(p, []) for p in projects]
        common = set.intersection(*({key(i) for i in lst} for lst in lists)) if lists else set()
        have = {key(i) for i in s.imports}
        for imp in lists[0] if lists else []:
            if key(imp) in common and key(imp) not in have:
                s.imports.append(imp)
                have.add(key(imp))


def _signature(rm: RawMember) -> tuple:
    m = rm.member
    return (m.kind, m.receiver, m.name, tuple(p.type_ref for p in m.params))


class _Builder:
    def __init__(self, root: str, files: list[RawFile], wrappers: Wrappers):
        self.ir = IR(root=root, files=len(files))
        self.wrappers = wrappers
        self.types: dict[str, RawType] = {}
        for f in files:
            self.ir.diagnostics.extend(f.diagnostics)
            for t in f.types:
                self._add(t)
        _share_project_imports([f.scope for f in files])
        self.resolver = Resolver(self.types, [f.scope for f in files])
        self.externals: dict[str, External] = {}
        self.unresolved: dict[tuple, Unresolved] = {}
        self.relations: list[Relation] = []
        # (file, line, column, from, to) of each name a body relation is drawn from
        self.body_uses: list[tuple[str, int, int, str, str]] = []
        # types some build declares that the parser never saw (LanguageSpec.left_out_types)
        self.left_out: set[str] = set().union(*(f.scope.left_out_types for f in files))
        # type id -> the build projects declaring a type of it: parts of a type in two
        # projects are two types (two projects' `partial class Program`), and so is one
        # a project declares implicitly (LanguageSpec.implicit_types)
        self.projects: dict[str, set] = {}
        for f in files:
            for t in f.types:
                self.projects.setdefault(t.qualified_name, set()).add(f.scope.project)
            for t in f.scope.implicit_types:
                self.projects.setdefault(t, set()).add(f.scope.project)
        self._alias_cache: dict[str, tuple[list, list]] = {}

    def _add(self, t: RawType) -> None:
        existing = self.types.get(t.qualified_name)
        if existing is None:
            t.arities = {len(t.generics)}
            self.types[t.qualified_name] = t
            return
        existing.arities.add(len(t.generics))
        # partial declarations (C# partial, TS declaration merging, Kotlin expect/actual)
        # merge by name; a class declaration wins over an interface of the same name,
        # and a Kotlin `expect` declaration is where the type is said to live
        here = lambda rm: rm.member.file or existing.location.file   # noqa: E731
        expect = "expect" in t.modifiers and "expect" not in existing.modifiers
        if expect or _KIND_STRENGTH.get(t.kind, 2) > _KIND_STRENGTH.get(existing.kind, 2):
            for rm in existing.members:
                rm.member.file = here(rm)
            if _KIND_STRENGTH.get(t.kind, 2) > _KIND_STRENGTH.get(existing.kind, 2):
                existing.kind = t.kind
            existing.location = t.location
            for rm in existing.members:
                if rm.member.file == existing.location.file:
                    rm.member.file = None
        names = {(m.member.name, m.member.kind) for m in existing.members}
        # the same method declared again in another file is one method (an expect and
        # its actuals, a partial method and its implementation). Same-file look-alikes
        # are overloads and stay.
        signatures: dict[tuple, int] = {}
        for i, rm in enumerate(existing.members):
            if rm.member.kind in ("method", "constructor"):
                signatures.setdefault(_signature(rm), i)
        for rm in t.members:
            if rm.member.kind in ("field", "property") and \
                    (rm.member.name, rm.member.kind) in names:
                continue
            rm.member.file = None if t.location.file == existing.location.file else t.location.file
            if rm.member.kind in ("method", "constructor"):
                i = signatures.get(_signature(rm))
                if i is not None and here(existing.members[i]) != t.location.file:
                    if "expect" in t.modifiers:   # keep the expect declaration's member
                        existing.members[i] = rm
                    continue
            existing.members.append(rm)
        existing.supers.extend(t.supers)
        existing.annotation_refs.extend(t.annotation_refs)
        existing.body_refs.extend(t.body_refs)
        existing.body_fields |= t.body_fields
        existing.conditional |= t.conditional
        existing.generics += [g for g in t.generics if g not in existing.generics]
        for m in t.modifiers:
            if m not in existing.modifiers:
                existing.modifiers.append(m)
        for a in t.annotations:
            if a not in existing.annotations:
                existing.annotations.append(a)

    def _is_project(self, rtype: RawType, member: Optional[RawMember]):
        return lambda name: self.resolver.resolve(name, rtype, member).status == PROJECT

    def _unresolved(self, rtype: RawType, raw: str, res: Resolution, loc: Location,
                    via: Optional[str]) -> None:
        key = (rtype.qualified_name, raw)
        if key not in self.unresolved:
            reason = "ambiguous" if res.candidates else "outside" if res.outside else "unexplained"
            self.unresolved[key] = Unresolved(
                rtype.qualified_name, raw, loc, via=via,
                candidates=res.candidates, hint=res.hint, reason=reason)

    # ------------------------------------------------------------------

    def build(self) -> IR:
        for rtype in self.types.values():
            self._supers(rtype)
            self._annotations(rtype)
            self._body(rtype)
            for rm in rtype.members:
                m = rm.member
                if m.kind in ("field", "property") and m.static:
                    # class-level constants/singletons are not part of an instance's
                    # structure; record them as a dependency instead
                    self._dependencies(rtype, rm)
                elif m.kind in ("field", "property"):
                    self._association(rtype, rm)
                elif m.kind in ("method", "constructor"):
                    self._dependencies(rtype, rm)

        self.ir.types = sorted((self._to_type(t) for t in self.types.values()),
                               key=lambda t: t.id)
        self.ir.languages = sorted({t.language for t in self.ir.types})
        self.ir.relations = self._finalize_relations()
        self.ir.externals = sorted(self.externals.values(), key=lambda e: e.id)
        self.ir.unresolved = sorted(self.unresolved.values(),
                                    key=lambda u: (u.from_, u.raw_type))
        self.ir.diagnostics.sort(key=lambda d: (d.file, d.line))
        return self.ir

    def _to_type(self, t: RawType) -> Type:
        return Type(
            id=t.qualified_name,
            name=t.name,
            qualified_name=t.qualified_name,
            kind=t.kind,
            language=t.language,
            location=t.location,
            namespace=t.namespace,
            outer=t.outer,
            modifiers=t.modifiers,
            annotations=t.annotations,
            generics=t.generics,
            members=[rm.member for rm in t.members],
        )

    def _supers(self, rtype: RawType) -> None:
        spec = LANGUAGES[rtype.language]
        for sup, res in zip(rtype.supers, self.resolver.supertypes(rtype)):
            ref = parse_type(sup.text)
            if not isinstance(ref, Named):
                continue
            loc = Location(sup.scope.file if sup.scope else rtype.location.file, sup.line)
            if res.status == ALIAS and res.target:   # `class X : AliasOfBase()`
                leaves, _ = self._expand_alias(res.target)
                if len(leaves) == 1:
                    res = Resolution(PROJECT, leaves[0][0])
            if res.status == PROJECT:
                if res.target == rtype.qualified_name:
                    continue
                kind = sup.kind
                if kind == "inherits":
                    target_kind = self.types[res.target].kind
                    if rtype.kind == "interface" or target_kind != "interface":
                        kind = "extends"
                    else:
                        kind = "implements"
                self.relations.append(Relation(rtype.qualified_name, res.target, kind, loc))
            elif res.status in (EXTERNAL, BUILTIN):
                ext_id = res.target or ref.name
                name = ext_id.rsplit("::", 1)[-1].rsplit("/", 1)[-1].rsplit(".", 1)[-1]
                self.externals.setdefault(ext_id, External(ext_id, name))
                kind = spec.external_super_kind(rtype.kind, sup.kind, name)
                self.relations.append(Relation(rtype.qualified_name, ext_id, kind, loc))
            elif res.status == UNRESOLVED:
                self._unresolved(rtype, ref.name, res, loc, via=None)

    def _annotations(self, rtype: RawType) -> None:
        """A dependency on the annotation type when it is the project's, and on the project
        types its arguments name (`@Import(Hints.class)`), `via` the annotation. Framework
        annotations stay names only; a class literal that names nothing known is
        unresolved, as in a signature, but a name that may be a value is never."""
        spec = LANGUAGES[rtype.language]
        sep = spec.separator
        for ann in rtype.annotation_refs:
            via = "@" + ann.name
            loc = Location(ann.scope.file, ann.line)
            maybe = None
            for name in spec.annotation_type_names(ann.name):
                res = self.resolver.resolve(name, rtype, None, scope=ann.scope)
                if res.status in (PROJECT, ALIAS):
                    self._annotation_target(rtype, res, via, loc)
                    break
                # the project declares an annotation of the name that this one may be;
                # a class of the name that is no annotation is not (eShopOnWeb's static
                # class `Route` is not ASP.NET's `[Route]`)
                cands = [c for c in res.candidates if self.types[c].kind == "annotation"
                         or self.types[c].name.endswith("Attribute")]
                if res.status == UNRESOLVED and cands and maybe is None:
                    maybe = (name, Resolution(UNRESOLVED, hint=res.hint, candidates=cands,
                                              outside=res.outside))
            else:
                if maybe is not None:
                    self._unresolved(rtype, maybe[0], maybe[1], loc, via=via)
            for text, is_type, line in ann.args:
                loc = Location(ann.scope.file, line)
                if is_type:
                    ref = parse_type(spec.normalize_type(text))
                    for name, arity in named_refs(ref, lambda n: self.resolver.resolve(
                            n, rtype, None, scope=ann.scope).status == PROJECT):
                        if self.wrappers.is_wrapper(name):
                            continue
                        res = self.resolver.resolve(name, rtype, None, scope=ann.scope,
                                                    arity=arity)
                        self._annotation_target(rtype, res, via, loc)
                        if res.status == UNRESOLVED:
                            self._unresolved(rtype, name, res, loc, via=via)
                    continue
                # `Kind.A`: the type Kind, or a constant of one; `Model`: a class or a value
                name = text.replace(" ", "")
                while name:
                    res = self.resolver.resolve(name, rtype, None, scope=ann.scope)
                    if res.status in (PROJECT, ALIAS):
                        self._annotation_target(rtype, res, via, loc)
                        break
                    name = name.rsplit(sep, 1)[0] if sep in name else ""

    def _body(self, rtype: RawType) -> None:
        """A dependency, `evidence` "body", on the project type each name in a body stands
        for; a name that may mean something else draws nothing, and is never unresolved."""
        for ref in rtype.body_refs:
            if ref.position == "type":
                target, n = self.resolver.body_type(ref.text, rtype, ref), len(ref.places)
            else:
                target, n = self.resolver.body_receiver(ref, rtype) or (None, 0)
            if target is None or target == rtype.qualified_name:
                continue
            # a type declared in code a build may leave out, or a name some build declares
            # a type of where the parser saw none: no one type for every build
            sep = LANGUAGES[rtype.language].separator
            if self.types[target].conditional or any(
                    p in self.left_out or p in ref.scope.left_out_names
                    for p in ref.text.split(sep)[:n]):
                continue
            if len(self.projects.get(target, ())) > 1:
                continue   # one id, a type in each of several projects
            if any(imp.conditional for imp in ref.scope.imports) and target != self._without(
                    ref, rtype, n):
                continue   # through an import some build leaves out
            if not self._visible(target, ref.scope.project, LANGUAGES[rtype.language]):
                continue   # declared in a project the file's project does not reference
            if ref.arities and ref.arities[n - 1] is not None \
                    and ref.arities[n - 1] not in self.types[target].arities:
                continue   # `Repo<int>` is no Repo: another type of the name, further out
            line, col = ref.places[n - 1]
            self.body_uses.append((ref.scope.file, line, col, rtype.qualified_name, target))
            self.relations.append(Relation(rtype.qualified_name, target, "dependency",
                                           Location(ref.scope.file, line), via=ref.via,
                                           evidence="body"))

    def _without(self, ref: RawBodyRef, rtype: RawType, n: int) -> Optional[str]:
        """What ``ref`` resolves to (its first ``n`` parts) without the file's conditional
        imports."""
        bare = replace(ref, scope=replace(ref.scope, imports=[
            i for i in ref.scope.imports if not i.conditional]))
        if ref.position == "type":
            return self.resolver.body_type(ref.text, rtype, bare)
        got = self.resolver.body_receiver(bare, rtype)
        return got[0] if got and got[1] == n else None

    def _visible(self, target: str, project: Optional[str], spec) -> bool:
        """Whether a type is declared in a project every project of a file sees
        (LanguageSpec.project_references; a file linked into several has them all)."""
        declared = {p for ps in self.projects.get(target, ()) if ps for p in ps.split(";")}
        if not declared or any(spec.project_references(p) is None for p in declared):
            return True   # declared outside any project file: no one knows who sees it
        for p in (project.split(";") if project else ()):
            seen = spec.project_references(p)
            if seen is not None and not declared & seen:
                return False
        return True

    def _annotation_target(self, rtype: RawType, res: Resolution, via: str,
                           loc: Location) -> None:
        targets = [res.target] if res.status == PROJECT else \
            self._expand_alias(res.target)[1] if res.status == ALIAS and res.target else []
        for target in targets:
            if target != rtype.qualified_name:
                self.relations.append(Relation(
                    rtype.qualified_name, target, "dependency", loc, via=via))

    def _association(self, rtype: RawType, rm: RawMember) -> None:
        m = rm.member
        ref = parse_type(m.type_ref)
        loc = Location(m.file or rtype.location.file, m.line)
        cpp = rtype.language == "cpp"
        others: list = []   # container arguments that are not the element: Map<K, V>'s K
        for leaf in self.wrappers.leaves(ref, self._is_project(rtype, rm), track_ownership=cpp,
                                         dropped=others):
            res = self.resolver.resolve(leaf.name, rtype, rm, arity=len(leaf.args))
            if res.status == PROJECT:
                self.relations.append(Relation(
                    rtype.qualified_name, res.target, "association", loc,
                    multiplicity=leaf.multiplicity, ownership=leaf.ownership, via=m.name))
            elif res.status == ALIAS and res.target:   # `Pt p;` with `using Pt = ...Point;`
                leaves, names = self._expand_alias(res.target)
                for target, mult, own in leaves:
                    if target != rtype.qualified_name:
                        self.relations.append(Relation(
                            rtype.qualified_name, target, "association", loc,
                            multiplicity=combine(leaf.multiplicity, mult),
                            ownership=own or leaf.ownership, via=m.name))
                for target in names:
                    if target != rtype.qualified_name and target not in {t for t, _, _ in leaves}:
                        self.relations.append(Relation(
                            rtype.qualified_name, target, "dependency", loc, via=m.name))
            elif res.status == UNRESOLVED and not leaf.value:   # `typeof fn`: a value
                self._unresolved(rtype, leaf.name, res, loc, via=m.name)
            # the arguments of a generic that is not a container (Repository<User>,
            # Type<Factory>, Observable<Order>) are written in the source too: the field
            # depends on them, as a signature does
            for arg in leaf.args:
                self._depend_on(rtype, rm, arg, loc)
        # a function-typed field (`config: HttpClientConfig.() -> Unit`, also inside a
        # container) holds no instance of those types; it depends on them, as on the
        # container arguments that are not its elements
        for other in [*function_types(ref), *others]:
            self._depend_on(rtype, rm, other, loc)

    def _dependencies(self, rtype: RawType, rm: RawMember) -> None:
        m = rm.member
        loc = Location(m.file or rtype.location.file, m.line)
        for text in [m.type_ref, m.receiver] + [p.type_ref for p in m.params] + rm.throws:
            self._depend_on(rtype, rm, parse_type(text), loc)

    def _depend_on(self, rtype: RawType, rm: RawMember, ref, loc: Location) -> None:
        """A dependency on every project type named in ``ref``, containers seen through."""
        m = rm.member
        values = value_names(ref)   # `typeof setTimeout`: a value, not a missing type
        is_project = self._is_project(rtype, rm)
        for name, arity in named_refs(ref, is_project):
            if self.wrappers.is_wrapper(name) and not is_project(name):
                continue
            res = self.resolver.resolve(name, rtype, rm, arity=arity)
            targets = [res.target] if res.status == PROJECT else \
                self._expand_alias(res.target)[1] if res.status == ALIAS and res.target else []
            for target in targets:
                if target != rtype.qualified_name:
                    self.relations.append(Relation(
                        rtype.qualified_name, target, "dependency", loc, via=m.name))
            if res.status == UNRESOLVED and name not in values:
                self._unresolved(rtype, name, res, loc, via=m.name)

    def _expand_alias(self, alias: str, depth: int = 0) -> tuple[list, list]:
        """What a type alias names, resolved where the alias is declared:
        ([(project type, multiplicity, ownership)] it points at as a field type would,
        [every project type it mentions]). Aliases of aliases are followed."""
        if alias in self._alias_cache:
            return self._alias_cache[alias]
        entry = self.resolver.alias_targets.get(alias)
        if entry is None or depth > 4:
            return [], []
        self._alias_cache[alias] = ([], [])   # a cycle expands to nothing
        text, scope = entry
        spec = spec_for_path(scope.file)
        sep = spec.separator
        owner = alias.rsplit(sep, 1)[0] if sep in alias else None
        ctx = RawType(alias, alias.rsplit(sep, 1)[-1], "alias", Location(scope.file, 0), scope,
                      spec.name, namespace=self.types[owner].namespace if owner in self.types
                      else owner or scope.namespace,
                      outer=owner if owner in self.types else None)
        ref = parse_type(text)
        leaves: list = []
        for leaf in self.wrappers.leaves(ref, self._is_project(ctx, None),
                                         track_ownership=spec.name == "cpp"):
            res = self.resolver.resolve(leaf.name, ctx, None, arity=len(leaf.args))
            if res.status == PROJECT:
                leaves.append((res.target, leaf.multiplicity, leaf.ownership))
            elif res.status == ALIAS and res.target:
                for target, mult, own in self._expand_alias(res.target, depth + 1)[0]:
                    leaves.append((target, combine(leaf.multiplicity, mult), own or leaf.ownership))
        names: list = []
        for name, arity in named_refs(ref, self._is_project(ctx, None)):
            res = self.resolver.resolve(name, ctx, None, arity=arity)
            if res.status == PROJECT:
                names.append(res.target)
            elif res.status == ALIAS and res.target and res.target != alias:
                names += self._expand_alias(res.target, depth + 1)[1]
        self._alias_cache[alias] = (leaves, list(dict.fromkeys(names)))
        return self._alias_cache[alias]

    def _finalize_relations(self) -> list[Relation]:
        # keep every fact: one relation per (from, to, kind, via). Collapsing
        # dependencies per pair is a presentation decision made by the renderer.
        unique = {r.key(): r for r in reversed(self.relations)}
        return sorted(unique.values(), key=lambda r: (r.from_, r.to, r.kind, r.via or ""))


def build_ir(root: str, files: list[RawFile], wrappers: Wrappers) -> IR:
    return _Builder(root, files, wrappers).build()


__all__ = ["build_ir", "Resolver", "Resolution", "Import"]
