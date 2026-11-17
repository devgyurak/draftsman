"""The same small "shop" domain written in every supported language."""

import re

import pytest

from conftest import FIXTURES, extract_dir

LANGS = ["java", "csharp", "kotlin", "typescript", "python", "cpp"]


def short(tid: str) -> str:
    return re.split(r"::|\.", tid)[-1]


@pytest.fixture(scope="module", params=LANGS)
def lang_ir(request):
    return request.param, extract_dir(FIXTURES / request.param / "shop")


def by_name(ir, name):
    hits = [t for t in ir.types if short(t.id) == name or t.name == name]
    assert hits, f"no type {name}"
    return hits[0]


def rels(ir):
    return {(short(r.from_), r.kind, short(r.to)) for r in ir.relations}


def mults(ir):
    return {(short(r.from_), short(r.to)): r.multiplicity
            for r in ir.relations if r.kind == "association"}


# names differ a little between languages
NAMES = {
    "csharp": {"PaymentGateway": "IPaymentGateway", "OrderRepository": "IOrderRepository",
               "Auditable": "IAuditable", "Listener": "IListener"},
    "typescript": {"Audit": "OrderAudit"},   # TS classes cannot nest classes
}


def n(lang, name):
    return NAMES.get(lang, {}).get(name, name)


def test_no_diagnostics(lang_ir):
    _, ir = lang_ir
    assert ir.diagnostics == []


def test_inheritance(lang_ir):
    lang, ir = lang_ir
    r = rels(ir)
    assert ("Customer", "extends", "BaseEntity") in r
    assert ("Order", "extends", "BaseEntity") in r
    impl = "extends" if lang in ("python", "cpp") else "implements"  # no interfaces to implement
    assert ("StripeGateway", impl, n(lang, "PaymentGateway")) in r
    if lang != "python":
        assert ("BaseEntity", "implements", n(lang, "Auditable")) in r


def test_kinds(lang_ir):
    lang, ir = lang_ir
    assert by_name(ir, "BaseEntity").kind == "abstract_class"
    assert by_name(ir, n(lang, "Auditable")).kind == "interface"
    assert by_name(ir, "Status").kind == "enum"
    assert by_name(ir, n(lang, "OrderRepository")).kind == "interface"


def test_associations_and_multiplicity(lang_ir):
    lang, ir = lang_ir
    m = mults(ir)
    assert m[("Order", "OrderLine")] == "*"
    assert m[("Customer", "Order")] == "*"
    assert m[("Order", "Customer")] == "1"
    assert m[("OrderLine", "Product")] == "1"
    assert m[("OrderService", n(lang, "OrderRepository"))] == "1"
    assert m[("OrderService", n(lang, "PaymentGateway"))] == "1"
    assert ("Receipt", "Money") in m          # nested type
    assert ("StripeGateway", "Money") in m    # Receipt.Money / Receipt::Money


def test_dependencies(lang_ir):
    lang, ir = lang_ir
    r = rels(ir)
    assert ("OrderService", "dependency", "Receipt") in r
    assert ("OrderService", "dependency", "Customer") in r
    assert (n(lang, "PaymentGateway"), "dependency", "Order") in r


def test_enum_constants(lang_ir):
    _, ir = lang_ir
    consts = [m.name.upper() for m in by_name(ir, "Status").members if m.kind == "enum_constant"]
    assert consts == ["NEW", "PAID", "SHIPPED"]


def test_lambda_params_are_not_method_params(lang_ir):
    lang, ir = lang_ir
    add = {"python": "add_line", "csharp": "AddLine"}.get(lang, "addLine")
    (m,) = [m for m in by_name(ir, "Order").members if m.name == add]
    assert [p.name for p in m.params] == ["line"]


def test_type_parameters_are_not_references(lang_ir):
    _, ir = lang_ir
    assert not any(u.raw_type == "T" for u in ir.unresolved)


EXPECTED_UNRESOLVED = {
    "java": {"Coupon", "StripeClient"},
    "csharp": {"Coupon", "StripeClient", "IRepository"},   # `using` brings whole namespaces
    "kotlin": {"Coupon", "StripeClient"},
    "typescript": set(),        # every name is imported explicitly from a package
    "python": {"Coupon", "StripeClient"},
    "cpp": set(),               # promo::Coupon, stripe::StripeClient are qualified externals
}


def test_unresolved(lang_ir):
    lang, ir = lang_ir
    assert {u.raw_type for u in ir.unresolved} == EXPECTED_UNRESOLVED[lang]
    assert all(u.hint for u in ir.unresolved)


# ------------------------------------------------------------------ scope rules
#
# One row per name-resolution rule, one witness per language: a relation in the shop
# fixture that only that rule can produce. A new rule (or a bug fix in resolve.py)
# adds a row and a witness to every language where the rule exists; `None` says the
# language has no such rule, with the reason. Rules a language must NOT apply are
# checked separately below (test_no_inherited_member_types_*).

