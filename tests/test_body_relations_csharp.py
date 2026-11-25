"""Relations read from names written in C# bodies (`evidence` "body", issue #5)."""

import sys
from pathlib import Path

from conftest import extract_source
from draftsman.extractor import Extractor
from draftsman.langs import spec_for_path
from draftsman.resolve import _Builder
from draftsman.wrappers import Wrappers

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench"))
from answer_key import expected  # noqa: E402   the hand-written answers' markers

# tests/fixtures/csharp/body, which `bench/roslyn_oracle/oracle.py selftest` checks against
# Roslyn
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "csharp" / "body"
SUFFIXES = (".cs",)


def _fixture() -> list:
    return [Extractor(spec_for_path(p.name)).extract(p, p.relative_to(FIXTURE).as_posix(), FIXTURE)
            for p in sorted(FIXTURE.rglob("*")) if p.suffix in SUFFIXES]


def test_body_names_stand_where_the_hand_written_answers_say():
    # every part of a name the extractor records is in the position its marker gives; one
    # no marker lists is lower case (a variable, a method), and one marked "-" (a member
    # after a type, `Status.Open`, or a namespace before one, `Shop.Order`) is part of a
    # name whose other part is a name; every marked name is recorded
    want = expected(FIXTURE, SUFFIXES)
    problems, recorded = [], set()
    for raw in _fixture():
        for r in (r for t in raw.types for r in t.body_refs):
            marks = [want.get((raw.path, line, col), (None, None)) for line, col in r.places]
            for part, (line, col), (answer, position) in zip(r.text.split("."), r.places, marks):
                recorded.add((raw.path, line, col))
                where = f"{raw.path}:{line}:{col + 1} {part} of {r.text}"
                if answer is None:
                    if part[:1].isupper():
                        problems.append(f"{where}: no marker")
                elif answer == "-":
                    if all(a in (None, "-") for a, _ in marks):
                        problems.append(f"{where}: a declaration, recorded as {r.position}")
                elif position != r.position:
                    problems.append(f"{where}: {r.position}, the marker says {position}")
    assert problems == []
    # top-level statements belong to no type the extractor sees, `global::A.B.C` is read
    # as a type, not as an expression's head, and a property pattern's path is not read
    missed = sorted((rel, line, answer) for (rel, line, col), (answer, _) in want.items()
                    if answer != "-" and (rel, line, col) not in recorded)
    assert missed == [("Program.cs", 4, "Shop.Order"), ("Program.cs", 5, "Shop.Customer"),
                      ("Program.cs", 5, "Shop.Order"), ("Shop/Positions.cs", 47, "Shop.Status"),
                      ("Shop/Review/Parse.cs", 31, "var"), ("Shop/Review/Parse.cs", 32, "var")]


