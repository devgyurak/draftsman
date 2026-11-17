import json
import shutil
import subprocess
from pathlib import Path

import pytest

from draftsman.render_mermaid import render
from draftsman.scene import build_scene
from draftsman.view import View, ViewError

SCRIPTS = Path(__file__).parents[1] / "skills" / "draftsman" / "scripts"


def scene(ir, **view):
    return build_scene(ir, View.from_dict(view))


def ids(s):
    return {t.id.rsplit(".", 1)[-1] for t in s.types}


def test_default_view_draws_everything(shop_ir):
    s = scene(shop_ir)
    assert len(s.types) == len(shop_ir.types)
    assert not s.externals  # externals are opt-in


def test_focus_hops(shop_ir):
    one = ids(scene(shop_ir, focus="OrderService", hops=1))
    assert one == {"OrderService", "OrderRepository", "PaymentGateway", "Customer",
                   "Order", "OrderLine", "Receipt"}
    zero = ids(scene(shop_ir, focus="OrderService", hops=0))
    assert zero == {"OrderService"}


def test_focus_respects_relation_filter(shop_ir):
    s = scene(shop_ir, focus="OrderService", hops=1, relations=["association"])
    assert ids(s) == {"OrderService", "OrderRepository", "PaymentGateway"}


def test_hidden_types_and_members(shop_ir):
    s = scene(shop_ir, hidden=["com.shop.common.*", "*#get*", "OrderService#toString"])
    assert "BaseEntity" not in ids(s)
    svc = next(t for t in s.types if t.name == "OrderService")
    assert "toString" not in {m.name for m in svc.members}
    assert not any(m.name.startswith("get") for t in s.types for m in t.members)
    assert not any(r.to.endswith("BaseEntity") for r in s.relations)


def test_dependencies_collapse_per_pair(shop_ir):
    s = scene(shop_ir)
    pairs = [(r.from_, r.to) for r in s.relations if r.kind == "dependency"]
    assert len(pairs) == len(set(pairs))
    svc = "com.shop.order.OrderService"
    # OrderService -> OrderRepository is an association, so no extra dependency arrow
    assert (svc, "com.shop.order.OrderRepository") not in pairs
    assert (svc, "com.shop.order.Order") in pairs


def test_hidden_member_hides_its_relations(shop_ir):
    s = scene(shop_ir, hidden=["Order#lines", "OrderService#place"])
    assert not any(r.via == "lines" for r in s.relations)
    pairs = {(r.from_, r.to) for r in s.relations}
    # place() was the only member of OrderService mentioning OrderLine ...
    assert ("com.shop.order.OrderService", "com.shop.order.OrderLine") not in pairs
    # ... while pay() still mentions Order
    assert ("com.shop.order.OrderService", "com.shop.order.Order") in pairs


def test_member_detail_per_type(shop_ir):
    # the last matching key wins: OrderService matches all three
    s = scene(shop_ir, members={"*": "none", "*Service": "public", "Order*": "public",
                                "OrderService": "all"})
    by = {t.name: t for t in s.types}
    assert by["Customer"].members == []
    svc = {m.name for m in by["OrderService"].members}
    assert "repository" in svc                                   # private, but "all" wins
    assert all(m.visibility == "public" for m in by["Order"].members)
    assert by["Order"].members
    # member detail never removes relations
    assert len(s.relations) == len(scene(shop_ir).relations)


def test_member_detail_unmatched_key_warns(shop_ir):
    s = scene(shop_ir, members={"*": "all", "Nothing*": "none"})
    assert any("Nothing*" in w for w in s.warnings)


@pytest.mark.parametrize("bad", ["some", {"*": "most"}, ["all"]])
def test_member_detail_is_validated(shop_ir, bad):
    with pytest.raises(ViewError):
        scene(shop_ir, members=bad)


def test_unknown_names_are_errors(shop_ir):
    with pytest.raises(ViewError):
        scene(shop_ir, focus="Invented")
    with pytest.raises(ViewError):
        scene(shop_ir, notes=[{"target": "Invented", "text": "x"}])
    with pytest.raises(ViewError):
        scene(shop_ir, groups=[{"name": "g", "members": ["Invented"]}])
    with pytest.raises(ViewError):
        View.from_dict({"focus": "Order", "colour": "red"})


