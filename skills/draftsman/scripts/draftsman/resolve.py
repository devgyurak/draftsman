"""Raw declarations -> IR: name resolution and relation building.

Every relation produced here comes from a written type reference: a
supertype clause, a field type, or a method/constructor signature. Names
that cannot be tied to a project type, a builtin, or an explicitly imported
external type end up in ``IR.unresolved`` for Claude to judge.
"""

from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, Optional

from .extractor import BodyNames, RawBodyRef, RawFile, RawMember, RawType
from .langs import LANGUAGES, FileScope, Import, Unseen, spec_for_path
from .model import IR, External, Location, Member, Relation, Type, Unresolved
from .typeref import Named, Nullable, function_types, named_refs, parse_type, value_names
from .wrappers import _RANK, Wrappers, combine

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
    # a base clause unresolved where the language cannot tell what it is (C++: a type of an
    # `#if` branch, of a file not included): a base whose members are not known
    opaque: bool = False


class Resolver:
    def __init__(self, types: dict[str, RawType], scopes: list[FileScope]):
        self.index = types
        self.inline_names: dict[str, str] = {}
        self.by_simple: dict[str, list[str]] = {}
        for qname, t in types.items():
            self.by_simple.setdefault(t.name, []).append(qname)
        self.namespaces = {t.namespace for t in types.values() if t.namespace}
        # every namespace a block of the sources opens (LanguageSpec.values_hide_types)
        self.opened_namespaces: set[str] = {
            "::".join(n.split("::")[:k]) for s in scopes for n in s.declared_namespaces
            for k in range(1, n.count("::") + 2)}   # `namespace a::b {}` opens a too
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
        # methods that may make a call an instance one (FileScope.extension_methods)
        self.resolver_extensions: set[str] = set().union(*(s.extension_methods for s in scopes)) \
            if scopes else set()
        # language -> names of functions and properties declared at a file's top
        # (FileScope.top_functions): Kotlin's `val Money` is no name of Java code beside it
        self.top_functions: dict[str, set[str]] = {}
        self.top_values: dict[str, set[str]] = {}
        for s in scopes:
            if s.top_functions or s.top_values:
                lang = spec_for_path(s.file).name
                self.top_functions.setdefault(lang, set()).update(s.top_functions)
                self.top_values.setdefault(lang, set()).update(s.top_values)
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
        self.alias_tparams: dict[str, set[str]] = {
            a: ps for s in scopes for a, ps in s.alias_tparams.items()}
        # C#'s `using X = ...` is its file's, at the namespace it stands in (the compilation
        # unit's, also before `namespace A;`: the global namespace's): (file, namespace) ->
        # simple name -> alias (LanguageSpec.body_aliases)
        self.file_aliases: dict[tuple[str, str], dict[str, str]] = {}
        for s in scopes:
            if LANGUAGES[spec_for_path(s.file).name].body_aliases:
                for a in s.alias_targets:
                    block = s.alias_blocks.get(a, "")
                    self.file_aliases.setdefault((s.file, block), {})[a.rsplit(".", 1)[-1]] = a
        # a `global using X = ...` is every file's of its project, at the global namespace
        for s in scopes:
            for a in s.global_aliases:
                for t in scopes:
                    if t.project == s.project and t.file != s.file:
                        self.file_aliases.setdefault((t.file, ""), {}).setdefault(
                            a.rsplit(".", 1)[-1], a)
        # whether a project type is one the file's project sees (_Builder._visible: C#'s
        # project references and `internal`), set by the builder
        self.visible: Optional[Callable[[str, FileScope], bool]] = None
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
        # what a base clause stands for where a language looks it up as a body looks names
        # up (LanguageSpec.declared_like_bodies; _Builder._base_like_body): the bases a
        # relation is drawn to are the ones names are looked up in
        self.base_lookup: Optional[Callable[[RawType, Any, Resolution], Resolution]] = None
        self._opaque_cache: dict[str, Optional[tuple[str, Resolution]]] = {}
        self._suffix_cache: dict[tuple[str, bool], Optional[str]] = {}
        self._tail_cache: dict[str, Optional[str]] = {}
        self._field_cache: dict[tuple[str, str], bool] = {}
        self._ancestors_cache: dict[tuple[str, bool], list[str]] = {}
        self._namespace_cache: dict[str, bool] = {}
        self._package_cache: dict[tuple[str, Optional[str]], bool] = {}
        # LanguageSpec.file_local_bodies: an id -> the files declaring it file-local, and
        # the ids declared not so somewhere (_Builder fills them)
        self.local_files: dict[str, set[str]] = {}
        self._unscoped: Optional[dict[str, set[str]]] = None   # _enum_constant_around
        # (id, file) -> None, "skip" or "stop" (_Builder._unseen_from)
        self.unseen_from = None
        # (scope, file) -> the scope a body of the file looks names up in (_Builder._body_scope)
        self.body_scope = None
        self.shared_ids: set[str] = set()

    def _elsewhere(self, qname: str, file: Optional[str]) -> bool:
        """Whether ``qname`` is a type only files other than ``file`` declare, each
        file-local (LanguageSpec.file_local_bodies): no candidate there."""
        return file is not None and qname in self.local_files \
            and qname not in self.shared_ids and file not in self.local_files[qname]

    def detached_owner(self, written: str, namespace: str, scope: FileScope) -> Optional[str]:
        """The project type a member defined outside it names (`Foo` of `void Foo::bar()`
        written in ``namespace``), or None."""
        spec = spec_for_path(scope.file)
        sep = spec.separator
        ctx = RawType("", "", "detached", Location(scope.file, 0), scope, spec.name,
                      namespace=namespace or None)
        res = self.resolve(written, ctx, None, scope=scope)
        return res.target if res.status == PROJECT else None

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

    def _imports_function(self, path: str, sep: str) -> bool:
        """Whether ``path`` is a function a file of the sources declares at its top in that
        package (FileScope.top_functions), and no type: an import of it brings in no type."""
        if sep not in path:
            return False
        ns, last = path.rsplit(sep, 1)
        return any(last in s.top_functions for s in self.scopes_by_ns.get(ns, ()))

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

    def expect_class(self, res: Resolution) -> Resolution:
        """Kotlin's `actual typealias Charset = java.nio.charset.Charset` beside `expect
        class Charset` of the same id: in a declaration the name is the expect class, the
        compiler's answer in every compilation's terms (in a body's value position the
        alias's object is meant: `Charsets.UTF_8`)."""
        if res.status == ALIAS and res.target in self.index \
                and "expect" in self.index[res.target].modifiers:
            return Resolution(PROJECT, res.target)
        return res

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
                ref = _parse(sup.text, rtype.language)
                if isinstance(ref, Named):
                    # a supertype clause cannot see the type's *own* inherited member
                    # types, but it does see those of its enclosing types
                    res = self.expect_class(self.rooted(ref.name, sup.text, rtype) or self.resolve(
                        ref.name, rtype, inherit=False, scope=sup.scope, arity=len(ref.args)))
                    if res.status == PROJECT and self.rebinding(
                            ref.name, res.target, sup.scope or rtype.scope,
                            LANGUAGES[rtype.language], stars=False):
                        res = Resolution(UNRESOLVED, hint=_REBOUND.format(ref.name, res.target))
                    if self.base_lookup is not None:
                        res = self.base_lookup(rtype, sup, res)
                    cached.append(res)
                else:
                    cached.append(Resolution(UNRESOLVED))
        finally:
            self._resolving_supers.discard(qname)
        self._supers_cache[qname] = cached
        return cached

    def _member_type(self, owner: RawType, name: str, sep: str, inherit: bool,
                     seen: set[str], body: bool = False,
                     from_ns: Optional[str] = None) -> Optional[str]:
        """A nested type or member type alias ``name`` declared in ``owner`` or inherited from
        its supertypes (`using CharacterMap = int[256];` in a base class). ``body``: for a
        name in a body, where C++ looks into no dependent base (`TBase<T>`) of ``owner``.
        ``from_ns``: the namespace of the type that inherits from ``owner``'s supertypes
        (``owner``'s own), which sees a base's package-private nested type in its own package
        only (Java); each step of a chain is its own (`a.Leaf extends b.Mid extends a.Base`:
        b.Mid does not inherit a.Base's, so neither does a.Leaf)."""
        if from_ns is None:
            from_ns = owner.namespace
        if owner.qualified_name in seen:
            return None
        seen.add(owner.qualified_name)
        cand = owner.qualified_name + sep + name
        if cand in self.index or cand in self.aliases:
            return cand
        if inherit:
            spec = LANGUAGES[owner.language]
            for sup in self._project_supers(owner, body):
                if sup.status == PROJECT:
                    if spec.class_nested_only and self.index[sup.target].kind == "interface":
                        continue   # Kotlin: an interface passes on no nested type
                    # (a base's own bases are known once the base is: `ViaPtr<int>`'s
                    # `TBase<T*>` is `TBase<int*>`)
                    found = self._member_type(self.index[sup.target], name, sep, inherit, seen)
                    # C#'s and Java's private nested type is no member of a subclass, nor
                    # Java's package-private one in another package, nor Kotlin's type
                    # nested in a superclass's companion object (folded into the class)
                    if found and (found not in self.index
                                  or spec.subtype_sees(self._access(found),
                                                       self.index[found].namespace == from_ns)
                                  and not (spec.class_nested_only
                                           and self.index[found].static_scope)):
                        return found
        return None

    def _access(self, qname: str) -> list[str]:
        """A nested type's modifiers, with `public` where the type it is declared in makes
        it so (a Java interface's or annotation's member types)."""
        t = self.index[qname]
        outer = self.index.get(t.outer) if t.outer else None
        if outer is not None and outer.kind in ("interface", "annotation") \
                and not any(m in ("public", "protected", "private") for m in t.modifiers):
            return [*t.modifiers, "public"]
        return t.modifiers

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
                ref = _parse(written.text, t.language)
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

    def _project_supers(self, rtype: RawType, body: bool) -> list[Resolution]:
        """The supertypes of ``rtype`` a name is looked up in; for a name in a body of
        ``rtype`` (or of a class it is around), C++'s written with the class's template
        parameters (`TBase<T>`) left out: looked into once the template is instantiated.
        A base's own bases are all looked into: they are known once the base is."""
        sups = self.supertypes(rtype)
        if not body or not LANGUAGES[rtype.language].values_hide_types:
            return sups
        return [s for w, s in zip(rtype.supers, sups) if not self._dependent_base(w.text, rtype)]

    def _enum_constant_around(self, name: str, rtype: RawType) -> Optional[int]:
        """Where a constant of an unscoped enum (C++'s `enum Status { Paid }`) named
        ``name`` is, nearest first: -1 for the classes around ``rtype`` and their project
        bases, else the index of the namespace in the chain around it; None if none is."""
        if self._unscoped is None:
            self._unscoped = {}
            for t in self.index.values():
                if t.kind == "enum" and not t.scoped:
                    key = t.outer or "ns:" + (t.namespace or "")
                    self._unscoped.setdefault(key, set()).update(
                        rm.member.name for rm in t.members if rm.member.kind == "enum_constant")
        seen: set[str] = set()
        stack = []   # (a type, whether a body is in it or in a class it is around)
        cur: Optional[RawType] = rtype
        while cur is not None:
            stack.append((cur, True))
            cur = self.index.get(cur.outer) if cur.outer else None
        while stack:
            t, around = stack.pop()
            if t.qualified_name in seen:
                continue
            seen.add(t.qualified_name)
            if name in self._unscoped.get(t.qualified_name, ()):
                return -1
            stack += [(self.index[s.target], False) for s in self._project_supers(t, around)
                      if s.status == PROJECT]
        spec = LANGUAGES[rtype.language]
        return next((i for i, ns in enumerate(self._namespace_chain(
            rtype.namespace, spec.separator, spec.parent_namespace_lookup))
            if name in self._unscoped.get("ns:" + ns, ())), None)

    def _type_depth(self, target: str, rtype: RawType) -> int:
        """Where a type found by its simple name from ``rtype`` is, as
        _enum_constant_around counts: -1 for a member of a class (found in the classes
        around), else its namespace's index in the chain around ``rtype`` (one the chain
        lacks, brought in by a `using`, counts as the farthest)."""
        spec = LANGUAGES[rtype.language]
        sep = spec.separator
        owner = target.rsplit(sep, 1)[0] if sep in target else ""
        if owner in self.index:
            return -1
        chain = self._namespace_chain(rtype.namespace, sep, spec.parent_namespace_lookup)
        return chain.index(owner) if owner in chain else len(chain)

    def _base_named(self, rtype: RawType, name: str, sep: str, body: bool = False
                    ) -> Optional[Resolution]:
        """A base class of ``rtype`` (also through project bases) whose own name is
        ``name``: in C++ it is in the scope of its derived classes."""
        seen: set[str] = set()
        stack = [rtype]
        while stack:
            t = stack.pop()
            if t.qualified_name in seen:
                continue
            seen.add(t.qualified_name)
            for sup in self._project_supers(t, body and t is rtype):
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
            if target not in self.index and spec is not None and target in self.aliases:
                # `MemTable::Table::Iterator` with `typedef SkipList<...> Table;`: the
                # members of the class (or template) the alias names
                target = self._alias_head_class(target, spec) or target
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

    def _in_types(self, name: str, rtype: RawType, inherit: bool, nested: bool,
                  spec, body: bool = False) -> Optional[Resolution]:
        """``name`` among the nested types of the type and its enclosing types, inherited
        ones too, or None."""
        sep = spec.separator
        cur: Optional[RawType] = rtype
        while cur is not None:
            hidden = cur.hidden_types.get(name)
            if hidden == "tparam":
                return Resolution(TPARAM)
            if hidden:   # a nested type ir.json does not record (a C# delegate)
                return Resolution(EXTERNAL, cur.qualified_name + sep + name)
            inherited = spec.inherited_member_types and (inherit or cur is not rtype)
            found = spec.nested_types_in_scope and nested and self._member_type(
                cur, name, sep, inherited, set(), body)
            if found:
                return self._found(found)
            if spec.base_names_in_scope and cur.name == name and cur.kind != "alias":
                return Resolution(PROJECT, cur.qualified_name)   # a class's own name first
            if inherited and spec.base_names_in_scope:
                base = self._base_named(cur, name, sep, body)
                if base is not None:   # `CodeGenerator::Properties` in a CodeGenerator subclass
                    return base
            if inherited:   # `Entry` in a HashMap subclass is Map.Entry, not the package's
                outside = self._inherited_external(
                    self._external_ancestors(cur, starred=True), name, spec)
                if outside:
                    return Resolution(EXTERNAL, outside)
            cur = self.index.get(cur.outer) if cur.outer else None
        return None

    def _namespace_exists(self, ns: str, spec) -> bool:
        """Whether ``ns`` is a namespace: one of the sources or one they are in (`App` of
        `App.Models`), or one the language's table knows."""
        found = self._namespace_cache.get(ns)
        if found is None:
            prefix = ns + spec.separator
            found = ns in self.namespaces or any(n.startswith(prefix) for n in self.namespaces) \
                or spec.outside_namespace_exists(ns)
            self._namespace_cache[ns] = found
        return found

    def _outside_around(self, ns: str, spec, scope: FileScope) -> bool:
        """Whether the namespace ``ns`` around the code is taken for one outside the sources
        the table does not know (LanguageSpec.enclosing_outside_hides): a package's the
        file's build project references (LanguageSpec.package_namespace)."""
        if not ns or not spec.enclosing_outside_hides:
            return False
        key = (ns, scope.project)
        found = self._package_cache.get(key)
        if found is None:
            found = spec.outside_namespace(ns) is None and spec.package_namespace(ns, scope.project)
            self._package_cache[key] = found
        return found

    def _qualified_head(self, head: str, rtype: RawType, member: Optional[RawMember],
                        inherit: bool, nested: bool, scope: FileScope, chain: list[str],
                        spec, strict: bool, head_arity: Optional[int] = None,
                        in_type: bool = True):
        """What the first part of a qualified name is, looked up as a simple name from the
        innermost scope out (LanguageSpec.qualified_heads_in_scope): "type" when a type of
        the name comes first, the namespace when one does (`App.Models` for `Models` in
        `namespace App.Web`), "outside" past a namespace _outside_around takes for one
        outside the sources, None when nothing in the namespaces around it has the name.
        A project type the head's written arity (``head_arity``) does not fit is passed
        over (`Lib.Order` beside a `Lib<T>`); ``in_type``: written in ``rtype``, whose type
        parameters and nested types come first."""
        sep = spec.separator

        def fits(found: Optional[Resolution]) -> bool:
            return head_arity is None or found is None or found.status != PROJECT \
                or head_arity in self.index[found.target].arities

        if in_type:
            if head in self._type_params(rtype, member):
                return "type"
            found = self._in_types(head, rtype, inherit, nested, spec)
            if found is not None and fits(found):
                return "type"
        for ns in chain:
            cand = ns + sep + head if ns else head
            if cand in self.index and not fits(Resolution(PROJECT, cand)):
                pass
            elif self._sees(rtype, cand) and (cand in self.index or cand in self.inline_names
                                              or cand in self.aliases) \
                    or head in self.build_types.get(ns, ()) \
                    or ns and head in (spec.outside_namespace(ns) or ()):
                return "type"
            if self._namespace_exists(cand, spec):
                return cand
            if strict and self._outside_around(ns, spec, scope):
                return "outside"
            if any(imp.block == ns and not imp.wildcard and imp.local_name == head
                   for imp in scope.imports):
                return None   # an alias the namespace block declares
            found = self._block_import(head, ns, scope, spec, strict)
            if found is not None and fits(found):
                return "type"   # not a `Lib<T>` the block's using brings in for `Lib.Order`
        return None

    def _through_alias(self, alias: Optional[str], rest: str, rtype: RawType,
                       member: Optional[RawMember], arity: Optional[int], inherit: bool,
                       spec: LanguageSpec) -> Resolution:
        """``rest`` after the alias ``alias`` (`L.Order`, `L::Order`, `ModelAlias::Ptr`)."""
        sep = spec.separator
        # C#'s `using L = Lib;` then `L.Order`: an alias of a namespace of the
        # sources stands for it; the name is read in that namespace
        entry = self.alias_targets.get(alias) if alias else None
        if entry is not None and spec.body_aliases:
            # (the alias's target is read from the namespace it stands in outward)
            block = entry[1].alias_blocks.get(alias, "")
            target = self._alias_namespace(alias, spec)
            if target is not None:
                return self.resolve(target + sep + rest, rtype, member,
                                    arity=arity, at_namespace="")
            written = re.sub(r"^\s*global::", "", entry[0]).strip()
            # a target after `global::` is the global namespace's alone
            rooted = self._rooted_text(entry[0], spec) is not None
            if not any(f"{ns}{sep}{written}" in self.index if ns else written in self.index
                       for ns in (self._namespace_chain(block, sep, True) if not rooted
                                  else [""])) \
                    and written not in self.aliases and "<" not in written :
                # `using pb = global::Google.Protobuf;` then `pb::CodedInputStream`:
                # a namespace (or type) outside the sources
                return Resolution(EXTERNAL, written + sep + rest)
        # `using ModelAlias = Model;` then `ModelAlias::Ptr`: an alias of one class
        # is that class, its members looked up there
        cls = self._alias_head_class(alias, spec) if alias else None
        if cls is not None:
            found = self._nested_path(cls, rest, sep, inherit, spec)
            if found:
                return found
        return Resolution(ALIAS)

    def _alias_namespace(self, alias: str, spec: LanguageSpec, depth: int = 0) -> Optional[str]:
        """The namespace of the sources a using alias names (`using L = Lib;`: Lib), its
        target read from the namespace it stands in outward; one written with the alias
        qualifier (`using LS = L::Sub;`) is read in what that alias names. None where it
        names none of them."""
        entry = self.alias_targets.get(alias)
        if entry is None or depth > 8:
            return None
        sep, q = spec.separator, spec.alias_qualifier
        text, scope = entry[0].strip(), entry[1]
        block = scope.alias_blocks.get(alias, "")
        if (written := self._rooted_text(text, spec)) is not None:
            # `using M = global::Lib.Sub;`: the global namespace's Lib.Sub, never a type or
            # namespace of a namespace around it (Shop.Lib)
            return written if written in self.namespaces else None
        if q and q in text:
            head, rest = (p.strip() for p in text.split(q, 1))
            # the aliases of the namespaces around it: one beside it is not seen there
            for ns in self._namespace_chain(block, sep, True):
                if ns == block and block:
                    continue
                other = self.file_aliases.get((scope.file, ns), {}).get(head)
                if other is not None and other != alias:
                    base = self._alias_namespace(other, spec, depth + 1)
                    found = f"{base}{sep}{rest}" if base is not None else None
                    return found if found in self.namespaces else None
            return None
        for ns in self._namespace_chain(block, sep, True):
            target = f"{ns}{sep}{text}" if ns else text
            if target in self.namespaces:
                return target
        return None

    @staticmethod
    def _rooted_text(text: str, spec: LanguageSpec) -> Optional[str]:
        """``text`` without the prefix that roots it at the global namespace (C#'s
        `global::Lib`: Lib), or None where it is not written so."""
        prefix = spec.rooted_prefix
        t = text.strip()
        return t[len(prefix):].strip() if prefix and t.startswith(prefix) else None

    def _alias_qualified(self, name: str, rtype: RawType, member: Optional[RawMember],
                         inherit: bool, scope: FileScope, arity: Optional[int],
                         spec: LanguageSpec) -> Optional[Resolution]:
        """C#'s alias qualifier (`L::Order`, LanguageSpec.alias_qualifier): the name before
        it is a using alias, never a type or namespace of its name (`Shop.L` in `namespace
        Shop.Inner`); None where ``name`` is not written so."""
        q = spec.alias_qualifier
        if not q or q not in name:
            return None
        head, rest = name.split(q, 1)
        head, rest = head.strip(), rest.strip()
        if spec.rooted_prefix and name.startswith(spec.rooted_prefix):
            # `global::Shop.Order` in a body: the global namespace's alone, not App.Shop's
            if rest in self.index:
                return Resolution(PROJECT, rest)
            first = rest.split(spec.separator, 1)[0]
            if any(n == first or n.startswith(first + spec.separator) for n in self.namespaces):
                return Resolution(UNRESOLVED, hint=f"no type {rest} in the sources")
            return Resolution(EXTERNAL, rest)
        for ns in self._namespace_chain(rtype.namespace, spec.separator,
                                        spec.parent_namespace_lookup, scope.namespace):
            alias = self.file_aliases.get((scope.file, ns), {}).get(head)
            if alias is not None and self._sees(rtype, alias):
                return self._through_alias(alias, rest, rtype, member, arity, inherit, spec)
        return Resolution(UNRESOLVED, hint=f"{head}{q} names a using alias, and the file has "
                                           f"none of the name")

    # ------------------------------------------------------------ resolve

    def resolve(self, name: str, rtype: RawType, member: Optional[RawMember] = None,
                inherit: bool = True, scope: Optional[FileScope] = None,
                arity: Optional[int] = None, strict: bool = False,
                nested: bool = True, head_arity: Optional[int] = None,
                at_namespace: Optional[str] = None, body_file: Optional[str] = None
                ) -> Resolution:
        """What ``name`` written in ``rtype`` stands for. ``strict``: a name more than one
        wildcard import provides is unresolved, not the first one's. ``nested``: whether
        the nested types of ``rtype`` and the types around it are in scope (in a body,
        LanguageSpec.nested_types_in_bodies). ``head_arity``: how many type arguments the
        first part of a qualified name is written with. ``at_namespace``: written in that
        namespace outside any type (the target of an alias declared there), not in
        ``rtype``. ``body_file``: written in a body of that file, where a file-local type
        of another file is no candidate (LanguageSpec.file_local_bodies)."""
        spec = LANGUAGES[rtype.language]
        sep = spec.separator
        scope = scope or (member.scope if member and member.scope else None) or rtype.scope
        if body_file is not None and spec.include_visibility and self.body_scope:
            # C++: a using declaration of a file it includes (`namespace app { using
            # lib::Money; }`) is its namespace's name there too
            scope = self.body_scope(scope, body_file)
        # C++ and the other languages name none of each other's types (no interop): in a
        # directory of both, a C++ `Helper` of the global namespace is no C# `Helper`
        cpp = spec.name == "cpp"
        # in a body: what the file does not include is skipped, unless it sees a declaration
        # of the name there (`struct Fwd;`): the name is that type (LanguageSpec.include_visibility)
        unseen = (lambda q: self.unseen_from(q, body_file)) \
            if body_file is not None and spec.include_visibility and self.unseen_from else (lambda q: None)
        # Kotlin: `import p.Money as Coin` hides p.Money's own name in the file, from its
        # package and its star imports (LanguageSpec.alias_import_hides)
        # C#: a type the file's project does not see (another project's `internal` one, an
        # unreferenced project's), or one of another arity (`Repo<int>` is no `Repo`), is no
        # candidate: the lookup goes on
        unfit = (lambda q: (self.visible is not None and not self.visible(q, scope))
                 or (arity is not None and q in self.index and self.index[q].arities
                     and arity not in self.index[q].arities)) \
            if spec.arity_selects else (lambda q: False)
        renamed = {i.path for i in scope.imports if not i.wildcard and i.alias
                   and i.local_name != i.path.rsplit(sep, 1)[-1]} \
            if spec.alias_import_hides else set()
        away = (lambda q: (q in self.index and (self.index[q].language == "cpp") != cpp)
                or (body_file is not None and self._elsewhere(q, body_file))
                or unseen(q) == "skip")
        chain = self._namespace_chain(
            rtype.namespace if at_namespace is None else at_namespace, sep,
            spec.parent_namespace_lookup, scope.namespace)

        if name in self._type_params(rtype, member) and at_namespace is None:
            return Resolution(TPARAM)
        if spec.alias_qualifier and (found := self._alias_qualified(
                name, rtype, member, inherit, scope, arity, spec)) is not None:
            return found

        if sep in name and body_file is not None and spec.values_hide_types and at_namespace is None:
            found = self._class_head(name, rtype, inherit, nested, spec)
            if found is not None:
                return found
        if sep in name:
            first_is = None
            if spec.qualified_heads_in_scope:
                head, rest = name.split(sep, 1)
                first_is = self._qualified_head(head, rtype, member, inherit, nested, scope,
                                                chain, spec, strict, head_arity,
                                                in_type=at_namespace is None)
                if first_is == "outside":
                    return Resolution(UNRESOLVED, outside=True)
                if first_is not in (None, "type", head):
                    name = first_is + sep + rest   # `Models.Order` is App.Models.Order
            if first_is == "type":
                pass   # what the type the head names has (`Lib.Order`: Shop.Lib's Order)
            elif name in self.index and unseen(name) == "stop":
                return Resolution(PROJECT, name)
            elif name in self.index and not away(name):
                return Resolution(PROJECT, name)
            elif name in self.inline_names:
                return Resolution(PROJECT, self.inline_names[name])
            elif name in self.aliases:   # n::Legacy_t
                return Resolution(ALIAS, name)
            else:
                for ns in chain:  # partially qualified: pay::Receipt inside namespace shop
                    if ns and ns + sep + name in self.index and unseen(ns + sep + name) == "stop":
                        return Resolution(PROJECT, ns + sep + name)
                    if ns and ns + sep + name in self.index and not away(ns + sep + name):
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
                                 nested=nested, at_namespace=at_namespace, body_file=body_file)
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
                return self._through_alias(first.target, rest, rtype, member, arity,
                                           inherit, spec)
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

        found = self._in_types(name, rtype, inherit, nested, spec, body_file is not None) \
            if at_namespace is None else None
        if found is not None:
            return found

        def in_namespaces() -> Optional[Resolution]:
            for ns in chain:
                cand = ns + sep + name if ns else name
                if cand in self.index and unseen(cand) == "stop":
                    return Resolution(PROJECT, cand)   # `struct Fwd;` here: that type
                if not self._sees(rtype, cand) or away(cand) or cand in renamed \
                        or cand in self.index and unfit(cand):
                    pass
                elif cand in self.index:
                    return Resolution(PROJECT, cand)
                elif cand in self.inline_names:
                    return Resolution(PROJECT, self.inline_names[cand])
                elif cand in self.aliases and not spec.body_aliases:
                    return Resolution(ALIAS, cand)  # a type alias: drawn through to its target
                if spec.body_aliases and (alias := self.file_aliases.get(
                        (scope.file, ns), {}).get(name)) is not None and self._sees(rtype, alias):
                    return Resolution(ALIAS, alias)   # C#: the file's alias, where it stands
                elif name in self.build_types.get(ns, ()):
                    return Resolution(EXTERNAL, cand)   # generated by the build (gRPC)
                if ns and name in (spec.outside_namespace(ns) or ()):
                    # `Host` in `namespace Microsoft.Extensions.Hosting`, before the usings
                    return Resolution(EXTERNAL, cand)
                if (strict or spec.enclosing_outside_hides) and self._outside_around(ns, spec, scope) \
                        and not spec.is_builtin(name):
                    return Resolution(UNRESOLVED, outside=True, hint=(
                        f"may be a type of {ns}, a namespace outside the sources around it"))
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
                    if self._imports_function(imp.path, sep):
                        continue   # Kotlin's `import other.Widget` of a `fun Widget`: no type
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
            if imp.wildcard and imp.block is not None:
                # looked at with its namespace's types (_block_import); one from outside the
                # sources still explains a name left unresolved
                if imp.external or (imp.path not in self.namespaces and imp.path not in self.index):
                    external_wildcards.append(imp)
                elif imp.path not in self.index:
                    shared_wildcards.append(imp)
                continue
            if imp.wildcard:
                found = None if imp.external or not self._exports(imp.path, name, spec, strict) \
                    else self.lookup(imp.path + sep + name, spec, certain=strict)
                if found and spec.body_aliases and found not in self.index:
                    found = None   # C#: a file's `using X = ...` is no member of its namespace
                if found and (unseen(found) == "skip" or found in renamed or unfit(found)):
                    found = None   # a type of a file the body's file does not include, or
                    # one the file imports under another name
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

    def _dependent_base(self, written: str, rtype: RawType) -> bool:
        """Whether a base class is written with a template parameter of the class (or of a
        class around it): C++ looks a name up in such a base only once it is instantiated."""
        params: set[str] = set()
        cur: Optional[RawType] = rtype
        while cur is not None:
            params.update(cur.generics)
            cur = self.index.get(cur.outer) if cur.outer else None
        return bool(params) and any(re.search(rf"\b{re.escape(p)}\b", written) for p in params)

    def _class_head(self, name: str, rtype: RawType, inherit: bool, nested: bool,
                    spec) -> Optional[Resolution]:
        """C++, in a body: a qualified name whose head is a member type or alias of the
        classes around, looked up there first as a simple name is (`Mutex::ScopedLock`
        after `using Mutex = Poco::FastMutex;` in the class); None when the head is none."""
        sep = spec.separator
        head, rest = name.split(sep, 1)
        found = self._in_types(head, rtype, inherit, nested, spec, True)
        if found is not None and found.status == ALIAS and found.target:
            # (also an alias of a template's specialisation: `Table::Iterator`)
            cls = self._alias_head_class(found.target, spec)
            if cls is None:
                return Resolution(UNRESOLVED)
            found = Resolution(PROJECT, cls)
        if found is not None and found.status == PROJECT:
            return self._nested_path(found.target, rest, sep, inherit, spec) or Resolution(UNRESOLVED)
        return None

    def body_alias(self, name: str, rtype: RawType, ref: RawBodyRef,
                   qualifier: bool = False) -> Optional[str]:
        """The alias a name in type position stands for (LanguageSpec.values_hide_types,
        whose aliases are followed as the declared relations follow them), or None."""
        res = self._body_resolution(name, rtype, ref, qualifier)
        return res.target if res is not None and res.status == ALIAS else None

    def _body_resolution(self, name: str, rtype: RawType, ref: RawBodyRef,
                         qualifier: bool) -> Optional[Resolution]:
        """_name_in_body, or None where a base whose members are not known may have the
        name (opaque_hides)."""
        res = self._name_in_body(name, rtype, ref, qualifier)
        if res is not None and res.status in (PROJECT, ALIAS) and res.target \
                and self.opaque_hides(rtype, ref, name):
            return None
        return res

    def opaque_hides(self, rtype: RawType, ref: RawBodyRef,
                     name: str) -> Optional[tuple[str, Resolution]]:
        """The base (as written, and its resolution) whose members are not known
        (Resolution.opaque) that may have ``name`` where ``ref`` is written, or None. A
        class's scope is its own members and its bases': a name found in the class or in a
        base of it is not hidden by the class's opaque base, one found further out (a class
        around it, a namespace) is."""
        chain = []
        cur: Optional[RawType] = rtype
        while cur is not None:
            chain.append(cur)
            cur = self.index.get(cur.outer) if cur.outer else None
        if not any(self._opaque_base(c) for c in chain):
            return None
        sep = LANGUAGES[rtype.language].separator
        head = name.split(sep, 1)[0]
        if sep in name and self._namespace_around(head, rtype):
            return None   # `lib::Base`: a namespace's name, which no base has as a member
        found = self._in_body(head, rtype, ref, 0)
        target = found.target if found.status in (PROJECT, ALIAS) else None
        owner = None
        if target is not None:
            if target in self.index:
                owner = self.index[target].outer
            elif sep in target:
                owner = target.rsplit(sep, 1)[0]
        for c in chain:
            scope = self._ancestors(c)
            if target is not None and (target in scope or owner in scope):
                return None
            hidden = self._opaque_base(c)
            if hidden is not None:
                return hidden
        return None

    def rooted(self, name: str, text: Optional[str], rtype: RawType) -> Optional[Resolution]:
        """What ``name`` is where ``text`` writes it from the global namespace (C#'s
        `global::Lib.Order`, LanguageSpec.rooted_prefix; the type parser drops the prefix):
        the project type of that id, else a type outside the sources; None where it is not
        written so."""
        prefix = LANGUAGES[rtype.language].rooted_prefix
        if not prefix or not text or not re.search(
                rf"(?<![\w:]){re.escape(prefix)}\s*{re.escape(name)}(?![\w.])", text):
            return None
        if name in self.index:
            return Resolution(PROJECT, name)
        return Resolution(ALIAS, name) if name in self.aliases else Resolution(EXTERNAL, name)

    def member_named(self, rtype: RawType, name: str, before_dot: bool = False) -> bool:
        """Whether ``rtype``, a type around it or a base of either has a member (a field,
        property, method, event or constant) ``name``, also one a base outside the sources
        has as far as the language knows it (LanguageSpec.outside_member). ``before_dot``:
        the name stands before a `.`, where a member whose type has its name is the type
        (C#'s "Color Color": `Kind.A` beside `public Kind Kind`)."""
        def hides(m) -> bool:
            if m.name != name or m.kind == "constructor":
                return False
            written = _parse(m.type_ref, rtype.language) if before_dot and m.type_ref else None
            return not (isinstance(written, Named) and written.name.rsplit(".", 1)[-1] == name)
        cur: Optional[RawType] = rtype
        while cur is not None:
            for q in self._ancestors(cur):
                if any(hides(rm.member) for rm in self.index[q].members):
                    return True
            if self._outside_member_of(cur, name, False, set()):
                return True
            cur = self.index.get(cur.outer) if cur.outer else None
        return False

    def _ancestors(self, rtype: RawType) -> set[str]:
        """``rtype`` and its project bases, followed through."""
        out: set[str] = set()
        stack = [rtype]
        while stack:
            t = stack.pop()
            if t.qualified_name in out:
                continue
            out.add(t.qualified_name)
            stack += [self.index[s.target] for s in self.supertypes(t)
                      if s.status == PROJECT and s.target in self.index]
        return out

    def _opaque_base(self, rtype: RawType) -> Optional[tuple[str, Resolution]]:
        """A base of ``rtype`` or of its project bases whose members are not known
        (Resolution.opaque): (as written, its resolution), or None."""
        key = rtype.qualified_name
        if key in self._opaque_cache:
            return self._opaque_cache[key]
        found = None
        seen: set[str] = set()
        stack = [rtype]
        while stack and found is None:
            t = stack.pop()
            if t.qualified_name in seen:
                continue
            seen.add(t.qualified_name)
            for written, sup in zip(t.supers, self.supertypes(t)):
                if sup.opaque:
                    found = (written.text, sup)
                    break
                if sup.status == PROJECT and sup.target in self.index:
                    stack.append(self.index[sup.target])
        if not self._resolving_supers:   # (not while a base is being resolved: cyclic)
            self._opaque_cache[key] = found
        return found

    def _name_in_body(self, name: str, rtype: RawType, ref: RawBodyRef,
                      qualifier: bool) -> Optional[Resolution]:
        """``name`` where ``ref`` is written, or None where a value or a namespace of the
        name may be meant (LanguageSpec.values_hide_types: `int Money;` hides the type
        Money; `Keywords::now` may be a namespace Keywords's). ``qualifier``: the name stands
        before `::`, where no variable is looked up."""
        spec = LANGUAGES[rtype.language]
        sep = spec.separator
        if spec.values_hide_types:
            if not qualifier and sep not in name and (
                    self._is_variable(name, rtype, ref) or self._method_around(name, rtype, ref)):
                return None
            if not qualifier and sep not in name and ref.position != "type":
                # where a value may stand, an enumerator as near as the type or nearer
                # hides it (`sizeof(Paid)`; not `Cash c;`, nor `sizeof(Cash)` beside a
                # global `enum Coin { Cash }` and the namespace's struct Cash)
                at = self._enum_constant_around(name, rtype)
                if at is not None:
                    res = self._in_body(name, rtype, ref, 0)
                    if res.status not in (PROJECT, ALIAS) or not res.target \
                            or at <= self._type_depth(res.target, rtype):
                        return None
                    return res
            head = name.split(sep, 1)[0]
            if (qualifier or sep in name) and self._namespace_around(head, rtype) and \
                    self._in_body(head, rtype, ref, 0).status in (PROJECT, ALIAS):
                return None   # a type and a namespace of the name: which is nearer is not known
        return self._in_body(name, rtype, ref, 0)

    def body_type(self, name: str, rtype: RawType, ref: RawBodyRef,
                  qualifier: bool = False) -> Optional[str]:
        """The project type a name in type position stands for where ``ref`` is written,
        or None: also when a type of the name is declared anywhere in the member."""
        spec = LANGUAGES[rtype.language]
        res = self._body_resolution(name, rtype, ref, qualifier)
        if res is None:
            return None
        if res.status == ALIAS and res.target:
            target = self._alias_type(res.target, name, rtype, ref)
        else:
            target = res.target if res.status == PROJECT else None
        head = name.split(spec.separator, 1)[0]
        if target is not None and head == name and (
                self._unseen_nested(target, head, rtype, ref) or spec.alias_import_hides
                and self._imported_under_another_name(res.target, head, ref)):
            return None   # `N` of an interface it implements; `Money` after `import p.Money as M`
        # a nested type of a superclass outside the sources may be it (Kotlin); C++: any
        # member of a base, but before `::`, where only types are looked up
        nested_only = not spec.values_hide_types or qualifier or spec.separator in name
        if target is not None and spec.outside_supers_hide and not self._own_nested(
                target, rtype) and self._outside_member(rtype, ref, head, nested_only):
            return None
        return target

    def _method_around(self, name: str, rtype: RawType, ref: RawBodyRef) -> bool:
        """Whether a type around ``ref`` (the named type, its outer types, a local class
        around it) or a project supertype of one declares a method ``name``."""
        for project, _ in self._around(rtype, ref, 0):
            if any(self._has_method(t, name, set()) for t in project):
                return True
        cur: Optional[RawType] = rtype
        while cur is not None:
            if self._has_method(cur, name, set()):
                return True
            cur = self.index.get(cur.outer) if cur.outer else None
        return False

    def _namespace_around(self, head: str, rtype: RawType, alias: bool = False) -> bool:
        """Whether ``head`` names a namespace of the sources the code around ``rtype``
        sees by that name: one inside a namespace around it, or a top one (with ``alias``,
        not a top one: a namespace alias of the file's scope is the file's top name)."""
        spec = LANGUAGES[rtype.language]
        sep = spec.separator
        for ns in self._namespace_chain(rtype.namespace, sep, spec.parent_namespace_lookup):
            if alias and not ns:
                continue
            cand = ns + sep + head if ns else head
            if cand in self.namespaces or cand in self.opened_namespaces:
                return True
        return False

    def _unseen_nested(self, target: str, head: str, rtype: RawType, ref: RawBodyRef) -> bool:
        """Whether ``head``, resolved to the nested type ``target``, cannot be it: the
        language passes on no nested type of an interface, nor one of a companion object
        (LanguageSpec.class_nested_only), so only the type around it, an import of it or a
        star import of its outer type sees it by simple name."""
        if not LANGUAGES[rtype.language].class_nested_only:
            return False
        t = self.index[target]
        outer = self.index.get(t.outer) if t.outer else None
        if t.name != head or outer is None or not (outer.kind == "interface" or t.static_scope):
            return False
        if self._own_nested(target, rtype):
            return False
        return not any(imp.path == target and imp.local_name == head if not imp.wildcard
                       else imp.path == t.outer for imp in ref.scope.imports)

    def _imported_under_another_name(self, target: str, head: str, ref: RawBodyRef) -> bool:
        """Whether the file imports ``target`` under another name than ``head``, its own
        (LanguageSpec.alias_import_hides: Kotlin then finds no ``head`` through it)."""
        imports = [imp for imp in ref.scope.imports if not imp.wildcard and imp.path == target
                   and imp.path.rsplit(".", 1)[-1] == head]
        # (`import p.Money` beside `import p.Money as Coin` still brings in `Money`)
        return any(imp.local_name != head for imp in imports) \
            and not any(imp.local_name == head for imp in imports)

    def _own_nested(self, target: str, rtype: RawType) -> bool:
        """Whether ``target`` is nested in ``rtype`` or a type around it: found before
        what any supertype has."""
        outer = self.index[target].outer
        cur: Optional[RawType] = rtype
        while cur is not None:
            if outer == cur.qualified_name:
                return True
            cur = self.index.get(cur.outer) if cur.outer else None
        return False

    def _outside_member(self, rtype: RawType, ref: RawBodyRef, name: str,
                        nested_only: bool) -> bool:
        """Whether a supertype outside the sources of the type, of a type around it, or of
        an anonymous or local class around ``ref`` may have a member ``name``
        (LanguageSpec.outside_member): with ``nested_only`` a nested type, which a class
        sees through its superclasses only, else any member."""
        spec = LANGUAGES[rtype.language]
        for supers in ref.classes:
            for sup in supers:
                # (an anonymous or local class's supertypes are not told apart: an
                # interface's are taken for a superclass's too)
                written = _parse(sup, rtype.language)
                if not isinstance(written, Named):
                    continue
                res = self._in_body(written.name, rtype, ref, 0)
                if res.status != PROJECT and any(
                        spec.outside_member(t, name, nested_only)
                        for t in self._outside_candidates(written.name, res, ref.scope, rtype)):
                    return True
                if res.status == PROJECT and self._outside_member_of(
                        self.index[res.target], name, nested_only, set()):
                    return True
        cur: Optional[RawType] = rtype
        while cur is not None:
            if self._outside_member_of(cur, name, nested_only, set()):
                return True
            cur = self.index.get(cur.outer) if cur.outer else None
        return False

    def _outside_candidates(self, name: str, res: Resolution, scope: FileScope,
                            rtype: RawType) -> list[Optional[str]]:
        """The types outside the sources a supertype's name may be (_outside); [None] when
        it may be any."""
        cands = self._outside(name, res, scope, rtype, True)
        return cands or ([] if res.status == UNRESOLVED and res.outside and name else [None])

    def _outside_member_of(self, rtype: RawType, name: str, nested_only: bool,
                           seen: set, instance: bool = False) -> bool:
        """Whether a supertype outside the sources of ``rtype`` or of its project
        supertypes may have a member ``name``: with ``instance`` an instance property or
        function only (what a value of the type has: an extension's receiver)."""
        if rtype.qualified_name in seen:
            return False
        around = not seen   # (a base's own bases are all looked into)
        seen.add(rtype.qualified_name)
        spec = LANGUAGES[rtype.language]
        for written, sup in zip(rtype.supers, self.supertypes(rtype)):
            if nested_only and written.kind != "extends" and not spec.values_hide_types:
                continue   # an interface passes on no nested type (C++ has none)
            if spec.values_hide_types and around and self._dependent_base(written.text, rtype):
                continue   # C++: `std::vector<T>` is looked into only once T is known
            if sup.status == PROJECT:
                if self._outside_member_of(self.index[sup.target], name, nested_only, seen,
                                           instance):
                    return True
                continue
            ref = _parse(written.text, rtype.language)
            sname = ref.name if isinstance(ref, Named) else ""
            if any(spec.outside_instance_member(t, name) if instance
                   else spec.outside_member(t, name, nested_only) for t in self._outside_candidates(
                    sname, sup, written.scope or rtype.scope, rtype)):
                return True
        return False

    def body_receiver(self, ref: RawBodyRef, rtype: RawType) -> Optional[tuple[str, int]]:
        """(project type, how many parts of the name it covers) a receiver starts with
        (`Util.Helper` in `Util.Helper.run()`, `Util` in `Util.VALUE.trim()`), or None. A
        variable wins over a type, and a type over a package (JLS 6.5.2): a head that may be
        a variable draws nothing, and after a type a field of the name ends it."""
        spec = LANGUAGES[rtype.language]
        sep = spec.separator
        parts = ref.text.split(sep)
        # a type the member declares (a local class) is no package either
        if parts[0] in ref.names.types:
            return None
        if self._is_variable(parts[0], rtype, ref):
            res = self._color_color(parts, rtype, ref, spec)
            if res is None:
                return None
        elif (head := self._receiver_head(parts[0], rtype, ref, spec)) is not None:
            if head == "outside":
                return None
            res = Resolution(UNRESOLVED)   # a namespace: the name goes on into it
        else:
            res = self._in_body(parts[0], rtype, ref, 0)
        if res.status == PROJECT and self._unseen_nested(res.target, parts[0], rtype, ref) or (
                res.status in (PROJECT, ALIAS) and res.target and spec.alias_import_hides
                and self._imported_under_another_name(res.target, parts[0], ref)):
            return None   # `N.x` of an interface it implements; `Money` after `import p.Money as M`
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
            # a package: the first prefix that is a project type (`io.netty.Foo.X`); in C#
            # as a qualified name is resolved (`Models.Order` in `namespace App.Web`)
            if spec.qualified_heads_in_scope:
                n, target = next(((k, r.target) for k in range(2, len(parts) + 1)
                                  if (r := self._in_body(sep.join(parts[:k]), rtype, ref, 0))
                                  .status == PROJECT), (0, None))
            else:
                n = next((k for k in range(2, len(parts) + 1)
                          if sep.join(parts[:k]) in self.index), 0)
                target = sep.join(parts[:n])
            if not n:
                return None
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
        if ref.position == "call" and len(parts) == 1 and (
                self._function_named(parts[0], rtype, ref) or spec.outside_functions(ref.scope)):
            return None   # `Foo(1)` may call a function Foo
        if spec.outside_supers_hide and self._outside_member(rtype, ref, parts[0], False):
            return None   # a property, function or nested type of a supertype outside
        if ref.member is not None and self._receiver_member(parts[0], rtype, ref):
            return None   # `fun Ctx.ext() = Money(2)`: a member of Ctx
        outer = None
        while n < len(parts) and not self._has_field(self.index[target], parts[n]):
            nested = self._member_type(self.index[target], parts[n], sep,
                                       spec.inherited_member_types, set())
            if nested is None or self.index[nested].kind in spec.type_only_kinds or (
                    spec.rebinding_hides and self._rebound(nested)):
                break   # `Foo.Cond` where Foo's body binds Cond twice: Foo alone
            outer, target, n = target, nested, n + 1
        if ref.position == "call" and n == len(parts) and outer is not None and \
                self._has_method(self.index[outer], parts[-1], set()):
            target, n = outer, n - 1   # `Outer.Inner()` may call Outer's function Inner
        return target, n

    def _receiver_member(self, name: str, rtype: RawType, ref: RawBodyRef) -> bool:
        """Whether a receiver of an extension the member is or declares (RawMember.receivers)
        has a property or function ``name``: a project type's own or inherited one, or one
        an outside type has as far as the language knows it
        (LanguageSpec.outside_instance_member).
        Its nested types are no names there."""
        spec = LANGUAGES[rtype.language]
        for text in ref.member.receivers:
            written = _parse(text, rtype.language)
            if not isinstance(written, Named):
                continue
            res = self._in_body(written.name, rtype, ref, 0)
            if res.status == ALIAS and res.target:   # `fun Cash.ext()`: the class it names
                aliased = self._alias_type(res.target, written.name, rtype, ref)
                res = Resolution(PROJECT, aliased) if aliased else \
                    self._alias_resolution(res.target, spec, 0) or res
            if res.status == PROJECT:
                t = self.index[res.target]
                # its own or a project supertype's, or one of a supertype outside
                if self._has_field(t, name) or self._has_method(t, name, set()) or \
                        self._outside_member_of(t, name, False, set(), instance=True):
                    return True
            elif any(spec.outside_instance_member(o, name)
                     for o in self._outside_candidates(written.name, res, ref.scope, rtype)):
                return True
        return False

    def _function_named(self, name: str, rtype: RawType, ref: RawBodyRef) -> bool:
        """Whether a call of ``name`` may be a function's: one declared at a file's top
        anywhere in the sources, or a method of a type around ``ref`` (its own, an outer
        type's, an anonymous or local class's) or of one of their project supertypes."""
        if name in self.top_functions.get(rtype.language, ()):
            return True
        for project, _ in self._around(rtype, ref, 0):
            if any(self._has_method(t, name, set()) for t in project):
                return True
        cur: Optional[RawType] = rtype
        while cur is not None:
            if self._has_method(cur, name, set()):
                return True
            cur = self.index.get(cur.outer) if cur.outer else None
        return False

    def _has_method(self, rtype: RawType, name: str, seen: set) -> bool:
        """Whether the project type or a project supertype declares a method ``name``."""
        if rtype.qualified_name in seen:
            return False
        around = not seen   # (a base's own bases are all looked into)
        seen.add(rtype.qualified_name)
        return any(rm.member.name == name and rm.member.kind == "method" for rm in rtype.members) \
            or any(self._has_method(self.index[s.target], name, seen)
                   for s in self._project_supers(rtype, around) if s.status == PROJECT)

    def _receiver_head(self, head: str, rtype: RawType, ref: RawBodyRef,
                       spec) -> Optional[str]:
        """The namespace a receiver's head is, looked up as the first part of a qualified
        name is (LanguageSpec.qualified_heads_in_scope: the global namespace `Models` comes
        before a class `Models` the file's `using App.Entities;` brings in), "outside" past
        a package's namespace, or None where a type may come first (also inside an
        anonymous or local class, whose inherited types are not looked at here)."""
        if not spec.qualified_heads_in_scope or ref.classes:
            return None
        chain = self._namespace_chain(rtype.namespace, spec.separator,
                                      spec.parent_namespace_lookup, ref.scope.namespace)
        found = self._qualified_head(head, rtype, ref.member, True, spec.nested_types_in_bodies,
                                     ref.scope, chain, spec, True,
                                     ref.arities[0] if ref.arities else None)
        return None if found in (None, "type") else found

    def _color_color(self, parts: list[str], rtype: RawType, ref: RawBodyRef,
                     spec) -> Optional[Resolution]:
        """The type a receiver's head names although a field or property of the name is
        in scope, when the field's type has the name and the next part is a static member
        or a nested type of it (LanguageSpec.color_color: `Order Order` and
        `Order.Create()`); None where the head is a variable (`Order.Total`), or the
        variable is one whose type the extractor does not know (a local, a parameter)."""
        head = parts[0]
        after = parts[1] if len(parts) > 1 else ref.next
        if not spec.color_color or after is None or head in ref.names.variables \
                or any(imp.static for imp in ref.scope.imports):
            return None
        if after in self.resolver_extensions:
            return None   # an extension method of the name may make it an instance call
        found, cur = None, rtype
        while cur is not None and found is None:
            if head in cur.body_fields or cur.hidden_types.get(head):
                return None
            found = self._field_named(cur, head, set())
            cur = self.index.get(cur.outer) if cur.outer else None
        if found is None:
            return None
        owner, member = found
        # the field's own type, where it is declared, must be the type the name is: not
        # `Lib.Order Order` in Shop, nor `Money? Money` of a struct (Nullable<Money>)
        written = member.type_ref and _parse(member.type_ref, rtype.language)
        nullable = isinstance(written, Nullable)
        if nullable:
            written = written.inner
        if not isinstance(written, Named) or written.args \
                or written.name.rsplit(spec.separator, 1)[-1] != head:
            return None
        declared = self.resolve(written.name, owner, None, strict=True)
        res = self._in_body(head, rtype, ref, 0)
        if res.status != PROJECT or declared.status != PROJECT or declared.target != res.target:
            return None
        target = self.index[res.target]
        if nullable and (target.kind in ("struct", "enum") or "struct" in target.modifiers):
            return None
        if not self._static_member(target, after, spec, set()):
            return None
        return res

    def _field_named(self, rtype: RawType, name: str,
                     seen: set) -> Optional[tuple[RawType, Member]]:
        """(the type declaring it, a field or property ``name``) of the type or a project
        supertype."""
        if rtype.qualified_name in seen:
            return None
        seen.add(rtype.qualified_name)
        for rm in rtype.members:
            if rm.member.name == name and rm.member.kind in ("field", "property"):
                return rtype, rm.member
        for s in self.supertypes(rtype):
            if s.status == PROJECT and (found := self._field_named(self.index[s.target], name, seen)):
                return found
        return None

    def _static_member(self, rtype: RawType, name: str, spec, seen: set) -> bool:
        """Whether ``name`` is a nested type of the type or of a project supertype, or
        names static members there (an enum's constants) and no instance member: with an
        instance overload beside a static one (`Make()` and `Make(int)`) the call decides."""
        if self._member_type(rtype, name, spec.separator, True, set()):
            return True
        found: list[bool] = []

        def walk(t: RawType) -> None:
            if t.qualified_name in seen:
                return
            seen.add(t.qualified_name)
            found.extend(rm.member.static or rm.member.kind == "enum_constant"
                         for rm in t.members if rm.member.name == name)
            for s in self.supertypes(t):
                if s.status == PROJECT:
                    walk(self.index[s.target])
        walk(rtype)
        return bool(found) and all(found)

    def _alias_type(self, alias: str, name: str, rtype: RawType,
                    ref: RawBodyRef) -> Optional[str]:
        """The project type an alias the file declares names as a whole (C#'s `using O =
        Shop.Order;`, not `using Orders = List<Order>;`; LanguageSpec.body_aliases), or
        None; also None for one in code a build may leave out, and where a namespace
        around declares a type of the name, which C# looks at before the file's aliases."""
        spec = LANGUAGES[rtype.language]
        entry = self.alias_targets.get(alias)
        if spec.alias_declarations:
            return self._declared_alias_type(alias, spec, 0)
        if not spec.body_aliases or entry is None or entry[1].file != ref.scope.file \
                or alias in entry[1].conditional_aliases or not isinstance(
                    written := _parse(entry[0], rtype.language), Named) or written.args:
            return None
        chain = self._namespace_chain(rtype.namespace, spec.separator,
                                      spec.parent_namespace_lookup, ref.scope.namespace)
        if any((ns + spec.separator + name if ns else name) in self.index for ns in chain):
            return None
        # the target is looked up where the alias is declared (`using O = Lib.Order;` at the
        # top of the file, also before `namespace A.C;`: from the global namespace, not from
        # the namespace of the use; in a namespace block or after a file-scoped namespace,
        # from that namespace)
        res = self.rooted(written.name, entry[0], rtype) or self.resolve(
            written.name, rtype, None, scope=entry[1], strict=True,
            at_namespace=entry[1].alias_blocks.get(alias, ""))
        return res.target if res.status == PROJECT else None

    def _alias_head_class(self, alias: str, spec, depth: int = 0) -> Optional[str]:
        """The project class whose members a qualified name through ``alias`` is looked up
        in: the class it names (_declared_alias_type), or the template a specialisation of
        it is (`typedef SkipList<const char*, Cmp> Table;` then `Table::Iterator`)."""
        cls = self._declared_alias_type(alias, spec, depth)
        if cls is not None or depth > 4:
            return cls
        entry = self.alias_targets.get(alias)
        written = parse_type(entry[0], spec.type_dialect) if entry else None
        if not isinstance(written, Named) or not written.args:
            return None
        sep = spec.separator
        owner = alias.rsplit(sep, 1)[0] if sep in alias else None
        scope = entry[1]
        ctx = RawType(alias, alias.rsplit(sep, 1)[-1], "alias", Location(scope.file, 0), scope,
                      spec.name, namespace=self.index[owner].namespace if owner in self.index
                      else owner or scope.namespace,
                      outer=owner if owner in self.index else None)
        tparams = self._type_params(ctx, None) | self.alias_tparams.get(alias, set())
        if any(n.split(sep, 1)[0] in tparams for arg in written.args for n, _ in named_refs(arg)):
            return None   # `ParallelSocketReactor<SR>`: known once the template is instantiated
        res = self.rooted(written.name, entry[0], ctx) \
            or self.resolve(written.name, ctx, None, strict=True)
        if res.status == ALIAS and res.target and res.target != alias:
            return self._alias_head_class(res.target, spec, depth + 1)
        return res.target if res.status == PROJECT else None

    def _declared_alias_type(self, alias: str, spec, depth: int) -> Optional[str]:
        """The project class a type alias that is a declaration names directly
        (LanguageSpec.alias_declarations: Kotlin's `typealias Cash = Money`; also through
        another alias), resolved where it is declared; None for one of a generic type or a
        function type."""
        res = self._alias_resolution(alias, spec, depth)
        return res.target if res is not None and res.status == PROJECT else None

    def _alias_resolution(self, alias: str, spec, depth: int) -> Optional[Resolution]:
        """What a type alias that is a declaration names directly, through other aliases,
        resolved where it is declared (a project class, or one outside the sources:
        `typealias T2 = Thread`); None for one of a generic type or a function type."""
        entry = self.alias_targets.get(alias)
        if entry is None or depth > 4:
            return None
        text, scope = entry
        written = parse_type(text, spec.type_dialect)
        if not isinstance(written, Named) or written.args:
            return None
        sep = spec.separator
        owner = alias.rsplit(sep, 1)[0] if sep in alias else None
        ctx = RawType(alias, alias.rsplit(sep, 1)[-1], "alias", Location(scope.file, 0), scope,
                      spec.name, namespace=self.index[owner].namespace if owner in self.index
                      else owner or scope.namespace,
                      outer=owner if owner in self.index else None)
        res = self.rooted(written.name, text, ctx) \
            or self.resolve(written.name, ctx, None, strict=True)
        if res.status == ALIAS and res.target and res.target != alias:
            return self._alias_resolution(res.target, spec, depth + 1)
        return res if res.status in (PROJECT, EXTERNAL, BUILTIN) else None

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
                written = _parse(sup, rtype.language)
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
                           nested=spec.nested_types_in_bodies,
                           arity=ref.arities[0] if ref.arities and sep not in name else None,
                           head_arity=ref.arities[0] if ref.arities and sep in name else None,
                           body_file=ref.scope.file if spec.file_local_bodies else None)
        if res.status == PROJECT and self.rebinding(name, res.target, ref.scope, spec):
            return Resolution(UNRESOLVED)
        return res

    def rebinding(self, name: str, target: str, scope: FileScope, spec,
                  stars: bool = True) -> bool:
        """Whether ``name``, resolved to the project type ``target``, may be another
        binding where ``scope`` writes it (LanguageSpec.rebinding_hides): `try: from x import
        Foo` / `except: class Foo`; `class Foo` beside a star import that brings in another
        Foo, or beside one that may bring in anything (from outside the sources), here or in
        a module the name comes through. Without ``stars``, a star import whose names are
        not known is not taken for another binding (a declaration's name, #7)."""
        return spec.rebinding_hides and (
            self._rebound(target) or self._uncertain_path(name, scope, spec, stars)
            or spec.separator not in name and any(
                found != target for found in self._star_provides(name, scope, spec)))

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
        # a namespace outside the sources: what the language's table says it declares
        # (`using System.Threading.Tasks;` in a block is nearer than a project's Task
        # around it); one the table does not know may have any name, which code that
        # compiles does not also find in a project namespace of the block (a declaration
        # goes on looking, as before: ``strict``)
        outside, unknown = [], None
        for imp in block:
            if imp.wildcard and imp.path not in self.namespaces and imp.path not in self.index \
                    and not spec.is_builtin(name):
                known = spec.outside_namespace(imp.path)
                if known is None:
                    unknown = unknown or imp
                elif name in known:
                    outside.append(imp.path + sep + name)
            elif imp.wildcard and imp.static and imp.path not in self.index \
                    and (nested := spec.inherited_type(imp.path, name)):
                outside.append(nested)
        if outside and not hits:
            return Resolution(EXTERNAL, outside[0])
        if unknown is not None and strict and not hits:
            return Resolution(UNRESOLVED, hint=f"may come from wildcard import "
                                               f"{unknown.path}{sep}*")
        if len(hits) + len(outside) > 1:
            return Resolution(UNRESOLVED, candidates=hits,
                              hint=f"{len(hits) + len(outside)} wildcard imports provide the name")
        return self._found(hits[0]) if hits else None

    def _module_scopes(self, module: str, spec) -> list[FileScope]:
        return self.scopes_by_ns.get(module) or self.scopes_by_ns.get(
            self._by_suffix(module, self.scopes_by_ns, spec) or "", [])

    def _uncertain_path(self, name: str, scope: FileScope, spec, stars: bool = True) -> bool:
        """_uncertain for a dotted name: its head in the file, then each part in the module
        the parts before it name (`relay.Button` after `from p import relay`)."""
        sep = spec.separator
        parts = name.split(sep)
        if self._uncertain(scope, parts[0], spec, stars):
            return True
        got = self._head_module(parts[0], scope, spec)
        if got is None:
            return False
        module = got[0]
        for part in parts[1:]:
            scopes = self._module_scopes(module, spec)
            if not scopes:
                return False
            if any(self._uncertain(s, part, spec, stars) for s in scopes):
                return True
            module = module + sep + part
        return False

    def _uncertain(self, scope: FileScope, name: str, spec, stars: bool = True) -> bool:
        """Whether a file's ``name`` may be another class than the one it resolves to: bound
        by a wildcard import of a module outside the sources (`from tkinter import *`),
        whose names are not known, bound to two things at the top of the file (`from .a
        import Foo` and `from .b import Foo`, two star imports that bring in two, an import
        and a class, a project class and `from tkinter import Foo` or `import tkinter as
        Foo`), or bound as a variable there (FileScope.variables); in the file, or
        in a project module the file takes the name from, by
        its name or by a wildcard import that brings it in (`from q.gui import *`, `gui.py`
        importing tkinter's *; `from q.dup import Foo`). Without ``stars``, a wildcard
        import whose names are not known is not taken to bind the name (a declaration's
        name: bound twice, not maybe bound)."""
        key = (id(scope), name, stars)
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
                found = (stars and not scopes) or any(
                    self._uncertain(s, name, spec, stars) for s in brings)
                if brings and (target := self.lookup(imp.path + sep + name, spec, certain=True)):
                    targets.add(target)
            elif not imp.module and imp.local_name == name:
                module, _, original = imp.path.rpartition(sep)
                found = any(self._uncertain(s, original, spec, stars)
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
        if name in ref.names.variables or name in self.top_values.get(rtype.language, ()):
            return True   # a property at a file's top: the sources may name it anywhere
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
            if self._has_field(cur, name) or spec.unknown_bases_hide and self._unknown_base(cur):
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

    def _unknown_base(self, rtype: RawType) -> bool:
        """Whether the type or a project supertype extends a class outside the sources the
        language's table does not know (LanguageSpec.unknown_bases_hide): an interface by
        .NET's convention (`I` + a capital) passes on no member."""
        key = (rtype.qualified_name, "?base")
        if key not in self._field_cache:
            self._field_cache[key] = False
            spec = LANGUAGES[rtype.language]
            found = False
            for written, sup in zip(rtype.supers, self.supertypes(rtype)):
                if sup.status == PROJECT:
                    found = self._unknown_base(self.index[sup.target])
                else:
                    ref = _parse(written.text, rtype.language)
                    name = ref.name if isinstance(ref, Named) else ""
                    last = name.rsplit(spec.separator, 1)[-1]
                    if not last or re.match(r"I[A-Z]", last):
                        continue
                    scope = written.scope or rtype.scope
                    if sup.status == EXTERNAL and sup.target:
                        cands = [sup.target]
                    else:   # any namespace a using brings in (the sources may share one)
                        cands = [name] + [i.path + spec.separator + name for i in scope.imports
                                          if i.wildcard]
                    found = not any(spec.outside_known(t) for t in cands)
                if found:
                    break
            self._field_cache[key] = found
        return self._field_cache[key]

    def _has_field(self, rtype: RawType, name: str, inherited: bool = False,
                   heir_ns: Optional[str] = None) -> bool:
        """Whether the project type has a field ``name``, also an enum constant, a record
        component or one of its RawType.body_fields, its own or inherited (through the JDK
        table for JDK supertypes). ``inherited``: asked for a subtype in namespace
        ``heir_ns``, which sees a Java package-private field in its own package only."""
        key = (rtype.qualified_name, name, inherited, heir_ns)
        if key not in self._field_cache:
            self._field_cache[key] = False   # a cycle of supertypes has no field
            spec = LANGUAGES[rtype.language]
            self._field_cache[key] = any(
                rm.member.name == name and rm.member.kind in ("field", "enum_constant", "property")
                and (not inherited or spec.subtype_sees([rm.member.visibility, *rm.member.modifiers],
                                                        rtype.namespace == heir_ns))
                for rm in rtype.members) or name in rtype.body_fields or any(
                self._has_field(self.index[s.target], name, True, rtype.namespace)
                for s in self._project_supers(rtype, not inherited) if s.status == PROJECT) or any(
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
        self.part_files: dict[str, set[str]] = {}   # type id -> the files declaring a part
        self.file_projects = {f.path: f.scope.project for f in files}
        for f in files:
            for t in f.types:
                self.projects.setdefault(t.qualified_name, set()).add(f.scope.project)
                self.part_files.setdefault(t.qualified_name, set()).add(f.path)
            for t in f.scope.implicit_types:
                self.projects.setdefault(t, set()).add(f.scope.project)
        self._alias_cache: dict[str, tuple[list, list]] = {}
        # LanguageSpec.file_local_bodies: an id -> the files declaring it file-local, and
        # the ids some file declares not so
        for f in files:
            for t in f.types:
                if t.file_local:
                    self.resolver.local_files.setdefault(t.qualified_name, set()).add(f.path)
                else:
                    self.resolver.shared_ids.add(t.qualified_name)
        # what each file includes (LanguageSpec.include_visibility)
        self.file_includes = {f.path: f.scope.includes for f in files}
        self.file_forwards = {f.path: f.scope.forward_types for f in files}
        self.file_plain_forwards = {f.path: f.scope.plain_forwards for f in files}
        self.file_branch_forwards = {f.path: f.scope.branch_forwards for f in files}
        self.file_error_branches = {f.path: f.scope.error_branches for f in files}
        self.resolver.base_lookup = self._base_like_body
        self.resolver.visible = lambda q, scope: self._visible(
            q, scope.project, LANGUAGES[spec_for_path(scope.file).name])
        self._closures: Optional[dict[str, set[str]]] = None
        self._includers: Optional[dict[str, set[str]]] = None   # _unseen_from
        self.unknown_includes = {f.path for f in files if f.scope.unknown_include}
        self.resolver.unseen_from = self._unseen_from
        self.resolver.body_scope = self._body_scope
        self._body_scopes: dict[str, FileScope] = {}
        self.file_scopes = {f.path: f.scope for f in files}
        # names in bodies of members defined outside their type: the type's
        for f in files:
            for written, ns, ref in f.scope.detached_refs:
                target = self.resolver.detached_owner(written, ns, f.scope)
                if target is not None:
                    self.types[target].body_refs.append(ref)

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
        existing.base_calls.extend(t.base_calls)
        existing.annotation_refs.extend(t.annotation_refs)
        existing.body_refs.extend(t.body_refs)
        existing.body_fields |= t.body_fields
        existing.conditional |= t.conditional
        existing.branches = None if existing.branches is None or t.branches is None \
            else existing.branches + t.branches
        existing.left_out |= t.left_out
        existing.hidden_types.update(t.hidden_types)
        existing.generics += [g for g in t.generics if g not in existing.generics]
        for m in t.modifiers:
            if m not in existing.modifiers:
                existing.modifiers.append(m)
        for a in t.annotations:
            if a not in existing.annotations:
                existing.annotations.append(a)

    def _is_project(self, rtype: RawType, member: Optional[RawMember]):
        """Whether a name is the project's: a type or a type alias of the sources, which a
        container of its name (`Provider`, `Vector`, `Map`) never is."""
        return lambda name: self.resolver.resolve(name, rtype, member).status in (PROJECT, ALIAS)

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
            self._base_calls(rtype)
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

    def _class_binds(self, rtype: RawType, name: str) -> bool:
        """Whether the class body of ``rtype`` binds ``name`` itself (a field, method or
        property of the name: `Other = print`), where its statements and its members'
        decorators and annotations are evaluated (LanguageSpec.initializers_in_class_scope)."""
        return LANGUAGES[rtype.language].initializers_in_class_scope and any(
            rm.member.name == name and rm.member.kind in ("field", "method", "property")
            for rm in rtype.members)

    def _module_binds(self, scope: FileScope, name: str, spec) -> bool:
        """Whether the file's top binds ``name`` (an import of it, a class, a variable)."""
        own = f"{scope.namespace}{spec.separator}{name}" if scope.namespace else name
        return own in self.types or name in scope.variables or any(
            not imp.wildcard and imp.local_name == name for imp in scope.imports)

    def _super_resolutions(self, rtype: RawType) -> list[Resolution]:
        """What each supertype clause of ``rtype`` draws to: the resolver's supertypes,
        which names are looked up in too (Resolver.base_lookup)."""
        return self.resolver.supertypes(rtype)

    def _base_like_body(self, rtype: RawType, sup: Any, res: Resolution) -> Resolution:
        """Resolver.base_lookup: a base clause looked up as a body looks names up where the
        language does so (LanguageSpec.declared_like_bodies); ``res`` is the resolver's own
        answer."""
        if not LANGUAGES[rtype.language].declared_like_bodies:
            return res
        ref = _parse(sup.text, rtype.language)
        found = self._like_body(ref.name, rtype, None, sup.scope or rtype.scope, len(ref.args),
                                sup.line, sup.text, res, base=True)
        if found.status == ALIAS and found.target:
            # `typedef lib::Base LB; struct D : LB`: an alias of a class is that class,
            # looked into as a base is; `typedef std::vector<int> IntVec;` is std::vector's
            named = self._alias_class(found.target)
            if named is not None:
                return named
        return found

    def _alias_class(self, alias: str, depth: int = 0) -> Optional[Resolution]:
        """The class an alias names as a whole (`typedef lib::Base LB;`, `using V =
        std::vector<int>;`, aliases of aliases followed): a project type (PROJECT) or one
        outside the sources (EXTERNAL), or None (a pointer, a dependent `typename`, a name
        it cannot tell)."""
        entry = self.resolver.alias_targets.get(alias)
        if entry is None or depth > 4:
            return None
        text, scope = entry
        if text.strip().startswith("typename "):
            return None
        spec = spec_for_path(scope.file)
        ref = parse_type(text, spec.type_dialect)
        if not isinstance(ref, Named):
            return None
        sep = spec.separator
        owner = alias.rsplit(sep, 1)[0] if sep in alias else None
        ctx = RawType(alias, alias.rsplit(sep, 1)[-1], "alias", Location(scope.file, 0), scope,
                      spec.name, namespace=self.types[owner].namespace if owner in self.types
                      else owner or scope.namespace,
                      outer=owner if owner in self.types else None)
        if ref.name.split(sep, 1)[0] in self.resolver.alias_tparams.get(alias, set()):
            return None
        res = self.resolver.resolve(ref.name, ctx, None, arity=len(ref.args),
                                    body_file=scope.file)
        if res.status == PROJECT or res.status == EXTERNAL and res.target:
            return Resolution(res.status, res.target)
        if res.status == ALIAS and res.target and res.target != alias:
            return self._alias_class(res.target, depth + 1)
        return None

    def _declared_resolution(self, name: str, rtype: RawType, rm: Optional[RawMember],
                             arity: Optional[int], text: Optional[str] = None) -> Resolution:
        """What a name of a member's declaration (its type, a parameter's or the return
        type, ``text`` as written) stands for."""
        res = self.resolver.expect_class(self.resolver.rooted(name, text, rtype)
                                         or self.resolver.resolve(name, rtype, rm, arity=arity))
        spec = LANGUAGES[rtype.language]
        scope = (rm.scope if rm is not None and rm.scope else None) or rtype.scope
        head = name.split(spec.separator, 1)[0]
        if res.status in (PROJECT, ALIAS) and (self._class_binds(rtype, head) or (
                spec.initializers_in_class_scope and res.target == rtype.qualified_name
                + spec.separator + head and self._module_binds(scope, head, spec))):
            return Resolution(UNRESOLVED, hint=(
                f"the class body binds {head}: the checkers disagree whether an annotation "
                "there means that binding or the module's"))
        if res.status == PROJECT and self.resolver.rebinding(name, res.target, scope, spec,
                                                             stars=False):
            return Resolution(UNRESOLVED, hint=_REBOUND.format(name, res.target))
        if not spec.declared_like_bodies:
            return res
        scope = (rm.scope if rm is not None and rm.scope else None) or rtype.scope
        line = rm.member.line if rm is not None else rtype.location.line
        return self._like_body(name, rtype, rm, scope, arity, line, text, res)

    def _like_body(self, name: str, rtype: RawType, rm: Optional[RawMember], scope: FileScope,
                   arity: Optional[int], line: int, text: Optional[str], res: Resolution,
                   base: bool = False) -> Resolution:
        """``name`` of a declaration looked up as _body looks a name up
        (LanguageSpec.declared_like_bodies); ``res`` is the resolver's own answer, kept for a
        name outside the sources. Where a body draws nothing the name is unresolved, with the
        reason."""
        spec = LANGUAGES[rtype.language]
        sep = spec.separator
        parts = name.split(sep)
        file = scope.file
        if not base and len(parts) > 1 and _dependent_member(text, parts, sep):
            # `typename UDPHandlerImpl<S>::List`: List is a member of the template once it is
            # instantiated (Clang: dependent). Where the member is found (an alias, a nested
            # type), the name stands for the template alone: what the member names is not
            # expanded, as an alias of it (`using L = typename X<S>::List;`) names nothing
            inner = self._like_body(name, rtype, rm, scope, arity, line, None, res)
            if inner.status != PROJECT and not (
                    inner.status == ALIAS and inner.target
                    and any(self._alias_names(inner.target, rtype))):
                return inner   # (a member drawing nothing, `CONSTTYPE` of `const T`)
            qual = sep.join(parts[:-1])
            return self._like_body(qual, rtype, rm, scope, None, line, None,
                                   self.resolver.resolve(qual, rtype, rm, scope=scope))
        ref = RawBodyRef(name, "type", [(line, 0)] * len(parts), rm.member.name if rm else "",
                         scope, rm, BodyNames(), arities=[None] * (len(parts) - 1) + [arity])
        # `::D`: the global namespace's (the type parser drops the leading `::`)
        rooted = bool(text) and re.search(
            rf"(?<![\w:])::\s*{re.escape(name)}(?![\w:])", text) is not None
        renamed = scope.namespace_aliases.get(parts[0]) if len(parts) > 1 and not rooted else None
        if renamed and (self.resolver._namespace_around(parts[0], rtype, alias=True)
                        or self.resolver._in_body(parts[0], rtype, ref, 0).status
                        in (PROJECT, ALIAS)):
            renamed = None
        target = alias = None
        if rooted or renamed:
            full = sep.join([renamed, *parts[1:]]) if renamed else name
            if full in self.types and not self.resolver._elsewhere(full, file):
                target = full
            elif full in self.resolver.aliases:
                alias = full
            elif res.target and res.status in (PROJECT, ALIAS):
                return Resolution(UNRESOLVED, hint=f"{full} is no type of the sources")
            else:
                return res
        elif base:
            # a base clause: the class's own (inherited) member types are not in scope yet
            found = self.resolver.resolve(name, rtype, None, inherit=False, scope=scope,
                                          arity=arity, body_file=file)
            if found.status == PROJECT:
                target = found.target
            elif found.status == ALIAS and found.target:
                alias = found.target
            elif res.target and res.status in (PROJECT, ALIAS):
                return Resolution(UNRESOLVED, hint=self._unseen_why(res.target, file)
                                  or f"{name} is no type {file} sees", opaque=True)
            else:
                return found
        else:
            target = self.resolver.body_type(name, rtype, ref)
            alias = None if target is not None else self.resolver.body_alias(name, rtype, ref)
            if target is None and alias is None:
                hidden = self.resolver.opaque_hides(rtype, ref, name)
                if hidden is not None and res.target and res.status in (PROJECT, ALIAS):
                    return Resolution(UNRESOLVED, hint=(
                        f"{name} may be a member of the base {hidden[0]}, whose members are "
                        f"not known: {hidden[1].hint}"))
                if res.target and res.status in (PROJECT, ALIAS):
                    return Resolution(UNRESOLVED, hint=self._unseen_why(res.target, file) or (
                        f"{name} may be a value, a namespace or a member of a base class "
                        "outside the sources here, which bodies draw nothing for"))
                return res
        if alias is not None:
            return Resolution(ALIAS, alias)
        why = self._declared_stop(target, scope, line)
        return Resolution(UNRESOLVED, hint=why, opaque=base) if why else Resolution(PROJECT, target)

    def _declared_stop(self, target: str, scope: FileScope, line: int) -> Optional[str]:
        """Why a body would draw nothing to ``target`` from ``line`` of ``scope``'s file
        (_draw), as far as it holds for a declaration, or None."""
        branches = self.types[target].branches
        if branches is not None:
            around = {cond for first, last, cond in scope.branches if first <= line <= last}
            if not any(f == scope.file and first <= line <= last or cond in around
                       for f, first, last, cond in branches) and not any(
                    target in self.file_plain_forwards.get(f, ())
                    for f in self._included(scope.file)) and not _every_branch(
                    self._chain_parts(target, branches)):
                # (a declaration of the id outside every branch, `class PollSetImpl;` in
                # the file or one it includes: the name is that type in every build)
                return (f"{target} is declared in an #if branch this declaration is outside "
                        "of: another type of the name may be meant")
        return self._unseen_why(target, scope.file)

    def _chain_parts(self, target: str, branches: list) -> list:
        """The branches that declare ``target`` in a build (Type.branches), with those that
        forward-declare it (`#ifdef _WIN32 / struct Fwd; / #else / struct Fwd {...}`) and
        those of the same files no build compiles (`#else / #error "unsupported"`)."""
        files = {f for f, _, _, _ in branches}
        return list(branches) + [
            (f, first, last, cond) for f in files
            for first, last, cond in [*self.file_branch_forwards.get(f, {}).get(target, ()),
                                      *self.file_error_branches.get(f, ())]]

    def _unseen_why(self, target: str, file: str) -> Optional[str]:
        if target in self.types and self._unseen_from(target, file) == "skip":
            return f"{target} is declared in a file {file} does not include"
        return None

    def _alias_names(self, alias: str, rtype: RawType) -> tuple[list, list]:
        """_expand_alias for a declared relation: as a body expands it where the language
        looks declared names up so (an alias's own template parameters name no type, a
        dependent `typename X<T>::Y` none), and the template arguments of an alias's
        qualifier (`std::vector<Item>::const_iterator`) name none."""
        if LANGUAGES[rtype.language].declared_like_bodies:
            return self._expand_alias(alias, body=True, qualifier_args=False)
        return self._expand_alias(alias)

    def _supers(self, rtype: RawType) -> None:
        spec = LANGUAGES[rtype.language]
        for sup, res in zip(rtype.supers, self._super_resolutions(rtype)):
            ref = parse_type(sup.text, spec.type_dialect)
            if not isinstance(ref, Named):
                continue
            loc = Location(sup.scope.file if sup.scope else rtype.location.file, sup.line)
            targets = [res.target] if res.status == PROJECT else []
            if res.status == ALIAS and res.target:
                # `class X : AliasOfBase()`; TypeScript's `interface I extends Joined` with
                # `type Joined = Options & Logger`: each type the alias is. The others it
                # names (an object type's members, `Omit<Base, "a">`'s Base) are
                # dependencies, as a field's alias draws them
                leaves, names = self._alias_names(res.target, rtype)
                targets = list(dict.fromkeys(t for t, _, _ in leaves))
                for other in names:
                    if other not in targets and other != rtype.qualified_name:
                        self.relations.append(Relation(rtype.qualified_name, other,
                                                       "dependency", loc))
            if targets:
                for target in targets:
                    if target == rtype.qualified_name:
                        continue
                    kind = sup.kind
                    if kind == "inherits":
                        target_kind = self.types[target].kind
                        if rtype.kind == "interface" or target_kind != "interface":
                            kind = "extends"
                        else:
                            kind = "implements"
                    self.relations.append(Relation(rtype.qualified_name, target, kind, loc))
            elif res.status in (EXTERNAL, BUILTIN):
                ext_id = res.target or ref.name
                name = ext_id.rsplit("::", 1)[-1].rsplit("/", 1)[-1].rsplit(".", 1)[-1]
                self.externals.setdefault(ext_id, External(ext_id, name))
                kind = spec.external_super_kind(rtype.kind, sup.kind, name)
                self.relations.append(Relation(rtype.qualified_name, ext_id, kind, loc))
            elif res.status == UNRESOLVED:
                self._unresolved(rtype, ref.name, res, loc, via=None)
            self._super_args(rtype, sup, ref, loc)

    def _base_calls(self, rtype: RawType) -> None:
        """A dependency on each project class a base written as a call names (Python's
        `class Manager(BaseManager.from_queryset(QuerySet))`: BaseManager, QuerySet), the
        longest part of a dotted name that is one; the class the call makes is not known,
        so no supertype."""
        spec = LANGUAGES[rtype.language]
        for call in rtype.base_calls:
            loc = Location(call.scope.file if call.scope else rtype.location.file, call.line)
            for written in spec.call_names(call.text):
                name = re.sub(r"\s+", "", written)
                res = self._base_call_resolution(name, rtype, call)
                if res.status == PROJECT and res.target != rtype.qualified_name:
                    self.relations.append(Relation(rtype.qualified_name, res.target,
                                                   "dependency", loc))

    def _base_call_resolution(self, name: str, rtype: RawType, call: Any) -> Resolution:
        """The project class a name in a base's call is, its longest part that is one."""
        sep = LANGUAGES[rtype.language].separator
        parts = name.split(sep)
        res = Resolution(UNRESOLVED)
        for k in range(len(parts), 0, -1):
            res = self._super_lookup(sep.join(parts[:k]), rtype, call, None)
            if res.status == PROJECT:
                return res
        return res

    def _super_args(self, rtype: RawType, sup: Any, ref: Named, loc: Location) -> None:
        """A dependency on every project type a supertype's type arguments name
        (`class NodeList extends ArrayList<Node>`), the supertype in the sources or not;
        containers are seen through, as in a signature. A type parameter and the type
        itself draw nothing; a name that names nothing of the project draws nothing and is
        not unresolved."""
        is_project = self._is_project(rtype, None)
        for arg in ref.outer_args + ref.args:   # (`Base.WithRequest<A>.WithResult<B>`)
            for name, arity in named_refs(arg, is_project):
                if self.wrappers.is_wrapper(name) and not is_project(name):
                    continue
                res = self._super_arg_resolution(name, rtype, sup, arity)
                targets = [res.target] if res.status == PROJECT else \
                    self._alias_names(res.target, rtype)[1] if res.status == ALIAS and res.target \
                    else []
                for target in targets:
                    if target != rtype.qualified_name:
                        self.relations.append(Relation(
                            rtype.qualified_name, target, "dependency", loc))

    def _super_arg_resolution(self, name: str, rtype: RawType, sup: Any,
                              arity: Optional[int]) -> Resolution:
        """What a name in a supertype's type arguments stands for (_super_lookup)."""
        return self._super_lookup(name, rtype, sup, arity)

    def _super_lookup(self, name: str, rtype: RawType, sup: Any,
                      arity: Optional[int]) -> Resolution:
        """A name written in a supertype clause looked up as the supertype itself is
        (Resolver.supertypes; C++ as a base clause of a body, _base_like_body), where the
        type's own inherited member types are not in scope."""
        spec = LANGUAGES[rtype.language]
        scope = sup.scope or rtype.scope
        res = self.resolver.expect_class(self.resolver.rooted(name, sup.text, rtype)
                                         or self.resolver.resolve(name, rtype, inherit=False,
                                                                  scope=scope, arity=arity))
        if res.status == PROJECT and self.resolver.rebinding(name, res.target, scope, spec,
                                                             stars=False):
            return Resolution(UNRESOLVED, hint=_REBOUND.format(name, res.target))
        if not spec.declared_like_bodies:
            return res
        return self._like_body(name, rtype, None, scope, arity, sup.line, sup.text, res,
                               base=True)

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
            if ann.line > rtype.location.line and self._class_binds(
                    rtype, ann.name.split(sep, 1)[0]):
                continue   # Python: a member's decorator the class body binds (`Other = print`)
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
                    ref = parse_type(spec.normalize_type(text), spec.type_dialect)
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
                if spec.members_hide_annotation_args and self.resolver.member_named(
                        rtype, name.split(sep, 1)[0], sep in name):
                    continue   # C#'s `nameof(Order)` beside a property Order: the property
                while name:
                    res = self.resolver.resolve(name, rtype, None, scope=ann.scope)
                    if res.status in (PROJECT, ALIAS):
                        self._annotation_target(rtype, res, via, loc)
                        break
                    name = name.rsplit(sep, 1)[0] if sep in name else ""

    def _body(self, rtype: RawType) -> None:
        """A dependency, `evidence` "body", on the project type each name in a body stands
        for; a name that may mean something else draws nothing, and is never unresolved."""
        spec = LANGUAGES[rtype.language]
        sep = spec.separator
        for ref in rtype.body_refs:
            targets: list[str] = []
            if spec.values_hide_types and ref.position == "call" and sep not in ref.text and (
                    self.resolver._function_named(ref.text, rtype, ref)
                    or spec.outside_functions(ref.scope)):
                continue   # `Ticket(1)` may call a function Ticket
            if spec.values_hide_types:
                # C++: a qualified name is types and namespaces; the longest prefix that is a
                # project type is drawn (`Order::Status::Paid`: Order::Status), and an alias
                # stands for every project type it names (as a declared relation's)
                rooted = ref.text.startswith(sep)   # `::Helper`: the global namespace's
                parts = ref.text[len(sep):].split(sep) if rooted else ref.text.split(sep)
                # `fs::D` after `namespace fs = a::inner;` in the file: a::inner::D, unless a
                # namespace or a class of the name is nearer (`shop::fs`, a nested `gs`)
                renamed = ref.scope.namespace_aliases.get(parts[0]) if len(parts) > 1 else None
                if renamed and not rooted and (
                        self.resolver._namespace_around(parts[0], rtype, alias=True)
                        or self.resolver._in_body(parts[0], rtype, ref, 0).status
                        in (PROJECT, ALIAS)):
                    renamed = None
                if renamed:
                    rooted = True
                n = 0
                for k in range(len(parts), 0, -1):
                    name, qualifier = sep.join(parts[:k]), k < len(parts)
                    if renamed:
                        if k == 1:
                            break   # the alias itself is a namespace
                        name = sep.join([renamed, *parts[1:k]])
                    if rooted:
                        target = name if name in self.types and not self.resolver._elsewhere(
                            name, ref.scope.file if spec.file_local_bodies else None) else None
                        alias = name if target is None and name in self.resolver.aliases else None
                    else:
                        target = self.resolver.body_type(name, rtype, ref, qualifier)
                        alias = None if target is not None else \
                            self.resolver.body_alias(name, rtype, ref, qualifier)
                    if target is not None:
                        # an enum's constant is read as the enum (`Status::Paid`): the place
                        # is the enum's name
                        while k > 1 and parts[k - 1] != self.types[target].name:
                            k -= 1
                        targets, n = [target], k
                        break
                    if alias is not None:
                        targets, n = self._expand_alias(alias, body=True)[1], k
                        break
            elif ref.position == "type":
                target, n = self.resolver.body_type(ref.text, rtype, ref), len(ref.places)
                targets = [target] if target else []
            else:
                target, n = self.resolver.body_receiver(ref, rtype) or (None, 0)
                targets = [target] if target else []
            for target in targets:
                if target != rtype.qualified_name:
                    self._draw(rtype, ref, target, n)

    def _draw(self, rtype: RawType, ref: RawBodyRef, target: str, n: int) -> None:
        """The body relation of ``ref``'s first ``n`` parts to ``target``, unless a build
        may see another type there."""
        # a type declared in code a build may leave out, or a name some build declares
        # a type of where the parser saw none: no one type for every build
        sep = LANGUAGES[rtype.language].separator
        if self.types[target].conditional or any(
                p in self.left_out or p in ref.scope.left_out_names or p in rtype.left_out
                for p in ref.text.split(sep)[:n]):
            return
        spec = LANGUAGES[rtype.language]
        if spec.file_local(self.types[target].modifiers) and (
                ref.scope.file not in self.part_files.get(target, set()) if spec.file_local_copies
                else self.part_files.get(target, set()) != {ref.scope.file}):
            return   # a C# `file` type is seen in its file only, and is one type there
        if len(self.projects.get(target, ())) > 1:
            return   # one id, a type in each of several projects
        branches = self.types[target].branches
        if branches is not None:
            line = ref.places[0][0]
            around = {cond for first, last, cond in ref.scope.branches if first <= line <= last}
            if not any(f == ref.scope.file and first <= line <= last or cond in around
                       for f, first, last, cond in branches):
                return   # declared in an `#if` branch, used outside it (or one of the same
                # condition): another type may be meant
        if spec.include_visibility and self._unseen_from(target, ref.scope.file) in ("skip", "unknown"):
            return   # declared in a file the body's file does not include (another program's),
            # or one it may see through a file around it or an include a macro makes
        if any(imp.conditional for imp in ref.scope.imports) and target != self._without(
                ref, rtype, n):
            return   # through an import some build leaves out
        if not self._visible(target, ref.scope.project, LANGUAGES[rtype.language]):
            return   # declared in a project the file's project does not reference
        if not spec.sees_declaration(ref.scope, target, self.types[target].namespace, [
                (f, self.file_projects.get(f)) for f in sorted(self.part_files.get(target, ()))]):
            return   # declared in a platform's source set the file's does not see
        if ref.arities and ref.arities[n - 1] is not None \
                and ref.arities[n - 1] not in self.types[target].arities:
            return   # `Repo<int>` is no Repo: another type of the name, further out
        line, col = ref.places[n - 1]
        self.body_uses.append((ref.scope.file, line, col, rtype.qualified_name, target))
        self.relations.append(Relation(rtype.qualified_name, target, "dependency",
                                       Location(ref.scope.file, line), via=ref.via,
                                       evidence="body"))

    def _unseen_from(self, target: str, file: str) -> Optional[str]:
        """How a body of ``file`` sees the project type ``target`` (include_visibility):
        None when a file it includes defines it; "stop" when one only declares it (`struct
        Fwd;`, `template <class T> struct Box;`, `enum class Mode : int;`: the name is that
        type, whose definition it does not see); "unknown" when what the file sees is not
        known: it or a file it includes has an include a macro makes, or a file including
        it sees the type (`foo_inl.h` included at the end of the `foo.h` that defines
        Helper); else "skip": lookup goes on past it."""
        if target not in self.types or self.types[target].language != "cpp":
            return None
        seen = self._included(file)
        where = self.part_files.get(target, set())
        if where & seen:
            return None
        if any(target in self.file_forwards.get(f, ()) for f in seen):
            return "stop"
        if seen & self.unknown_includes or any(
                where & self._included(f) for f in self._including(file)):
            return "unknown"
        return "skip"

    def _body_scope(self, scope: FileScope, file: str) -> FileScope:
        """``scope`` as a body of ``file`` looks names up in it (LanguageSpec.include_visibility):
        a using declaration of a namespace or of the file's scope (`namespace app { using
        lib::Money; }`) is a name of that namespace, after a type it declares nearer
        (Import.block), also in every file that includes its file, directly or through others."""
        if scope is not self.file_scopes.get(file):
            return scope
        if file not in self._body_scopes:
            imports = [replace(i, block=i.namespace) if i.namespace is not None else i
                       for i in scope.imports]
            have = {(i.path, i.local_name, i.block) for i in imports}
            for f in sorted(self._included(file) - {file}):
                for imp in self.file_scopes[f].imports:
                    if imp.namespace is None:
                        continue   # (in a class or a function of that file)
                    key = (imp.path, imp.local_name, imp.namespace)
                    if key not in have:
                        imports.append(replace(imp, block=imp.namespace))
                        have.add(key)
            self._body_scopes[file] = replace(scope, imports=imports)
        return self._body_scopes[file]

    def _including(self, file: str) -> set[str]:
        """The files that include ``file``, directly or through others."""
        if self._includers is None:
            self._includers = {}
            for f in self.file_includes:
                for g in self._included(f):
                    if g != f:
                        self._includers.setdefault(g, set()).add(f)
        return self._includers.get(file, set())

    def _included(self, file: str) -> set[str]:
        """The file and the files it includes, directly or through others
        (LanguageSpec.include_visibility): a quoted path from the file's directory first,
        else every file of the sources whose path ends with the one written."""
        if self._closures is None:
            self._closures = {}
            self._by_tail: dict[str, list[str]] = {}
            for path in self.file_includes:
                parts = path.split("/")
                for k in range(len(parts)):
                    self._by_tail.setdefault("/".join(parts[k:]), []).append(path)
        if file in self._closures:
            return self._closures[file]
        seen, todo = {file}, [file]
        while todo:
            cur = todo.pop()
            for written in self.file_includes.get(cur, ()):
                path = written.strip()[1:-1].strip()
                found = []
                if written.startswith('"'):
                    near = posixpath.normpath(posixpath.join(posixpath.dirname(cur), path))
                    if near in self.file_includes:
                        found = [near]
                found = found or self._by_tail.get(posixpath.normpath(path), [])
                for f in found:
                    if f not in seen:
                        seen.add(f)
                        todo.append(f)
        self._closures[file] = seen
        return seen

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
        internal, cur, nested = False, self.types.get(target), False
        while cur is not None and not internal:
            internal = spec.internal_type(cur.modifiers, cur.outer is not None)
            cur = self.types.get(cur.outer) if cur.outer else None
        for p in (project.split(";") if project else ()):
            seen = spec.project_references(p)
            if seen is not None and not declared & seen:
                return False
            # an internal type only in its own project, or one its InternalsVisibleTo names
            if internal and p not in declared and not any(
                    spec.internals_visible(d, p) for d in declared):
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
        start = len(self.relations)
        self._field_relations(rtype, rm)
        # one field naming a type twice (`UpdateFilter<T> | Document[]`, whose alias names
        # Document too): one association, of the largest multiplicity
        best: dict[str, Relation] = {}
        for r in self.relations[start:]:
            if r.kind == "association":
                kept = best.get(r.to)
                if kept is None or _RANK[r.multiplicity] > _RANK[kept.multiplicity]:
                    best[r.to] = r
        if best:
            self.relations[start:] = [r for r in self.relations[start:]
                                      if r.kind != "association" or best[r.to] is r]

    def _field_relations(self, rtype: RawType, rm: RawMember) -> None:
        m = rm.member
        ref = _parse(m.type_ref, rtype.language)
        loc = Location(m.file or rtype.location.file, m.line)
        cpp = rtype.language == "cpp"
        others: list = []   # container arguments that are not the element: Map<K, V>'s K
        for leaf in self.wrappers.leaves(ref, self._is_project(rtype, rm), track_ownership=cpp,
                                         dropped=others):
            res = self._declared_resolution(leaf.name, rtype, rm, len(leaf.args), m.type_ref)
            if leaf.value and not self._value_type(res):
                continue   # `typeof value`: a variable, though a type alias has the name
            if res.status == PROJECT:
                self.relations.append(Relation(
                    rtype.qualified_name, res.target, "association", loc,
                    multiplicity=leaf.multiplicity, ownership=leaf.ownership, via=m.name))
            elif res.status == ALIAS and res.target:   # `Pt p;` with `using Pt = ...Point;`
                leaves, names = self._alias_names(res.target, rtype)
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
                self._depend_on(rtype, rm, arg, loc, m.type_ref)
        # a function-typed field (`config: HttpClientConfig.() -> Unit`, also inside a
        # container) holds no instance of those types; it depends on them, as on the
        # container arguments that are not its elements
        for other in [*function_types(ref), *others]:
            self._depend_on(rtype, rm, other, loc, m.type_ref)
        if m.receiver:   # Kotlin's extension property `val Box<Job>.done`: its receiver
            self._depend_on(rtype, rm, _parse(m.receiver, rtype.language), loc, m.receiver)

    def _dependencies(self, rtype: RawType, rm: RawMember) -> None:
        m = rm.member
        loc = Location(m.file or rtype.location.file, m.line)
        for text in [m.type_ref, m.receiver] + [p.type_ref for p in m.params] + rm.throws:
            self._depend_on(rtype, rm, _parse(text, rtype.language), loc, text)

    def _depend_on(self, rtype: RawType, rm: RawMember, ref, loc: Location,
                   text: Optional[str] = None) -> None:
        """A dependency on every project type named in ``ref`` (written ``text``),
        containers seen through."""
        m = rm.member
        values = value_names(ref)   # `typeof setTimeout`: a value, not a missing type
        is_project = self._is_project(rtype, rm)
        for name, arity in named_refs(ref, is_project):
            if self.wrappers.is_wrapper(name) and not is_project(name):
                continue
            res = self._declared_resolution(name, rtype, rm, arity, text)
            if name in values and not self._value_type(res):
                continue   # `typeof value`: a variable, though a type alias has the name
            targets = [res.target] if res.status == PROJECT else \
                self._alias_names(res.target, rtype)[1] if res.status == ALIAS and res.target else []
            for target in targets:
                if target != rtype.qualified_name:
                    self.relations.append(Relation(
                        rtype.qualified_name, target, "dependency", loc, via=m.name))
            if res.status == UNRESOLVED and name not in values:
                self._unresolved(rtype, name, res, loc, via=m.name)

    def _value_type(self, res: Resolution) -> bool:
        """Whether a name written as a value (TypeScript's `typeof x`) may be the project
        type ``res`` gives: a class or an enum, which are values too; an interface or a type
        alias of the name is no value, so a variable of the name is meant."""
        return res.status != ALIAS and not (
            res.status == PROJECT and self.types[res.target].kind == "interface")

    def _expand_alias(self, alias: str, depth: int = 0, body: bool = False,
                      qualifier_args: bool = True) -> tuple[list, list]:
        """What a type alias names, resolved where the alias is declared:
        ([(project type, multiplicity, ownership)] it points at as a field type would,
        [every project type it mentions]). Aliases of aliases are followed; the alias's own
        type parameters name no type (`Hash` of `template <class K, class Hash> using M =
        map<K, Hash>`). ``body``: for a name in a body (a dependent `typename` names
        nothing). Without ``qualifier_args``
        the template arguments of a qualifier name no type: `std::vector<Item>::const_iterator`
        is std's iterator, whatever it is instantiated with (C++'s declared relations)."""
        key = (alias, body) if body and qualifier_args else (alias, body, False) \
            if not qualifier_args else alias
        if key in self._alias_cache:
            return self._alias_cache[key]
        entry = self.resolver.alias_targets.get(alias)
        if entry is None or depth > 4:
            return [], []
        self._alias_cache[key] = ([], [])   # a cycle expands to nothing
        # the alias's own type parameters name no type (C++'s alias templates, whose every
        # expansion is ``body``, and TypeScript's `type Fn<T> = (x: T) => void`)
        own = self.resolver.alias_tparams.get(alias, set())
        written = entry[0].strip()
        if body and written.startswith("typename ") and (
                qualifier_args or not written.endswith(">")):
            # `typename NObserver<C, N>::Ptr`: known once instantiated; a declared relation
            # reads `typename std::pair<K, Var>`, which names no member, as it is
            return [], []
        text, scope = entry
        if not qualifier_args:
            text = _without_qualifier_args(text)
        spec = spec_for_path(scope.file)
        sep = spec.separator
        owner = alias.rsplit(sep, 1)[0] if sep in alias else None
        ctx = RawType(alias, alias.rsplit(sep, 1)[-1], "alias", Location(scope.file, 0), scope,
                      spec.name, namespace=self.types[owner].namespace if owner in self.types
                      else owner or scope.namespace,
                      outer=owner if owner in self.types else None)
        ref = parse_type(text, spec.type_dialect)
        values = value_names(ref)
        leaves: list = []
        for leaf in self.wrappers.leaves(ref, self._is_project(ctx, None),
                                         track_ownership=spec.name == "cpp"):
            if leaf.name.split(sep, 1)[0] in own:
                continue
            res = self.resolver.rooted(leaf.name, text, ctx) or self.resolver.resolve(
                leaf.name, ctx, None, arity=len(leaf.args), body_file=scope.file if body else None)
            if leaf.value and not self._value_type(res):
                continue
            if res.status == PROJECT:
                leaves.append((res.target, leaf.multiplicity, leaf.ownership))
            elif res.status == ALIAS and res.target:
                for target, mult, owner in self._expand_alias(res.target, depth + 1, body,
                                                              qualifier_args)[0]:
                    leaves.append((target, combine(leaf.multiplicity, mult), owner or leaf.ownership))
        names: list = []
        for name, arity in named_refs(ref, self._is_project(ctx, None)):
            if name.split(sep, 1)[0] in own:
                continue
            res = self.resolver.rooted(name, text, ctx) or self.resolver.resolve(
                name, ctx, None, arity=arity, body_file=scope.file if body else None)
            if name in values and not self._value_type(res):
                continue
            if res.status == PROJECT:
                names.append(res.target)
            elif res.status == ALIAS and res.target and res.target != alias:
                names += self._expand_alias(res.target, depth + 1, body, qualifier_args)[1]
        self._alias_cache[key] = (leaves, list(dict.fromkeys(names)))
        return self._alias_cache[key]

    def _finalize_relations(self) -> list[Relation]:
        # keep every fact: one relation per (from, to, kind, via). Collapsing
        # dependencies per pair is a presentation decision made by the renderer.
        unique = {r.key(): r for r in reversed(self.relations)}
        return sorted(unique.values(), key=lambda r: (r.from_, r.to, r.kind, r.via or ""))


_TEMPLATE_ARGS = re.compile(r"<[^<>]*(?:<[^<>]*(?:<[^<>]*>[^<>]*)*>[^<>]*)*>")


def _dependent_member(text: Optional[str], parts: list[str], sep: str) -> bool:
    """Whether ``text`` writes the name ``parts`` as `typename Q<...>::Last`: a member of a
    template written with arguments, which only an instantiation tells."""
    if not text or "typename" not in text:
        return False
    m = re.search(r"\btypename\s+(.*?)::\s*" + re.escape(parts[-1]) + r"\b", text)
    if not m or "<" not in m.group(1):
        return False
    qual = _TEMPLATE_ARGS.sub("", m.group(1)).replace(" ", "")
    return qual.lstrip(":") == sep.join(parts[:-1])


def _parse(text: Optional[str], language: str):
    """parse_type in the language's dialect (LanguageSpec.type_dialect)."""
    return parse_type(text, LANGUAGES[language].type_dialect)


_REBOUND = ("{} is bound more than once where it is written ({} among the bindings): which "
            "binding it is depends on what ran")


def _every_branch(branches: list[tuple[str, int, int, str]]) -> bool:
    """Whether the branches declaring a type (Type.branches) are every branch of one
    `#if ... #else ... #endif` chain of a file (`#elif`s too): the type is there whatever the
    condition. A chain's branches follow each other (one ends on the line the next starts),
    the first's condition is an `#if`'s and the last's an `#else`'s."""
    by_file: dict[str, list[tuple[int, int, str]]] = {}
    for f, first, last, cond in branches:
        by_file.setdefault(f, []).append((first, last, cond))
    for parts in by_file.values():
        parts = sorted(set(parts))
        for i, (first, _, cond) in enumerate(parts):
            if "|" in cond or not cond.startswith("if"):
                continue   # not the first branch of a chain
            j = i
            while j + 1 < len(parts) and parts[j + 1][0] == parts[j][1] \
                    and parts[j + 1][2].endswith("|" + cond):
                j += 1
                if parts[j][2].startswith("else|"):
                    return True
    return False


def _without_qualifier_args(text: str) -> str:
    """``text`` with the template arguments of each qualifier left out
    (`std::vector<Item>::const_iterator` -> `std::vector::const_iterator`)."""
    out, i = [], 0
    while i < len(text):
        if text[i] == "<":
            depth, j = 0, i
            while j < len(text):
                depth += {"<": 1, ">": -1}.get(text[j], 0)
                if depth == 0:
                    break
                j += 1
            if text[j + 1:].lstrip().startswith("::"):
                i = j + 1
                continue
        out.append(text[i])
        i += 1
    return "".join(out)


def build_ir(root: str, files: list[RawFile], wrappers: Wrappers) -> IR:
    return _Builder(root, files, wrappers).build()


__all__ = ["build_ir", "Resolver", "Resolution", "Import"]