def test_body_relations_go_where_the_hand_written_answers_say():
    want = expected(FIXTURE, SUFFIXES)
    builder = _Builder("body", _fixture(), Wrappers.load())
    builder.build()
    wrong, drawn = [], set()
    for file, line, col, _, to in builder.body_uses:
        drawn.add((file, line, col))
        answer, _ = want[(file, line, col)]
        if answer != to:
            wrong.append((file, line, answer))
    assert wrong == []
    # every project type is drawn, but a type's own name, the part of a longer name
    # (`Order` in `Order.Line`), in top-level statements, after `global::`, where a
    # parameter of the name has the type's name for its type (`Customer Customer`:
    # Roslyn reads `Customer.Guest` as the type; the extractor knows a field's type, not a
    # parameter's) or a field does and the member after it has a static and an instance
    # overload (`Order.Of()`), where the arity written is not the nearest type's (`Box`
    # beside Shop.Box<T>: Roslyn's is Lib.Box further out), and where a static field a
    # file's `using static` brings in shares the name (Roslyn looks at the namespaces
    # around first; the extractor takes the field wherever), and a `file` type's name in
    # any file but its only one (two files' `file class Local` are one id in ir.json; in
    # FileB.cs the extractor finds FileA.cs's Helper before Shop.Rev's and gives up)
    missed = [(file, line, answer) for (file, line, col), (answer, position) in want.items()
              if answer in builder.types and (file, line, col) not in drawn]
    own = [("Lib/Lib.cs", 37, "Lib.Extra.Receipt"), ("Shop/Bodies.cs", 30, "Shop.Bodies"),
           ("Shop/Order.cs", 9, "Shop.Order"), ("Shop/Order.cs", 10, "Shop.Order"),
           ("Shop/Order.cs", 16, "Shop.Order.Line"), ("Shop/Order.cs", 23, "Shop.Customer"),
           ("Shop/Order.cs", 28, "Shop.Status"), ("Shop/Order.cs", 42, "Shop.Money"),
           ("Shop/Repo.cs", 11, "Shop.Repo")]
    parts = [("Shop/Positions.cs", 27, "Shop.Order"), ("Shop/Positions.cs", 43, "Shop.Order"),
             ("Shop/Positions.cs", 44, "Shop.Util"), ("Shop/ColorColor.cs", 12, "Shop.Order"),
             ("Shop/Review/Qualified.cs", 44, "Shop.Rev.Qual.Lib"),
             ("Shop/Review/Qualified.cs", 45, "Shop.Rev.Qual.Lib"),
             ("Shop/Review/Qualified.cs", 46, "Shop.Rev.Qual.Lib"),
             ("Shop/Review/Heads.cs", 53, "Shop.Rev.Gen.Lib")]
    top_level = [("Program.cs", 4, "Shop.Order"), ("Program.cs", 5, "Shop.Customer"),
                 ("Program.cs", 5, "Shop.Order")]
    global_ = [("Shop/Positions.cs", 28, "Shop.Order"), ("Shop/Positions.cs", 47, "Shop.Status")]
    color_color = [("Shop/Hiding.cs", 77, "Shop.Customer"), ("Shop/ColorColor.cs", 13, "Shop.Order")]
    arity = [("Shop/Signatures.cs", 14, "Lib.Box")]
    using_static = [("Shop/Inner.cs", 17, "Shop.Money")]
    file_types = [("Shop/Review/FileA.cs", 9, "Shop.Rev.Files.Local"),
                  ("Shop/Review/FileB.cs", 7, "Shop.Rev.Helper"),
                  ("Shop/Review/FileB.cs", 8, "Shop.Rev.Files.Local")]
    # (through an alias where a namespace around declares a type of the name, Roslyn's
    # type is drawn: #7)
    assert sorted(missed) == sorted(own + parts + top_level + global_ + color_color
                                    + arity + using_static + file_types)


def _body(ir) -> list[tuple]:
    return sorted((r.from_, r.to, r.via, r.source_location.line)
                  for r in ir.relations if r.evidence == "body")


def test_a_using_in_a_namespace_block_comes_before_the_namespaces_around_it(tmp_path):
    ir = extract_source(tmp_path, {
        "Order.cs": "namespace Shop { public class Order { } }\nnamespace Lib { public class Order { } }\n",
        "Near.cs": """namespace Shop.Other
{
    using Lib;
    public class Near { object M() => new Order(); }
}
namespace Shop.Far
{
    public class Far { object M() => new Order(); }
}
"""})
    assert _body(ir) == [("Shop.Far.Far", "Shop.Order", "M", 8),
                         ("Shop.Other.Near", "Lib.Order", "M", 4)]


def test_a_primary_constructor_parameter_hides_a_type_in_every_member(tmp_path):
    # a record's parameters are its properties, which hide it the same
    ir = extract_source(tmp_path, {"A.cs": """namespace Shop;
public class Customer { public static Customer Guest = new(); public string Name = ""; }
public class Service(int Customer)
{
    public string M() => Customer.ToString();
    public object N() => Customer.Guest;
}
public record Info(int Customer)
{
    public string M() => Customer.ToString();
}
public class Other
{
    public object M() => Customer.Guest;
}
"""})
    assert _body(ir) == [("Shop.Other", "Shop.Customer", "M", 14)]


