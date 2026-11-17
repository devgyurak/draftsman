import json

from conftest import FIXTURES, extract_dir, extract_source
from draftsman.model import Diagnostic


def rels(ir, kind=None):
    return {(r.from_.rsplit(".", 1)[-1], r.kind, r.to.rsplit(".", 1)[-1], r.multiplicity)
            for r in ir.relations if kind is None or r.kind == kind}


def members(ir, tid):
    return {m.name: m for m in ir.type_index()[tid].members}


def test_types_and_kinds(shop_ir):
    kinds = {t.id: t.kind for t in shop_ir.types}
    assert kinds["com.shop.common.BaseEntity"] == "abstract_class"
    assert kinds["com.shop.common.Auditable"] == "interface"
    assert kinds["com.shop.order.OrderLine"] == "record"
    assert kinds["com.shop.order.Order.Status"] == "enum"
    assert kinds["com.shop.customer.Customer.Address"] == "class"
    assert shop_ir.type_index()["com.shop.order.Order.Status"].outer == "com.shop.order.Order"


def test_local_and_anonymous_types_are_skipped(shop_ir):
    # OrderService.place() declares an anonymous Order subclass
    assert len(shop_ir.types) == 16
    assert "terminal" in members(shop_ir, "com.shop.order.Order.Status")
    # the constant-specific body of SHIPPED must not add a second `terminal`
    status = shop_ir.type_index()["com.shop.order.Order.Status"]
    assert [m.name for m in status.members].count("terminal") == 1


def test_supertypes(shop_ir):
    r = rels(shop_ir)
    assert ("Customer", "extends", "BaseEntity", None) in r
    assert ("BaseEntity", "implements", "Auditable", None) in r
    assert ("StripeGateway", "implements", "PaymentGateway", None) in r
    ext = [x for x in shop_ir.relations if x.to.endswith("CrudRepository")]
    assert ext and ext[0].kind == "extends"
    assert [e.id for e in shop_ir.externals] == [
        "org.springframework.data.repository.CrudRepository"]


def test_associations_unwrap_containers(shop_ir):
    r = rels(shop_ir, "association")
    assert ("Order", "association", "OrderLine", "*") in r
    assert ("Customer", "association", "Order", "*") in r
    assert ("Order", "association", "Customer", "1") in r
    assert ("Order", "association", "Status", "1") in r          # nested type by simple name
    assert ("StripeGateway", "association", "Money", "1") in r   # Receipt.Money
    assert ("OrderLine", "association", "Product", "1") in r     # record component


def test_dependencies_keep_every_member(shop_ir):
    deps = rels(shop_ir, "dependency")
    assert ("OrderService", "dependency", "Receipt", None) in deps
    assert ("OrderService", "dependency", "Customer", None) in deps
    # the IR keeps one fact per member; collapsing is the renderer's job
    vias = {r.via for r in shop_ir.relations
            if r.kind == "dependency" and r.from_.endswith("OrderService")
            and r.to.endswith(".Order")}
    assert vias == {"place", "pay"}
    # the constructor mentions OrderRepository too (also an association)
    assert ("OrderService", "dependency", "OrderRepository", None) in deps


def test_static_fields_are_dependencies(tmp_path):
    ir = extract_source(tmp_path, {
        "p/Node.java": "package p; import java.util.List;"
                       " class Node { static final List<Node> EMPTY = null; Node parent; }",
        "p/Tree.java": "package p; class Tree { static Node ROOT; Node first; }",
    })
    assert {(r.from_, r.kind, r.via) for r in ir.relations} == {
        ("p.Node", "association", "parent"),   # static self-reference EMPTY: no relation
        ("p.Tree", "dependency", "ROOT"),
        ("p.Tree", "association", "first")}


