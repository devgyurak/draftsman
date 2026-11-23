from __future__ import annotations

import json
import os
import re
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path
from typing import Optional

from .base import SKIP_DIRS, LanguageSpec

# The namespaces the .NET SDK imports into every file when <ImplicitUsings> is enable/true
# (learn.microsoft.com/dotnet/core/project-sdk/overview#implicit-using-directives).
# Other SDKs (Razor, BlazorWebAssembly) document no list, so none is assumed for them.
_BASE_USINGS = ("System", "System.Collections.Generic", "System.IO", "System.Linq",
                "System.Net.Http", "System.Threading", "System.Threading.Tasks")
_HOSTING = ("Microsoft.Extensions.Configuration", "Microsoft.Extensions.DependencyInjection",
            "Microsoft.Extensions.Hosting", "Microsoft.Extensions.Logging")
_SDK_USINGS = {
    "Microsoft.NET.Sdk": _BASE_USINGS,
    "Microsoft.NET.Sdk.Web": _BASE_USINGS + (
        "System.Net.Http.Json", "Microsoft.AspNetCore.Builder", "Microsoft.AspNetCore.Hosting",
        "Microsoft.AspNetCore.Http", "Microsoft.AspNetCore.Routing") + _HOSTING,
    "Microsoft.NET.Sdk.Worker": _BASE_USINGS + _HOSTING,
    "Microsoft.NET.Sdk.WindowsDesktop": _BASE_USINGS,
}
# SDKs that import another one (and with it its implicit usings), read from their sources:
# Aspire.AppHost.Sdk (github.com/microsoft/aspire, src/Aspire.AppHost.Sdk/SDK/Sdk.in.props)
# adds no <Using>; MSTest.Sdk (github.com/microsoft/testfx, src/Package/MSTest.Sdk/Sdk)
# adds one, Microsoft.VisualStudio.TestTools.UnitTesting, only with UseVSTest.
_SDK_IMPORTS = {"Aspire.AppHost.Sdk": "Microsoft.NET.Sdk", "MSTest.Sdk": "Microsoft.NET.Sdk"}
_WINFORMS = ("System.Drawing", "System.Windows.Forms")
_WPF_REMOVED = ("System.IO", "System.Net.Http")


# conditional-compilation lines. tree-sitter accepts them between members, but not inside
# a base list, a parameter list, an expression, or around a second method header
_CONDITIONAL = re.compile(rb"^[ \t]*#[ \t]*(if|elif|else|endif)\b")


# a type declared in blanked code (LanguageSpec.left_out_types)
_TYPE_DECL = re.compile(rb"\b(?:class|struct|interface|record|enum)[ \t]+(?:class[ \t]+|struct[ \t]+)?"
                        rb"([A-Za-z_][A-Za-z0-9_]*)")


_MEMBER_DECL = re.compile(rb"\b(?:using[ \t]+)?([A-Za-z_][A-Za-z0-9_]*)[ \t]*"
                          rb"(?:;|=(?![=>])|\{[ \t\r\n]*(?:get|set|init)\b|=>)")


def _blanked(src: bytes) -> bytes:
    """The code preprocess blanks that some build compiles: #elif and #else branches, not
    a branch no build takes (`#if false`, the #else of `#if true`)."""
    return b"\n".join(line for line, kept, _, dead in _lines(src) if not kept and not dead
                      and not _CONDITIONAL.match(line))


def _lines(src: bytes):
    """(line, kept, a build may leave it out, no build compiles it) for each line. Of each
    #if one branch is read: the first whose condition is not false whatever the symbols
    (`#if false ... #else` reads the #else). A directive line is not kept."""
    # per #if: [active, inside, dead around it, a branch read, an earlier condition that
    # depends on a symbol, one true whatever the symbols]
    stack: list[list] = []
    active, inside, dead = True, False, False
    for line in src.split(b"\n"):
        m = _CONDITIONAL.match(line)
        if not m:
            yield line, active, inside, dead
            continue
        kw = m.group(1)
        if kw == b"if":
            stack.append([active, inside, dead, False, False, False])
        if kw == b"endif":
            if stack:
                active, inside, dead = stack.pop()[:3]
            yield line, False, inside, dead
            continue
        if not stack:   # an #elif or #else without its #if
            yield line, False, inside, dead
            continue
        frame = stack[-1]
        value = True if kw == b"else" else _without_platforms(
            line[m.end():].decode("utf8", "replace"), False)
        read = not frame[3] and value is not False
        active = frame[0] and read
        inside = frame[1] or value is None or frame[4]
        dead = frame[2] or value is False or frame[5]
        frame[3] = frame[3] or read
        frame[4] = frame[4] or value is None
        frame[5] = frame[5] or value is True
        yield line, False, frame[1], frame[2]


