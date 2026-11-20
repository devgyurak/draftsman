"""draw.js and the HTML viewer, tested in node (tests/js/*.test.mjs).

The viewer is loaded into jsdom with its inlined ELK, as a browser would open it,
and driven through clicks, keys and the search box.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from draftsman.graph import build_graph
from draftsman.render_web import ELK_BUNDLE, render_html
from draftsman.scene import build_scene
from draftsman.view import View

JS = Path(__file__).parent / "js"
SCRIPTS = ELK_BUNDLE.parents[3]

pytestmark = pytest.mark.skipif(
    not shutil.which("node") or not ELK_BUNDLE.exists()
    or not (SCRIPTS / "node_modules" / "jsdom").exists(),
    reason="node with elkjs and jsdom (npm ci --prefix skills/draftsman/scripts) not installed")

VIEW = {
    "title": "<Shop> & co",
    "focus": "OrderService", "hops": 1,
    "externals": True,
    "notes": [{"target": "Order", "text": "<img src=x onerror=alert(1)>"}],
    "highlights": [{"target": "PaymentGateway", "reason": "boundary"}],
    "inferred_edges": [{"from": "StripeGateway", "to": "StripeClient", "kind": "association",
                        "rationale": "import com.stripe.*"}],
}


@pytest.fixture(scope="module")
def inputs(shop_ir, tmp_path_factory):
    out = tmp_path_factory.mktemp("frontend")
    # the viewer gets every class and starts at the focus, as render.py does; nested
    # types are folded into their outer types, as around a focus
    scene = build_scene(shop_ir, View.from_dict(VIEW), whole=True)
    (out / "graph.json").write_text(json.dumps(build_graph(scene, shop_ir)), encoding="utf-8")
    (out / "viewer.html").write_text(render_html(scene, shop_ir), encoding="utf-8")
    return out


@pytest.mark.parametrize("suite", ["draw", "viewer"])
def test_js(suite, inputs):
    res = subprocess.run(
        ["node", "--test", "--test-reporter=spec", str(JS / f"{suite}.test.mjs")],
        capture_output=True, text=True, timeout=180,
        env={"PATH": __import__("os").environ["PATH"], "DRAFTSMAN_SCRIPTS": str(SCRIPTS),
             "DRAFTSMAN_GRAPH": str(inputs / "graph.json"),
             "DRAFTSMAN_VIEWER": str(inputs / "viewer.html")})
    assert res.returncode == 0, res.stdout[-6000:] + res.stderr[-3000:]


def test_viewer_neighbourhood(tmp_path):
    """The viewer's focus and hops follow scene.py's rules (tests/js/neighbourhood.test.mjs)."""
    from conftest import extract_source
    ir = extract_source(tmp_path / "src", {
        "p/Mark.java": "package p; @interface Mark { }",
        "p/A.java": "package p; @Mark class A { }",
        "p/B.java": "package p; @Mark class B { }",
        "p/C.java": "package p; @Mark class C { void use(Mark m) { } }",
        "p/D.java": "package p; class D { C c; }"})
    scene = build_scene(ir, View.from_dict({"focus": "A", "hops": 3}), whole=True)
    (tmp_path / "viewer.html").write_text(render_html(scene, ir), encoding="utf-8")
    res = subprocess.run(
        ["node", "--test", "--test-reporter=spec", str(JS / "neighbourhood.test.mjs")],
        capture_output=True, text=True, timeout=180,
        env={"PATH": __import__("os").environ["PATH"], "DRAFTSMAN_SCRIPTS": str(SCRIPTS),
             "DRAFTSMAN_VIEWER": str(tmp_path / "viewer.html")})
    assert res.returncode == 0, res.stdout[-6000:] + res.stderr[-3000:]