def test_a_type_only_some_builds_declare_draws_nothing(tmp_path):
    # in the #if branch the parser reads, or in an #else branch it blanks
    ir = extract_source(tmp_path, {"A.cs": """namespace Shop;
public class Order { public static int Max = 1; }
public class Clock { }
#if !NET8_0_OR_GREATER
public class TimeProvider { public static TimeProvider System = new(); }
#endif
public class Twin
{
#if NET11_0_OR_GREATER
    public class Spare { }
#else
    public class Order { }
#endif
    public object M() => new Order();
    public object N() => TimeProvider.System;
    public object K() => new Clock();
}
"""})
    assert _body(ir) == [("Shop.Twin", "Shop.Clock", "K", 16)]


def test_one_id_declared_by_two_projects_draws_nothing(tmp_path):
    # two projects' `partial class Program` are two types; top-level statements declare
    # one more, in their project
    sdk = '<Project Sdk="Microsoft.NET.Sdk"></Project>'
    ir = extract_source(tmp_path, {
        "A/A.csproj": sdk, "A/Program.cs": "public partial class Program { }\n",
        "A/Use.cs": "namespace A; public class Use { object M() => typeof(Program); }\n",
        "B/B.csproj": sdk, "B/Program.cs": "System.Console.WriteLine();\n",
        "B/Use.cs": "namespace B; public class Use { object M() => typeof(Program); }\n",
        "C/C.csproj": sdk, "C/Program.cs": "public partial class Program { }\n",
        "C/Use.cs": "namespace C; public class Use { object M() => typeof(Program); }\n"})
    assert _body(ir) == []
    alone = extract_source(tmp_path / "alone", {
        "A/A.csproj": sdk, "A/Program.cs": "public partial class Program { }\n",
        "A/Use.cs": "namespace A; public class Use { object M() => typeof(Program); }\n"})
    assert _body(alone) == [("A.Use", "Program", "M", 1)]


def test_a_type_grpc_generates_hides_one_an_import_brings_in(tmp_path):
    # Grpc.Tools compiles the .proto into the project's namespace; with
    # CompileOutputs="false" the generated code is in the sources instead
    ir = extract_source(tmp_path, {
        "Api/Api.csproj": """<Project Sdk="Microsoft.NET.Sdk.Web"><ItemGroup>
<Protobuf Include="Proto\\basket.proto" GrpcServices="Server" />
</ItemGroup></Project>""",
        "Api/Proto/basket.proto": """syntax = "proto3";
option csharp_namespace = "Shop.Api.Grpc";
service Basket { rpc Get(GetRequest) returns (BasketItem) {} }
message GetRequest { message Inner { } }
message BasketItem { }
""",
        "Api/Model/BasketItem.cs": "namespace Shop.Api.Model;\npublic class BasketItem { }\npublic class GetRequest { }\n",
        "Api/Grpc/Service.cs": """using Shop.Api.Model;
namespace Shop.Api.Grpc;
public class Service
{
    object M() => new BasketItem();
    object N() => new Inner();
}
"""})
    assert _body(ir) == []
    assert any(r.from_ == "Shop.Api.Grpc.Service" and r.to == "Shop.Api.Model.BasketItem"
               for r in ir.relations) is False


def test_code_only_a_platform_builds_draws_nothing_in_a_maui_app(tmp_path):
    # Platforms/<platform>/ and `#if ANDROID`; `#if !WINDOWS` is compiled for net11.0 too
    app = """<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><UseMaui>true</UseMaui>
</PropertyGroup></Project>"""
    ir = extract_source(tmp_path, {
        "App/App.csproj": app,
        "App/MauiProgram.cs": """namespace App;
public static class MauiProgram
{
    public static object Create()
    {
#if ANDROID
        _ = new Handler();
#elif IOS
        _ = new Handler();
#endif
#if IOS || MACCATALYST
        _ = new Handler();
#endif
#if !WINDOWS
        _ = new Handler();
#endif
        return null!;
    }
}
public class Handler { }
""",
        "App/Platforms/Android/MainApplication.cs":
            "namespace App;\npublic class MainApplication { object M() => MauiProgram.Create(); }\n"})
    assert _body(ir) == [("App.MauiProgram", "App.Handler", "Create", 15)]