_ALL = dict.fromkeys(LANGS)
SCOPE_RULES = {
    "nested type of the type itself": {l: ("Receipt", "association", "Money") for l in LANGS},
    "nested type named through its outer type": {
        l: ("StripeGateway", "association", "Money") for l in LANGS},
    # by simple name; Python through the subclass (Customer.Listener, attributes are inherited)
    "member type inherited from a supertype": {
        **{l: ("Customer", "association", "Listener") for l in LANGS},
        "typescript": None,  # merged namespace members are not inherited
    },
    "member type inherited by the enclosing type": {
        **{l: ("Audit", "implements", "Listener") for l in LANGS},
        "python": None,      # class bodies are not scopes (test_no_inherited_member_types_*)
        "typescript": None,  # merged namespace members are not inherited
    },
    "same package / namespace / module": {
        l: ("Order", "association", "OrderLine") for l in LANGS},
    "single-name import": {
        "java": ("Order", "association", "Customer"),
        "kotlin": ("Order", "extends", "BaseEntity"),
        "typescript": ("Order", "association", "Customer"),
        "python": ("Customer", "extends", "BaseEntity"),
        "csharp": None,      # `using` imports whole namespaces
        "cpp": None,         # names come from namespaces, not imports
    },
    "wildcard import of a project package": {
        "java": ("PaymentGateway", "dependency", "Order"),
        "kotlin": ("PaymentGateway", "dependency", "Order"),
        "csharp": ("Customer", "extends", "BaseEntity"),
        "typescript": None,  # no wildcard imports (`export *` is the re-export row below)
        "python": None,      # `from x import *` of project modules: test_extract_* unit tests
        "cpp": None,         # `using namespace`: covered by the enclosing-namespace row
    },
    "enclosing namespace": {
        **_ALL,
        "cpp": ("PaymentGateway", "dependency", "Order"),   # shop::pay sees shop::Order
    },
    "namespace block sees its module": {
        **_ALL,
        "typescript": ("Listener", "dependency", "BaseEntity"),
    },
    "module alias": {
        **_ALL,
        "typescript": ("OrderService", "dependency", "Receipt"),   # pay.Receipt
        "python": ("OrderService", "dependency", "Receipt"),       # gw.Receipt
    },
    "workspace package import": {
        **_ALL,
        # `@shop/pay` is the "name" in src/pay/package.json; `@shop/promotions` is not ours
        "typescript": ("Order", "association", "Receipt"),
    },
    "package re-export": {
        **_ALL,
        "python": ("PaymentGateway", "dependency", "Order"),       # shop.order.__init__
    },
    "package re-export by wildcard": {
        **_ALL,
        # shop/pay/__init__.py: from .gateway import *
        "python": ("OrderService", "association", "PaymentGateway"),
        # src/common/index.ts: export * from './base-entity'
        "typescript": ("Customer", "extends", "BaseEntity"),
    },
}


@pytest.mark.parametrize("rule", sorted(SCOPE_RULES))
def test_scope_rules(irs, rule):
    missing = []
    for lang, witness in SCOPE_RULES[rule].items():
        if witness is None:
            continue
        a, kind, b = witness
        expected = (n(lang, a), kind, n(lang, b))
        if expected not in rels(irs[lang]):
            missing.append(f"{lang}: {expected}")
    assert not missing, f"{rule}: " + "; ".join(missing)


def test_no_inherited_member_types_in_python(tmp_path):
    """A class body is not a scope: a base's nested class needs its qualified name."""
    from conftest import extract_source
    ir = extract_source(tmp_path, {
        "m/base.py": "class Base:\n    class Listener: ...\n",
        "m/sub.py": "from m.base import Base\n\nclass Listener: ...\n\n"
                    "class Sub(Base):\n    def __init__(self, l: Listener) -> None:\n"
                    "        self.l = l\n",
    })
    # the module-level Listener, never Base.Listener
    assert ("Sub", "association", "Listener") in rels(ir)
    assert not any(r.to.endswith("Base.Listener") for r in ir.relations)


def test_python_root_inside_a_package(tmp_path):
    """Extracting django/db/models: modules are named as Python names them, so absolute
    imports and `from pkg.sub import *` re-exports resolve exactly, and a look-alike
    external path is not taken for a project module."""
    from conftest import extract_dir
    files = {
        "django/__init__.py": "",
        "django/db/__init__.py": "",
        "django/db/models/__init__.py": "from django.db.models.fields import *\n",
        "django/db/models/expressions.py": "class BaseExpression: ...\n",
        "django/db/models/fields/__init__.py": "class Field: ...\n",
        "django/db/models/utils.py": "class Helper: ...\n",
        "django/db/models/query.py": (
            "from django.db import models\n"
            "from django.db.models.expressions import BaseExpression\n"
            "from other.utils import Helper\n\n"
            "class Query:\n"
            "    def __init__(self, e: BaseExpression, f: models.Field, h: Helper) -> None:\n"
            "        self.e = e\n        self.f = f\n        self.h = h\n"),
    }
    for name, text in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text)
    ir = extract_dir(tmp_path / "django" / "db" / "models")
    ids = {t.id for t in ir.types}
    assert "django.db.models.query.Query" in ids
    assert all(i.startswith("django.db.models.") for i in ids)
    r = {(a, k, b) for a, k, b in ((x.from_, x.kind, x.to) for x in ir.relations)}
    assert ("django.db.models.query.Query", "association",
            "django.db.models.expressions.BaseExpression") in r
    assert ("django.db.models.query.Query", "association",
            "django.db.models.fields.Field") in r                 # through the * re-export
    assert not any(b.endswith("utils.Helper") for _, _, b in r)   # other.utils is not ours
    assert not ir.unresolved


def test_python_builtin_classes_are_known(tmp_path):
    from conftest import extract_source
    ir = extract_source(tmp_path, {"m.py": "class Registry(dict): ...\n"
                                           "class Missing(LookupError): ...\n"})
    assert not ir.unresolved
    assert {(r.from_.rsplit(".", 1)[-1], r.to) for r in ir.relations} == {
        ("Registry", "dict"), ("Missing", "LookupError")}