# the symbols a platform's target framework defines (`net11.0-ios`: IOS, and
# IOS15_0_OR_GREATER and the like), none of which a plain `net11.0` build defines
_PLATFORM_SYMBOL = re.compile(r"(ANDROID|IOS|MACCATALYST|MACOS|TVOS|WINDOWS|TIZEN)"
                              r"(\d+(_\d+)*_OR_GREATER)?")
# the folders a .NET MAUI app compiles for one platform only
_PLATFORM_FOLDERS = ("Android", "iOS", "MacCatalyst", "Windows", "Tizen")


def _without_platforms(condition: str, platforms: bool = True) -> Optional[bool]:
    """An #if condition with every platform symbol false (``platforms``; else they are
    unknown, as any other symbol): True, False, or None when it depends on a symbol."""
    tokens = re.findall(r"&&|\|\||==|!=|[!()]|[A-Za-z_][A-Za-z0-9_]*", condition.split("//")[0])
    at = 0

    def peek():
        return tokens[at] if at < len(tokens) else None

    def take():
        nonlocal at
        at += 1
        return tokens[at - 1]

    def unary():
        if peek() == "!":
            take()
            v = unary()
            return None if v is None else not v
        if peek() == "(":
            take()
            v = disjunction()
            if peek() == ")":
                take()
            return v
        t = take() if peek() is not None else ""
        if t == "true":
            return True
        if t == "false" or platforms and _PLATFORM_SYMBOL.fullmatch(t):
            return False
        return None

    def equality():
        v = unary()
        while peek() in ("==", "!="):
            negate = take() == "!="
            w = unary()
            v = None if v is None or w is None else (v == w) != negate
        return v

    def conjunction():
        v = equality()
        while peek() == "&&":
            take()
            w = equality()
            v = False if v is False or w is False else (None if v is None or w is None else True)
        return v

    def disjunction():
        v = conjunction()
        while peek() == "||":
            take()
            w = conjunction()
            v = True if v is True or w is True else (None if v is None or w is None else False)
        return v

    return disjunction()


@lru_cache(maxsize=None)
def _references(project: str) -> Optional[frozenset[str]]:
    """The .csproj files a project sees the types of: itself and its <ProjectReference>s,
    followed through; None for no project file."""
    start = Path(project)
    if start.suffix != ".csproj" or _msbuild(start) is None:
        return None
    seen, todo = set(), [start.resolve()]
    while todo:
        cur = todo.pop()
        if cur in seen:
            continue
        seen.add(cur)
        doc = _msbuild(cur)
        for el in doc.iter() if doc is not None else ():
            if _local(el.tag) == "ProjectReference" and el.get("Include"):
                todo.append((cur.parent / el.get("Include").replace("\\", "/")).resolve())
    return frozenset(str(p) for p in seen)


@lru_cache(maxsize=None)
def _framework() -> dict:
    """langs/csharp_framework.json: what .NET's and ASP.NET Core's reference assemblies
    declare (`bench/roslyn_oracle/oracle.py framework` writes it)."""
    with open(Path(__file__).with_name("csharp_framework.json")) as f:
        return json.load(f)


@lru_cache(maxsize=None)
def _framework_namespaces() -> dict[str, frozenset]:
    return {ns: frozenset(names) for ns, names in _framework()["namespaces"].items()}


@lru_cache(maxsize=None)
def _framework_namespace_parents() -> frozenset:
    """The table's namespaces and every namespace they are in (`Microsoft.Extensions`)."""
    out = set()
    for ns in _framework()["namespaces"]:
        parts = ns.split(".")
        out.update(".".join(parts[:i]) for i in range(1, len(parts) + 1) if ns)
    return frozenset(out)


@lru_cache(maxsize=None)
def _framework_types() -> frozenset:
    return frozenset(f"{ns}.{n}" if ns else n
                     for ns, names in _framework()["namespaces"].items() for n in names)


@lru_cache(maxsize=None)
def _assembly_name(project: Path) -> str:
    doc = _msbuild(project)
    names = [el.text.strip() for el in doc.iter() if _local(el.tag) == "AssemblyName"
             and el.text] if doc is not None else []
    return names[-1] if names else project.stem