def test_a_member_generated_code_declares_hides_a_type(tmp_path):
    # Razor's @inject (also from _Imports.razor) and @code members, XAML's x:Name,
    # CommunityToolkit.Mvvm's [ObservableProperty] and [RelayCommand], System.Text.Json's
    # [JsonSerializable] (Roslyn: each is the generated member, not the type)
    types = "namespace Gen;\npublic class Customer { public static Customer Guest = new(); }\n" \
            "public class Order { public static int Max = 1; }\npublic class Load { public static int Max = 1; }\n"
    ir = extract_source(tmp_path, {
        "Types.cs": types,
        "Web/Web.csproj": '<Project Sdk="Microsoft.NET.Sdk.Razor"></Project>',
        "Web/_Imports.razor": "@inject System.Text.StringBuilder Order\n",
        "Web/Pages/Comp.razor": "@inject System.Text.StringBuilder Customer\n<p></p>\n"
                                "@code {\n    private int Load = 1;\n}\n",
        "Web/Pages/Comp.razor.cs": """namespace Gen.Web;
public partial class Comp
{
    int M() => Customer.Length + Order.Length + Load.CompareTo(1);
}
public class Plain { object M() => Customer.Guest; }
""",
        "App/MainPage.xaml": '<ContentPage x:Class="Gen.App.MainPage"><Label x:Name="Customer" /></ContentPage>',
        "App/MainPage.xaml.cs": "namespace Gen.App;\npublic partial class MainPage { object M() => Customer.Text; }\n",
        "Lib/Model.cs": """using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using System.Text.Json.Serialization;
namespace Gen;
public partial class ViewModel
{
    [ObservableProperty] private string _customer = "";
    [RelayCommand] private void Load() { }
    int M() => Customer.Length + LoadCommand.GetHashCode() + Order.Max;
}
[JsonSerializable(typeof(Customer))]
[JsonSerializable(typeof(System.Collections.Generic.List<Order>))]
public partial class Ctx
{
    object M() => Customer.Type;
    object N() => Order.Max;
}
"""})
    assert _body(ir) == [("Gen.Ctx", "Gen.Order", "N", 16), ("Gen.ViewModel", "Gen.Order", "M", 9),
                         ("Gen.Web.Plain", "Gen.Customer", "M", 6)]


def test_a_type_of_a_project_the_file_does_not_reference_draws_nothing(tmp_path):
    # B does not reference A, whose Shop.Order is around Shop.B: Roslyn takes Lib.Order
    # from L through `using Lib;` (the extractor draws nothing there)
    sdk = '<Project Sdk="Microsoft.NET.Sdk">{}</Project>'
    ir = extract_source(tmp_path, {
        "L/L.csproj": sdk.format(""), "L/Lib.cs": "namespace Lib { public class Order { } }\n",
        "A/A.csproj": sdk.format(""), "A/Shop.cs": "namespace Shop { public class Order { } }\n",
        "B/B.csproj": sdk.format('<ItemGroup><ProjectReference Include="..\\L\\L.csproj" /></ItemGroup>'),
        "B/Use.cs": "using Lib;\nnamespace Shop.B { public class Use { object M() => new Order(); } }\n",
        "C/C.csproj": sdk.format('<ItemGroup><ProjectReference Include="../B/B.csproj" /></ItemGroup>'),
        "C/Use.cs": "namespace C { public class Use { object M() => new Lib.Order(); } }\n"})
    # C sees L through B
    assert _body(ir) == [("C.Use", "Lib.Order", "M", 1)]


