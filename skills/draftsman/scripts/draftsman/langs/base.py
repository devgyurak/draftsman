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
from typing import TYPE_CHECKING, Callable, NamedTuple, Optional

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
    static: bool = False   # Java `import static`: members of a type (`a.B.N`, `a.B.*`)

    @property
    def local_name(self) -> str:
        return self.alias or self.path.rsplit(self.sep, 1)[-1]


class Unseen(NamedTuple):
    """A place that mentions a name the parser could not see declared."""

    file: str
    line: int
    end_line: int
    macro: Optional[str] = None   # the blanked macro it is passed to; None: a class head
                                  # inside a syntax error


@dataclass
class FileScope:
    """What name resolution needs to know about one source file."""

    file: str
    namespace: Optional[str] = None
    imports: list[Import] = field(default_factory=list)
    type_params: set[str] = field(default_factory=set)  # file-wide (Python TypeVar)
    aliases: set[str] = field(default_factory=set)      # qualified type alias names
    alias_targets: dict[str, str] = field(default_factory=dict)  # alias -> type it names
    inline_namespaces: set[str] = field(default_factory=set)    # C++ `inline namespace v1`
    # names the file may declare where the parser could not see it: simple name ->
    # namespace around it -> places (an argument of a blanked macro, a class head inside
    # a syntax error)
    unseen_types: dict[str, dict[str, list[Unseen]]] = field(default_factory=dict)
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
    # Names of those scopes in a qualified type name (`X.Companion.Inner`): the types
    # declared in one are recorded as the enclosing type's, so the name is skipped.
    static_scope_names: frozenset[str] = frozenset()

    # Node types inside a modifiers capture that carry an annotation/decorator,
    # and the field holding its name.
    annotation_nodes: frozenset[str] = frozenset()
    annotation_name_field: str = "name"
    # Nodes of the type arguments inside a type name (`Outer<T>.Inner`): no part of the name
    type_argument_nodes: frozenset[str] = frozenset()
    # Nodes a receiver in a body (`@body.ref.receiver`) may be made of, the dotted ones
    # among them too: a dotted name, not an expression (`this.x`, `a[0].B`, `new Foo(x).m`)
    receiver_part_nodes: frozenset[str] = frozenset()
    # Kinds of type that are no value: in a receiver position the name is whatever value
    # shares it, and draws nothing (a TypeScript interface beside `const Token = ...`)
    type_only_kinds: frozenset[str] = frozenset()
    # Whether a body sees the fields of the types around it by their simple names (Java's
    # `X.m()` may be a field X); in TypeScript a field is always `this.X`. An enum's own
    # constants are in scope in its bodies either way (`B = A` in a TypeScript enum)
    fields_in_scope: bool = True
    # How a dotted receiver whose head is no type and no variable is read: as a package
    # (Java's `io.netty.Foo.m()`), or, when False, through what the scope binds the head to
    # (TypeScript's `ns.Foo.m()` after `import * as ns`)
    receiver_package_heads: bool = True

    # Nodes in an annotation's arguments that name a type (`X.class`, `typeof(X)`,
    # `X::class`; see annotation_arg), and nodes that name a type or a value (`E.V`,
    # `Model`), drawn only when they turn out to be a project type.
    annotation_type_args: frozenset[str] = frozenset()
    annotation_value_args: frozenset[str] = frozenset()

    # For grammars without a modifiers node: direct children of a declaration
    # that count as modifiers, by node type or by keyword text.
    modifier_node_types: frozenset[str] = frozenset()
    modifier_keywords: frozenset[str] = frozenset()

    # Names that never need resolving: primitives and the implicit standard
    # library scope (java.lang.*, etc.).
    builtins: frozenset[str] = frozenset()

    visibility_keywords: dict[str, str] = {}

    # Query files added to `query` (queries/<name>.scm): what only this grammar has (TSX)
    extra_queries: tuple[str, ...] = ()

    # Name resolution behaviour
    parent_namespace_lookup: bool = False  # C#, C++: types of enclosing namespaces are visible
    import_suffix_match: bool = False      # Python, TS: match import paths by unique suffix
    # Whether the types and aliases of the namespaces around a type come before the file's
    # imports of one name: TypeScript's `namespace N { class Foo {} }` is a scope inside
    # the module, so its Foo hides an imported Foo (Java's single-type import comes first)
    namespaces_before_imports: bool = False
    # Java, C#, Kotlin, C++: member types of supertypes are in scope by simple name.
    # Not in Python (class bodies are not scopes) or TS (merged namespaces are not inherited)
    inherited_member_types: bool = True
    # Whether a type's own nested types are in scope inside it by simple name. Not in TS:
    # the types of a namespace merged with a class are `Foo.Inner` in the class's methods
    nested_types_in_scope: bool = True

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

    def is_varargs(self, param_node) -> bool:
        """Whether a parameter is variadic when the query cannot say (a modifier that is
        the parameter's sibling, like Kotlin's `vararg`)."""
        return False

    def type_text(self, type_node, text: str, src: bytes) -> str:
        """A member's or parameter's type text, with modifiers the grammar keeps beside
        the type node (Kotlin `suspend`, `context(A)`)."""
        return text

    def alias_target(self, alias_node, type_node, text: str) -> Optional[str]:
        """The type an alias names, given the text of its `@alias.type`; None when the
        declaration is the type itself rather than an alias."""
        return text

    def is_import(self, node) -> bool:
        """Whether an `@import*` capture really imports (C++ `using` in a class does not)."""
        return True

    def member_name(self, kind: str, name: str) -> Optional[str]:
        """The name a member is listed under (Kotlin calls every constructor `constructor`),
        or None for no member: a name no declaration can have, read inside a syntax error."""
        return name

    def body_name(self, member_name: str) -> str:
        """The name a member, as listed, is in scope by in a body (TypeScript's enum
        member `"Foo" = 1` is Foo)."""
        return member_name

    def type_name(self, node, name: str) -> str:
        """The name of a type declaration whose @name capture is not the name itself."""
        return name

    def accepts(self, filename: str) -> bool:
        """Whether a file with one of ``extensions`` is source to extract."""
        return True

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

    def library_type(self, name: str, imported: set[str], arity: Optional[int] = None,
                     external_supers: Optional[Callable[[], list[str]]] = None) -> Optional[str]:
        """Qualified id of a well-known library type ``name`` reachable through one of
        the ``imported`` namespaces, else None; ``arity`` is its number of type
        arguments when known (generic and plain versions can live apart).
        ``external_supers()`` lists the external supertypes whose nested types are in
        scope there, for languages where such a nested type would win over an import."""
        return None

    # C++: the name of a base class is in the scope of its derived classes
    base_names_in_scope: bool = False

    def owns_namespace(self, namespace: str) -> bool:
        """Whether a name missing from a namespace the project declares types in may be
        the project's own, declared where the parser could not see it (FileScope.unseen_types),
        rather than a library's. Off by default: not checked for packages."""
        return False

    def macro_declared_names(self, src: bytes) -> list[tuple[str, int, str]]:
        """(name, line, macro) for names passed to macros the preprocessing blanks, which
        may declare them (`POCO_DECLARE_EXCEPTION(API, DataException, Exception)`)."""
        return []

    def is_package_head(self, head: str, known: set[str]) -> bool:
        """Whether ``head`` in ``head.Rest`` names a package rather than a type: lower
        case by convention, or a first segment of an import or a project namespace."""
        return head[:1].islower() or head in known

    def default_import(self, name: str) -> Optional[str]:
        """Qualified id of a type the language imports into every file by default but a
        star import of another package could shadow (Kotlin java.lang.*), else None."""
        return None

    def inherited_type(self, super_id: str, name: str) -> Optional[str]:
        """The qualified name of the nested type ``name`` the external supertype ``super_id``
        passes on to its subclasses, when the language knows that library and it does;
        else None (also when it does not know)."""
        return None

    def inherited_field(self, super_id: str, name: str, static: bool = False) -> bool:
        """Whether the external type ``super_id`` is known to have a field ``name`` its
        subclasses inherit (``static``: one `import static` brings in)."""
        return False

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

    def annotation_arg(self, node, text: Callable[["ts.Node"], str]) -> Optional[tuple[str, bool]]:
        """(the type name, whether it certainly is a type) for a node of an annotation's
        arguments, ``text`` giving a node's source text: `X.class` -> ("X", True),
        `Kind.A` -> ("Kind.A", False); None to look inside the node instead."""
        if node.type in self.annotation_type_args:
            return text(node), True
        if node.type in self.annotation_value_args:
            written = text(node)
            # a dotted name, not an expression such as a call (`a.b(c)`): look inside that
            return (written, False) if _DOTTED.match(written) else None
        return None

    def annotation_type_names(self, name: str) -> list[str]:
        """The type names an annotation written ``name`` may stand for, first match wins
        (C# `[Obsolete]` is `ObsoleteAttribute`)."""
        return [name]

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


_DOTTED = re.compile(r"^[\w$]+(?:\s*\.\s*[\w$]+)*$")


def annotation_name(text: str) -> str:
    """'@a.b.Name(args)' -> 'a.b.Name'."""
    m = re.match(r"@?\s*([\w.:]+)", text)
    return m.group(1) if m else text
