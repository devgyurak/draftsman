"""Java: a superclass's private member class is not inherited (issue #7, case 49), in
declarations and bodies alike. A form of bench/javac_oracle/review/jv1."""

from conftest import extract_source


def test_a_private_nested_type_of_a_superclass_is_not_inherited(tmp_path):
    ir = extract_source(tmp_path, {
        "p/Base.java": ("package p;\npublic class Base {\n  private static class Hidden {}\n"
                        "  protected static class Deep {}\n}\n"),
        "p/Hidden.java": "package p; public class Hidden {}\n",
        "p/Deep.java": "package p; public class Deep {}\n",
        "p/Mid.java": "package p; public class Mid extends Base {}\n",
        "p/Sub.java": ("package p;\npublic class Sub extends Mid {\n  Hidden b;\n  Deep c;\n"
                       "  Object m() { Hidden h = new Hidden(); return h; }\n}\n"),
        "p/Own.java": ("package p;\npublic class Own {\n  private static class Hidden {}\n"
                       "  Hidden a;\n}\n")})
    rels = {(r.from_, r.to, r.via, r.evidence) for r in ir.relations}
    assert ("p.Sub", "p.Hidden", "b", None) in rels
    assert ("p.Sub", "p.Hidden", "m", "body") in rels
    assert not any(to == "p.Base.Hidden" for f, to, _, _ in rels if f == "p.Sub")
    assert ("p.Sub", "p.Base.Deep", "c", None) in rels   # a protected one is inherited
    assert ("p.Own", "p.Own.Hidden", "a", None) in rels  # its own class sees it


def test_a_package_private_nested_type_is_not_inherited_in_another_package(tmp_path):
    # b.SubB extends a.Base: Base's package-private Pkg is b.Pkg there, also through a
    # subclass of SubB and in SubB's nested class; a.SubA inherits it; protected and
    # public ones and an interface's (public) are inherited across packages (jv2)
    ir = extract_source(tmp_path, {
        "a/Base.java": ("package a;\npublic class Base implements Face {\n  static class Pkg {}\n"
                        "  protected static class Prot {}\n}\n"),
        "a/Face.java": "package a;\npublic interface Face { class Fn {} }\n",
        "a/Pkg.java": "package a; public class Pkg {}\n",
        "a/SubA.java": "package a;\npublic class SubA extends Base { Pkg p; }\n",
        "b/Pkg.java": "package b; public class Pkg {}\n",
        "b/Prot.java": "package b; public class Prot {}\n",
        "b/Fn.java": "package b; public class Fn {}\n",
        "b/SubB.java": ("package b;\npublic class SubB extends a.Base {\n  Pkg p;\n  Prot q;\n"
                        "  Object m() { return new Pkg(); }\n  class In { Pkg p2; }\n}\n"),
        "b/Third.java": "package b;\npublic class Third extends SubB { Pkg p; }\n",
        "b/Imp.java": "package b;\npublic class Imp implements a.Face { Fn f; }\n"})
    rels = {(r.from_, r.to, r.via, r.evidence) for r in ir.relations}
    assert ("a.SubA", "a.Base.Pkg", "p", None) in rels
    assert ("b.SubB", "b.Pkg", "p", None) in rels
    assert ("b.SubB", "b.Pkg", "m", "body") in rels
    assert ("b.SubB.In", "b.Pkg", "p2", None) in rels
    assert ("b.Third", "b.Pkg", "p", None) in rels
    assert ("b.SubB", "a.Base.Prot", "q", None) in rels
    assert ("b.Imp", "a.Face.Fn", "f", None) in rels


def test_package_private_members_are_inherited_step_by_step(tmp_path):
    # #7's forms found after 0.10.0 (bench/javac_oracle/review/jv5): b.Mid does not inherit
    # a.Base's package-private Pkg, so neither does a.Leaf, though it is in a; nor does a
    # subclass in another package see a package-private field, which then hides nothing
    ir = extract_source(tmp_path, {
        "a/Base.java": ("package a;\npublic class Base {\n  static class Pkg {}\n"
                        "  static Object Item;\n}\n"),
        "a/Pkg.java": "package a; public class Pkg {}\n",
        "b/Mid.java": "package b; public class Mid extends a.Base {}\n",
        "a/Leaf.java": ("package a;\npublic class Leaf extends b.Mid {\n  Pkg p;\n"
                        "  Object m() { return new Pkg(); }\n}\n"),
        "b/Item.java": "package b; public class Item { public static void m() {} }\n",
        "b/Sub.java": "package b;\npublic class Sub extends a.Base {\n  void f() { Item.m(); }\n}\n"})
    rels = {(r.from_, r.to, r.via, r.evidence) for r in ir.relations}
    assert ("a.Leaf", "a.Pkg", "p", None) in rels and ("a.Leaf", "a.Pkg", "m", "body") in rels
    assert not any(to == "a.Base.Pkg" for _, to, _, _ in rels)
    assert ("b.Sub", "b.Item", "f", "body") in rels


def test_wildcards_annotated_qualified_names_and_enum_constants(tmp_path):
    # #9, cases 26, 27, 28: `? super X` names X; `Conn.@Nullable Response` is Conn.Response;
    # an annotation on an enum constant is the enum's
    ir = extract_source(tmp_path, {
        "p/Item.java": "package p; public class Item {}\n",
        "p/Unstable.java": "package p; public @interface Unstable {}\n",
        "p/Other.java": "package p; public @interface Other { Class<?> value(); }\n",
        "p/Nullable.java": ("package p;\nimport java.lang.annotation.*;\n"
                            "@Target(ElementType.TYPE_USE) public @interface Nullable {}\n"),
        "p/Conn.java": "package p; public interface Conn { interface Response {} }\n",
        "p/Http.java": ("package p;\nimport java.util.Collection;\npublic class Http {\n"
                        "  private Conn.@Nullable Response res;\n"
                        "  void drain(Collection<? super Item> out) {}\n}\n"),
        "p/Provider.java": ("package p;\npublic enum Provider {\n  JDK,\n  @Unstable OPENSSL,\n"
                            "  @Other(Item.class) BORING { void f() {} }\n}\n")})
    rels = {(r.from_, r.to, r.kind, r.via) for r in ir.relations if r.evidence is None}
    assert ("p.Http", "p.Conn.Response", "association", "res") in rels
    assert ("p.Http", "p.Item", "dependency", "drain") in rels
    assert {(to, via) for f, to, _, via in rels if f == "p.Provider"} >= {
        ("p.Unstable", "@Unstable"), ("p.Other", "@Other"), ("p.Item", "@Other")}
