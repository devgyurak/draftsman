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


def test_a_global_using_alias_is_every_file_of_its_project(tmp_path):
    # `global using Cash = Lib.Money;` is a name of every file of P, not of Q (cs19)
    ir = extract_source(tmp_path, {
        "P/P.csproj": SDK.format(""),
        "P/T.cs": "namespace Lib { public class Money {} }\nnamespace Shop { public class Cash {} }\n",
        "P/G.cs": "global using Cash = Lib.Money;\n",
        "P/A.cs": ("namespace Shop.Sub { public class A { public Cash C; "
                   "public object M() => new Cash(); } }\n"),
        "P/B.cs": "public class B { public Cash C; }\n",
        "Q/Q.csproj": SDK.format(""),
        "Q/T.cs": "namespace Lib { public class Money {} }\npublic class Cash {}\n",
        "Q/U.cs": "public class U { public Cash C; }\n"})
    assert _rels(ir, "B") == {("Lib.Money", "C")}
    # a namespace around comes before the global using's alias
    assert _rels(ir, "Shop.Sub.A") == {("Shop.Cash", "C")}
    assert _rels(ir, "U") == {("Cash", "C")}


def test_a_namespace_blocks_alias_is_that_blocks(tmp_path):
    # `namespace Shop.Sub4 { using Order = Lib.Order; }` is not another Shop.Sub4 block's
    ir = extract_source(tmp_path, {
        "T.cs": ("namespace Lib { public class Order {} }\n"
                 "namespace Shop { public class Order {} }\n"),
        "B.cs": ("namespace Shop.Sub4 {\n  using Order = Lib.Order;\n"
                 "  public class C4 { public Order O; }\n}\n"
                 "namespace Shop.Sub4 {\n  public class D4 { public Order O; "
                 "public object M() => new Order(); }\n}\n")})
    assert _rels(ir, "Shop.Sub4.C4") == {("Lib.Order", "O")}
    assert _rels(ir, "Shop.Sub4.D4") == {("Shop.Order", "O")}
    assert _body(ir, "Shop.Sub4.D4") == {"Shop.Order"}


def test_a_member_named_like_its_type_is_the_type_before_a_dot(tmp_path):
    # `[Tag(Kind.A)]` beside `public Kind Kind` of a base: Shop.Kind (Color Color);
    # `nameof(Order)` beside a property Order stays the property (cs19)
    ir = extract_source(tmp_path, {"A.cs": (
        "using System;\nnamespace Shop {\n  public enum Kind { A }\n  public class Order {}\n"
        "  public class TagAttribute : Attribute { public TagAttribute(object o) {} }\n"
        "  public class Base6 { public string Order => \"\"; public Kind Kind => Kind.A; }\n"
        "  public class OnClass : Base6 {\n    [Tag(Kind.A)] public void N() {}\n"
        "    [Tag(nameof(Order))] public void O() {}\n  }\n}\n")})
    assert _rels(ir, "Shop.OnClass") >= {("Shop.Kind", "@Tag")}
    assert ("Shop.Order", "@Tag") not in _rels(ir, "Shop.OnClass")


def test_a_type_through_an_alias_of_a_namespace(tmp_path):
    # #9, case 57: `using L = Lib;` then `L.Order`, `L::Order`; the alias's target is read
    # from the namespace it stands in outward (in `namespace Shop`, `Lib.Sub` is Shop.Lib.Sub)
    ir = extract_source(tmp_path, {"P/T.cs": (
        "namespace Lib { public class Order {} }\n"
        "namespace Lib.Sub { public class Item {} }\n"
        "namespace Shop { public class Order {} }\n"
        "namespace Shop.Lib.Sub { public class Item {} }\n"),
        "P/U.cs": ("using L = Lib;\nusing pb = global::Google.Protobuf;\n"
                   "namespace Shop.Uses { public class A { public L.Order O; public L::Order P;\n"
                   "  public pb::CodedInputStream S; } }\n"
                   "namespace Shop { using B = Lib.Sub; public class C { public B.Item I; } }\n")})
    rels = {(r.from_, r.to, r.via) for r in ir.relations if r.evidence is None}
    assert {("Shop.Uses.A", "Lib.Order", "O"), ("Shop.Uses.A", "Lib.Order", "P"),
            ("Shop.C", "Shop.Lib.Sub.Item", "I")} <= rels
    # an alias of a namespace outside the sources: a type outside them, not unresolved
    assert not ir.unresolved


