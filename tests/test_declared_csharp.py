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