def test_python_builtin_wins_unless_the_project_class_is_imported(tmp_path):
    """django: ProxyModelWarning(Warning) is the builtin Warning, although the project has
    django.core.checks.messages.Warning; a module that imports that one gets it."""
    from conftest import extract_source
    ir = extract_source(tmp_path, {
        "app/checks.py": "class Warning: ...\n",
        "app/dump.py": "class ProxyModelWarning(Warning): ...\n",
        "app/check.py": "from app.checks import Warning\n\nclass Strict(Warning): ...\n",
    })
    sup = {r.from_.rsplit(".", 1)[-1]: r.to for r in ir.relations if r.kind == "extends"}
    assert sup["ProxyModelWarning"] == "Warning"            # builtin, not a guess
    assert sup["Strict"] == "app.checks.Warning"            # imported, so the project's
    assert not ir.unresolved


def test_python_namespace_package_import_is_flagged_not_dropped(tmp_path):
    """PEP 420: no __init__.py, so the root's package prefix is unknown. An import that
    ends with a project id stays unresolved with that id as a candidate, not external."""
    from conftest import extract_dir
    files = {
        "nspkg/sub/mod.py": "class X: ...\n",
        "nspkg/sub/user.py": ("from nspkg.sub.mod import X\n"
                              "from nspkg.sub import mod as m\n"
                              "from requests.adapters import HTTPAdapter\n\n"
                              "class U:\n"
                              "    def __init__(self, a: X, b: m.X, c: HTTPAdapter) -> None:\n"
                              "        self.a = a\n        self.b = b\n        self.c = c\n"),
    }
    for name, text in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text)
    ir = extract_dir(tmp_path / "nspkg" / "sub")
    assert not ir.relations                                  # nothing guessed
    flagged = {(u.raw_type, tuple(u.candidates)) for u in ir.unresolved}
    assert flagged == {("X", ("mod.X",)), ("m.X", ("mod.X",))}
    assert all("__init__.py" in u.hint for u in ir.unresolved)   # HTTPAdapter: just external


def test_python_reexport_chains_do_not_depend_on_file_order(tmp_path):
    """p0 -> p1 -> ... -> p4 -> m.X by `from .next import *`. a.py is past the depth limit,
    b.py one step away; neither may change what the other resolves to."""
    from draftsman.extractor import Extractor
    from draftsman.langs import spec_for_path
    from draftsman.resolve import build_ir
    from draftsman.wrappers import Wrappers
    files = {"a.py": "from p0 import X\n\nclass A:\n    x: X\n",
             "b.py": "from p0.p1.p2.p3.p4 import X\n\nclass B:\n    x: X\n"}
    pkg = "p0"
    for i in range(5):
        nxt = "m" if i == 4 else f"p{i + 1}"
        files[pkg.replace(".", "/") + "/__init__.py"] = f"from {pkg}.{nxt} import *\n"
        pkg = f"{pkg}.{nxt}"
    files["p0/p1/p2/p3/p4/m.py"] = "class X: ...\n"
    for name, text in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text)
    ex = Extractor(spec_for_path("a.py"))
    raw = {p.relative_to(tmp_path).as_posix(): ex.extract(p, p.relative_to(tmp_path).as_posix(), tmp_path)
           for p in sorted(tmp_path.rglob("*.py"))}
    results = []
    for first in ("a.py", "b.py"):
        ordered = [raw[first]] + [r for name, r in raw.items() if name != first]
        ir = build_ir("r", ordered, Wrappers.load())
        results.append(sorted((r.from_, r.to) for r in ir.relations))
    assert results[0] == results[1]
    assert ("b.B", "p0.p1.p2.p3.p4.m.X") in results[0]
    assert not any(f == "a.A" for f, _ in results[0])        # beyond the depth limit


def test_typescript_imports_into_the_sources(tmp_path):
    """Relative imports point into the sources: a name they do not reach is unresolved,
    unless the chain re-exports it from a package, which is then the external id."""
    from conftest import extract_source
    ir = extract_source(tmp_path, {
        "platform.ts": 'export { EventEmitter } from "events";\n',
        "a.ts": ('import { EventEmitter } from "./platform";\n'
                 'import { Missing } from "./nowhere";\n'
                 "export class A extends EventEmitter {\n  m?: Missing;\n"
                 "  d?: AsyncDisposable;\n  f?: Float32Array;\n  r?: Required<A>;\n}\n"),
    })
    assert ("a.A", "extends", "events.EventEmitter") in {
        (r.from_, r.kind, r.to) for r in ir.relations}
    (u,) = ir.unresolved
    assert u.raw_type == "Missing" and "relative path" in u.hint


def test_typescript_workspace_packages(tmp_path):
    """Packages are linked by their exact package.json name: the declared source entry,
    subpaths below the package, unresolved when the name is missing inside it or the
    package name is declared twice; a look-alike package name stays external."""
    from conftest import extract_source
    ir = extract_source(tmp_path, {
        "core/package.json": '{"name": "@acme/core", "types": "src/index.ts"}',
        "core/src/index.ts": 'export * from "./thing";\n',
        "core/src/thing.ts": "export class Thing {}\n",
        "core/internal/index.ts": "export class Hidden {}\n",
        "dup1/package.json": '{"name": "@acme/dup"}', "dup1/index.ts": "export class D {}\n",
        "dup2/package.json": '{"name": "@acme/dup"}', "dup2/index.ts": "export class D {}\n",
        "app/package.json": '{"name": "@acme/app"}',
        "app/a.ts": ('import { Thing } from "@acme/core";\n'
                     'import { Hidden } from "@acme/core/internal";\n'
                     'import { Nope } from "@acme/core";\n'
                     'import { Util } from "@acme/core-utils";\n'
                     'import { D } from "@acme/dup";\n'
                     "export class A { t?: Thing; h?: Hidden; n?: Nope; u?: Util; d?: D; }\n"),
    })
    targets = {r.to for r in ir.relations if r.from_ == "app/a.A"}
    assert targets == {"core/src/thing.Thing", "core/internal.Hidden"}
    by_name = {u.raw_type: u for u in ir.unresolved}
    assert set(by_name) == {"Nope", "D"}
    assert "workspace package" in by_name["Nope"].hint
    # two package.json files named @acme/dup: inside the project, but not one to pick
    assert sorted(by_name["D"].candidates) == ["dup1.D", "dup2.D"]
    assert "@acme/dup" in by_name["D"].hint and "2 package.json" in by_name["D"].hint


