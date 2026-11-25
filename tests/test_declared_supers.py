"""A supertype's type arguments (issue #9, case 24), in every language. Each test is a
form of the review sets jv3, py3, ts2, cs21, kt17, cpp14 (bench/*_oracle/review), whose
answers the compilers and checkers give; the relation each form draws is pinned here, as the keys do not tell a dependency
from an association."""

from conftest import extract_source


def _rels(ir, src: str) -> set[tuple[str, str]]:
    """Declared relations of ``src`` to project types (supertypes outside the sources left
    out)."""
    ids = {t.id for t in ir.types}
    return {(r.kind, r.to) for r in ir.relations
            if r.from_ == src and r.evidence is None and r.to in ids}


# ------------------------------------------------------------------ 24: type arguments

def test_java_supertype_type_arguments_are_dependencies(tmp_path):
    ir = extract_source(tmp_path, {
        "a/Node.java": "package a; public class Node {}",
        "b/Node.java": "package b; public class Node {}",
        "a/Item.java": "package a; public class Item {}",
        "a/T.java": "package a; public class T {}",
        "a/Base.java": "package a; public class Base<X> { public static class In<Y> {} }",
        "a/S.java": (
            "package a;\nimport java.util.*;\n"
            "class NodeList extends ArrayList<Node> {}\n"
            "class Gen<T> extends ArrayList<T> {}\n"
            "class Nested extends HashMap<String, List<Item>> implements Comparable<Nested> {\n"
            "  public int compareTo(Nested o) { return 0; }\n}\n"
            "class UsesB extends ArrayList<b.Node> {}\n"
            "class Sub extends Base<Item> {}\n"
            "class SubIn extends Base.In<Node> {}\n")})
    assert _rels(ir, "a.NodeList") == {("dependency", "a.Node")}
    assert not _rels(ir, "a.Gen")   # the type parameter, not the class a.T
    # the class itself draws nothing; nor does an unknown name become unresolved
    assert _rels(ir, "a.Nested") == {("dependency", "a.Item")}
    assert _rels(ir, "a.UsesB") == {("dependency", "b.Node")}
    assert _rels(ir, "a.Sub") == {("extends", "a.Base"), ("dependency", "a.Item")}
    assert _rels(ir, "a.SubIn") == {("extends", "a.Base.In"), ("dependency", "a.Node")}
    # (the supertypes `ArrayList`, `HashMap` through `java.util.*` are unresolved as before)
    assert {u.raw_type for u in ir.unresolved} <= {"ArrayList", "HashMap"}


def test_kotlin_supertype_type_arguments_and_delegation(tmp_path):
    ir = extract_source(tmp_path, {
        "a/T.kt": "package a\nclass Node\nclass Item\nclass T\n",
        "b/T.kt": "package b\nclass Node\n",
        "a/S.kt": ("package a\n"
                   "class NodeList : ArrayList<Node>()\n"
                   "class Gen<T> : ArrayList<T>()\n"
                   "class UsesB : ArrayList<b.Node>()\n"
                   "class Deleg(private val d: List<Item>) : List<Item> by d\n")})
    assert ("dependency", "a.Node") in _rels(ir, "a.NodeList")
    assert not any(to == "a.T" for _, to in _rels(ir, "a.Gen"))
    assert ("dependency", "b.Node") in _rels(ir, "a.UsesB")
    assert ("dependency", "a.Item") in _rels(ir, "a.Deleg")


def test_csharp_supertype_type_arguments_also_a_qualifiers(tmp_path):
    ir = extract_source(tmp_path, {"P/T.cs": (
        "using System.Collections.Generic;\n"
        "namespace A { public class Node {} public class Item {} public class T {}\n"
        "  public class Outer<X> { public class Inner<Y> {} }\n"
        "  public class NodeList : List<Node> {}\n"
        "  public class Gen<T> : List<T> {}\n"
        "  public class Q : Outer<Item>.Inner<Node> {}\n}\n"
        "namespace Lib { public class Order {} }\n"
        "namespace Shop { namespace Lib { public class Order {} }\n"
        "  public class R : System.Collections.Generic.List<global::Lib.Order> {} }\n")})
    assert _rels(ir, "A.NodeList") == {("dependency", "A.Node")}
    assert not _rels(ir, "A.Gen")
    # `Outer<Item>.Inner<Node>`: the qualifier's argument too
    assert {("dependency", "A.Item"), ("dependency", "A.Node")} <= _rels(ir, "A.Q")
    # `global::Lib.Order` is the global namespace's, not Shop.Lib's
    assert _rels(ir, "Shop.R") == {("dependency", "Lib.Order")}


def test_python_base_type_arguments(tmp_path):
    ir = extract_source(tmp_path, {
        "a/__init__.py": "", "b/__init__.py": "", "p/__init__.py": "",
        "a/models.py": "class Node: ...\nclass Item: ...\nclass T: ...\n",
        "b/models.py": "class Node: ...\n",
        "p/lists.py": (
            "from typing import Dict, Generic, List, TypeVar\nimport b.models\n"
            "from a.models import Item, Node\nT = TypeVar('T')\n\n"
            "class NodeList(List[Node]): ...\n"
            "class Gen(Generic[T]): ...\n"
            "class Nested(Dict[str, List[Item]]): ...\n"
            "class UsesB(List[b.models.Node]): ...\n")})
    assert _rels(ir, "p.lists.NodeList") == {("dependency", "a.models.Node")}
    assert not _rels(ir, "p.lists.Gen")
    assert _rels(ir, "p.lists.Nested") == {("dependency", "a.models.Item")}
    assert _rels(ir, "p.lists.UsesB") == {("dependency", "b.models.Node")}


def test_python_a_name_bound_twice_in_type_arguments_draws_nothing(tmp_path):
    ir = extract_source(tmp_path, {
        "q/__init__.py": "", "q/x.py": "class Foo: ...\n",
        "q/t.py": ("from typing import List\ntry:\n    from q.x import Foo\nexcept ImportError:\n"
                   "    class Foo: ...\n\n\nclass X(List[Foo]): ...\n")})
    assert not _rels(ir, "q.t.X")


def test_cpp_base_template_arguments(tmp_path):
    ir = extract_source(tmp_path, {"s.h": (
        "#include <map>\n#include <vector>\n"
        "namespace a { struct Node {}; struct Item {}; struct T {};\n"
        "template <class X> struct Base {}; }\n"
        "namespace b { struct Node {}; }\n"
        "namespace a {\n"
        "struct NodeList : std::vector<Node> {};\n"
        "template <class T> struct Gen : std::vector<T> {};\n"
        "struct Nested : std::map<int, std::vector<Item>> {};\n"
        "struct UsesB : std::vector<b::Node> {};\n"
        "struct Sub : Base<Item> {};\n}\n")})
    assert _rels(ir, "a::NodeList") == {("dependency", "a::Node")}
    assert not _rels(ir, "a::Gen")
    assert _rels(ir, "a::Nested") == {("dependency", "a::Item")}
    assert _rels(ir, "a::UsesB") == {("dependency", "b::Node")}
    assert _rels(ir, "a::Sub") == {("extends", "a::Base"), ("dependency", "a::Item")}


def test_cpp_base_template_arguments_are_looked_up_as_bodies_do(tmp_path):
    # a type declared in an #if branch the base clause is outside of: another type of the
    # name may be meant (the body rule C++'s declarations follow); nothing is drawn
    ir = extract_source(tmp_path, {"s.h": (
        "#include <vector>\n#ifdef _WIN32\nstruct Win {};\n#endif\n"
        "struct D : std::vector<Win> {};\n")})
    assert not _rels(ir, "D")
