import json
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import FIXTURES

SCRIPTS = Path(__file__).parents[1] / "skills" / "draftsman" / "scripts"
SHOP = FIXTURES / "java" / "shop"


def run(script, *args):
    return subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)],
                          capture_output=True, text=True)


@pytest.mark.parametrize("rel, hit", [
    ("src/test/java/A.java", True),
    ("test/A.java", True),
    ("src/main/java/A.java", False),
    ("src/main/java/contest/A.java", False),
])
def test_exclude_globs(rel, hit):
    sys.path.insert(0, str(SCRIPTS))
    from extract import excluded
    assert excluded(rel, ["**/test/**"]) is hit


def test_extract_render_pipeline(tmp_path):
    ir, view, out = tmp_path / "ir.json", tmp_path / "view.json", tmp_path / "d.mmd"
    res = run("extract.py", SHOP, "-o", ir)
    assert res.returncode == 0, res.stderr
    assert "16 types" in res.stderr

    view.write_text(json.dumps({"focus": "OrderService", "hops": 1, "hidden": ["*#nothing"]}))
    res = run("render.py", ir, view, "-o", out)
    assert res.returncode == 0, res.stderr
    assert "matches no visible member" in res.stderr
    assert out.read_text().startswith("classDiagram")

    res = run("summary.py", ir)
    assert res.returncode == 0 and "StripeClient" in res.stdout


def test_render_rejects_bad_view(tmp_path):
    ir, view = tmp_path / "ir.json", tmp_path / "view.json"
    run("extract.py", SHOP, "-o", ir)
    view.write_text(json.dumps({"focus": "Nope"}))
    res = run("render.py", ir, view)
    assert res.returncode == 1 and "no type 'Nope'" in res.stderr


def test_html_and_svg_formats(tmp_path):
    ir, view = tmp_path / "ir.json", tmp_path / "view.json"
    run("extract.py", SHOP, "-o", ir)
    view.write_text(json.dumps({"focus": "OrderService", "hops": 1, "output": "html"}))
    res = run("render.py", ir, view, "-o", tmp_path / "d.html")
    assert res.returncode == 0, res.stderr
    # the viewer gets every class; focus/hops are only where it starts. Its 5 nested
    # types are folded into their outer types, as around the focus
    assert "rendered 11 types" in res.stderr
    html = (tmp_path / "d.html").read_text()
    assert '"focus": "com.shop.order.OrderService"' in html
    assert '"nested": "fold"' in html
    view.write_text(json.dumps({"focus": "OrderService", "hops": 1, "output": "html",
                                "nested": "boxes"}))
    res = run("render.py", ir, view, "-o", tmp_path / "d.html")
    assert "rendered 16 types" in res.stderr

    res = run("render.py", ir, "--format", "svg", "-o", tmp_path / "d.svg")
    if res.returncode == 2:  # no node/elkjs here: a clear message, no traceback
        assert "npm install" in res.stderr
    else:
        assert res.returncode == 0, res.stderr
        assert (tmp_path / "d.svg").read_text().startswith("<svg")


def test_summary_describes_a_type(tmp_path):
    ir = tmp_path / "ir.json"
    run("extract.py", SHOP, "-o", ir)
    res = run("summary.py", ir, "--type", "PaymentGateway")
    assert res.returncode == 0, res.stderr
    assert "charge(Order order): Receipt  abstract" in res.stdout
    assert "in  implements  com.shop.pay.StripeGateway" in res.stdout
    assert run("summary.py", ir, "--type", "Nope").returncode == 1
    # a nested type's relations are its outer type's in a focus diagram: listed, marked
    out = run("summary.py", ir, "--type", "Receipt").stdout
    assert "  nested: Receipt.Money" in out
    assert "in  association com.shop.pay.StripeGateway  1 via fee [Receipt.Money]" in out
    assert "out association com.shop.pay.Receipt.Money  1 via amount" in out


def test_summary_groups_likely_external_names(tmp_path):
    src = tmp_path / "src" / "p"
    src.mkdir(parents=True)
    (src / "MyLayout.java").write_text(
        "package p; import android.widget.FrameLayout;"
        " class MyLayout extends FrameLayout { LayoutParams lp; MarginLayoutParams m; }")
    ir = tmp_path / "ir.json"
    res = run("extract.py", tmp_path / "src", "-o", ir)
    assert "2 unresolved (2 outside the sources)" in res.stderr
    out = run("summary.py", ir).stdout
    assert "unresolved references (2: 2 outside):" in out
    assert "+ 2 only explained by wildcard imports or external supertypes" in out
    assert "LayoutParams" in out and "in MyLayout" not in out


def test_members_flag_overrides_view(tmp_path):
    ir, view = tmp_path / "ir.json", tmp_path / "view.json"
    run("extract.py", SHOP, "-o", ir)
    view.write_text(json.dumps({"focus": "OrderService", "hops": 1, "members": "all"}))
    full = run("render.py", ir, view)
    bare = run("render.py", ir, view, "--members", "none")
    assert full.returncode == bare.returncode == 0, bare.stderr
    assert "+place(" in full.stdout and "+place(" not in bare.stdout
    # same classes and relations either way
    arrows = lambda out: sorted(l for l in out.splitlines() if "--" in l or ".." in l)
    assert arrows(full.stdout) == arrows(bare.stdout)


def test_summary_focus_prints_overview_and_type(tmp_path):
    ir = tmp_path / "ir.json"
    run("extract.py", SHOP, "-o", ir)
    out = run("summary.py", ir, "--focus", "PaymentGateway").stdout
    assert out.startswith("root: ") and "most connected" in out
    assert "in  implements  com.shop.pay.StripeGateway" in out
    assert run("summary.py", ir, "--focus", "Nope").returncode == 1