def test_typescript_typeof_names_a_value(tmp_path):
    """`typeof x` is a class when x is one, else a value: never an unresolved type."""
    from conftest import extract_source
    ir = extract_source(tmp_path, {"a.ts": (
        "export class Order {}\n"
        "export class Timer {\n"
        "  retry?: ReturnType<typeof setTimeout>;\n"
        "  make?: InstanceType<typeof Order>;\n"
        "  run(fn: typeof helper): void {}\n}\n")})
    assert not ir.unresolved
    assert ("a.Timer", "dependency", "a.Order") in {(r.from_, r.kind, r.to) for r in ir.relations}


def test_comments_are_not_part_of_type_text(tmp_path):
    """A JSDoc block inside an inline type, or a comment in a generic argument, is not
    type text; `//` inside a string literal type is."""
    from conftest import extract_source
    ir = extract_source(tmp_path, {
        "a.ts": ("export class Order {}\n"
                 "export class Box {\n"
                 "  opts?: {\n    /** Maximum size (default: 16 * Order) */\n    max?: number;\n  };\n"
                 '  url?: "http://x" | Order;\n}\n'),
        "p/B.java": "package p; import java.util.List; class B { List</* never empty */ Line> lines; }\n",
        "p/Line.java": "package p; class Line {}",
    })
    refs = {m.name: m.type_ref for t in ir.types for m in t.members}
    assert refs["opts"] == "{ max?: number; }"
    assert refs["url"] == '"http://x" | Order'
    assert refs["lines"] == "List<Line>"
    assert ("p.B", "association", "p.Line") in {(r.from_, r.kind, r.to) for r in ir.relations}


def test_csharp_namespace_shared_with_a_library(tmp_path):
    """The project declares a type in Microsoft.AspNetCore.Mvc; a name that `using` does
    not reach there may still come from the library part of it."""
    from conftest import extract_source
    ir = extract_source(tmp_path, {
        "Ext.cs": "namespace Microsoft.AspNetCore.Mvc;\npublic static class UrlHelperExtensions {}\n",
        "Api.cs": ("using Microsoft.AspNetCore.Mvc;\nnamespace Shop;\n"
                   "public class BaseApiController : ControllerBase {}\n"),
    })
    (u,) = ir.unresolved
    assert u.raw_type == "ControllerBase" and "Microsoft.AspNetCore.Mvc.*" in u.hint


def test_csharp_build_imports(tmp_path):
    """SDK implicit usings, <Using> items, Directory.Build.props and `global using` are
    imports of every file of the project, and only of that project."""
    from conftest import extract_source
    from draftsman.extractor import Extractor
    from draftsman.langs import spec_for_path
    files = {
        "Directory.Build.props": "<Project><PropertyGroup><ImplicitUsings>enable</ImplicitUsings>"
                                 "</PropertyGroup></Project>",
        "Web/Web.csproj": ('<Project Sdk="Microsoft.NET.Sdk.Web"><ItemGroup>'
                           '<Using Include="Acme.Extra" /><Using Remove="System.IO" />'
                           '<Using Include="Acme.Results" Alias="Results" />'
                           "</ItemGroup></Project>"),
        "Web/GlobalUsings.cs": "global using Acme.Domain;\n",
        "Web/Domain/Order.cs": "namespace Acme.Domain;\npublic class Order {}\n",
        "Web/App/Service.cs": "namespace Acme.App;\npublic class Service { Order order; }\n",
        "Web/App/Job.cs": "namespace Acme.App;\npublic class Job { IMailer mailer; }\n",
        "Lib/Lib.csproj": '<Project Sdk="Microsoft.NET.Sdk"></Project>',
        "Lib/Other.cs": "namespace Acme.Lib;\npublic class Other { Order order; }\n",
    }
    ir = extract_source(tmp_path, files)
    rels = {(r.from_, r.kind, r.to) for r in ir.relations}
    assert ("Acme.App.Service", "association", "Acme.Domain.Order") in rels   # global using
    assert not any(f == "Acme.Lib.Other" for f, _, _ in rels)                  # other project
    hints = {u.raw_type: u.hint for u in ir.unresolved}
    assert set(hints) == {"Order", "IMailer"}
    # the hint says where project-wide imports come from, instead of picking examples
    assert hints["Order"].endswith("Microsoft.NET.Sdk implicit usings (7 namespaces)")
    assert ("Microsoft.NET.Sdk.Web implicit usings (15 namespaces), <Using> items (1 namespace), "
            "1 global using (Acme.Domain.*)") in hints["IMailer"]

    ex = Extractor(spec_for_path("x.cs"))
    web = ex.extract(tmp_path / "Web/App/Service.cs", "Web/App/Service.cs", tmp_path).scope
    paths = [i.path for i in web.imports]
    assert {"System", "System.Linq", "Microsoft.Extensions.Logging", "System.Net.Http.Json",
            "Acme.Extra"} <= set(paths)
    assert "System.IO" not in paths and "Acme.Results" not in paths     # removed; alias
    lib = ex.extract(tmp_path / "Lib/Other.cs", "Lib/Other.cs", tmp_path).scope
    assert [i.path for i in lib.imports] == ["System", "System.Collections.Generic", "System.IO",
                                             "System.Linq", "System.Net.Http", "System.Threading",
                                             "System.Threading.Tasks"]   # props, base SDK