@lru_cache(maxsize=None)
def _friends(project: Path) -> frozenset:
    """The assemblies a project's InternalsVisibleTo names: <InternalsVisibleTo Include>
    items, `[assembly: InternalsVisibleTo("Name")]` in its sources."""
    doc = _msbuild(project)
    out = {el.get("Include").split(",")[0].strip() for el in doc.iter()
           if _local(el.tag) == "InternalsVisibleTo" and el.get("Include")} if doc is not None \
        else set()
    for dirpath, dirnames, filenames in os.walk(project.parent):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and d not in ("bin", "obj")]
        for f in filenames:
            if f.endswith(".cs"):
                try:
                    text = Path(dirpath, f).read_text(encoding="utf-8-sig", errors="replace")
                except OSError:
                    continue
                out.update(n.split(",")[0].strip() for n in re.findall(
                    r'InternalsVisibleTo\s*\(\s*"([^"]+)"', text))
    return frozenset(out)


@lru_cache(maxsize=None)
def _razor_types(project: Path) -> tuple[tuple[str, frozenset], ...]:
    """(namespace, class names) of the components the project's .razor files declare: a
    class named after the file, in its `@namespace`, else the nearest `_Imports.razor`'s
    with the folders below it, else the root namespace with the folders."""
    doc = _msbuild(project)
    roots = [el.text.strip() for el in doc.iter() if _local(el.tag) == "RootNamespace"
             and el.text] if doc is not None else []
    root_ns = roots[-1] if roots else re.sub(r"[^A-Za-z0-9_.]", "_", project.stem)
    out: dict[str, set[str]] = {}
    for dirpath, dirnames, filenames in os.walk(project.parent):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and d not in ("bin", "obj")]
        for f in filenames:
            if not f.endswith(".razor") or f == "_Imports.razor":
                continue
            folder = Path(dirpath)
            try:
                own = re.search(r"^\s*@namespace\s+([\w.]+)", Path(folder, f).read_text(
                    encoding="utf-8-sig", errors="replace"), re.M)
            except OSError:
                continue
            ns = own.group(1) if own else _razor_namespace(folder, project.parent, root_ns)
            out.setdefault(ns, set()).add(re.sub(r"\W", "_", f[:-len(".razor")]))
    return tuple((ns, frozenset(n)) for ns, n in out.items())


def _razor_namespace(folder: Path, top: Path, root_ns: str) -> str:
    """A component's namespace from its folder: the nearest `_Imports.razor` `@namespace`
    above it, then the folders below that one, else the root namespace and the folders."""
    rel = folder.relative_to(top).parts
    for k in range(len(rel), -1, -1):
        imports = top.joinpath(*rel[:k], "_Imports.razor")
        try:
            m = re.search(r"^\s*@namespace\s+([\w.]+)", imports.read_text(
                encoding="utf-8-sig", errors="replace"), re.M)
        except OSError:
            continue
        if m:
            return ".".join([m.group(1), *rel[k:]])
    return ".".join([root_ns, *(re.sub(r"\W", "_", p) for p in rel)])


@lru_cache(maxsize=None)
def _uses_maui(project: Path) -> bool:
    for p in (project, _build_props(project.parent)):
        doc = _msbuild(p) if p else None
        if doc is not None and any(_local(el.tag) == "UseMaui" and (el.text or "").strip().lower()
                                   == "true" for el in doc.iter()):
            return True
    return False


@lru_cache(maxsize=None)
def _protobuf_types(project: Path) -> tuple[tuple[str, frozenset], ...]:
    """(namespace, type names) Grpc.Tools generates for the project's `<Protobuf Include>`
    items: each .proto's top-level messages and enums, a class per service and
    `<File>Reflection`, in its `csharp_namespace` (or its package, each part capitalized).
    Not for items with CompileOutputs="false", whose generated code is in the sources."""
    doc = _msbuild(project)
    out: dict[str, set[str]] = {}
    for el in doc.iter() if doc is not None else ():
        if _local(el.tag) != "Protobuf" or not el.get("Include") \
                or el.get("CompileOutputs", "").lower() == "false":
            continue
        proto = project.parent / el.get("Include").replace("\\", "/")
        try:
            text = proto.read_text(encoding="utf-8-sig")
        except OSError:
            continue
        text = re.sub(r"//[^\n]*|/\*.*?\*/", "", text, flags=re.S)
        ns = re.search(r'option\s+csharp_namespace\s*=\s*"([^"]+)"', text)
        package = re.search(r"^\s*package\s+([\w.]+)\s*;", text, re.M)
        namespace = ns.group(1) if ns else ".".join(
            p[:1].upper() + p[1:] for p in package.group(1).split(".")) if package else ""
        names = out.setdefault(namespace, set())
        depth = 0
        for m in re.finditer(r"\b(message|enum|service)\s+(\w+)|[{}]", text):
            if m.group(0) == "{":
                depth += 1
            elif m.group(0) == "}":
                depth -= 1
            elif depth == 0:
                names.add(m.group(2))
        stem = "".join(p[:1].upper() + p[1:] for p in re.split(r"[_.\-]", proto.stem) if p)
        names.add(f"{stem}Reflection")
    return tuple((ns, frozenset(n)) for ns, n in out.items())


