"""C# declared relations looked up as Roslyn does (issue #7: cases 2, 3, 4, 5, 35): the
resolver's own lookup, which bodies share. Each test is a form of
bench/roslyn_oracle/review/cs18, whose answers Roslyn gives."""

from conftest import extract_source

SDK = '<Project Sdk="Microsoft.NET.Sdk">{}</Project>'


def _rels(ir, src: str) -> set[tuple[str, str]]:
    return {(r.to, r.via) for r in ir.relations if r.from_ == src and r.evidence is None}


def _body(ir, src: str) -> set[str]:
    return {r.to for r in ir.relations if r.from_ == src and r.evidence == "body"}


def test_a_using_alias_is_its_files_only(tmp_path):
    # #2: `using Order = Lib.Order;` in Api.cs is no name of Y.cs, also not through a
    # (global) using of the namespace it stands in
    ir = extract_source(tmp_path, {
        "T.cs": ("namespace Lib { public class Order {} }\n"
                 "namespace Shop { public class Order {} }\n"),
        "Api.cs": "using Order = Lib.Order;\npublic class Api { public Order O; }\n",
        "Y.cs": ("using Shop;\npublic class Y { public Order O; "
                 "public object M() => new Order(); }\n"),
        "S.cs": ("using Order = Lib.Order;\nnamespace App.Vm;\n"
                 "public class S { public Order O; }\n"),
        "G.cs": "global using App.Vm;\n",
        "Map.cs": "using Shop;\nnamespace Other;\npublic class Map { public Order O; }\n"})
    assert _rels(ir, "Api") == {("Lib.Order", "O")}
    assert _rels(ir, "Y") == {("Shop.Order", "O")}
    assert _body(ir, "Y") == {"Shop.Order"}
    assert _rels(ir, "Other.Map") == {("Shop.Order", "O")}


def test_an_alias_before_a_file_scoped_namespace_comes_after_the_namespaces_around(tmp_path):
    # #3: the compilation unit's alias is looked at with the global namespace
    ir = extract_source(tmp_path, {
        "T.cs": ("namespace Lib { public class Order {} }\n"
                 "namespace Shop { public class Order {} }\n"),
        "X.cs": ("using Order = Lib.Order;\nnamespace Shop.Sub;\n"
                 "public class X { public Order O; public object M() => new Order(); }\n"
                 "public class X2 : Order {}\n")})
    assert _rels(ir, "Shop.Sub.X") == {("Shop.Order", "O")}
    assert _body(ir, "Shop.Sub.X") == {"Shop.Order"}
    assert ("Shop.Order", None) in _rels(ir, "Shop.Sub.X2")


def test_another_projects_internal_type_is_no_candidate(tmp_path):
    # #4: L's internal Core.Order is not B's: lookup goes on to `using Lib2;`
    ir = extract_source(tmp_path, {
        "L/L.csproj": SDK.format(""),
        "L/Lib.cs": "namespace Core { internal class Order {} }\n",
        "B/B.csproj": SDK.format('<ItemGroup><ProjectReference Include="../L/L.csproj" /></ItemGroup>'),
        "B/Lib2.cs": "namespace Lib2 { public class Order {} }\n",
        "B/Use.cs": ("using Lib2;\nnamespace Core.Sub { public class X { public Order O; "
                     "public object M() => new Order(); } }\n")})
    assert _rels(ir, "Core.Sub.X") == {("Lib2.Order", "O")}
    assert _body(ir, "Core.Sub.X") == {"Lib2.Order"}


def test_the_arity_written_chooses_the_type(tmp_path):
    # #4: `Repo<int>` is Lib.Repo<T>, not Shop.Repo around the code
    ir = extract_source(tmp_path, {
        "T.cs": ("namespace Lib { public class Repo<T> {} }\n"
                 "namespace Shop { public class Repo {} }\n"),
        "X.cs": ("using Lib;\nnamespace Shop.Sub { public class X { public Repo<int> R; "
                 "public Repo P; public object M() => new Repo<int>(); } }\n")})
    assert _rels(ir, "Shop.Sub.X") == {("Lib.Repo", "R"), ("Shop.Repo", "P")}
    assert _body(ir, "Shop.Sub.X") == {"Lib.Repo"}


def test_a_packages_namespace_around_the_code_may_have_the_type(tmp_path):
    # #5: in CommunityToolkit.Mvvm.Input.Mine, `RelayCommand` is the package's (Roslyn): the
    # extractor cannot tell what the package has, so the name is unresolved with the reason
    ir = extract_source(tmp_path, {
        "P.csproj": SDK.format('<ItemGroup><PackageReference Include="CommunityToolkit.Mvvm" '
                               'Version="8.4.0" /></ItemGroup>'),
        "T.cs": "namespace Shop { public class RelayCommand {} }\n",
        "Pkg.cs": ("using Shop;\nnamespace CommunityToolkit.Mvvm.Input.Mine "
                   "{ public class PP { public RelayCommand C; } }\n")})
    assert not _rels(ir, "CommunityToolkit.Mvvm.Input.Mine.PP")
    (u,) = [u for u in ir.unresolved if u.from_ == "CommunityToolkit.Mvvm.Input.Mine.PP"]
    assert "namespace outside the sources around it" in u.hint


def test_a_member_of_the_class_hides_a_name_in_an_attributes_argument(tmp_path):
    # #35: `nameof(Order)` beside a property Order of a base is the property
    ir = extract_source(tmp_path, {"A.cs": (
        "using System;\nnamespace Shop {\n  public class Order {}\n"
        "  public class Base2 { public string Order => \"\"; }\n"
        "  public class Bodies : Base2 { [Obsolete(nameof(Order))] public void M() {} }\n"
        "  public class Plain2 { [Obsolete(nameof(Order))] public void M() {} }\n}\n")})
    assert _rels(ir, "Shop.Bodies") == {("Shop.Base2", None)}
    assert _rels(ir, "Shop.Plain2") == {("Shop.Order", "@Obsolete")}


def test_a_name_after_global_is_the_global_namespaces(tmp_path):
    # `global::Lib.Order` beside a Shop.Lib.Order nearer: the global namespace's (cs1)
    ir = extract_source(tmp_path, {
        "T.cs": ("namespace Lib { public class Order {} public class Base {} }\n"
                 "namespace Shop.Lib { public class Order {} public class Base {} }\n"),
        "X.cs": ("namespace Shop.CC { public class X { public global::Lib.Order O; "
                 "public Lib.Order N; }\n  public class D : global::Lib.Base {} }\n")})
    assert _rels(ir, "Shop.CC.X") == {("Lib.Order", "O"), ("Shop.Lib.Order", "N")}
    assert _rels(ir, "Shop.CC.D") == {("Lib.Base", None)}
