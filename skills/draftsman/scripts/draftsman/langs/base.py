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
    aliased: bool = False  # a module import given its own name (Python's `import a.b as c`)
    # the namespace block it stands in (LanguageSpec.block_imports): it is looked at with
    # that namespace's types, before the namespaces around it
    block: Optional[str] = None
    # in code a build may leave out (LanguageSpec.conditional_ranges): not every build
    # resolves a name through it
    conditional: bool = False
    # C++: the namespace a using declaration stands in ("" for the file's scope; None in a
    # class or a function): a name of that namespace, which bodies look up with its types
    # (and in every file that includes it: LanguageSpec.include_visibility)
    namespace: Optional[str] = None

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
    # alias -> the namespace it is declared in, where its target is looked up ("" for the
    # top of the file; LanguageSpec.block_imports)
    alias_blocks: dict[str, str] = field(default_factory=dict)
    # aliases every file of the file's project sees (C#'s `global using X = ...`)
    global_aliases: set[str] = field(default_factory=set)
    inline_namespaces: set[str] = field(default_factory=set)    # C++ `inline namespace v1`
    # a type or alias seen only inside the namespace block that declares it -> that
    # block's first and last line (TypeScript's member a block does not export)
    block_local: dict[str, tuple[int, int]] = field(default_factory=dict)
    # the names a wildcard import of the file brings in, when it lists them (Python's
    # `__all__`); None when it lists none, or when the listing cannot be read (exports_unread)
    exports: Optional[set[str]] = None
    exports_unread: bool = False
    # top-level names the file binds more than once, one of them by a class statement
    # (LanguageSpec.rebinding_hides): no one class, also where another file imports it
    rebound: set[str] = field(default_factory=set)
    # LanguageSpec.left_out_types: types a build may declare that the parser never saw
    left_out_types: set[str] = field(default_factory=set)
    left_out_names: set[str] = field(default_factory=set)   # LanguageSpec.left_out_names
    # methods that extend a type (C#'s `this` parameter, `extension(T t)` blocks): a call of
    # one of these names may be an instance call on any value (`@body.extension`)
    extension_methods: set[str] = field(default_factory=set)
    # functions and properties the file declares at its top, which other files may name
    # (Kotlin's top-level declarations; `@body.function`, `@body.value`): a call of such a
    # function's name may be that function, and any name of such a property that property
    top_functions: set[str] = field(default_factory=set)
    top_values: set[str] = field(default_factory=set)
    # aliases declared in code a build may leave out (LanguageSpec.conditional_ranges)
    conditional_aliases: set[str] = field(default_factory=set)
    implicit_types: list[str] = field(default_factory=list)          # LanguageSpec.implicit_types
    build_types: dict[str, set[str]] = field(default_factory=dict)   # LanguageSpec.build_types
    # names a statement at its top binds as a variable (`if x: Foo = None`, `del Foo`,
    # `global Foo` in a function): no class, also where another file takes them from it
    variables: set[str] = field(default_factory=set)
    # names the file may declare where the parser could not see it: simple name ->
    # namespace around it -> places (an argument of a blanked macro, a class head inside
    # a syntax error)
    unseen_types: dict[str, dict[str, list[Unseen]]] = field(default_factory=dict)
    project: Optional[str] = None   # build project the file compiles in (C#: its .csproj)
    # names in bodies of members defined outside their type (C++'s `void Foo::bar() {}`,
    # `@body.detached`): (the type as written, the namespace the definition stands in, the
    # name), each the type's once the types are known
    detached_refs: list = field(default_factory=list)
    # the files the file includes as written (`"Poco/Foo.h"`, `<Poco/Foo.h>`; C++,
    # `@body.include`): LanguageSpec.include_visibility
    includes: list[str] = field(default_factory=list)
    # the branches of the file's conditional groups: (first line, last line, condition)
    # (LanguageSpec.branch_ranges)
    branches: list[tuple[int, int, str]] = field(default_factory=list)
    # namespace aliases of the file's scope: name -> the namespace (C++'s `namespace fs =
    # a::inner;`, `@body.nsalias`)
    namespace_aliases: dict[str, str] = field(default_factory=dict)
    # the types the file declares without defining them (C++'s `struct Fwd;`, `@body.forward`)
    forward_types: set[str] = field(default_factory=set)
    # of those, the ones declared outside every `#if` branch of the file (`class
    # PollSetImpl;`): the file sees a type of the id in every build
    plain_forwards: set[str] = field(default_factory=set)
    # whether the file includes a path a macro makes (C++'s `#include APP_UTIL`,
    # `@body.include_unknown`): what it sees is not known
    unknown_include: bool = False
    # every namespace the file opens a block of, also one declaring no type (C++'s
    # `namespace Keywords { int now(); }`): LanguageSpec.values_hide_types
    declared_namespaces: set[str] = field(default_factory=set)
    # alias -> its own type parameters (C++'s `template <class K> using M = map<K, Hash>`)
    alias_tparams: dict[str, set[str]] = field(default_factory=dict)


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
    # The same in the bodies of its members. Not in Python, where a class body is a scope
    # of its own statements but not of the functions defined in it (a method writes
    # `Outer.Inner`), though its annotations see it
    nested_types_in_bodies: bool = True
    # Whether a field's initializer runs in the class body as a scope, where the names the
    # class binds (its fields, methods and nested types, and any name its statements bind:
    # `if x: Foo = 1`, `from m import Bar as Foo`) hide a type of the same name (Python's
    # `value = Foo` after `Foo = 1` in the class body)
    initializers_in_class_scope: bool = False
    # Whether a name a module binds more than once at its top (two class statements, a
    # class and an import) draws nothing in a body, as a variable would: which binding a
    # body sees depends on what ran (Python's `try: from x import Foo` / `except: class Foo`)
    rebinding_hides: bool = False
    # Whether, under a base class outside the sources the language's table does not know
    # (C#'s EF Core DbContext), a receiver draws nothing: the base may have any member
    unknown_bases_hide: bool = False
    # Whether a type sees by simple name the nested types of its superclasses only: not
    # those of an interface, nor those of a superclass's companion object (Kotlin); bodies
    # only
    class_nested_only: bool = False
    # Whether importing a declaration under another name (`import p.Money as Coin`) hides
    # its own name in the file, also through a star import and the file's package (Kotlin);
    # bodies only
    alias_import_hides: bool = False
    # Whether a file-local type (LanguageSpec.file_local) of one id that several files
    # declare is still that id where one of them names it: Kotlin's `private class` of each
    # platform's file, which ir.json makes one type (C#'s two `file class Local` are not)
    file_local_copies: bool = False
    # Whether a type declared file-local (LanguageSpec.file_local_node: C++'s anonymous
    # namespace) is a candidate for a name in a body of its file only: elsewhere the lookup
    # goes on past it (bodies only)
    file_local_bodies: bool = False
    # Whether a variable, a parameter, a field or a method of a type around hides a type of
    # its name also where only a type may stand (C++: one scope for both), and the parts of
    # a qualified name are types or namespaces only (`A::B::c`: no variable is looked up
    # before `::`), of which the longest prefix that is a project type is drawn; a call of
    # a qualified name is read so too. A qualifier that a namespace around may be draws
    # nothing
    values_hide_types: bool = False
    # Whether a type is a candidate for a name in a body only where its file is included,
    # directly or through others, by the body's file (C++: a translation unit sees what it
    # includes; another program's class of the name is none). Bodies only
    include_visibility: bool = False
    # Whether a name of a declaration (a base, a member's or a parameter's type) is looked
    # up as a name in a body is (`::D`, a namespace alias of the file, the classes around
    # first, using declarations where they stand, include visibility; an alias's own
    # template parameters name no type), and is unresolved, with the reason, where a body
    # draws nothing (C++, issue #7). A type the file cannot tell whether it sees (one its
    # includer brings in) is still drawn
    declared_like_bodies: bool = False
    # When one node is captured as names of several positions, the one kept, by position
    # (C++: what is called before what only a type may be)
    ref_priority: tuple[str, ...] = ()
    # Whether a supertype outside the sources may hide a name in a body by a member of it
    # (LanguageSpec.outside_member): a value (`Foo(`, `Foo.x`) under any such supertype, a
    # type under a superclass, whose nested types the class sees (Kotlin)
    outside_supers_hide: bool = False
    # Whether a field or property whose type has its name (C#'s `Order Order`) leaves the
    # name a type before a static member (`Order.Create()`), and a variable before any
    # other (`Order.Total`): C#'s "Color Color" rule
    color_color: bool = False
    # Whether a name in a body that is an alias the file declares of one project type
    # (C#'s `using O = Shop.Order;`) draws a relation to that type; a TypeScript alias
    # draws nothing in a body
    body_aliases: bool = False
    # Whether a type alias is a declaration every file may name, as a type is (Kotlin's
    # `typealias`): a name of it in a body draws a relation to the class it names directly
    # (`typealias Cash = Money`), looked up where the alias is declared; one of a generic
    # type or a function type draws nothing
    alias_declarations: bool = False
    # Whether an import in a namespace block belongs to that namespace (C#'s `namespace A {
    # using B; }`): looked at after A's types and before the namespaces around A
    block_imports: bool = False
    # Whether the first part of a qualified name is looked up as a simple name is, a type or
    # a namespace from the innermost scope out (C#: `Models.Order` in `namespace App.Web` is
    # App.Models.Order when App.Models exists, and `Lib.Order` in `namespace Shop.Sub` is
    # the class Shop.Lib's nested Order before a namespace Lib)
    qualified_heads_in_scope: bool = False
    # Whether a namespace around the code that is a package's (LanguageSpec.package_namespace:
    # C#'s `namespace CommunityToolkit.Mvvm.Input.Mine` in a project that references
    # CommunityToolkit.Mvvm) and the table does not know is taken for one outside the
    # sources: its types may hide any name found further out, which a body then draws
    # nothing from
    enclosing_outside_hides: bool = False
    # Whether the number of type arguments written chooses the type (C#'s `Repo<int>` is
    # no `Repo`), and a project the file's project does not see holds no candidate: the
    # lookup passes such a type over (Resolver.resolve, issue #7)
    arity_selects: bool = False
    # Whether a member of the class (or of a base) hides a name in an attribute's argument
    # (C#'s `[Obsolete(nameof(Order))]` beside a property Order)
    members_hide_annotation_args: bool = False
    # The prefix that roots a name at the global namespace in a declaration (C#'s `global::`)
    rooted_prefix: Optional[str] = None
    # Whether `import a.b` binds the head `a`, so that `a.b.Foo()` in a body goes through it
    # (Python)
    module_imports_bind_heads: bool = False
    # Whether a dotted receiver reaches a submodule as an attribute of its package
    # (`models.base.ModelBase()`) only when the file imports that submodule: in Python the
    # attribute exists once something imported it, which is no certainty
    submodules_need_import: bool = False
    # Whether a suffix match of an import path (import_suffix_match) must not drop a
    # package: Python's `import jinja2` is no `django.template.backends.jinja2`, since every
    # directory above it is a package (its __init__ is a source); only directories that
    # are none (`src/`) may be dropped
    suffix_skips_no_package: bool = False
    # Whether an import inside a function or a class binds its names there only, not in the
    # file (Python's `def helper(): from gui import Button`)
    local_imports: bool = False

    # ------------------------------------------------------------- files

    def preprocess(self, src: bytes) -> bytes:
        """Source cleanup before parsing; must keep byte offsets (C++ macros)."""
        return src

    def conditional_ranges(self, src: bytes) -> list[tuple[int, int]]:
        """Byte ranges of the code preprocess keeps that a build may leave out (C#'s first
        branch of an `#if`): a type declared there is no certain type for a body."""
        return []

    def branch_ranges(self, src: bytes) -> list[tuple[int, int, int, int, str]]:
        """(first byte, end byte, first line, last line, condition) of each branch of a
        conditional group (C++'s `#if`/`#elif`/`#else`, include guards aside), innermost
        first: a type declared in one is a candidate for a name in a body of that branch,
        or of a branch of the same condition as written (`#if defined(POCO_HAVE_IPv6)`),
        only."""
        return []

    def left_out_types(self, src: bytes) -> set[str]:
        """Simple names of the types declared in the code preprocess blanks (C#'s `#elif`
        and `#else` branches): a body name of one of them may be that type in a build."""
        return set()

    def left_out_names(self, src: bytes) -> set[str]:
        """Other names declared there, which hide a type in this file's bodies in a build
        (C#'s fields and aliases)."""
        return set()

    def unbuilt_ranges(self, src: bytes, path: Path, root: Path) -> list[tuple[int, int]]:
        """Byte ranges of code no build compiles (C#'s `#if false`) or only a platform's
        build does, which the answer key cannot compile (a .NET MAUI app's `Platforms/iOS/`,
        its `#if ANDROID`): no name in them is read for a body relation."""
        return []

    def subtype_sees(self, modifiers: list[str]) -> bool:
        """Whether a subtype sees by its simple name a nested type or field a supertype
        declares with these modifiers (or visibility); not C#'s private ones."""
        return True

    def file_local(self, modifiers: list[str]) -> bool:
        """Whether a type with these modifiers is seen in its own file only (C#'s `file`)."""
        return False

    def outside_known(self, type_id: str) -> bool:
        """Whether the language's table of libraries knows the type outside the sources
        (C#'s .NET and ASP.NET Core); a base class it does not know may pass on anything."""
        return False

    def outside_namespace(self, namespace: str) -> Optional[frozenset[str]]:
        """The types a namespace outside the sources declares, when the table knows it."""
        return None

    def package_namespace(self, namespace: str, project: Optional[str]) -> bool:
        """Whether a namespace is a package's the build project (FileScope.project)
        references: C#'s is the package's id or below it (`CommunityToolkit.Mvvm.Input`)."""
        return False

    def outside_namespace_exists(self, namespace: str) -> bool:
        """Whether the table knows a namespace of that name outside the sources, also one
        that only holds other namespaces (C#'s `Microsoft.Extensions`)."""
        return False

    def internal_type(self, modifiers: list[str], nested: bool) -> bool:
        """Whether a type declared with these modifiers is seen only in its own build project
        (C#'s internal, the default of a top-level type)."""
        return False

    def internals_visible(self, owner_project: str, project: str) -> bool:
        """Whether ``project`` sees ``owner_project``'s internal types (C#'s
        InternalsVisibleTo)."""
        return False

    def declaration_read(self, decl_node: "ts.Node") -> bool:
        """Whether a declaration captured `@body.declared_type` is read as one where it
        stands (C#: an `out` argument, a deconstruction's tuple), or is what the language
        reads otherwise there, which names no type."""
        return True

    def implicit_variables(self, node: "ts.Node") -> frozenset[str]:
        """Variables the language binds around a name in a body without a declaration in
        the source (C#'s `value` in a setter, `field` in a property's accessor)."""
        return frozenset()

    def receiver_types(self, node: "ts.Node", text: str, src: bytes) -> list[str]:
        """The types an extension's receiver (`@body.receiver`, written ``text``) stands
        for, whose members are names in its body: the type written; Kotlin's type
        parameter its bounds (`fun <T : Ctx> T.ext()`)."""
        return [text]

    def top_function(self, node: "ts.Node") -> bool:
        """Whether a `@body.function` capture is a function of a namespace (C++: not one of
        a class's or a block's `#if` branch)."""
        return True

    def unreadable(self, node: "ts.Node") -> bool:
        """Whether a name a `@body.ref.*` captures stands where the parse cannot be trusted
        (C++: a function definition inside a block, an `#if` the grammar could not close)."""
        return False

    def alias_params(self, node: "ts.Node") -> list[str]:
        """The type parameters of the alias whose name is ``node`` (C++'s alias template)."""
        return []

    def ref_text(self, node: "ts.Node", text: str) -> str:
        """The name a `@body.ref.*` capture is, its parts joined by the separator (C++'s
        `::Helper` keeps its `::`: the global namespace's)."""
        return text

    def ref_position(self, node: "ts.Node", position: str) -> str:
        """The position of a name a `@body.ref.*` captures (C++: a block-scope function
        declaration's parameter types, `Lock l(Tag);`, where a variable may stand)."""
        return position

    def detached_owner(self, node: "ts.Node", src: bytes) -> Optional[tuple[str, str, list[str]]]:
        """For a member defined outside its type (`@body.detached`: C++'s `void
        Foo::bar() {}`, `int Foo::x = 1;`): (the type as written, the member's name, the
        type parameters of the definition), or None when it is none (a free function, a
        template specialisation's member)."""
        return None

    def scoped_enum(self, node: "ts.Node") -> bool:
        """Whether the enum declared at ``node`` keeps its constants to itself (C++'s
        `enum class`); an unscoped one's are names of the scope around it."""
        return False

    def file_local_node(self, node: "ts.Node") -> bool:
        """Whether a type declared at ``node`` is seen in its file only (C++'s anonymous
        namespace; LanguageSpec.file_local_bodies)."""
        return False

    def member_of(self, node: "ts.Node") -> Optional["ts.Node"]:
        """The declaration a node outside it belongs to (Kotlin's accessor on the line
        after its property, which the grammar puts beside it), or None."""
        return None

    def implicit_types(self, root_node: "ts.Node") -> list[str]:
        """Ids of the types a file declares without a declaration (C#'s `Program` of
        top-level statements): one per build project that has such a file."""
        return []

    def build_types(self, path: Path, root: Path) -> dict[str, set[str]]:
        """namespace -> simple names of the types the build generates outside the sources
        for the file's project (C#'s from `<Protobuf Include>`): they hide what the
        namespaces around and the imports bring in, as declared types do."""
        return {}

    def generated_fields(self, node: "ts.Node", src: bytes) -> list[str]:
        """The members a source generator declares in the type around ``node``, an
        attribute captured as `@body.generated` (C#'s `[ObservableProperty] string name`
        declares `Name`): they hide a type in its bodies as fields do."""
        return []

    def companion_fields(self, path: Path) -> dict[str, set[str]]:
        """Simple name of a type the file declares -> members a file beside it declares
        in that type's generated part (C#'s `X.razor` `@inject`, `X.xaml` `x:Name` for
        `X.razor.cs`, `X.xaml.cs`): they hide a type in its bodies as fields do."""
        return {}

    def sees_declaration(self, scope: FileScope, target: str, namespace: Optional[str],
                         declared: list[tuple[str, Optional[str]]]) -> bool:
        """Whether code of the file ``scope`` is, which the name ``target`` (a project
        type of ``namespace``) was resolved for, surely sees that type, declared in the files
        ``declared`` ([(file, project)]): Kotlin Multiplatform's platform source sets see
        their own declarations and the common ones, not one another's."""
        return True

    def outside_member(self, super_id: Optional[str], name: str, nested_only: bool) -> bool:
        """Whether a supertype outside the sources (its id, None when not known) may have a
        member ``name`` (LanguageSpec.outside_supers_hide): a nested type with
        ``nested_only``, else also a property or function."""
        return False

    def outside_instance_member(self, type_id: Optional[str], name: str) -> bool:
        """Whether a value of a type outside the sources (an extension's receiver) has a
        property or function ``name`` as far as the language knows the type."""
        return False

    def outside_functions(self, scope: FileScope) -> bool:
        """Whether the file's star imports bring in functions of any name, of which a call
        of a class's name may be one (Kotlin/Native's platform libraries, C's functions)."""
        return False

    def project_references(self, project: str) -> Optional[frozenset[str]]:
        """The build projects whose types code of ``project`` (FileScope.project) sees: it
        and those it references, followed through (C#'s <ProjectReference>). None where
        every project sees every other."""
        return None

    def body_name_text(self, text: str) -> str:
        """The name an identifier in a body is, as written (C#'s `@Order` is `Order`)."""
        return text

    def arity(self, part: "ts.Node") -> Optional[int]:
        """How many type arguments a part of a name in a body is written with (C#'s
        `Repo<int>`: 1, `Repo`: 0), or None where a type's arity does not choose it."""
        return None

    def init_via(self, node: "ts.Node", src: bytes) -> Optional[str]:
        """The `via` of a body no listed member holds (`@body.init` without `.name`), or
        None for its text before `{` (Java's `static {}`)."""
        return None

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

    def star_exports(self, name: str, scope: FileScope, certain: bool = False) -> bool:
        """Whether a wildcard import of the module of ``scope`` brings in its ``name``
        (FileScope.exports); ``certain``: only if that is known, as in a body."""
        return True

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

    def local_block(self, decl_node: "ts.Node") -> Optional["ts.Node"]:
        """The namespace block a type or alias declaration is seen in alone, or None when
        every block of its namespace sees it."""
        return None

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