def _razor_members(text: str) -> set[str]:
    """The members a .razor file declares in its component class: `@inject T Name`, and
    the fields and properties of its @code and @functions blocks (any name before `;`,
    `=`, `{ get` or `=>` there, which may take in a local or two: those only hide)."""
    names = set(re.findall(r"^\s*@inject\s+.+?\s+(\w+)\s*$", text, re.M))
    for block in re.finditer(r"@(?:code|functions)\s*\{", text):
        depth, at = 1, block.end()
        while depth and at < len(text):
            depth += {"{": 1, "}": -1}.get(text[at], 0)
            at += 1
        names |= set(re.findall(r"(\w+)\s*(?:;|=(?!=)|\{\s*(?:get|set|init)\b|=>)",
                                text[block.end():at]))
    return names


def _blank(line: bytes) -> bytes:
    return re.sub(rb"[^\r]", b" ", line)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]   # old-style projects carry an XML namespace


def _msbuild(path: Path) -> Optional[ET.Element]:
    try:
        return ET.parse(path).getroot()
    except (OSError, ET.ParseError):
        return None


@lru_cache(maxsize=None)
def _project_file(directory: Path) -> Optional[Path]:
    """The .csproj a file in ``directory`` compiles in: the nearest one above it."""
    projects = sorted(directory.glob("*.csproj"))
    if len(projects) == 1:
        return projects[0]
    if projects or directory.parent == directory:
        return None   # none at the top, or several: not knowable from the files
    return _project_file(directory.parent)


@lru_cache(maxsize=None)
def _build_props(directory: Path) -> Optional[Path]:
    """Directory.Build.props, which MSBuild reads from the nearest directory above."""
    props = directory / "Directory.Build.props"
    if props.is_file():
        return props
    return None if directory.parent == directory else _build_props(directory.parent)


@lru_cache(maxsize=None)
def _linked_files(root: Path) -> dict[Path, tuple[Path, ...]]:
    """Files a .csproj below ``root`` compiles from outside its own directory
    (`<Compile Include="..\\Shared\\X.cs" Link="..."/>`) -> those projects."""
    links: dict[Path, list[Path]] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(f for f in filenames if f.endswith(".csproj")):
            project = Path(dirpath) / name
            doc = _msbuild(project)
            if doc is None:
                continue
            for el in doc.iter():
                if _local(el.tag) != "Compile" or not el.get("Include"):
                    continue
                for pattern in el.get("Include").split(";"):
                    pattern = pattern.strip().replace("\\", "/")
                    if not pattern or "$(" in pattern:
                        continue
                    hits = (project.parent.glob(pattern) if any(c in pattern for c in "*?[")
                            else [project.parent / pattern])
                    for hit in hits:
                        hit = hit.resolve()
                        if hit.is_file() and project not in links.setdefault(hit, []):
                            links[hit].append(project)
    return {f: tuple(ps) for f, ps in links.items()}