def test_member_details(shop_ir):
    svc = members(shop_ir, "com.shop.order.OrderService")
    assert svc["repository"].visibility == "private"
    assert svc["OrderService"].kind == "constructor"
    assert [p.type_ref for p in svc["place"].params] == ["Customer", "List<OrderLine>"]
    assert "Override" in svc["toString"].annotations
    gw = members(shop_ir, "com.shop.pay.PaymentGateway")
    assert gw["charge"].abstract and not gw["supportsRefund"].abstract
    assert members(shop_ir, "com.shop.common.BaseEntity")["id"].visibility == "protected"
    assert members(shop_ir, "com.shop.order.Order.Status")["NEW"].kind == "enum_constant"
    # lambda parameters inside addLine() are not method parameters
    assert [p.name for p in members(shop_ir, "com.shop.order.Order")["addLine"].params] == ["line"]


def test_type_parameters_are_not_references(shop_ir):
    assert not any(u.raw_type == "T" for u in shop_ir.unresolved)


def test_unresolved_with_hints(shop_ir):
    found = {u.raw_type: u for u in shop_ir.unresolved}
    assert set(found) == {"Coupon", "StripeClient"}
    assert found["StripeClient"].hint == "may come from wildcard import com.stripe.*"
    assert found["Coupon"].via == "coupon"


def test_output_is_deterministic():
    a = extract_dir(FIXTURES / "java" / "shop").to_dict()
    b = extract_dir(FIXTURES / "java" / "shop").to_dict()
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_unresolved_lists_same_named_candidates(tmp_path):
    ir = extract_source(tmp_path, {
        "a/Money.java": "package a; public class Money {}",
        "b/Wallet.java": "package b; public class Wallet { Money balance; }",
    })
    (u,) = ir.unresolved
    assert u.raw_type == "Money" and u.candidates == ["a.Money"]
    assert not ir.relations  # never linked by guesswork


def test_syntax_errors_are_reported_not_fatal(tmp_path):
    ir = extract_source(tmp_path, {
        "p/Ok.java": "package p; class Ok { Broken b; }",
        "p/Broken.java": "package p; class Broken { void x( { }",
    })
    assert {t.name for t in ir.types} >= {"Ok"}
    assert ir.diagnostics and ir.diagnostics[0].file == "p/Broken.java"


def test_every_syntax_error_span_is_reported(tmp_path):
    ir = extract_source(tmp_path, {"p/Two.java": (
        "package p;\n"
        "class Two {\n"
        "    void a( { }\n"          # line 3: broken
        "    int ok;\n"
        "    void b() { }\n"
        "    void c( { }\n"          # line 6: broken again
        "    String fine;\n"
        "}\n")})
    assert [(d.file, d.line) for d in ir.diagnostics] == [("p/Two.java", 3), ("p/Two.java", 6)]
    assert [d.to_dict() for d in ir.diagnostics] == [
        Diagnostic.from_dict(d.to_dict()).to_dict() for d in ir.diagnostics]


def test_generic_field_depends_on_its_type_arguments(tmp_path):
    """A generic that is not a container keeps its association, and the field depends on
    the project types written as its arguments (Repository<User>, Envelope<Order>)."""
    ir = extract_source(tmp_path, {
        "p/User.java": "package p; public class User {}",
        "p/Order.java": "package p; public class Order {}",
        "p/Repository.java": "package p; public interface Repository<T> {}",
        "p/Service.java": ("package p; import com.acme.Envelope;\n"   # external, no container
                           "class Service { Repository<User> repo; Envelope<Order> orders; }"),
    })
    rels = {(r.kind, r.to.rsplit(".", 1)[-1], r.via) for r in ir.relations
            if r.from_ == "p.Service"}
    assert rels == {("association", "Repository", "repo"), ("dependency", "User", "repo"),
                    ("dependency", "Order", "orders")}


def test_container_arguments_that_are_not_elements_are_dependencies(tmp_path):
    ir = extract_source(tmp_path, {
        "p/Customer.java": "package p; public class Customer {}",
        "p/Order.java": "package p; public class Order {}",
        "p/Index.java": "package p; import java.util.Map; class Index { Map<Customer, Order> byCustomer; }",
    })
    rels = {(r.kind, r.to, r.via) for r in ir.relations if r.from_ == "p.Index"}
    assert rels == {("association", "p.Order", "byCustomer"), ("dependency", "p.Customer", "byCustomer")}