def test_inferred_edges_only_reach_unresolved_names(shop_ir):
    ok = scene(shop_ir, inferred_edges=[
        {"from": "StripeGateway", "to": "StripeClient", "kind": "association", "rationale": "r"}])
    assert ok.ghosts == ["StripeClient"]
    with pytest.raises(ViewError):
        scene(shop_ir, inferred_edges=[
            {"from": "Order", "to": "Made", "kind": "association", "rationale": "r"}])
    with pytest.raises(ViewError):  # rationale is mandatory
        View.from_dict({"inferred_edges": [{"from": "Order", "to": "Coupon", "kind": "association"}]})


def test_inferred_edge_duplicating_a_fact_is_dropped(shop_ir):
    s = scene(shop_ir, inferred_edges=[
        {"from": "Customer", "to": "BaseEntity", "kind": "extends", "rationale": "r"}])
    assert not s.inferred and s.warnings


def test_ambiguous_simple_name(tmp_path):
    from conftest import extract_source
    ir = extract_source(tmp_path, {"a/X.java": "package a; class X {}",
                                   "b/X.java": "package b; class X {}"})
    with pytest.raises(ViewError, match="ambiguous"):
        scene(ir, focus="X")
    text = render(scene(ir))
    assert 'class a_X["X"]' in text and 'class b_X["X"]' in text


@pytest.mark.parametrize("title", [
    "Shop: orders", 'He said "hi" #1', "null", "yes", "- dash", "line1\nline2", "주문: 결제"])
def test_mermaid_title_is_quoted_yaml(shop_ir, title):
    import json
    import yaml
    text = render(scene(shop_ir, title=title))
    front = text.split("---")[1]
    assert yaml.safe_load(front)["title"] == title
    assert front.strip() == f"title: {json.dumps(title, ensure_ascii=False)}"


def test_mermaid_shapes(shop_ir):
    text = render(scene(shop_ir, focus="Order", hops=1, externals=True,
                        notes=[{"target": "Order", "text": 'says "hi"'}],
                        highlights=[{"target": "Customer", "reason": "cycle"}],
                        groups=[{"name": "주문 도메인", "members": ["Order", "OrderLine"]}]))
    assert "  BaseEntity <|-- Order" in text
    assert '  Order --> "*" OrderLine : lines' in text
    assert "  Order --> Customer : customer" in text
    assert 'class Order_Status["Order.Status"]' in text
    assert "namespace 주문_도메인 {" in text
    assert 'note for Order "says #quot;hi#quot;"' in text
    assert "style Customer stroke:#e03131" in text
    assert "-List~OrderLine~ lines" in text


@pytest.mark.skipif(not (SCRIPTS / "node_modules" / "mermaid").exists() and not shutil.which("mmdc"),
                    reason="no Mermaid validator installed")
def test_mermaid_validates(shop_ir, tmp_path):
    views = [
        {},
        {"focus": "OrderService", "hops": 2, "externals": True, "direction": "LR",
         "title": "주문: 결제 #1", "groups": [{"name": "결제 도메인", "members": ["PaymentGateway", "Receipt"]}],
         "notes": [{"target": "OrderService", "text": "a \"quoted\"\nnote {x}"}],
         "highlights": [{"target": "Order", "reason": "god {class}"}],
         "inferred_edges": [{"from": "StripeGateway", "to": "StripeClient",
                             "kind": "association", "rationale": "wildcard {import}"}]},
        {"members": "none"},
    ]
    for i, v in enumerate(views):
        path = tmp_path / f"d{i}.mmd"
        path.write_text(render(scene(shop_ir, **v)))
        res = subprocess.run([str(SCRIPTS / "validate.sh"), str(path)],
                             capture_output=True, text=True)
        assert res.returncode == 0, res.stderr + path.read_text()


# ------------------------------------------------------------------ svg / html

from draftsman.graph import build_graph, find_cycles  # noqa: E402
from draftsman.render_web import ELK_BUNDLE, render_html, render_svg  # noqa: E402