@lru_cache(maxsize=None)
def _project_usings(project: Path) -> tuple[tuple[str, str], ...]:
    """(namespace, origin) every file of ``project`` sees without a `using` of its own."""
    root = _msbuild(project)
    if root is None:
        return ()
    # every SDK the project uses: `Sdk="A;B/1.0"`, <Sdk Name="..."/>, <Import Sdk="..."/>
    named = (root.get("Sdk") or "").split(";")
    named += [el.get("Name") or el.get("Sdk") or "" for el in root.iter()
              if _local(el.tag) in ("Sdk", "Import") and (el.get("Name") or el.get("Sdk"))]
    sdks: list[str] = []
    for text in named:
        sdk = text.split("/")[0].strip()   # `Aspire.AppHost.Sdk/13.6.0`
        while sdk and sdk not in sdks:
            sdks.append(sdk)
            sdk = _SDK_IMPORTS.get(sdk, "")
    props: dict[str, str] = {}
    includes: list[str] = []
    special: list[tuple[str, str]] = []   # <Using Alias>, <Using Static>
    removes: set[str] = set()
    # Directory.Build.props is evaluated first; the project file overrides it
    docs = [d for d in (_msbuild(p) for p in [_build_props(project.parent)] if p) if d is not None]
    for doc in docs + [root]:
        for el in doc.iter():
            tag = _local(el.tag)
            if tag in ("ImplicitUsings", "UseWPF", "UseWindowsForms", "UseVSTest") and el.text:
                props[tag] = el.text.strip().lower()
            elif tag == "Using":
                if el.get("Include") and el.get("Alias"):
                    special.append((el.get("Include").strip(), f"alias={el.get('Alias').strip()}"))
                elif el.get("Include") and el.get("Static", "").lower() == "true":
                    special.append((el.get("Include").strip(), "static"))
                elif el.get("Include"):
                    includes.append(el.get("Include").strip())
                if el.get("Remove"):
                    removes.add(el.get("Remove").strip())
    known = [sdk for sdk in sdks if sdk in _SDK_USINGS]
    implicit: list[str] = []
    if props.get("ImplicitUsings") in ("enable", "true") and known:
        for sdk in known:
            implicit += _SDK_USINGS[sdk]
        if props.get("UseWindowsForms") == "true":
            implicit += _WINFORMS
        if props.get("UseWPF") == "true":
            implicit = [n for n in implicit if n not in _WPF_REMOVED]
        if "MSTest.Sdk" in sdks and props.get("UseVSTest") == "true":
            implicit.append("Microsoft.VisualStudio.TestTools.UnitTesting")
    label = ""
    if known:   # name the SDK whose list it is, and the one that brought it in
        label = f"{known[0]} implicit usings" + (f" (via {sdks[0]})" if sdks[0] != known[0] else "")
    out = {n: label for n in dict.fromkeys(implicit)}
    for n in includes:
        out.setdefault(n, "<Using> items")
    return tuple((n, origin) for n, origin in out.items() if n not in removes) + tuple(
        (n, "<Using> items", kind) for n, kind in special)

# type keywords: visible everywhere
_BUILTINS = {
    "bool", "byte", "sbyte", "char", "decimal", "double", "float", "int", "uint", "nint",
    "nuint", "long", "ulong", "short", "ushort", "object", "string", "void", "dynamic",
    "var",
}

# well-known library types by the namespace that holds them (a `*` marks the namespace of
# the generic version, so `IComparer<T>` and `IComparer` are told apart by their arguments). A name is taken to be one
# of these only when the file imports exactly one of its namespaces (`using`, implicit or
# global usings); otherwise it stays unresolved, never a guessed `System.X`.
_SYSTEM = (
    "Object", "String", "Boolean", "Byte", "Char", "Decimal", "Double", "Single", "Int16",
    "Int32", "Int64", "UInt16", "UInt32", "UInt64", "DateTime", "DateTimeOffset", "DateOnly",
    "TimeOnly", "TimeSpan", "Guid", "Uri", "Type", "Exception", "ArgumentException",
    "ArgumentNullException", "ArgumentOutOfRangeException", "InvalidOperationException",
    "NotSupportedException", "NotImplementedException", "ObjectDisposedException",
    "FormatException", "Attribute", "EventArgs", "EventHandler", "Action", "Func",
    "Predicate", "Delegate", "Enum", "Array", "Math", "Random", "Version", "Tuple",
    "ValueTuple", "IDisposable", "IAsyncDisposable", "IEquatable", "IComparable",
    "ICloneable", "IFormattable", "IFormatProvider", "IServiceProvider", "IObservable",
    "IObserver", "IProgress", "Lazy", "Nullable", "Span", "ReadOnlySpan", "Memory",
    "ReadOnlyMemory", "StringComparer", "StringComparison",
)
_LIBRARY: dict[str, tuple[str, ...]] = {name: ("System",) for name in _SYSTEM}
_LIBRARY.update({
    # generic and non-generic versions live in different namespaces
    "IComparer": ("System.Collections.Generic*", "System.Collections"),
    "IEqualityComparer": ("System.Collections.Generic*", "System.Collections"),
    "CancellationToken": ("System.Threading",),
    "CancellationTokenSource": ("System.Threading",),
    "Stream": ("System.IO",), "TextWriter": ("System.IO",), "TextReader": ("System.IO",),
    "StringBuilder": ("System.Text",), "Encoding": ("System.Text",),
    "Regex": ("System.Text.RegularExpressions",),
    "ILogger": ("Microsoft.Extensions.Logging",),
})