def test_csharp_conditional_compilation_keeps_the_first_branch(tmp_path):
    """`#if` inside a base list, a parameter list, a pattern or around a second method
    header breaks the parse; every file is read with the first branch of each #if."""
    from conftest import extract_source
    ir = extract_source(tmp_path, {"A.cs": (
        "namespace N;\npublic interface IFoo {}\npublic interface IBar {}\n"
        "public interface IBaz {}\n"
        "public sealed class A : IFoo\n#if FEATURE_X\n    , IBar\n#else\n    , IBaz\n#endif\n{\n"
        "  public A(int a,\n#if FEATURE_X\n      IBar bar,\n#endif\n      IFoo foo) {}\n"
        "#if FEATURE_SPAN\n  public void Write(IBar s)\n#else\n  public void Write(IBaz s)\n#endif\n"
        "  { var ok = s is IFoo\n#if FEATURE_X\n    or IBar\n#endif\n    ; }\n}\n"
        "#if DEBUG\npublic class Probe {}\n#if NESTED\npublic class Inner {}\n#endif\n"
        "#else\npublic class Release {}\n#endif\n")})
    assert ir.diagnostics == []
    rels = {(r.kind, r.to.rsplit(".", 1)[-1], r.via) for r in ir.relations if r.from_ == "N.A"}
    assert {k for k in rels if k[0] == "implements"} == {("implements", "IFoo", None),
                                                          ("implements", "IBar", None)}
    write = [m for t in ir.types if t.id == "N.A" for m in t.members if m.name == "Write"]
    assert [p.type_ref for m in write for p in m.params] == ["IBar"]      # one header
    assert {t.id for t in ir.types} >= {"N.Probe", "N.Inner"}
    assert "N.Release" not in {t.id for t in ir.types}


def test_csharp_library_types_need_their_namespace(tmp_path):
    """A well-known library name is that library type only through an imported namespace
    that holds it: no `System.` guess, and the project's own type of the name wins."""
    from conftest import extract_source
    ir = extract_source(tmp_path, {
        "Log.cs": "namespace Serilog;\npublic interface ILogger {}\n",
        "Core.cs": ("using System;\nusing System.Collections;\nusing System.Collections.Generic;\n"
                    "using System.Text;\nnamespace Serilog.Core;\n"
                    "public class Logger : ILogger, IDisposable {}\n"
                    "public class Cmp : IEqualityComparer<string> {}\n"     # generic one
                    "public class Plain : IEqualityComparer {}\n"            # System.Collections
                    "public class Enc : Encoding {}\n"),
        "Bare.cs": "namespace Other;\npublic class Thing : IDisposable {}\n",
    })
    sup = {(r.from_.rsplit(".", 1)[-1], r.to) for r in ir.relations}
    assert ("Logger", "Serilog.ILogger") in sup and ("Logger", "System.IDisposable") in sup
    assert ("Cmp", "System.Collections.Generic.IEqualityComparer") in sup
    assert ("Plain", "System.Collections.IEqualityComparer") in sup
    assert ("Enc", "System.Text.Encoding") in sup
    assert not any(t.startswith("System.") and f == "Thing" for f, t in sup)  # no using System
    assert [u.raw_type for u in ir.unresolved] == ["IDisposable"]


