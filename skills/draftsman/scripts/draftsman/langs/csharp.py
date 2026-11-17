from __future__ import annotations

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
    removes: set[str] = set()
    # Directory.Build.props is evaluated first; the project file overrides it
    docs = [d for d in (_msbuild(p) for p in [_build_props(project.parent)] if p) if d is not None]
    for doc in docs + [root]:
        for el in doc.iter():
            tag = _local(el.tag)
            if tag in ("ImplicitUsings", "UseWPF", "UseWindowsForms", "UseVSTest") and el.text:
                props[tag] = el.text.strip().lower()
            elif tag == "Using":
                if el.get("Include") and not el.get("Alias") and el.get("Static", "").lower() != "true":
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
    return tuple((n, origin) for n, origin in out.items() if n not in removes)

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
    builtins = frozenset(_BUILTINS)
    visibility_keywords = {
        "public": "public", "protected": "protected", "private": "private",
        "internal": "internal",
    }
    parent_namespace_lookup = True

    def preprocess(self, src):
        # keep the first branch of every #if, blank the #elif/#else branches and the
        # directive lines (same length, so line numbers stay exact). One deterministic
        # configuration, and it parses wherever the directives sit
        out, stack, active = [], [], True
        for line in src.split(b"\n"):
            m = _CONDITIONAL.match(line)
            if m:
                kw = m.group(1)
                if kw == b"if":
                    stack.append(active)
                elif kw in (b"elif", b"else"):
                    active = False if stack else active
                elif stack:   # endif
                    active = stack.pop()
                out.append(_blank(line))
            else:
                out.append(line if active else _blank(line))
        return b"\n".join(out)

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
        each = [dict(_project_usings(p)) for p in projects]
        common = [ns for ns in each[0] if all(ns in e for e in each[1:])]
        origin = f"usings common to the {len(projects)} projects that compile it"
        return ";".join(sorted(map(str, projects))), [(ns, origin) for ns in common]

    def library_type(self, name, imported, arity=None):
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
        if node.type == "parameter":  # positional record property
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
