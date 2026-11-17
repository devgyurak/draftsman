"""Scene -> static SVG (ELK layout via node) or a single-file interactive HTML viewer."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .graph import build_graph
from .model import IR
from .scene import Scene

SKILL_DIR = Path(__file__).resolve().parents[2]
SCRIPTS = SKILL_DIR / "scripts"
ASSETS = SKILL_DIR / "assets"
ELK_BUNDLE = SCRIPTS / "node_modules" / "elkjs" / "lib" / "elk.bundled.js"
# the same version as scripts/package.json and package-lock.json, so a viewer that
# falls back to the CDN lays out exactly like the SVG renderer (tests check it)
ELK_VERSION = "0.9.3"
ELK_CDN = f"https://cdn.jsdelivr.net/npm/elkjs@{ELK_VERSION}/lib/elk.bundled.js"


class RenderError(RuntimeError):
    pass


def render_svg(scene: Scene, ir: IR | None = None) -> str:
    node = shutil.which("node")
    if node is None or not ELK_BUNDLE.exists():
        raise RenderError(
            "SVG output needs node and elkjs: run `npm ci --prefix "
            f"{SCRIPTS}` (or use --format mermaid / html)")
    graph = build_graph(scene, ir)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False)
        path = f.name
    try:
        res = subprocess.run([node, str(SCRIPTS / "layout.mjs"), path],
                             capture_output=True, text=True, timeout=300)
    finally:
        Path(path).unlink(missing_ok=True)
    if res.returncode != 0:
        raise RenderError(f"layout failed: {res.stderr.strip()[:2000]}")
    return res.stdout


def _script_safe(code: str) -> str:
    """Make JavaScript source safe to inline in a <script> element."""
    return re.sub(r"</(script)", r"<\\/\1", code, flags=re.IGNORECASE)


def _json_safe(data: str) -> str:
    return data.replace("</", "<\\/")  # a valid escape inside JSON strings


def render_html(scene: Scene, ir: IR | None = None, inline_elk: bool = True) -> str:
    graph = build_graph(scene, ir)
    template = (ASSETS / "viewer.html").read_text(encoding="utf-8")
    draw = (ASSETS / "draw.js").read_text(encoding="utf-8")
    if inline_elk and ELK_BUNDLE.exists():
        elk = ("<!-- elkjs (Eclipse Layout Kernel) - Copyright Kiel University and others - "
               "Eclipse Public License 2.0 - source: https://github.com/kieler/elkjs -->\n"
               "<script>" + _script_safe(ELK_BUNDLE.read_text(encoding="utf-8")) + "</script>")
    else:
        elk = f'<script src="{ELK_CDN}"></script>'
    title = scene.title or "Class diagram"
    data = _json_safe(json.dumps(graph, ensure_ascii=False))
    # title first: later insertions (library code, user text) must not be rescanned
    head, body = template.split("<!--DRAFTSMAN_ELK-->", 1)
    head = head.replace("DRAFTSMAN_TITLE", _html_escape(title))
    body = body.replace("/*DRAFTSMAN_DRAW*/", _script_safe(draw), 1)
    body = body.replace("/*DRAFTSMAN_DATA*/null", data, 1)
    return head + elk + body


def _html_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