def test_the_name_before_the_alias_qualifier_is_always_an_alias(tmp_path):
    # `L::Order` reads only the file's using aliases before `::`; `L.Order` finds a type
    # `Shop.L` of a namespace around first (Roslyn: Lib.Order and Shop.L.Order)
    ir = extract_source(tmp_path, {"P/T.cs": (
        "namespace Lib { public class Order {} }\n"
        "namespace Shop { public class Order {} public class L { public class Order {} } }\n"),
        "P/U.cs": ("using L = Lib;\n"
                   "namespace Shop.Inner { public class B { public L.Order Q; public L::Order R; } }\n"
                   "namespace App { public class A { public L::Order R; } }\n")})
    rels = {(r.from_, r.to, r.via) for r in ir.relations if r.evidence is None}
    assert {("Shop.Inner.B", "Shop.L.Order", "Q"), ("Shop.Inner.B", "Lib.Order", "R"),
            ("App.A", "Lib.Order", "R")} <= rels
    assert ("Shop.Inner.B", "Shop.L.Order", "R") not in rels


def test_an_alias_qualifier_without_an_alias_draws_nothing(tmp_path):
    # `X::Order` with no alias X (a compile error): not the type X's Order
    ir = extract_source(tmp_path, {"P/T.cs": (
        "namespace Shop { public class X { public class Order {} }\n"
        "  public class B { public X::Order R; } }\n")})
    assert not [r for r in ir.relations if r.from_ == "Shop.B" and r.evidence is None]
    assert [u.raw_type for u in ir.unresolved] == ["X::Order"]


_LIB = ("namespace Lib { public class Order { public static Order Make() => null; }\n"
        "  public static class Util { public static void Run() {} }\n"
        "  namespace Sub { public class Deep {} } }\n"
        "namespace Shop { public class L { public class Order {} public static class Util {}\n"
        "  public class Sub { public class Deep {} } }\n"
        "  public class M { public class Deep {} } public class LS { public class Deep {} } }\n")


def test_body_names_after_the_alias_qualifier_are_the_aliases(tmp_path):
    # #11, case 64: in a body too, the name before `::` is a using alias alone, beside
    # classes `Shop.L` and `Shop.M` a namespace around has (Roslyn: Lib's)
    ir = extract_source(tmp_path, {"P/T.cs": _LIB, "P/U.cs": (
        "using L = Lib;\nnamespace Shop.Inner { using M = Lib.Sub;\n"
        "public class A {\n"
        "  public object B1() => new L::Order();\n"
        "  public object B2() => L::Order.Make();\n"
        "  public void B3() { L::Util.Run(); }\n"
        "  public object B4() => typeof(L::Sub.Deep);\n"
        "  public object B5(object o) => o is M::Deep ? 1 : 0;\n} }\n")})
    body = {(r.to, r.via) for r in ir.relations if r.from_ == "Shop.Inner.A" and r.evidence}
    assert body == {("Lib.Order", "B1"), ("Lib.Order", "B2"), ("Lib.Util", "B3"),
                    ("Lib.Sub.Deep", "B4"), ("Lib.Sub.Deep", "B5")}


def test_a_receiver_after_the_alias_qualifier_stands_at_the_type(tmp_path):
    # the alias `L` has no place of its own in `L::Order.Make()`: the name's place is
    # `Order`'s, where Roslyn records it
    from draftsman.extractor import Extractor
    from draftsman.langs import spec_for_path
    src = tmp_path / "U.cs"
    src.write_text("using L = Lib;\nclass A { object B() => L::Order.Make(); }\n")
    raw = Extractor(spec_for_path("U.cs")).extract(src, "U.cs", tmp_path)
    refs = [(r.text, r.places) for t in raw.types for r in t.body_refs]
    assert ("L::Order", [(2, 27)]) in refs


def test_a_base_written_with_the_alias_qualifier(tmp_path):
    # #11, case 65: `class C : L::Order`, eShop's gRPC `: pb::IMessage<X>`
    ir = extract_source(tmp_path, {"P/T.cs": _LIB, "P/U.cs": (
        "using L = Lib;\nusing pb = global::Google.Protobuf;\n"
        "namespace Shop.Inner { public class C : L::Order { }\n"
        "  public class D : pb::IMessage<D>, pb::IBufferMessage { } }\n")})
    rels = {(r.from_, r.kind, r.to) for r in ir.relations if r.evidence is None}
    assert ("Shop.Inner.C", "extends", "Lib.Order") in rels
    assert {("Shop.Inner.D", "implements", "Google.Protobuf.IMessage"),
            ("Shop.Inner.D", "implements", "Google.Protobuf.IBufferMessage")} <= rels
    assert not ir.unresolved