def test_draw_focus_in_one_step(tmp_path):
    res = run("draw.py", SHOP, "--focus", "OrderService", "--hops", "1",
              "--members", "public", "--work", tmp_path)
    assert res.returncode == 0, res.stderr
    assert res.stdout.startswith("classDiagram") and "+place(" in res.stdout
    err = res.stderr
    assert "draftsman: repository: 11 files, 16 types" in err
    assert "draftsman: excluded: **/test/**, **/tests/**" in err
    assert "draftsman: scope: focus com.shop.order.OrderService, 1 hop" in err
    assert "draftsman: drawn: 7 types, 13 relations, 0 inferred" in err
    assert "draftsman: one more hop adds 3 types: BaseEntity, StripeGateway, Product" in err
    assert "Coupon" in err   # the unresolved reference of a drawn type
    assert (tmp_path / "ir.json").is_file()
    assert (tmp_path / "diagram.mmd").read_text() == res.stdout
    # the diagram is the one render.py draws from the same view
    view = tmp_path / "view.json"
    view.write_text(json.dumps({"focus": "OrderService", "hops": 1, "members": "public"}))
    assert run("render.py", tmp_path / "ir.json", view).stdout == res.stdout


def test_draw_again_from_ir_json_with_a_view(tmp_path):
    run("extract.py", SHOP, "-o", tmp_path / "ir.json")
    view = tmp_path / "view.json"
    view.write_text(json.dumps({"focus": "Order", "hops": 2, "members": "none",
                                "notes": [{"target": "Order", "text": "aggregate root"}]}))
    # flags override the view's keys; --hide adds to its hidden list
    res = run("draw.py", tmp_path / "ir.json", "--view", view, "--hops", "1",
              "--hide", "Customer")
    assert res.returncode == 0, res.stderr
    assert "note for Order" in res.stdout and "class Customer" not in res.stdout
    assert "scope: focus com.shop.order.Order, 1 hop" in res.stderr
    assert "hidden types: Customer (1)" in res.stderr
    assert "excluded:" not in res.stderr   # nothing was extracted
    assert (tmp_path / "diagram.mmd").is_file()


def test_draw_refuses_too_many_types(tmp_path):
    res = run("draw.py", SHOP, "--max-types", "5", "--work", tmp_path)
    assert res.returncode == 3 and res.stdout == ""
    assert "NOT DRAWN: 16 types is over --max-types 5" in res.stderr
    assert "  --max-types 16: all 16 types" in res.stderr
    assert "most connected: Order (8)" in res.stderr
    assert "--relations" not in res.stderr   # it would not narrow a diagram without focus
    # hops given: not changed; every option with its count, the ones keeping relations first
    res = run("draw.py", tmp_path / "ir.json", "--focus", "Order", "--hops", "2",
              "--max-types", "8")
    assert res.returncode == 3
    options = [l.split(":")[0].strip() for l in res.stderr.splitlines() if l.startswith("  --")]
    assert options == ["--max-types 11", "--hops 1",
                       "--relations extends,implements,association", "--format html"]
    assert "  --hops 1: 8 types" in res.stderr


def test_draw_chooses_hops_within_the_limit(tmp_path):
    """Without --hops, the widest neighbourhood that fits, and the report says why."""
    res = run("draw.py", SHOP, "--focus", "Order", "--max-types", "8", "--work", tmp_path)
    assert res.returncode == 0, res.stderr
    assert ("scope: focus com.shop.order.Order, 1 hop (chosen: 2 hops would draw 11 types, "
            "over --max-types 8; --hops 2 --max-types 11 draws them)") in res.stderr
    assert "drawn: 8 types" in res.stderr
    wide = run("draw.py", tmp_path / "ir.json", "--focus", "Order")
    assert "scope: focus com.shop.order.Order, 2 hops\n" in wide.stderr   # it fits: as asked
    # never below one hop: a focus alone answers nothing
    res = run("draw.py", tmp_path / "ir.json", "--focus", "Order", "--max-types", "3")
    assert res.returncode == 3 and "  --hops 1: 8 types" in res.stderr


def test_draw_html_and_errors(tmp_path):
    out = tmp_path / "d.html"
    res = run("draw.py", SHOP, "--focus", "OrderService", "-o", out, "--work", tmp_path)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "" and f"html: {out}" in res.stderr   # format from -o
    assert '"focus": "com.shop.order.OrderService"' in out.read_text()

    res = run("draw.py", tmp_path / "ir.json", "--focus", "Nope")
    assert res.returncode == 1 and "no type 'Nope'" in res.stderr
    res = run("draw.py", tmp_path / "ir.json", "--relations", "extends,uses")
    assert res.returncode == 1 and "unknown relation kinds" in res.stderr
    assert run("draw.py", tmp_path / "missing").returncode == 1


def test_draw_keeps_tests_on_request(tmp_path):
    src = tmp_path / "src"
    for rel, body in (("main/A.java", "class A { B b; }"), ("test/B.java", "class B {}")):
        (src / rel).parent.mkdir(parents=True, exist_ok=True)
        (src / rel).write_text(body)
    without = run("draw.py", src, "--work", tmp_path / "w1")
    assert "1 types" in without.stderr and "class B" not in without.stdout
    keep = run("draw.py", src, "--tests", "--work", tmp_path / "w2")
    assert "2 types" in keep.stderr and "A --> B : b" in keep.stdout