def test_csharp_linked_files_and_sdks(tmp_path):
    """A file several projects compile through <Compile Include> links gets the imports
    they all have; SDKs that import Microsoft.NET.Sdk (Aspire) bring its implicit usings,
    and an extra <Sdk Name> does not replace the project's SDK."""
    from conftest import extract_source
    from draftsman.extractor import Extractor
    from draftsman.langs import spec_for_path
    on = "<PropertyGroup><ImplicitUsings>enable</ImplicitUsings></PropertyGroup>"
    files = {
        "src/Web/Web.csproj": ('<Project Sdk="Microsoft.NET.Sdk.Web">' + on +
                               '<ItemGroup><Compile Include="..\\Shared\\Ext.cs" Link="Ext.cs" />'
                               "</ItemGroup></Project>"),
        "src/Lib/Lib.csproj": ('<Project Sdk="Microsoft.NET.Sdk">' + on +
                               '<ItemGroup><Compile Include="..\\Shared\\*.cs" /></ItemGroup></Project>'),
        "src/Shared/Ext.cs": ("namespace Shared;\n"
                              "public class Ext : IDisposable { CancellationToken t; ILogger log; }\n"),
        "src/Host/Host.csproj": '<Project Sdk="Aspire.AppHost.Sdk/13.6.0">' + on + "</Project>",
        "src/Host/AppHost.cs": "namespace Host;\npublic class AppHost : IDisposable {}\n",
        "src/Old/Old.csproj": ('<Project Sdk="Microsoft.NET.Sdk">' + on +
                               '<Sdk Name="Microsoft.Build.CentralPackageVersions" Version="2.1.3" />'
                               "</Project>"),
        "src/Old/Old.cs": "namespace Old;\npublic class OldHost : IDisposable {}\n",
        "tests/Unit/Unit.csproj": '<Project Sdk="MSTest.Sdk/3.6.0">' + on + "</Project>",
        "tests/Unit/T.cs": "namespace Unit;\npublic class Handler : IDisposable {}\n",
        "tests/Vs/Vs.csproj": ('<Project Sdk="MSTest.Sdk"><PropertyGroup><ImplicitUsings>enable'
                              "</ImplicitUsings><UseVSTest>true</UseVSTest></PropertyGroup></Project>"),
        "tests/Vs/V.cs": "namespace Vs;\npublic class V {}\n",
    }
    ir = extract_source(tmp_path, files)
    sup = {(r.from_, r.to) for r in ir.relations}
    for t in ("Shared.Ext", "Host.AppHost", "Old.OldHost", "Unit.Handler"):
        assert (t, "System.IDisposable") in sup, t
    # ILogger's namespace is an implicit using of the Web SDK only: not common to both
    assert [(u.raw_type, u.from_) for u in ir.unresolved] == [("ILogger", "Shared.Ext")]

    ex = Extractor(spec_for_path("x.cs"))
    shared = ex.extract(tmp_path / "src/Shared/Ext.cs", "src/Shared/Ext.cs", tmp_path).scope
    assert ";" in shared.project and "System.Threading" in [i.path for i in shared.imports]
    host = ex.extract(tmp_path / "src/Host/AppHost.cs", "src/Host/AppHost.cs", tmp_path).scope
    assert {i.origin for i in host.imports} == {
        "Microsoft.NET.Sdk implicit usings (via Aspire.AppHost.Sdk)"}
    vs = ex.extract(tmp_path / "tests/Vs/V.cs", "tests/Vs/V.cs", tmp_path).scope
    assert "Microsoft.VisualStudio.TestTools.UnitTesting" in [i.path for i in vs.imports]
    unit = ex.extract(tmp_path / "tests/Unit/T.cs", "tests/Unit/T.cs", tmp_path).scope
    assert "Microsoft.VisualStudio.TestTools.UnitTesting" not in [i.path for i in unit.imports]


def test_kotlin_expect_actual_is_one_type(tmp_path):
    """expect in common and actuals per platform merge into one type with each method once,
    kept from the expect declaration even when an actual is read first (androidMain
    sorts before commonMain); look-alike overloads of one file all stay."""
    from conftest import extract_source
    body = "actual fun start(wait: Boolean) {}\n  actual fun stop(a: Long, b: Long) {}\n"
    ir = extract_source(tmp_path, {
        "commonMain/E.kt": ("package p\nclass A\nclass B\n"
                        "expect class Engine {\n  fun start(wait: Boolean)\n  fun stop(a: Long, b: Long)\n"
                        "  fun <T : A> pick(x: T)\n  fun <T : B> pick(x: T)\n}\n"),
        "androidMain/E.kt": "package p\nactual class Engine {\n  " + body + "  fun jvmOnly() {}\n}\n",
        "jsMain/E.kt": "package p\nactual class Engine {\n  " + body + "}\n",
    })
    (engine,) = [t for t in ir.types if t.name == "Engine"]
    names = [m.name for m in engine.members]
    assert sorted(names) == ["jvmOnly", "pick", "pick", "start", "stop"]
    assert engine.location.file == "commonMain/E.kt"                  # where the expect is
    start = next(m for m in engine.members if m.name == "start")
    assert start.file is None and start.line == 5                 # the expect's member


def test_kotlin_default_imports(tmp_path):
    """Default imports are external with their package; with a star import of an outside
    package they are only a hint; a project type of the name wins; `dynamic` is nothing."""
    from conftest import extract_source
    ir = extract_source(tmp_path, {
        "a/Fetch.kt": ("package io.app.fetch\nimport io.app.model.*\n"
                       "class Fetch(val any: JsAny, val d: dynamic) : Exception()\n"),
        "a/model/M.kt": "package io.app.model\nclass M\n",
        "b/Loader.kt": ("package io.app.load\nimport kotlinx.coroutines.*\n"
                        "class Loader(val c: Class<*>)\n"),
        "c/Class.kt": "package io.app.own\nclass Class\nclass Uses(val k: Class)\n",
    })
    rels = {(r.from_, r.kind, r.to) for r in ir.relations}
    assert ("io.app.fetch.Fetch", "extends", "kotlin.Exception") in rels
    assert ("io.app.own.Uses", "association", "io.app.own.Class") in rels
    (u,) = ir.unresolved
    assert u.raw_type == "Class" and "default import java.lang.Class" in u.hint
    assert not any("JsAny" in r.to or "dynamic" in r.to for r in ir.relations)


def test_kotlin_build_scripts_are_not_sources(tmp_path):
    from conftest import extract_source
    ir = extract_source(tmp_path, {
        "build.gradle.kts": "class BuildOnly\n",
        "settings.gradle.kts": "class SettingsOnly\n",
        "x/ktorsettings.cache.settings.gradle.kts": "class Convention\n",
        "scripts/tool.main.kts": "class Tool\n",
    })
    assert {t.name for t in ir.types} == {"Tool"}