def test_graph_json(shop_ir):
    g = build_graph(scene(shop_ir, externals=True, notes=[{"target": "Order", "text": "n"}],
                          inferred_edges=[{"from": "StripeGateway", "to": "StripeClient",
                                           "kind": "association", "rationale": "r"}]), shop_ir)
    kinds = {n["id"]: n["kind"] for n in g["nodes"]}
    assert kinds["StripeClient"] == "inferred"
    assert kinds["org.springframework.data.repository.CrudRepository"] == "external"
    order = next(n for n in g["nodes"] if n["id"] == "com.shop.order.Order")
    assert "- lines: List<OrderLine>" in [m["text"] for m in order["members"]]
    assert any(e["inferred"] and e["rationale"] == "r" for e in g["edges"])
    assert g["cycles"] == [["com.shop.customer.Customer", "com.shop.order.Order"]]
    assert {u["raw_type"] for u in g["unresolved"]} == {"Coupon", "StripeClient"}


def test_find_cycles_ignores_inheritance():
    from draftsman.model import Location, Relation
    loc = Location("f", 1)
    rels = [Relation("a", "b", "association", loc), Relation("b", "c", "dependency", loc),
            Relation("c", "a", "association", loc), Relation("d", "a", "extends", loc),
            Relation("a", "d", "association", loc)]
    assert find_cycles(["a", "b", "c", "d"], rels) == [["a", "b", "c"]]


def test_html_is_self_contained(shop_ir):
    html = render_html(scene(shop_ir, title="<Shop>", notes=[
        {"target": "Order", "text": "</script><b>x</b>"}]), shop_ir)
    assert "<title>&lt;Shop&gt;</title>" in html
    assert "</script><b>" not in html            # user text cannot close the script
    assert "DRAFTSMAN_" not in html.replace("DraftsmanDraw", "")
    if ELK_BUNDLE.exists():
        assert "cdn.jsdelivr.net" not in html     # works offline


@pytest.mark.skipif(not ELK_BUNDLE.exists() or not shutil.which("node"),
                    reason="elkjs/node not installed")
def test_svg_layout(shop_ir):
    svg = render_svg(scene(shop_ir, groups=[{"name": "주문", "members": ["Order", "OrderLine"]}],
                           notes=[{"target": "Order", "text": "note text"}],
                           highlights=[{"target": "Customer", "reason": "r"}]), shop_ir)
    assert svg.startswith("<svg")
    assert svg.count('class="node ') == len(shop_ir.types)
    assert 'data-id="com.shop.order.Order"' in svg
    assert "note text" in svg and "주문" in svg
    assert "highlight" in svg and "url(#dm-tri)" in svg
    # role name and multiplicity share one label at the target end, on a backing box
    assert ">lines *</text>" in svg and 'class="lbg"' in svg


@pytest.mark.skipif(not ELK_BUNDLE.exists() or not shutil.which("node"),
                    reason="elkjs/node not installed")
def test_svg_sheet_and_viewer_marks(shop_ir, tmp_path):
    """A standalone SVG is a drawing sheet; the viewer's selection marks come from the same code."""
    svg = render_svg(scene(shop_ir, title="Shop", focus="OrderService", hops=1), shop_ir)
    assert 'class="sheet"' in svg and 'class="titleblock"' in svg
    assert ">Shop</text>" in svg and ">CLASSES</text>" in svg and "OrderService ±1" in svg
    assert ">I</text>" in svg                         # kind badge on the interfaces
    assert '<tspan class="mt">' in svg                # member types set apart from names

    graph = tmp_path / "g.json"
    graph.write_text(json.dumps(build_graph(scene(shop_ir), shop_ir)), encoding="utf-8")
    js = (f"const ELK = require({json.dumps(str(ELK_BUNDLE))});"
          f"const D = require({json.dumps(str(ELK_BUNDLE.parents[3].parent / 'assets' / 'draw.js'))});"
          f"const g = JSON.parse(require('fs').readFileSync({json.dumps(str(graph))}, 'utf8'));"
          "new ELK().layout(D.toElk(g, {notes: false})).then((l) => process.stdout.write(D.toSvg(g, l, "
          "{selected: 'com.shop.order.Order', noted: new Set(['com.shop.order.Order'])})));")
    res = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    assert 'class="crop"' in res.stdout and 'class="notedot"' in res.stdout
    assert 'class="sheet"' not in res.stdout          # the viewer has no frame
