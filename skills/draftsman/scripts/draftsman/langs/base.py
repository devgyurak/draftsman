"""Per-language knowledge that a tree-sitter query cannot express.

A language is a query file (queries/<name>.scm) plus a small LanguageSpec
subclass. The query decides *what* is captured; the spec answers questions
like "what is the default visibility here" and "how are names resolved".
Every hook has a default that suits Java-like languages.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import tree_sitter as ts

    from ..extractor import RawType


# directories that hold no sources of the project (dependencies, build output, tools)
SKIP_DIRS = frozenset({
    ".git", ".hg", ".svn", ".idea", ".vscode", ".gradle", ".mvn", "node_modules",
    "build", "target", "out", "dist", "bin", "obj", "__pycache__", ".venv", "venv",
    ".tox", ".mypy_cache", ".pytest_cache",
})


@dataclass
class Import:
    path: str                    # qualified target, e.g. "com.shop.pay.Payment"
    wildcard: bool = False       # path is a namespace whose members are all visible
    alias: Optional[str] = None  # local name, if different from the last path segment
    module: bool = False         # path names a module/namespace, not a type
    external: bool = False       # known to point outside the sources (package import)
    local: bool = False          # a relative path (`./x`, `.models`): inside the sources
    # applies to every file of the build project (C# `global using`, SDK implicit usings)
    project_wide: bool = False
    origin: Optional[str] = None   # where a project-wide import comes from, for hints
    # modules it may name when several workspace packages share its package name
    ambiguous: tuple[str, ...] = ()
    sep: str = "."

    @property
    def local_name(self) -> str:
        return self.alias or self.path.rsplit(self.sep, 1)[-1]


@dataclass
class FileScope:
    """What name resolution needs to know about one source file."""

    file: str
    namespace: Optional[str] = None
    imports: list[Import] = field(default_factory=list)
    type_params: set[str] = field(default_factory=set)  # file-wide (Python TypeVar)
    aliases: set[str] = field(default_factory=set)      # qualified type alias names
    project: Optional[str] = None   # build project the file compiles in (C#: its .csproj)


class LanguageSpec:
    name: str = ""
    grammar: str = ""                    # tree-sitter-language-pack name
    query: str = ""                      # queries/<query>.scm; defaults to `name`
    extensions: tuple[str, ...] = ()
    separator: str = "."                 # namespace separator in qualified names

    # Node types that start a new lexical world (method bodies, lambdas,
    # anonymous classes). Declarations found below them are not members of
    # the enclosing type and local types are skipped.
    opaque_nodes: frozenset[str] = frozenset()

    # Node types whose members belong to the enclosing type as static members
    # (Kotlin companion objects).
    static_scope_nodes: frozenset[str] = frozenset()

    # Node types inside a modifiers capture that carry an annotation/decorator,
    # and the field holding its name.
    annotation_nodes: frozenset[str] = frozenset()
    annotation_name_field: str = "name"

    # For grammars without a modifiers node: direct children of a declaration
    # that count as modifiers, by node type or by keyword text.
    modifier_node_types: frozenset[str] = frozenset()
    modifier_keywords: frozenset[str] = frozenset()

    # Names that never need resolving: primitives and the implicit standard
    # library scope (java.lang.*, etc.).
    builtins: frozenset[str] = frozenset()

    visibility_keywords: dict[str, str] = {}

    # Name resolution behaviour
    parent_namespace_lookup: bool = False  # C#, C++: types of enclosing namespaces are visible
    import_suffix_match: bool = False      # Python, TS: match import paths by unique suffix
    # Java, C#, Kotlin, C++: member types of supertypes are in scope by simple name.
    # Not in Python (class bodies are not scopes) or TS (merged namespaces are not inherited)
    inherited_member_types: bool = True

    # ------------------------------------------------------------- files

    def preprocess(self, src: bytes) -> bytes:
        """Source cleanup before parsing; must keep byte offsets (C++ macros)."""
        return src

    def file_namespace(self, rel: str) -> Optional[str]:
        """Namespace implied by the file path (module languages), else None."""
        return None

    def package_root(self, root: Path) -> str:
        """Module path of the package the extraction root itself sits in ("" if none),
        prepended to every file's path before file_namespace/module_id see it."""
        return ""

    def is_project_wide(self, import_node) -> bool:
        """Whether an import applies to the whole build project (`global using`)."""
        return False

    def project_imports(self, path: Path,
                        root: Path) -> tuple[Optional[str], list[tuple[str, str]]]:
        """(the build project(s) ``path`` compiles in, ``;``-joined, [(namespace, origin)]
        the build itself imports into every file of it: .NET implicit usings and <Using>
        items). ``root`` is the extraction root, where linking project files are found."""
        return None, []

    def workspace_packages(self, root: Path) -> dict[str, list[tuple[str, str]]]:
        """Packages inside the extraction root, by the name other code imports them
        with -> [(directory, entry file)] below the root (JS/TS workspaces); more than
        one when several package.json files declare the same name."""
        return {}

    def workspace_modules(self, text: str,
                          packages: dict[str, list[tuple[str, str]]]) -> list[str]:
        """Module ids an import of a workspace package (``@acme/core/sub``) names: none
        if it is no workspace package, several if the package name is ambiguous."""
        return []

    def module_id(self, text: str, rel: str) -> Optional[str]:
        """Turn an import's module text into a namespace id; None = external package."""
        return text

    # ------------------------------------------------------------- types

    def is_opaque(self, node: "ts.Node") -> bool:
        return node.type in self.opaque_nodes

    def type_kind(self, captured_kind: str, modifiers: list[str]) -> str:
        if captured_kind == "class" and "abstract" in modifiers:
            return "abstract_class"
        return captured_kind

    def normalize_type(self, text: Optional[str]) -> Optional[str]:
        return text

    def library_type(self, name: str, imported: set[str],
                     arity: Optional[int] = None) -> Optional[str]:
        """Qualified id of a well-known library type ``name`` reachable through one of
        the ``imported`` namespaces, else None; ``arity`` is its number of type
        arguments when known (generic and plain versions can live apart)."""
        return None

    def is_builtin(self, name: str) -> bool:
        return name in self.builtins

    def builtin_id(self, name: str) -> str:
        """Qualified name used when a builtin appears as an external supertype."""
        return name

    def external_super_kind(self, owner_kind: str, captured: str, name: str) -> str:
        """Relation kind for an ``inherits`` clause whose target is outside the sources."""
        return "extends" if captured == "inherits" else captured

    def finalize_type(self, raw: "RawType") -> None:
        """Last chance to adjust a type after all its captures were attached."""

    # ------------------------------------------------------------- members

    def ownership_start(self, caps: dict, root: "ts.Node") -> Optional["ts.Node"]:
        """Node from which the owning type is searched (its strict ancestors)."""
        return root

    def declarator(self, node: "ts.Node", src: bytes) -> tuple[Optional[str], str, bool]:
        """(name, type suffix such as '*', is_function) for C-style declarators."""
        return None, "", False

    def default_visibility(self, owner_kind: str, member_kind: str) -> str:
        return "public"

    def visibility(self, owner_kind: str, member_kind: str, modifiers: list[str],
                   name: str, node: "ts.Node") -> str:
        for m in modifiers:
            if m in self.visibility_keywords:
                return self.visibility_keywords[m]
        return self.default_visibility(owner_kind, member_kind)

    def is_static(self, owner_kind: str, member_kind: str, modifiers: list[str]) -> bool:
        return "static" in modifiers

    def is_abstract(self, owner_kind: str, member_kind: str, modifiers: list[str],
                    has_body: bool, marker: Optional[str] = None) -> bool:
        return "abstract" in modifiers


def annotation_name(text: str) -> str:
    """'@a.b.Name(args)' -> 'a.b.Name'."""
    m = re.match(r"@?\s*([\w.:]+)", text)
    return m.group(1) if m else text