def test_a_using_item_of_the_project_file_is_a_using_of_every_file(tmp_path):
    # <Using Alias> names a type before the usings' (Roslyn: Lib2.Order for `Ord`, though
    # `using Shop;` brings in an Ord); <Using Static> brings in a type's nested types
    ir = extract_source(tmp_path, {
        "P.csproj": """<Project Sdk="Microsoft.NET.Sdk"><ItemGroup>
  <Using Include="Lib2.Order" Alias="Ord" />
  <Using Include="Lib2.Defaults" Static="true" />
</ItemGroup></Project>""",
        "Lib.cs": """namespace Lib2 { public class Order { } public static class Defaults { public class Inner { } } }
namespace Shop { public class Ord { } }
""",
        "Use.cs": """using Shop;
namespace Other
{
    public class Use { object A() => new Ord(); object B() => new Inner(); }
}
"""})
    assert _body(ir) == [("Other.Use", "Lib2.Defaults.Inner", "B", 4), ("Other.Use", "Lib2.Order", "A", 4)]


def test_an_internal_type_of_another_project_is_seen_by_its_friends_only(tmp_path):
    # L's internal Lib.Secret: A is a friend (an InternalsVisibleTo item), B (an attribute)
    # too, C is not (Roslyn: inaccessible)
    sdk = '<Project Sdk="Microsoft.NET.Sdk">{}</Project>'
    ref = '<ItemGroup><ProjectReference Include="../L/L.csproj" /></ItemGroup>'
    use = "using Lib;\nnamespace Other.{0} {{ public class Use {{ object M() => Secret.Count; }} }}\n"
    ir = extract_source(tmp_path, {
        "L/L.csproj": sdk.format('<ItemGroup><InternalsVisibleTo Include="A" /></ItemGroup>'),
        "L/Lib.cs": "namespace Lib { internal class Secret { public static int Count = 1; } }\n",
        "L/Friends.cs": '[assembly: System.Runtime.CompilerServices.InternalsVisibleTo("B")]\n',
        "A/A.csproj": sdk.format(ref), "A/Use.cs": use.format("A"),
        "B/B.csproj": sdk.format(ref), "B/Use.cs": use.format("B"),
        "C/C.csproj": sdk.format(ref), "C/Use.cs": use.format("C")})
    assert _body(ir) == [("Other.A.Use", "Lib.Secret", "M", 2), ("Other.B.Use", "Lib.Secret", "M", 2)]


def test_a_razor_component_is_a_type_of_its_namespace(tmp_path):
    # Card.razor is Web.Comp.Card (_Imports.razor's @namespace), Sub/Grid.razor
    # Web.Comp.Sub.Grid, Item.razor its own @namespace: each hides Shop's in its namespace
    ir = extract_source(tmp_path, {
        "W/W.csproj": '<Project Sdk="Microsoft.NET.Sdk.Razor"><PropertyGroup>'
                      '<RootNamespace>Web.App</RootNamespace></PropertyGroup></Project>',
        "W/Types.cs": "namespace Shop { public class Card { } public class Grid { } public class Item { } }\n",
        "W/Pages/_Imports.razor": "@namespace Web.Comp\n@using Shop\n",
        "W/Pages/Card.razor": "<p>card</p>\n",
        "W/Pages/Sub/Grid.razor": "<p>grid</p>\n",
        "W/Pages/Sub/Item.razor": "@namespace Web.Other\n<p>item</p>\n",
        "W/Pages/Use.cs": """using Shop;
namespace Web.Comp
{
    public class Use { object A() => new Card(); object B() => typeof(Grid); object C() => typeof(Item); }
}
namespace Web.Comp.Sub
{
    public class Use2 { object A() => typeof(Grid); object B() => typeof(Item); }
}
"""})
    assert _body(ir) == [("Web.Comp.Sub.Use2", "Shop.Item", "B", 8),
                         ("Web.Comp.Use", "Shop.Grid", "B", 4), ("Web.Comp.Use", "Shop.Item", "C", 4)]