def test_dotted_name_with_an_unknown_head_is_not_external(tmp_path):
    """`Outer.Inner` under a star import is unresolved; `com.foo.Bar` and C#'s
    `System.Text.Encoding` are qualified external names."""
    from conftest import extract_source
    ir = extract_source(tmp_path, {
        "J.kt": ("package app\nimport io.ktor.http.*\n"
                 "class J(val a: OutgoingContent.ReadChannelContent, val b: com.foo.Bar)\n"),
        "C.cs": ("using Acme.Web;\nnamespace App;\n"
                 "public class C { System.Text.Encoding e; Outer.Inner i; }\n"),
    })
    unresolved = {u.raw_type: u.hint for u in ir.unresolved}
    assert set(unresolved) == {"OutgoingContent.ReadChannelContent", "Outer.Inner"}
    assert "io.ktor.http.*" in unresolved["OutgoingContent.ReadChannelContent"]
    assert not any("OutgoingContent" in e.id for e in ir.externals)


def test_kotlin_signatures_keep_vararg_receiver_and_suspend(tmp_path):
    from conftest import extract_source
    from draftsman.graph import member_text
    ir = extract_source(tmp_path, {"G.kt": (
        "package p\nclass Grammar\nclass Ctx\nclass B {\n"
        "  constructor(uri: String, rel: String)\n  constructor(uri: String, vararg rel: String)\n"
        "  operator fun Grammar.unaryPlus(): Grammar = this\n"
        "  operator fun String.unaryPlus(): Grammar = Grammar()\n"
        "  fun module(body: Ctx.() -> Unit) {}\n  fun module(body: suspend Ctx.() -> Unit) {}\n}\n")})
    (b,) = [t for t in ir.types if t.name == "B"]
    assert [member_text(m) for m in b.members] == [
        "+ constructor(uri: String, rel: String)", "+ constructor(uri: String, rel: String...)",
        "+ Grammar.unaryPlus(): Grammar", "+ String.unaryPlus(): Grammar",
        "+ module(body: Ctx.() -> Unit)", "+ module(body: suspend Ctx.() -> Unit)"]
    assert not ir.unresolved


def test_function_types_are_dependencies(tmp_path):
    """Types inside a function type (Kotlin DSL lambdas, TS callbacks, Python callables)
    are dependencies of the field or method that writes them; no association."""
    from conftest import extract_source
    ir = extract_source(tmp_path, {
        "k/Client.kt": ("package k\nclass Config\nclass Client\nclass Key\nclass Route\nclass Call\n"
                        "class Log\n"
                        "class Holder(val config: Config.() -> Unit,\n"
                        "             val plugins: MutableMap<Key, (Client) -> Unit>,\n"
                        "             val scoped: context(Log) () -> Unit) {\n"
                        "  fun route(body: suspend Route.(Call) -> Unit) {}\n}\n"),
        "t/hooks.ts": ("export class Req {}\nexport class Res {}\n"
                       "export class Hooks { onRequest?: (req: Req) => Res; }\n"),
        "p/handlers.py": ("from typing import Callable\nclass Event: ...\nclass Result: ...\n"
                          "class Bus:\n    def __init__(self, cb: Callable[[Event], Result]) -> None:\n"
                          "        self.cb = cb\n"),
    })
    rels = {(r.from_.rsplit(".", 1)[-1], r.kind, r.to.rsplit(".", 1)[-1], r.via) for r in ir.relations}
    assert {("Holder", "dependency", "Config", "config"), ("Holder", "dependency", "Client", "plugins"),
            ("Holder", "dependency", "Route", "route"), ("Holder", "dependency", "Call", "route"),
            ("Hooks", "dependency", "Req", "onRequest"), ("Hooks", "dependency", "Res", "onRequest"),
            ("Bus", "dependency", "Event", "cb"), ("Bus", "dependency", "Result", "cb")} <= rels
    assert not any(kind == "association" and to in ("Config", "Req", "Event")
                   for _, kind, to, _ in rels)
    # a map key is no element of the map, but the field depends on it
    assert ("Holder", "association", "Key", "plugins") not in rels
    assert ("Holder", "dependency", "Key", "plugins") in rels
    assert ("Holder", "dependency", "Log", "scoped") in rels      # context parameters
    assert not ir.unresolved


def test_no_inherited_member_types_in_typescript(tmp_path):
    """Merged namespace members are not inherited by subclasses."""
    from conftest import extract_source
    ir = extract_source(tmp_path, {
        "base.ts": "export class Base {}\nexport namespace Base { export interface Listener {} }\n",
        "sub.ts": "import { Base } from './base';\nclass Sub extends Base { l?: Listener; }\n",
    })
    assert not any(r.to.endswith("Base.Listener") for r in ir.relations)
    assert {u.raw_type for u in ir.unresolved} == {"Listener"}


# ------------------------------------------------------------------ language pitfalls

@pytest.fixture(scope="module")
def irs():
    return {lang: extract_dir(FIXTURES / lang / "shop") for lang in LANGS}


def members(ir, name):
    return {m.name: m for m in by_name(ir, name).members}


def test_csharp_partial_class_is_merged(irs):
    ir = irs["csharp"]
    order = members(ir, "Order")
    assert {"AddLine", "IsNew", "Customer", "lines"} <= set(order)
    assert order["Customer"].kind == "property"
    files = {m.file or by_name(ir, "Order").location.file for m in order.values()}
    assert files == {"Orders/Order.cs", "Orders/Order.Logic.cs"}
    assert ("StripeGateway", "implements", "IDisposable") in rels(ir)
    assert members(ir, "OrderLine")["Product"].visibility == "public"  # positional record