def test_an_alias_written_with_the_alias_qualifier(tmp_path):
    # #11, case 66: `using LS = L::Sub;` is Lib.Sub (beside a class `Shop.LS`); an alias
    # beside it in the same block is not seen there (a compile error: nothing drawn)
    ir = extract_source(tmp_path, {"P/T.cs": _LIB, "P/U.cs": (
        "using L = Lib;\n"
        "namespace Shop.Other { using LS = L::Sub;\n"
        "  public class E { public LS::Deep F1; public LS.Deep F2; } }\n"
        "namespace Shop.Third { using K = Lib; using KS = K::Sub;\n"
        "  public class F { public KS::Deep F1; } }\n")})
    rels = {(r.from_, r.to, r.via) for r in ir.relations if r.evidence is None}
    assert {("Shop.Other.E", "Lib.Sub.Deep", "F1"), ("Shop.Other.E", "Lib.Sub.Deep", "F2")} <= rels
    assert not any(f == "Shop.Third.F" for f, _, _ in rels)


_ROOTED = ("namespace Lib { public class Order { public static Order Make() => null;\n"
           "  public class Line {} } public class Box<T> { public class Inner {} }\n"
           "  namespace Sub { public class Deep {} } }\n"
           "namespace Shop { public class Lib { public class Order { public static Order Make() => null;\n"
           "  public class Line {} } public class Box<T> { public class Inner {} }\n"
           "  public class Sub { public class Deep {} } }\n"
           "  public class Google { public class Protobuf { public class IMessage {} } } }\n")


def test_an_alias_of_a_namespace_written_from_the_global_namespace(tmp_path):
    # #11, case 67: `using M = global::Lib.Sub;` is the global namespace's Lib.Sub, not the
    # class Shop.Lib's member beside it, nor a namespace outside the sources (which made
    # `externals` carry the project's own ids)
    ir = extract_source(tmp_path, {"P/T.cs": _ROOTED, "P/U.cs": (
        "using N = global::Lib;\n"
        "namespace Shop.Inner { using M = global::Lib.Sub;\n"
        "  public class A { public M::Deep F1; public M.Deep F2; public N::Order F3;\n"
        "    public object B() => new M::Deep(); }\n"
        "  public class C : N::Box<M::Deep> { } }\n")})
    rels = {(r.from_, r.kind, r.to, r.via) for r in ir.relations}
    assert {("Shop.Inner.A", "association", "Lib.Sub.Deep", "F1"),
            ("Shop.Inner.A", "association", "Lib.Sub.Deep", "F2"),
            ("Shop.Inner.A", "association", "Lib.Order", "F3"),
            ("Shop.Inner.A", "dependency", "Lib.Sub.Deep", "B"),
            ("Shop.Inner.C", "extends", "Lib.Box", None),
            ("Shop.Inner.C", "dependency", "Lib.Sub.Deep", None)} <= rels
    assert not any(t.startswith("Shop.Lib") for _, _, t, _ in rels)
    ids = {t.id for t in ir.types}
    assert not [e.id for e in ir.externals if e.id in ids]
    assert not ir.unresolved


def test_an_alias_of_a_class_written_from_the_global_namespace(tmp_path):
    # the same for an alias of a class, in a namespace block (beside Shop.Lib.Order)
    ir = extract_source(tmp_path, {"P/T.cs": _ROOTED, "P/U.cs": (
        "namespace Shop.Inner { using P = global::Lib.Order; using Q = global::Lib.Box<int>;\n"
        "  using pb = global::Google.Protobuf;\n"
        "  public class A { public P F1; public P.Line F2; public object B() => new P.Line();\n"
        "    public object C() => P.Make(); public Q.Inner F3; }\n"
        "  public class E : pb::IMessage { } }\n")})
    rels = {(r.to, r.via) for r in ir.relations if r.from_ == "Shop.Inner.A"}
    assert rels == {("Lib.Order", "F1"), ("Lib.Order.Line", "F2"), ("Lib.Order.Line", "B"),
                    ("Lib.Order", "C"), ("Lib.Box.Inner", "F3")}
    # a namespace outside the sources beside a class `Shop.Google.Protobuf`: a type outside
    assert {r.to for r in ir.relations if r.from_ == "Shop.Inner.E"} == {"Google.Protobuf.IMessage"}