def test_explicit_import_beats_same_package(tmp_path):
    ir = extract_source(tmp_path, {
        "a/Item.java": "package a; public class Item {}",
        "b/Item.java": "package b; public class Item {}",
        "b/Cart.java": "package b; import a.Item; class Cart { Item item; }",
    })
    assert [(r.from_, r.to) for r in ir.relations] == [("b.Cart", "a.Item")]


def test_nested_types_inherited_from_supertypes(tmp_path):
    ir = extract_source(tmp_path, {
        "p/Filter.java": "package p; public interface Filter { enum Result { GO, STOP } }",
        "p/Base.java": "package p; public class Base implements Filter { class Node {} }",
        "q/Printer.java": "package q; import p.Base; class Printer extends Base {"
                          " Result last; Node node; Base.Result viaOuter; }",
    })
    assert not ir.unresolved
    targets = {(r.via, r.to) for r in ir.relations if r.kind == "association"}
    assert targets == {("last", "p.Filter.Result"), ("node", "p.Base.Node"),
                       ("viaOuter", "p.Filter.Result")}


def test_unresolved_hint_for_external_supertype(tmp_path):
    ir = extract_source(tmp_path, {
        "p/Dataset.java": "package p; import java.util.AbstractMap;"
                          " class Dataset extends AbstractMap<String, String> { Entry first; }",
    })
    (u,) = ir.unresolved
    assert u.hint == "may be a nested type inherited from java.util.AbstractMap"


def test_java_lang_supertypes_are_qualified(tmp_path):
    ir = extract_source(tmp_path, {
        "p/Oops.java": "package p; class Oops extends RuntimeException implements Runnable {"
                       " public void run() {} }",
    })
    assert [e.id for e in ir.externals] == ["java.lang.Runnable", "java.lang.RuntimeException"]


def test_inner_supertype_inherited_by_the_enclosing_class(tmp_path):
    # `Listener` is a member of Base; Impl's implements clause sees it through Outer
    ir = extract_source(tmp_path, {
        "p/Base.java": "package p; public class Base { public interface Listener {} }",
        "p/Outer.java": "package p; class Outer extends Base { class Impl implements Listener {} }",
    })
    assert not ir.unresolved
    assert ("p.Outer.Impl", "p.Base.Listener", "implements") in {
        (r.from_, r.to, r.kind) for r in ir.relations}


def test_cyclic_supertypes_do_not_recurse_forever(tmp_path):
    ir = extract_source(tmp_path, {
        "p/A.java": "package p; class A extends B { Nested n; }",
        "p/B.java": "package p; class B extends A {}",
    })
    assert [u.raw_type for u in ir.unresolved] == ["Nested"]


def test_external_ancestor_hint_through_project_superclass(tmp_path):
    ir = extract_source(tmp_path, {
        "p/BaseLayout.java": "package p; import android.widget.FrameLayout;"
                             " class BaseLayout extends FrameLayout {}",
        "p/MyLayout.java": "package p; class MyLayout extends BaseLayout { LayoutParams lp; }",
    })
    (u,) = ir.unresolved
    assert u.hint == "may be a nested type inherited from android.widget.FrameLayout"


def test_type_annotations_before_varargs_parse(tmp_path):
    # valid Java 8 that tree-sitter-java rejects; blanked before parsing, lines kept
    ir = extract_source(tmp_path, {
        "p/Cert.java": "package p; public class Cert {}",
        "p/Ctx.java": "package p;\nclass Ctx {\n  void trust(Cert @Nullable ... certs) {}\n"
                      "  void keys(String a,\n      Cert @Size(max = (3)) @Nullable\n      ... more) {}\n"
                      "  void arr(Cert @Nullable [] arr) {}\n}\n",
    })
    assert not ir.diagnostics
    ctx = next(t for t in ir.types if t.name == "Ctx")
    params = {m.name: [(p.name, p.type_ref) for p in m.params] for m in ctx.members}
    assert params["trust"] == [("certs", "Cert...")]
    assert params["keys"] == [("a", "String"), ("more", "Cert...")]
    assert [m.line for m in ctx.members] == [3, 4, 7]
    deps = {(r.via, r.to) for r in ir.relations if r.kind == "dependency"}
    assert deps == {("trust", "p.Cert"), ("keys", "p.Cert"), ("arr", "p.Cert")}