def test_kotlin_specifics(irs):
    ir = irs["kotlin"]
    customer = members(ir, "Customer")
    assert customer["orders"].visibility == "private"            # primary constructor property
    assert "constructorOnly" not in members(ir, "Order")          # plain constructor parameter
    order = members(ir, "Order")
    assert order["EMPTY"].static and order["create"].static     # companion object
    assert ("StripeGateway", "implements", "Closeable") in rels(ir)
    assert by_name(ir, "GatewayRegistry").kind == "object"
    assert not members(ir, "PaymentGateway")["supportsRefund"].abstract


def test_typescript_specifics(irs):
    ir = irs["typescript"]
    svc = members(ir, "OrderService")
    assert svc["repository"].visibility == "private"            # parameter property
    assert svc["constructor"].kind == "constructor"
    assert members(ir, "StripeGateway")["#client"].visibility == "private"
    assert "Injectable" in by_name(ir, "OrderService").annotations
    # `import * as pay` then `pay.Receipt`; namespace-merged Customer.Address
    assert ("OrderService", "dependency", "Receipt") in rels(ir)
    assert ("Customer", "association", "Address") in rels(ir)
    assert ("OrderRepository", "extends", "Repository") in rels(ir)  # external typeorm
    # barrel `export type *` (TS 5.0, blanked to `export *` before parsing)
    assert ("Customer", "association", "EntityRef") in rels(ir)
    # imported type aliases are aliases: no relation, not external, not unresolved
    assert not any(short(r.to) in ("OrderId", "RefMap") for r in ir.relations)
    assert not any(short(e.id) in ("OrderId", "RefMap") for e in ir.externals)


def test_python_specifics(irs):
    ir = irs["python"]
    order = members(ir, "Order")
    assert order["customer"].type_ref == "Customer"         # self.customer = customer
    assert order["__lines"].visibility == "private"
    assert "hidden" not in order and "last_added" not in order  # only __init__, not nested
    assert members(ir, "OrderService")["instance"].static     # ClassVar
    assert members(ir, "OrderService")["create"].static       # @staticmethod
    assert by_name(ir, "PaymentGateway").kind == "abstract_class"
    assert members(ir, "PaymentGateway")["charge"].abstract
    assert "dataclass" in by_name(ir, "OrderLine").annotations
    # gateway.py imports Order through the shop.order package re-export
    assert ("PaymentGateway", "dependency", "Order") in rels(ir)


def test_cpp_specifics(irs):
    ir = irs["cpp"]
    own = {(short(r.from_), short(r.to)): r.ownership
           for r in ir.relations if r.kind == "association"}
    assert own[("OrderLine", "Product")] == "owned"         # value member
    assert own[("Customer", "Address")] == "owned"          # unique_ptr
    assert own[("Order", "Customer")] == "shared"           # raw pointer
    assert own[("OrderService", "OrderRepository")] == "shared"  # shared_ptr
    assert own[("OrderService", "PaymentGateway")] == "shared"   # reference
    order = members(ir, "Order")
    assert order["customer_"].visibility == "private" and order["isNew"].visibility == "public"
    assert order["Order"].kind == "constructor"
    assert members(ir, "Product")["sku"].visibility == "public"  # struct default
    assert by_name(ir, "PaymentGateway").kind == "abstract_class"
    assert by_name(ir, "Repository").generics == ["T"]
    assert ("StripeGateway", "extends", "ClientHolder") in rels(ir)
    # out-of-class definitions in order.cpp do not add members
    assert [m.name for m in by_name(ir, "Customer").members].count("isNew") == 1


def test_csharp_inner_type_sees_members_inherited_by_its_outer(tmp_path):
    from conftest import extract_source
    ir = extract_source(tmp_path, {
        "Base.cs": "namespace N { public class Base { public interface IListener {} } }",
        "Outer.cs": "namespace N { class Outer : Base { class Impl : IListener {} } }",
    })
    assert not ir.unresolved
    assert ("Impl", "implements", "IListener") in rels(ir)


# ------------------------------------------------------------------ declarations once missed

def _rels(ir):
    return {(short(r.from_), r.kind, short(r.to), r.via, r.multiplicity) for r in ir.relations}


def test_cpp_class_level_using_is_no_import(tmp_path):
    """`using B::B;` inherits constructors; it must not turn every B into B::B."""
    from conftest import extract_source
    ir = extract_source(tmp_path, {"f.h": (
        "namespace n {\nclass B { public: B(int); };\n"
        "class F1 : public B { using B::B; B* other; };\n}\n")})
    assert {(r.from_, r.kind, r.to) for r in ir.relations} == {
        ("n::F1", "extends", "n::B"), ("n::F1", "association", "n::B")}
    assert not ir.unresolved


def test_kotlin_companion_with_supertypes_is_its_own_type(tmp_path):
    from conftest import extract_source
    ir = extract_source(tmp_path, {"A.kt": (
        "package p\ninterface Creator<T>\nclass Id\n"
        "class A {\n  companion object : Creator<A> { fun make(): A = A() }\n}\n"
        "class B {\n  companion object Factory : Creator<B>\n}\n"
        "class C {\n  companion object { fun id(): Id = Id() }\n}\n")})
    kinds = {t.id: t.kind for t in ir.types}
    assert kinds["p.A.Companion"] == kinds["p.B.Factory"] == "object"
    assert "p.C.Companion" not in kinds                  # no supertypes: a static scope
    r = {(r.from_, r.kind, r.to) for r in ir.relations}
    assert ("p.A.Companion", "implements", "p.Creator") in r
    assert ("p.B.Factory", "implements", "p.Creator") in r
    assert not any(f in ("p.A", "p.B") and k == "implements" for f, k, _ in r)
    assert members(ir, "C")["id"].static