class CSharpSpec(LanguageSpec):
    name = "csharp"
    grammar = "csharp"
    extensions = (".cs",)
    separator = "."
    opaque_nodes = frozenset({
        "block", "arrow_expression_clause", "lambda_expression",
        "anonymous_method_expression", "anonymous_object_creation_expression",
        "accessor_list", "local_function_statement",
    })
    annotation_nodes = frozenset({"attribute"})
    type_argument_nodes = frozenset({"type_argument_list"})
    receiver_part_nodes = frozenset({"identifier", "generic_name", "member_access_expression",
                                     "qualified_name"})
    # `E.V`, and a bare name, which in `nameof(Order)` is a type
    annotation_value_args = frozenset({"member_access_expression", "identifier"})

    def project_references(self, project):
        return _references(project)

    def subtype_sees(self, modifiers):
        # a private member, or a nested type with no access modifier (private), is not
        # seen in a subtype; `private protected` is
        return any(m in ("public", "protected", "internal", "package") for m in modifiers)

    def file_local(self, modifiers):
        return "file" in modifiers

    def outside_known(self, type_id):
        return type_id in _framework()["types"] or type_id in _framework_types()

    def outside_namespace(self, namespace):
        return _framework_namespaces().get(namespace)

    def outside_namespace_exists(self, namespace):
        return namespace in _framework_namespace_parents()

    def inherited_field(self, super_id, name, static=False):
        # a field, property or event a .NET or ASP.NET Core class (or one it extends)
        # declares; with ``static``, a static one (what `using static` brings in)
        seen: set[str] = set()
        cur: Optional[str] = super_id
        while cur and cur not in seen:
            seen.add(cur)
            entry = _framework()["types"].get(cur)
            if entry is None:
                return False
            if name in entry.get("s", ()) or not static and name in entry.get("f", ()):
                return True
            cur = entry.get("b")
        return False

    def inherited_type(self, super_id, name):
        seen: set[str] = set()
        cur: Optional[str] = super_id
        while cur and cur not in seen:
            seen.add(cur)
            entry = _framework()["types"].get(cur)
            if entry is None:
                return None
            if name in entry.get("n", ()):
                return f"{cur}.{name}"
            cur = entry.get("b")
        return None

    def internal_type(self, modifiers, nested):
        if "public" in modifiers or "protected" in modifiers and "private" not in modifiers:
            return False
        return True if not nested else any(m in ("internal", "private") for m in modifiers) \
            or not any(m in ("public", "protected") for m in modifiers)

    def internals_visible(self, owner_project, project):
        return _assembly_name(Path(project)) in _friends(Path(owner_project))

    def body_name_text(self, text):
        return text.removeprefix("@")   # a verbatim identifier

    def arity(self, part):
        args = part.parent.child_by_field_name("type_arguments") if part.parent is not None \
            and part.parent.type == "generic_name" else None
        if args is None and part.parent is not None and part.parent.type == "generic_name":
            args = next((c for c in part.parent.named_children
                         if c.type == "type_argument_list"), None)
        if args is None:
            return 0
        # `Repo<,>`: no type in it, a comma between two
        return max(len(args.named_children), sum(1 for c in args.children if c.type == ",") + 1)

    def init_via(self, node, src):
        # an operator, a destructor, an indexer or an event (their accessors), or a
        # primary constructor's base arguments (the constructor's, named as the class)
        decl = node if node.type != "argument_list" else node.parent
        text = lambda n: src[n.start_byte:n.end_byte].decode("utf8", "replace")   # noqa: E731
        if decl.type == "operator_declaration":
            op = decl.child_by_field_name("operator")
            return f"operator {text(op)}" if op is not None else "operator"
        if decl.type == "conversion_operator_declaration":
            return f"operator {text(decl.child_by_field_name('type'))}"
        if decl.type == "destructor_declaration":
            return f"~{text(decl.child_by_field_name('name'))}"
        if decl.type == "indexer_declaration":
            return "this[]"
        if decl.type == "event_declaration":
            return text(decl.child_by_field_name("name"))
        if decl.type == "base_list":
            return text(decl.parent.child_by_field_name("name"))
        return None

    def annotation_arg(self, node, text):
        if node.type == "typeof_expression":   # `typeof(X)`
            t = node.child_by_field_name("type")
            return (text(t), True) if t is not None else None
        return super().annotation_arg(node, text)

    def annotation_type_names(self, name):
        # `[Obsolete]` is ObsoleteAttribute, `[ObsoleteAttribute]` may be written too. A
        # class `Route` is no attribute unless it derives from Attribute, which the name
        # alone cannot tell; by convention attribute classes end in Attribute
        return [name] if name.endswith("Attribute") else [name + "Attribute"]
    builtins = frozenset(_BUILTINS)
    visibility_keywords = {
        "public": "public", "protected": "protected", "private": "private",
        "internal": "internal",
    }
    parent_namespace_lookup = True
    qualified_heads_in_scope = True
    enclosing_outside_hides = True
    block_imports = True
    body_aliases = True
    color_color = True
    unknown_bases_hide = True

    def preprocess(self, src):
        # keep one branch of every #if (the first, unless its condition is false whatever
        # the symbols: `#if false ... #else`), blank the others and the directive lines
        # (same length, so line numbers stay exact). One deterministic configuration, and
        # it parses wherever the directives sit
        return b"\n".join(line if kept else _blank(line) for line, kept, _, _ in _lines(src))

    def unbuilt_ranges(self, src, path, root):
        # the first branch of an #if that is false whatever the symbols (`#if false`); in a
        # .NET MAUI app also its Platforms/<platform>/ folders, and a first branch false with
        # every platform symbol false (`#if IOS || MACCATALYST`, not `#if !WINDOWS`), which
        # only a platform's build compiles
        project = _project_file(path.resolve().parent)
        maui = project is not None and _uses_maui(project)
        if maui:
            below = path.resolve().relative_to(project.parent).parts
            if len(below) > 2 and below[0] == "Platforms" and below[1] in _PLATFORM_FOLDERS:
                return [(0, len(src))]
        out, at, stack, off = [], 0, [], False   # stack: whether each #if's branch was off
        for line in src.split(b"\n"):
            m = re.match(rb"^[ \t]*#[ \t]*(if|elif|else|endif)\b(.*)", line)
            if m and m.group(1) == b"if":
                stack.append(off)
                off = off or _without_platforms(m.group(2).decode("utf8", "replace"), maui) is False
            elif m and m.group(1) in (b"elif", b"else"):
                off = stack[-1] if stack else off   # blanked anyway
            elif m and stack:
                off = stack.pop()
            elif off:
                out.append((at, at + len(line)))
            at += len(line) + 1
        return out

    def generated_fields(self, node, src):
        text = lambda n: src[n.start_byte:n.end_byte].decode("utf8", "replace")   # noqa: E731
        name = text(node.child_by_field_name("name")).rsplit(".", 1)[-1].removesuffix("Attribute")
        target = node.parent.parent if node.parent is not None else None   # attribute_list's
        if target is None:
            return []
        if name == "ObservableProperty" and target.type == "field_declaration":
            # `_name`, `m_name` and `name` all make `Name`
            out = []
            for d in (c for c in target.named_children if c.type == "variable_declaration"):
                for v in (c for c in d.named_children if c.type == "variable_declarator"):
                    n = re.sub(r"^(m_|_)", "", text(v.child_by_field_name("name")))
                    out.append(n[:1].upper() + n[1:])
            return out
        if name == "RelayCommand" and target.type == "method_declaration":
            return [text(target.child_by_field_name("name")).removesuffix("Async") + "Command"]
        if name == "JsonSerializable":
            # a property per type, named by it (`List<Order>`: ListOrder, `Order[]`:
            # OrderArray) unless TypeInfoPropertyName says otherwise, and Default
            args = text(node)
            given = re.search(r'TypeInfoPropertyName\s*=\s*"(\w+)"', args)
            of = re.search(r"typeof\s*\((.*)\)", args, re.S)
            if given:
                return [given.group(1), "Default"]
            if of:
                written = re.sub(r"\bglobal::|[\w]+\.(?=\w)", "", of.group(1))
                written = written.replace("[]", "Array")
                return ["".join(re.findall(r"\w+", written)), "Default"]
            return ["Default"]
        return []

    def companion_fields(self, path):
        name = path.name
        if name.endswith(".razor.cs"):
            razor = path.with_name(name.removesuffix(".cs"))
            texts = [razor]
            project = _project_file(path.resolve().parent)
            top = project.parent if project else path.parent
            cur = path.parent
            while True:   # _Imports.razor injects into every component below it
                texts.append(cur / "_Imports.razor")
                if cur.resolve() == top.resolve() or cur.parent == cur:
                    break
                cur = cur.parent
            names: set[str] = set()
            for t in texts:
                try:
                    names |= _razor_members(t.read_text(encoding="utf-8-sig"))
                except OSError:
                    pass
            return {razor.stem: names} if names else {}
        if name.endswith(".xaml.cs"):
            try:
                xaml = path.with_name(name.removesuffix(".cs")).read_text(encoding="utf-8-sig")
            except OSError:
                return {}
            cls = re.search(r'\bx:Class\s*=\s*"([\w.]+)"', xaml)
            names = set(re.findall(r'\bx:Name\s*=\s*"(\w+)"', xaml))
            return {cls.group(1).rsplit(".", 1)[-1]: names} if cls and names else {}
        return {}

    def implicit_types(self, root_node):
        # top-level statements are the body of an implicit `Program` of the project
        return ["Program"] if any(c.type == "global_statement" for c in root_node.children) else []

    def build_types(self, path, root):
        own = _project_file(path.resolve().parent)
        projects = ([own] if own else []) + list(_linked_files(root.resolve()).get(path.resolve(), ()))
        out: dict[str, set[str]] = {}
        for project in dict.fromkeys(projects):
            for ns, names in _protobuf_types(project) + _razor_types(project):
                out.setdefault(ns, set()).update(names)
        return out

    def conditional_ranges(self, src):
        # what the first branch of an #if keeps
        out, at = [], 0
        for line, kept, inside, _ in _lines(src):
            if kept and inside:
                out.append((at, at + len(line)))
            at += len(line) + 1
        return out

    def left_out_types(self, src):
        return {m.decode() for m in _TYPE_DECL.findall(_blanked(src))}

    def left_out_names(self, src):
        # members (any name before `;`, `=`, `{ get` or `=>`, locals too: those only hide)
        # and aliases
        return {m.decode() for m in _MEMBER_DECL.findall(_blanked(src))}

    def is_package_head(self, head, known):
        # namespaces are capitalised too: only what the file or the project uses as one
        return head in known or head in ("System", "Microsoft", "global")

    def is_project_wide(self, import_node):
        parent = import_node.parent
        return parent is not None and any(c.type == "global" for c in parent.children)

    def project_imports(self, path, root):
        # the project above the file, and every project that links it in
        file = path.resolve()
        own = _project_file(file.parent)
        projects = list(dict.fromkeys(([own] if own else []) + list(_linked_files(root.resolve()).get(file, ()))))
        if not projects:
            return "csharp", []   # files without a project file compile together
        if len(projects) == 1:
            return str(projects[0]), list(_project_usings(projects[0]))   # [(namespace, origin)]
        # compiled into several projects: only what every one of them imports is certain
        each = [{(u[0], *u[2:]): u[1] for u in _project_usings(p)} for p in projects]
        common = [key for key in each[0] if all(key in e for e in each[1:])]
        origin = f"usings common to the {len(projects)} projects that compile it"
        return ";".join(sorted(map(str, projects))), [(k[0], origin, *k[1:]) for k in common]

    def library_type(self, name, imported, arity=None, external_supers=None):
        spaces = []
        for ns in _LIBRARY.get(name, ()):
            generic = ns.endswith("*")
            ns = ns.rstrip("*")
            if ns in imported and (arity is None or generic == (arity > 0)
                                   or not any(n.endswith("*") for n in _LIBRARY[name])):
                spaces.append(ns)
        return f"{spaces[0]}.{name}" if len(spaces) == 1 else None

    def default_visibility(self, owner_kind, member_kind):
        if owner_kind == "interface" or member_kind == "enum_constant":
            return "public"
        return "private"

    def visibility(self, owner_kind, member_kind, modifiers, name, node):
        if node.type in ("parameter", "parameter_list"):  # record property, primary constructor
            return "public"
        return super().visibility(owner_kind, member_kind, modifiers, name, node)

    def is_static(self, owner_kind, member_kind, modifiers):
        return member_kind == "enum_constant" or "static" in modifiers or "const" in modifiers

    def is_abstract(self, owner_kind, member_kind, modifiers, has_body, marker=None):
        if "abstract" in modifiers:
            return True
        return owner_kind == "interface" and member_kind == "method" and not has_body \
            and "static" not in modifiers

    def external_super_kind(self, owner_kind, captured, name):
        if captured != "inherits":
            return captured
        # .NET convention: interfaces are named IXxx
        if owner_kind != "interface" and re.match(r"I[A-Z]", name):
            return "implements"
        return "extends"