def test_a_member_of_an_outside_base_class_hides_a_type(tmp_path):
    # ControllerBase.User and Request (the .NET table); a base no table knows may have any
    # member: nothing is drawn under it where a variable may stand; an interface passes
    # on none
    ir = extract_source(tmp_path, {
        "Types.cs": "namespace Shop { public class User { public static int Count = 0; } "
                    "public class Request { public static int Count = 0; } }\n",
        "Use.cs": """using Microsoft.AspNetCore.Mvc;
using Some.Package;
namespace Shop.Web
{
    public class Users : ControllerBase { object A() => User.Identity; object B() => new User(); object C() => Request.Count; }
    public class Other : PackageBase { object A() => User.Count; object B() => new User(); }
    public class Plain : IPackage { object A() => User.Count; }
}
"""})
    assert _body(ir) == [("Shop.Web.Other", "Shop.User", "B", 6), ("Shop.Web.Plain", "Shop.User", "A", 7),
                         ("Shop.Web.Users", "Shop.User", "B", 5)]


def test_a_using_of_an_unknown_namespace_in_a_block_may_bring_in_any_name(tmp_path):
    # `using Some.Package;` in the block comes before Shop around it: Task may be its;
    # System.Threading.Tasks is known to have Task, System.IO known not to
    ir = extract_source(tmp_path, {
        "Types.cs": "namespace Shop { public class Task { } public class Order { } }\n",
        "Use.cs": """namespace Shop.A { using Some.Package; public class Use { object M() => new Task(); } }
namespace Shop.B { using System.Threading.Tasks; public class Use { object M() => new Task(); } }
namespace Shop.C { using System.IO; public class Use { object M() => new Task(); } }
"""})
    assert _body(ir) == [("Shop.C.Use", "Shop.Task", "M", 3)]


def test_a_package_namespace_around_the_code_hides_names_found_further_out(tmp_path):
    # the project references CommunityToolkit.Mvvm: a namespace that is its id or below it
    # (case aside) is the package's, also where the sources declare a type in it, and its
    # types may hide whatever is found further out (Shop's, through the file's using); a
    # namespace of the sources a using imports (App) is no package's
    ir = extract_source(tmp_path, {
        "P.csproj": """<Project Sdk="Microsoft.NET.Sdk"><ItemGroup>
<PackageReference Include="communitytoolkit.mvvm" Version="8.4.0" />
</ItemGroup></Project>
""",
        "Types.cs": "namespace Shop { public class RelayCommand { } public class ObservableObject { } "
                    "public class Order { public static int Count = 0; } }\n"
                    "namespace App.Models { public class Item { } }\n",
        "Use.cs": "using App;\nnamespace Shop.Uses { public class U { } }\n",
        "Package.cs": """using Shop;
namespace CommunityToolkit.Mvvm.Input.Mine
{
    public class P { object A() => typeof(RelayCommand); object B() => new Order(); object C() => Order.Count; object D() => new Shop.Order(); }
}
namespace CommunityToolkit.Mvvm.ComponentModel
{
    public class Q { object A() => typeof(ObservableObject); }
}
namespace Other.Mine
{
    public class P { object A() => typeof(RelayCommand); }
}
namespace App.Web
{
    public class W { object A() => new App.Models.Item(); object B() => new Models.Item(); }
}
"""})
    assert _body(ir) == [("App.Web.W", "App.Models.Item", "A", 16), ("App.Web.W", "App.Models.Item", "B", 16),
                         ("Other.Mine.P", "Shop.RelayCommand", "A", 12)]


