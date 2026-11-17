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
    # the viewer gets every class; focus/hops are only where it starts
    assert "rendered 16 types" in res.stderr
    html = (tmp_path / "d.html").read_text()
    assert '"focus": "com.shop.order.OrderService"' in html

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


def test_summary_groups_likely_external_names(tmp_path):
    src = tmp_path / "src" / "p"
    src.mkdir(parents=True)
    (src / "MyLayout.java").write_text(
        "package p; import android.widget.FrameLayout;"
        " class MyLayout extends FrameLayout { LayoutParams lp; MarginLayoutParams m; }")
    ir = tmp_path / "ir.json"
    run("extract.py", tmp_path / "src", "-o", ir)
    out = run("summary.py", ir).stdout
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
