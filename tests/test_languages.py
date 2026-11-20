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
    "companion object named in a path": {
        **_ALL,
        # `Receipt.Companion.Parser`: the types of a plain companion are Receipt's
        "kotlin": ("StripeGateway", "dependency", "Parser"),
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
    ir = extract_source(tmp_path, {
        "f.h": ("namespace n {\nclass B { public: B(int); };\n"
                "class F1 : public B { using B::B; B* other; };\n}\n"),
        # at file level it imports, also inside an include guard
        "u.h": ("#ifndef U_H\n#define U_H\nnamespace lib { class Widget {}; }\n"
                "using lib::Widget;\nclass User { Widget* w; };\n#endif\n")})
    assert {(r.from_, r.kind, r.to) for r in ir.relations} == {
        ("n::F1", "extends", "n::B"), ("n::F1", "association", "n::B"),
        ("User", "association", "lib::Widget")}
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


def test_variadic_default_and_optional_parameters(tmp_path):
    from conftest import extract_source
    from draftsman.graph import member_text
    ir = extract_source(tmp_path, {
        "py/m.py": ("class Item: ...\nclass Status: ...\n"
                    "class S:\n    def f(self, *args: Item, **kw: Status) -> None: ...\n"
                    "    def g(self, *args, **kw): ...\n"),
        "ts/a.ts": ("export class P {}\nexport class Q {}\n"
                    "export class S { constructor(protected q?: Q) {} f(...rest: P[]) {} }\n"),
        "cs/O.cs": ("namespace N { class Q {} class S { void F(params Q[] qs) {} } }"),
        "cpp/s.h": "class P {};\nclass S { void a(P p = P()); };\n",
    })
    sigs = {t.id: [member_text(m) for m in t.members] for t in ir.types}
    assert sigs["py.m.S"] == ["+ f(*args: Item, **kw: Status): None", "+ g(*args, **kw)"]
    assert sigs["ts/a.S"] == ["+ constructor(q: Q)", "# q: Q", "+ f(...rest: P[])"]
    assert sigs["N.S"] == ["- F(qs: Q[]): void"]
    assert sigs["S"] == ["- a(p: P): void"]
    r = {(r.from_, r.kind, r.to, r.via) for r in ir.relations}
    assert {("py.m.S", "dependency", "py.m.Item", "f"), ("py.m.S", "dependency", "py.m.Status", "f"),
            ("ts/a.S", "dependency", "ts/a.P", "f"), ("ts/a.S", "association", "ts/a.Q", "q"),
            ("N.S", "dependency", "N.Q", "F"), ("S", "dependency", "P", "a")} <= r


def test_primary_constructors(tmp_path):
    from conftest import extract_source
    from draftsman.graph import member_text
    ir = extract_source(tmp_path, {
        "Order.cs": ("namespace N { interface IRepo<T> {} class Person {}\n"
                     "class Order(IRepo<Order> repo, Person owner) {}\n"
                     "record Rec(Person P); }"),
        "W.kt": ("package p\nclass P\nclass Item\nclass WithInit(p: P, vararg val items: Item)\n"
                 "class Hidden private constructor(p: P)\n"
                 "data class Point(val x: Int, val p: P)\n"
                 "class Injected @Inject constructor(private val p: P)\n"),
    })
    sigs = {t.id: [member_text(m) for m in t.members] for t in ir.types}
    assert sigs["N.Order"] == ["+ Order(repo: IRepo<Order>, owner: Person)"]
    assert sigs["N.Rec"] == ["+ P: Person"]                       # records: properties only
    assert sigs["p.WithInit"] == ["+ constructor(p: P, items: Item...)", "+ items: Item..."]
    assert sigs["p.Hidden"] == ["- constructor(p: P)"]
    # only properties: the constructor would repeat them
    assert sigs["p.Point"] == ["+ x: Int", "+ p: P"]
    assert sigs["p.Injected"] == ["- p: P"]
    r = _rels(ir)
    assert {("Order", "dependency", "IRepo", "Order", None),
            ("Order", "dependency", "Person", "Order", None),
            ("WithInit", "dependency", "P", "constructor", None),
            ("WithInit", "association", "Item", "items", "*")} <= r


def test_aliases_are_drawn_through_to_what_they_name(tmp_path):
    from conftest import extract_source
    ir = extract_source(tmp_path, {
        "cs/Point.cs": "namespace Acme.Core { class Point {} }",
        "cs/Uses.cs": ("using Pt = Acme.Core.Point;\nnamespace App { class Uses {\n"
                       "  Pt p; global::Acme.Core.Point q; void F(Pt x) {} } }"),
        "kt/U.kt": ("package k\nclass Pt\nopen class Base\ntypealias PtAlias = List<Pt>\n"
                    "typealias BaseAlias = Base\nclass Uses(val p: PtAlias) : BaseAlias()\n"),
        "ts/u.ts": ("export class A {}\nexport class B {}\nexport type X = A | B;\n"
                    "type Y = X;\nexport class Uses { x?: X; y?: Y; }\n"),
        "cpp/s.h": ("class Circle {};\nclass S {\n  typedef Circle* CirclePtr;\n"
                    "  using Ref = Circle;\n  CirclePtr c;\n  Ref r;\n};\n"),
        "cpp/l.h": ("namespace n {\ntypedef struct Legacy { int a; } Legacy_t, *LegacyPtr;\n"
                    "typedef struct { int b; } Anon_t, *AnonPtr;\n}\n"
                    "class L { n::Legacy_t v; n::LegacyPtr p; n::Anon_t a; n::AnonPtr ap; };\n"
                    # an anonymous union is no type: an alias with nothing to draw
                    "typedef union { int i; float f; } U_t, *UPtr;\n"
                    "class H { U_t u; UPtr p; };\n"),
    })
    r = _rels(ir)
    assert {("Uses", "association", "Point", "p", "1"), ("Uses", "association", "Point", "q", "1"),
            ("Uses", "dependency", "Point", "F", None),
            ("Uses", "association", "Pt", "p", "*"), ("Uses", "extends", "Base", None, None),
            ("Uses", "association", "A", "x", "1"), ("Uses", "association", "B", "x", "1"),
            ("Uses", "association", "A", "y", "1"),
            ("S", "association", "Circle", "c", "1"), ("S", "association", "Circle", "r", "1")} <= r
    own = {(r.via, r.ownership) for r in ir.relations if r.from_ == "S"}
    assert own == {("c", "shared"), ("r", "owned")}
    # a typedef of a struct definition names the struct; an anonymous one is the struct
    assert {(r.via, r.to, r.ownership) for r in ir.relations if r.from_ == "L"} == {
        ("v", "n::Legacy", "owned"), ("p", "n::Legacy", "shared"),
        ("a", "n::Anon_t", "owned"), ("ap", "n::Anon_t", "shared")}
    assert by_name(ir, "Anon_t").kind == "struct"
    assert not ir.unresolved


def test_tuples_relate_to_each_element_once(tmp_path):
    from conftest import extract_source
    ir = extract_source(tmp_path, {
        "cs/T.cs": "namespace N { class Person {} class Point {} class T { (Person a, Point b) pair; } }",
        "ts/t.ts": ("export class Point {}\nexport class Circle {}\n"
                    "export class T { pair?: [Point, Circle]; named?: [a: Point, b?: Circle]; }\n"),
        "py/t.py": ("class P: ...\nclass Q: ...\nclass T:\n    pair: tuple[P, Q]\n"
                    "    many: tuple[P, ...]\n"),
        "cpp/t.h": "#include <tuple>\nclass P {};\nclass B {};\nclass T { std::tuple<P, B*> t; };\n",
    })
    r = {(r.from_, r.to, r.via, r.multiplicity) for r in ir.relations}
    assert r == {("N.T", "N.Person", "pair", "1"), ("N.T", "N.Point", "pair", "1"),
                 ("ts/t.T", "ts/t.Point", "pair", "1"), ("ts/t.T", "ts/t.Circle", "pair", "1"),
                 ("ts/t.T", "ts/t.Point", "named", "1"), ("ts/t.T", "ts/t.Circle", "named", "1"),
                 ("py.t.T", "py.t.P", "pair", "1"), ("py.t.T", "py.t.Q", "pair", "1"),
                 ("py.t.T", "py.t.P", "many", "*"),
                 ("T", "P", "t", "1"), ("T", "B", "t", "1")}


def test_java_throws_is_a_dependency(tmp_path):
    from conftest import extract_source
    ir = extract_source(tmp_path, {
        "p/E.java": "package p; public class E extends Exception {}",
        "p/S.java": "package p; class S { void f() throws E, java.io.IOException {} }"})
    assert ("p.S", "dependency", "p.E", "f") in {(r.from_, r.kind, r.to, r.via) for r in ir.relations}
    assert [m.params for m in by_name(ir, "S").members] == [[]]
    assert not ir.unresolved


def test_python_literal_annotated_and_type_parameters(tmp_path):
    from conftest import extract_source
    ir = extract_source(tmp_path, {"m.py": (
        "from typing import Annotated, Literal\nclass Item: ...\nclass Order[K]: ...\n"
        "class S:\n    mode: Literal['a', 'b']\n    item: Annotated[Item, 'x']\n"
        "    gt: Annotated[Item, Field(gt=0, json_schema_extra={'a': [1]})]\n"
        "    many: list[Annotated[Item, Depends(get_db)]]\n"
        "class New[K: Item, *Ts, **P](Order[K]):\n    k: K\n"
        "    def f[T](self, x: T) -> T: ...\n")})
    assert not ir.unresolved
    r = {(short(r.from_), r.kind, short(r.to), r.via) for r in ir.relations}
    assert {("S", "association", "Item", "item"), ("S", "association", "Item", "gt"),
            ("S", "association", "Item", "many")} <= r
    assert ("New", "extends", "Order", None) in r
    assert by_name(ir, "New").generics == ["K", "Ts", "P"]


def test_python_literal_values_are_no_types_anywhere(tmp_path):
    """Literal["Item"] names a value, also in signatures, aliases and container keys,
    where the dependency path reads the type (Python drops the quotes first)."""
    from conftest import extract_source
    ir = extract_source(tmp_path, {
        "m.py": ("from typing import Literal\nclass Item: ...\nclass Db: ...\n"
                 "type Mode = Literal['Item', 'Db']\n"
                 "class A:\n    a: Literal['Item', 'Db']\n    g: Mode\n"
                 "    def m(self, k: Literal['Item']) -> Literal['ok', 'fail']: ...\n"
                 "class C:\n    kinds: dict[Literal['Db'], int]\n"),
        # a project class called Literal is a class: its arguments are types
        "own/lit.py": ("class Literal: ...\nclass Item: ...\n"
                       "class B:\n    def m(self, k: Literal['Item']) -> None: ...\n"),
    })
    assert {(r.from_, r.kind, r.to, r.via) for r in ir.relations} == {
        ("own.lit.B", "dependency", "own.lit.Literal", "m"),
        ("own.lit.B", "dependency", "own.lit.Item", "m")}
    assert not ir.unresolved


def test_project_classes_named_like_special_forms_win(tmp_path):
    """Tuple, Literal, ...: read as a tuple or as values only when the project has no class
    of the name (Java has no tuples, so projects write their own Tuple<A, B>)."""
    from conftest import extract_source
    ir = extract_source(tmp_path, {
        "p/Tuple.java": "package p; class Tuple<A, B> {}",
        "p/P.java": "package p; class P {}",
        "p/Holder.java": "package p; class Holder { Tuple<P, P> t; Tuple<P, P> f() { return null; } }",
        "t.ts": "export class Tuple<A, B> {}\nexport class Q {}\nexport class H { t?: Tuple<Q, Q>; }\n",
        "py/m.py": ("class Literal: ...\nclass Annotated: ...\nclass Item: ...\n"
                    "class S:\n    l: Literal[Item]\n    a: Annotated[Item, 'x']\n"),
    })
    assert {(short(r.from_), r.kind, short(r.to), r.via) for r in ir.relations} == {
        ("Holder", "association", "Tuple", "t"), ("Holder", "dependency", "P", "t"),
        ("Holder", "dependency", "Tuple", "f"), ("Holder", "dependency", "P", "f"),
        ("H", "association", "Tuple", "t"), ("H", "dependency", "Q", "t"),
        ("S", "association", "Literal", "l"), ("S", "dependency", "Item", "l"),
        ("S", "association", "Annotated", "a"), ("S", "dependency", "Item", "a")}
    assert not ir.unresolved


def test_literal_and_annotated_are_ordinary_names_elsewhere(tmp_path):
    """The Python rules need a subscript: a Java or TypeScript class called Literal (an
    AST node, say) is an ordinary type, also as `Literal[]` or `List<Literal>`."""
    from conftest import extract_source
    ir = extract_source(tmp_path, {
        "p/Literal.java": "package p; class Literal {}",
        "p/Annotated.java": "package p; class Annotated {}",
        "p/U.java": ("package p; import java.util.List;\n"
                     "class U { Literal l; List<Literal> ls; Annotated[] as;\n"
                     "  Literal f(Annotated a) { return null; } }"),
        "t.ts": "export class Literal {}\nexport class T { l?: Literal; ls?: Literal[]; }\n",
    })
    assert {(r.from_, r.kind, r.to, r.via) for r in ir.relations} == {
        ("p.U", "association", "p.Literal", "l"), ("p.U", "association", "p.Literal", "ls"),
        ("p.U", "association", "p.Annotated", "as"), ("p.U", "dependency", "p.Literal", "f"),
        ("p.U", "dependency", "p.Annotated", "f"),
        ("t.T", "association", "t.Literal", "l"), ("t.T", "association", "t.Literal", "ls")}
    assert not ir.unresolved


def test_typescript_import_types(tmp_path):
    """`import("rxjs").Observable<P>` is not in the grammar; the field keeps its type and
    the rest of the class is still read."""
    from conftest import extract_source
    from draftsman.graph import member_text
    ir = extract_source(tmp_path, {
        "other.ts": "export class Foo {}\n",
        "a.ts": ("export class P {}\nexport class Foo {}\n"
                 "export type T = import('./other').Foo;\n"
                 "export class S {\n  o?: import('rxjs').Observable<P>;\n  p?: P;\n"
                 "  f?: import(\"./other\").Foo;\n  t?: T;\n}\n")})
    assert not ir.diagnostics and not ir.unresolved
    # from the module named, never the file's own Foo
    assert {(r.via, r.to, r.multiplicity) for r in ir.relations} == {
        ("o", "a.P", "*"), ("p", "a.P", "1"), ("f", "other.Foo", "1"), ("t", "other.Foo", "1")}
    s = by_name(ir, "S")
    assert s.generics == []
    assert [(member_text(m), m.line) for m in s.members] == [
        ("+ o: rxjs.Observable<P>", 5), ("+ p: P", 6), ("+ f: other.Foo", 7), ("+ t: T", 8)]


def test_cpp_qt_function_pointers_unions_and_inline_namespaces(tmp_path):
    from conftest import extract_source
    from draftsman.graph import member_text
    ir = extract_source(tmp_path, {
        "w.h": ("class QObject {};\nclass Model {};\nclass W : public QObject {\n"
                "  Q_OBJECT\n  Q_PROPERTY(int x\n             READ x)\npublic:\n  Model* model;\n"
                "  virtual Q_INVOKABLE void load();\n  Q_REVISION(2) Q_INVOKABLE void more() Q_DECL_OVERRIDE;\npublic slots:\n  void reload();\nsignals:\n"
                "  void changed();\nprivate Q_SLOTS:\n  void tick();\n};\n"),
        "m.h": ("namespace acme { inline namespace v1 { class Versioned {}; } }\n"
                "class Cb {\n  void (*cb)(int);\n  union { int a; float b; };\n"
                "  acme::Versioned v;\n};\n"
                "namespace acme { class User { Versioned v; }; }\n"),
        "q.h": ("QT_BEGIN_NAMESPACE\nclass QLabel;\nQT_END_NAMESPACE\nclass Model {};\n"
                "class Item : public QObject {\n  Q_OBJECT\n  QML_ELEMENT\n  QML_NAMED_ELEMENT(Thing)\n"
                "  Q_PROPERTY(int x READ x) /* moc */\npublic:\n  Model* m;\n};\n"),
        # a forward-declaration header with no other Qt macro
        "fwd.h": "QT_BEGIN_NAMESPACE\nclass Fwd;\nQT_END_NAMESPACE\nclass Panel { Model* m; };\n",
        # C code may name constants like Qt's macros
        "e.h": "enum Flags {\n  Q_FIRST = 1,\n  Q_SECOND,\n  Q_FLAG = 4,\n  QML_LAST\n};\n",
    })
    assert not ir.diagnostics and not ir.unresolved
    sigs = {t.id: [member_text(m) for m in t.members] for t in ir.types}
    assert sigs["Item"] == ["+ m: Model*"]
    assert {("Item", "Model"), ("Panel", "Model")} <= {(r.from_, r.to) for r in ir.relations}
    assert sigs["W"] == ["+ model: Model*", "+ load(): void", "+ more(): void", "+ reload(): void",
                         "+ changed(): void", "- tick(): void"]
    w = next(t for t in ir.types if t.id == "W")
    assert [m.line for m in w.members] == [8, 9, 10, 12, 14, 16]       # line numbers kept
    # a function pointer is a field; anonymous union members are members of the class
    assert sigs["Cb"] == ["- cb: void(int)*", "- a: int", "- b: float", "- v: acme::Versioned"]
    assert sigs["Flags"] == ["Q_FIRST", "Q_SECOND", "Q_FLAG", "QML_LAST"]   # enum constants, no Qt macros
    r = {(r.from_, r.to) for r in ir.relations}
    assert ("Cb", "acme::v1::Versioned") in r and ("acme::User", "acme::v1::Versioned") in r


def test_kotlin_annotation_class(tmp_path):
    from conftest import extract_source
    ir = extract_source(tmp_path, {"A.kt": "package p\nannotation class Marker\n"})
    assert by_name(ir, "Marker").kind == "annotation"


# ------------------------------------------------------------------ library types and reasons

def test_kotlin_library_types_through_star_imports(tmp_path):
    """`import kotlinx.coroutines.*` makes CoroutineScope kotlinx.coroutines.CoroutineScope;
    the project's own type, an explicit import or the same package come first, and
    without the star import the name stays unresolved."""
    from conftest import extract_source
    ir = extract_source(tmp_path, {
        "k/Worker.kt": ("package io.app\nimport kotlinx.coroutines.*\nimport kotlin.coroutines.*\n"
                        "class Worker : CoroutineScope {\n  val job: Job? = null\n"
                        "  override val coroutineContext: CoroutineContext get() = TODO()\n}\n"
                        "class Elem\nobject CurrentKey : CoroutineContext.Key<Elem>\n"),
        "own/Job.kt": ("package io.own\nimport kotlinx.coroutines.*\nclass Job\n"
                       "class Holder(val j: Job)\n"),
        "exp/A.kt": "package io.exp\nimport kotlinx.coroutines.*\nimport my.lib.Job\nclass A : Job\n",
        "none/B.kt": "package io.none\nimport io.vendor.*\nclass B : CoroutineScope\n",
    })
    rels = {(r.from_, r.kind, r.to) for r in ir.relations}
    assert ("io.app.Worker", "implements", "kotlinx.coroutines.CoroutineScope") in rels
    assert ("io.app.CurrentKey", "implements", "kotlin.coroutines.CoroutineContext.Key") in rels
    assert ("io.own.Holder", "association", "io.own.Job") in rels          # same package
    assert ("io.exp.A", "implements", "my.lib.Job") in rels                 # explicit import
    (u,) = ir.unresolved                                                    # not star-imported
    assert (u.from_, u.raw_type, u.reason) == ("io.none.B", "CoroutineScope", "outside")


def test_kotlin_library_types_give_way_to_inherited_nested_types(tmp_path):
    """A nested type of a supertype comes before any import in Kotlin. Under an external
    supertype whose nested types are not known, the table is not used."""
    from conftest import extract_source
    ir = extract_source(tmp_path, {"C.kt": (
        "package io.app\nimport kotlinx.coroutines.*\nimport java.io.FilterInputStream\n"
        "class C(i: java.io.InputStream) : FilterInputStream(i) {\n  val job: Job? = null\n"
        # a nested class's own supertype clause sees the nested types of C's supertypes
        "  class Inner : CoroutineScope\n}\n"
        "class D : CoroutineScope {\n  val job: Job? = null\n}\n")})
    assert {(u.from_, u.raw_type) for u in ir.unresolved} == {
        ("io.app.C", "Job"), ("io.app.C.Inner", "CoroutineScope")}
    assert all("inherited from java.io.FilterInputStream" in u.hint for u in ir.unresolved)


def test_kotlin_library_type_rules(tmp_path, monkeypatch):
    """Two star-imported packages with the name are an ambiguity, not a choice; a known
    nested type of the same name in a supertype wins."""
    from conftest import extract_source
    from draftsman.langs import kotlin
    monkeypatch.setitem(kotlin._LIBRARY, "Flow",
                        ("kotlinx.coroutines.flow", "kotlinx.coroutines.channels"))
    monkeypatch.setitem(kotlin._NESTED, "kotlinx.coroutines.CoroutineScope", frozenset({"Job"}))
    ir = extract_source(tmp_path, {
        "a/F.kt": ("package io.a\nimport kotlinx.coroutines.flow.*\n"
                   "import kotlinx.coroutines.channels.*\nclass F : Flow<Int>\n"),
        "b/G.kt": "package io.b\nimport kotlinx.coroutines.flow.*\nclass G : Flow<Int>\n",
        "c/S.kt": "package io.c\nimport kotlinx.coroutines.*\nclass S : CoroutineScope {\n  val job: Job? = null\n}\n",
    })
    rels = {(r.from_, r.kind, r.to) for r in ir.relations}
    assert ("io.b.G", "implements", "kotlinx.coroutines.flow.Flow") in rels
    assert ("io.c.S", "implements", "kotlinx.coroutines.CoroutineScope") in rels
    assert {(u.from_, u.raw_type) for u in ir.unresolved} == {("io.a.F", "Flow"), ("io.c.S", "Job")}


def test_wildcard_hint_names_outside_packages_first(tmp_path):
    """Packages outside the sources are named, all of them; those the project declares too
    are counted after them."""
    from conftest import extract_source
    ir = extract_source(tmp_path, {
        "b/B.kt": "package io.app.b\nclass B\n",
        "c/C.kt": "package io.app.c\nclass C\n",
        "d/D.kt": "package io.app.d\nclass D\n",
        "a/A.kt": ("package io.app.a\nimport io.app.b.*\nimport kotlinx.io.*\nimport io.app.c.*\n"
                   "import okio.*\nclass A(val buf: Buffer)\n"),
        "e/E.kt": "package io.app.e\nimport io.app.d.*\nimport kotlinx.io.*\nclass E(val buf: Buffer)\n",
        "f/F.kt": "package io.app.f\nimport io.app.d.*\nclass F(val buf: Buffer)\n",
    })
    hints = {u.from_: u.hint for u in ir.unresolved}
    assert hints["io.app.a.A"] == ("may come from wildcard import kotlinx.io.*, okio.*; "
                                   "or from one of 2 packages the project also declares")
    assert hints["io.app.e.E"] == ("may come from wildcard import kotlinx.io.*; "
                                   "or from io.app.d.*, a package the project also declares")
    assert hints["io.app.f.F"] == ("may come from wildcard import io.app.d.* "
                                   "(a package the project also declares)")


def test_unresolved_reasons(tmp_path):
    from conftest import extract_source
    ir = extract_source(tmp_path, {
        "p/Request.java": "package p; public class Request {}",
        "q/A.java": ("package q; import com.vendor.*;\n"
                     "class A { Request r; Gadget g; Outer.Missing m; Nowhere n; Gizmo.Part p; }"),
        "q/Outer.java": "package q; class Outer {}",
        "r/B.java": "package r; class B { Elsewhere e; }",
    })
    reasons = {u.raw_type: u.reason for u in ir.unresolved}
    assert reasons == {"Request": "ambiguous",       # p.Request shares the name
                       "Gadget": "outside",          # only com.vendor.* explains it
                       "Outer.Missing": "unexplained",   # Outer has no such nested type
                       "Nowhere": "outside",         # com.vendor.* could still provide it
                       "Elsewhere": "unexplained",   # no import could provide it
                       "Gizmo.Part": "outside"}      # as its head is


def test_kotlin_library_table_leaves_out_platform_typealiases(tmp_path):
    """kotlinx.coroutines.Runnable is java.lang.Runnable on the JVM (an `actual typealias`),
    so it is not in the table: still the uncertain default import, as before."""
    from conftest import extract_source
    ir = extract_source(tmp_path, {"W.kt": (
        "package io.app\nimport kotlinx.coroutines.*\nclass Worker : Runnable\n"
        "class D(val d: CloseableCoroutineDispatcher)\n")})
    assert not ir.relations
    hints = {u.raw_type: u.hint for u in ir.unresolved}
    assert set(hints) == {"Runnable", "CloseableCoroutineDispatcher"}
    assert "may be the default import java.lang.Runnable" in hints["Runnable"]


def test_kotlin_library_types_under_known_library_supertypes(tmp_path):
    """Under a library supertype whose nested types are known (its own and inherited:
    CoroutineContext.Element sees CoroutineContext's Element and Key), the table applies."""
    from conftest import extract_source
    from draftsman.langs import kotlin
    assert kotlin._NESTED["kotlinx.coroutines.CompletableJob"] == {"Element", "Key"}
    assert kotlin._NESTED["kotlinx.coroutines.channels.Channel"] == {"Factory"}
    ir = extract_source(tmp_path, {"E.kt": (
        "package io.app\nimport kotlin.coroutines.*\nimport kotlinx.coroutines.channels.*\n"
        "class Ctx : CoroutineContext.Element {\n"
        "  override val key: CoroutineContext.Key<*> get() = TODO()\n"
        "  object MyKey : CoroutineContext.Key<Ctx>\n}\n"
        "class Tracer<E>(val delegate: ChannelIterator<E>) : ChannelIterator<E>\n")})
    assert not ir.unresolved
    assert {(r.from_, r.to) for r in ir.relations} == {
        ("io.app.Ctx", "kotlin.coroutines.CoroutineContext.Element"),
        ("io.app.Ctx.MyKey", "kotlin.coroutines.CoroutineContext.Key"),
        ("io.app.Tracer", "kotlinx.coroutines.channels.ChannelIterator")}


def test_kotlin_serialization_types_through_star_imports(tmp_path):
    """kotlinx.serialization through star imports; the project's own Decoder wins where its
    package is imported; Json (also kotlin.js's default import) is not decided by the table."""
    from conftest import extract_source
    ir = extract_source(tmp_path, {
        "own/Decoder.kt": "package io.app.charsets\nclass Decoder\n",
        "a/D.kt": ("package io.app.a\nimport kotlinx.serialization.*\n"
                   "import kotlinx.serialization.encoding.*\n"
                   "class D : AbstractDecoder() {\n  val s: KSerializer<Int>? = null\n}\n"
                   "class E(val d: Decoder) : Encoder\n"),
        "b/U.kt": "package io.app.b\nimport io.app.charsets.*\nclass U(val d: Decoder)\n",
        "c/J.kt": "package io.app.c\nimport kotlinx.serialization.json.*\nclass J(val j: Json, val e: JsonElement)\n",
    })
    rels = {(r.from_, r.kind, r.to) for r in ir.relations}
    assert ("io.app.a.D", "extends", "kotlinx.serialization.encoding.AbstractDecoder") in rels
    assert ("io.app.a.E", "implements", "kotlinx.serialization.encoding.Encoder") in rels
    assert ("io.app.b.U", "association", "io.app.charsets.Decoder") in rels
    (u,) = ir.unresolved
    assert (u.from_, u.raw_type, u.reason) == ("io.app.c.J", "Json", "outside")
    assert "may be the default import kotlin.js.Json" in u.hint


def test_kotlin_core_supertypes_have_known_nested_types(tmp_path):
    """Exception and AutoCloseable declare no nested types (nor their java.lang classes):
    the table applies under them."""
    from conftest import extract_source
    ir = extract_source(tmp_path, {"X.kt": (
        "package io.app\nimport kotlinx.coroutines.*\n"
        "class Failure : IllegalStateException() {\n  val job: Job? = null\n}\n"
        "class Res : AutoCloseable {\n  val scope: CoroutineScope? = null\n"
        "  override fun close() {}\n}\n")})
    assert not ir.unresolved


def test_kotlin_js_any_is_a_core_type(tmp_path):
    """`: JsAny` is drawn like `: Exception`, also next to a star import of an outside package;
    a JsAny field relates to nothing."""
    from conftest import extract_source
    ir = extract_source(tmp_path, {"O.kt": (
        "package io.app\nimport org.khronos.webgl.*\n"
        "external interface Options : JsAny\nclass Holder(val any: JsAny)\n")})
    assert {(r.from_, r.kind, r.to) for r in ir.relations} == {
        ("io.app.Options", "extends", "kotlin.js.JsAny")}
    assert not ir.unresolved


def test_unreachable_nested_types_are_no_candidates(tmp_path):
    """A nested type is a candidate only inside its outer type; elsewhere it is named in the
    hint and the reason follows what is left."""
    from conftest import extract_source
    ir = extract_source(tmp_path, {
        "a/Outer.java": ("package a; public class Outer { public static class Entry {}\n"
                         "  public static class Link { public static class Map {} } }"),
        "b/U.java": "package b; class U { Entry e; Map.Entry m; Link l; }",
        "c/V.java": "package c; import com.vendor.*; class V { Link l; }",
        "d/Entry.java": "package d; public class Entry {}",
        "f/Box.java": "package f; public class Box { public static class Gone {} }",
        "g/X.java": "package g; import a.Outer; class X { Outer.Gone g; }",
    })
    found = {(u.from_, u.raw_type): u for u in ir.unresolved}
    e = found[("b.U", "Entry")]
    assert e.reason == "ambiguous" and e.candidates == ["d.Entry"]   # top-level stays
    assert "out of scope here: a.Outer.Entry" in e.hint
    m = found[("b.U", "Map.Entry")]                                    # dotted: by its head
    assert m.candidates == [] and m.reason == "unexplained"
    assert "a.Outer.Link.Map" in m.hint
    # only a nested type has the name: no candidate, the reason is what else explains it
    assert (found[("b.U", "Link")].candidates, found[("b.U", "Link")].reason) == ([], "unexplained")
    assert (found[("c.V", "Link")].candidates, found[("c.V", "Link")].reason) == ([], "outside")
    assert "out of scope here: a.Outer.Link" in found[("c.V", "Link")].hint
    # the head found, the rest not: other nested types of the name are out of scope too
    g = found[("g.X", "Outer.Gone")]
    assert g.candidates == [] and g.hint == ("a.Outer has no nested type Gone; project nested "
                                             "type of the name, out of scope here: f.Box.Gone")


def test_typescript_import_alias_of_a_namespace_member(tmp_path):
    from conftest import extract_source
    ir = extract_source(tmp_path, {
        "o.ts": "export namespace Outer { export class Inner {} }\n",
        "u.ts": "import { Outer } from './o';\nimport Inner = Outer.Inner;\nexport class U { i?: Inner; }\n"})
    assert {(r.from_, r.to) for r in ir.relations} == {("u.U", "o.Outer.Inner")}
    assert not ir.unresolved


def test_focus_diagram_folds_nested_types(lang_ir):
    """`StripeGateway.fee: Receipt.Money` is drawn as one arrow to Receipt in a diagram
    focused on Receipt; `Receipt.amount: Money` folds onto Receipt itself and draws
    nothing; the fact behind the arrow still names the nested type."""
    from draftsman.scene import FoldedRelation, build_scene
    from draftsman.view import View

    lang, ir = lang_ir
    if lang == "typescript":
        return   # TS classes cannot nest classes: nothing to fold
    receipt = by_name(ir, "Receipt").id
    scene = build_scene(ir, View.from_dict({"focus": receipt, "hops": 1}))
    shown = {short(t.id) for t in scene.types}
    assert "Money" not in shown and "Receipt" in shown and "StripeGateway" in shown
    assert by_name(ir, "Money").id in scene.folded[receipt]
    fee = [r for r in scene.relations if short(r.from_) == "StripeGateway"
           and r.kind == "association"]
    assert [(short(r.to), short(r.fact.to)) for r in fee] == [("Receipt", "Money")]
    assert isinstance(fee[0], FoldedRelation) and fee[0].via == fee[0].fact.via
    assert not [r for r in scene.relations if r.from_ == r.to]

    boxes = build_scene(ir, View.from_dict({"focus": receipt, "hops": 1, "nested": "boxes"}))
    assert {"Money", "Receipt", "StripeGateway"} <= {short(t.id) for t in boxes.types}
    assert not boxes.folded and not any(isinstance(r, FoldedRelation) for r in boxes.relations)