def test_a_package_a_referenced_project_references_is_the_projects_too(tmp_path):
    # B references L, which references CommunityToolkit.Mvvm: the package flows on to B, and
    # B's `namespace CommunityToolkit.Mvvm.Input.Mine` is the package's; P references Q,
    # whose reference is PrivateAssets="all" (an attribute or an element), which does not
    sdk = '<Project Sdk="Microsoft.NET.Sdk">{}</Project>'
    ref = '<ItemGroup><ProjectReference Include="../{0}/{0}.csproj" /></ItemGroup>'
    pkg = '<ItemGroup><PackageReference Include="CommunityToolkit.Mvvm" Version="8.4.0"{} /></ItemGroup>'
    use = ("using {1};\nnamespace CommunityToolkit.Mvvm.Input.{0} "
           "{{ public class Use {{ object M() => typeof(RelayCommand); }} }}\n")
    ir = extract_source(tmp_path, {
        "L/L.csproj": sdk.format(pkg.format("")),
        "L/Shop.cs": "namespace Shop { public class RelayCommand { } }\n",
        "B/B.csproj": sdk.format(ref.format("L")), "B/Use.cs": use.format("B", "Shop"),
        "Q/Q.csproj": sdk.format(pkg.format(' PrivateAssets="all"')),
        "P/P.csproj": sdk.format(ref.format("Q") + ref.format("L2")), "P/Use.cs": use.format("P", "Mine"),
        "L2/L2.csproj": sdk.format('<ItemGroup><PackageReference Include="CommunityToolkit.Mvvm" '
                                   'Version="8.4.0"><PrivateAssets>all</PrivateAssets>'
                                   '</PackageReference></ItemGroup>' + ref.format("L3")),
        "L3/L3.csproj": sdk.format(""),
        "P/Mine.cs": "namespace Mine { public class RelayCommand { } }\n"})
    assert _body(ir) == [("CommunityToolkit.Mvvm.Input.P.Use", "Mine.RelayCommand", "M", 2)]


def test_a_records_base_arguments_are_its_primary_constructors_body(tmp_path):
    # `record Sub(int M) : Rec(Order.Count)`: the base arguments are read, `via` the
    # primary constructor (the record's name), as a class's `class B(int x) : A(x)` are
    ir = extract_source(tmp_path, {
        "Types.cs": "namespace Shop { public class Order { public static int Count = 0; } "
                    "public record Rec(int N); "
                    "public record Sub(int M) : Rec(Order.Count); "
                    "public class Base { public Base(int n) { } } "
                    "public class Derived(int x) : Base(Order.Count + x); }\n"})
    assert _body(ir) == [("Shop.Derived", "Shop.Order", "Derived", 1), ("Shop.Sub", "Shop.Order", "Sub", 1)]


def test_a_directive_is_told_from_text_that_looks_like_one():
    # a `#if` line inside a multi-line string or comment is text; a string, a char or a
    # comment that ends on its line leaves the next line's directive one, as does a
    # directive line's own text (`#region "Quoted`)
    from draftsman.langs.csharp import _lines

    def kept(src: str) -> list[str]:
        return [line.decode().strip() for line, keep, _, _ in _lines(src.encode())
                if keep and line.strip()]

    after = "\n#if false\nA();\n#else\nB();\n#endif\n"
    for text in ["var c = '\"';", 'var s = "a\\"b";', 'var s = "a\\\\";', 'var s = "http://x/*y";',
                 'var s = @"c:\\";', 'var s = $"{(a ? "x" : "y")}";', 'var s = """x""";',
                 'var s = """"x"""";', "// it's \"here /*", "#region Don't touch",
                 "var c = '\\\\';", "var c = '\\'';", '#region "Quoted', '#error "not supported']:
        assert "B();" in kept(text + after) and "A();" not in kept(text + after), text
    for text in ['var s = @"a""b', "/* it's", 'var s = $@"a{b}""c', 'var s = """']:
        close = {"/": "*/", "v": '";'}[text[0]] if '"""' not in text else '""";'
        assert "C();" in kept(f"{text}\n#if false\n{close}\nC();\n"), text
    assert kept("#if NEVER\nA();\n#else\nB();\n#endif\n") == ["A();"]
    assert kept("#if false\nthis isn't \"code\n#else\nB();\n#endif\n") == ["B();"]
