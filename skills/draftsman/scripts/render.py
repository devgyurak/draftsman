#!/usr/bin/env python3
"""Render ir.json (+ optional view.json) as a class diagram.

    python scripts/render.py ir.json [view.json] [--format mermaid|svg|html]
                             [--members all|public|none] [-o FILE]

mermaid: text for docs and PRs. svg: static image laid out with ELK (needs node
and `npm ci --prefix scripts`). html: single-file interactive viewer; it
contains every class the view allows, and starts at the view's focus/hops.

The view selects and annotates facts; it cannot add types or relations.
Warnings about view entries that had no effect go to stderr.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from draftsman.model import IR
from draftsman.render_mermaid import render as render_mermaid
from draftsman.render_web import RenderError, render_html, render_svg
from draftsman.scene import build_scene
from draftsman.view import MEMBER_DETAIL, OUTPUTS, View, ViewError

RENDERERS = {
    "mermaid": lambda scene, ir: render_mermaid(scene),
    "svg": render_svg,
    "html": render_html,
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("ir", type=Path)
    ap.add_argument("view", type=Path, nargs="?")
    ap.add_argument("--format", choices=OUTPUTS, help="overrides view.output")
    ap.add_argument("--members", choices=MEMBER_DETAIL,
                    help="member detail for every class; overrides view.members")
    ap.add_argument("-o", "--output", type=Path, help="write here (default: stdout)")
    args = ap.parse_args(argv)

    try:
        ir = IR.load(args.ir)
        view = View.load(args.view)
        if args.members:
            view = replace(view, members=args.members)
        fmt = args.format or view.output
        scene = build_scene(ir, view)
        if fmt == "html" and scene.focus:
            # the viewer gets everything the view allows; focus is only its start
            full = build_scene(ir, replace(view, focus=None))
            full.focus, full.hops = scene.focus, scene.hops
            scene = full
    except (ViewError, ValueError) as e:
        print(f"draftsman: view error: {e}", file=sys.stderr)
        return 1

    for w in scene.warnings:
        print(f"draftsman: warning: {w}", file=sys.stderr)
    try:
        text = RENDERERS[fmt](scene, ir)
    except RenderError as e:
        print(f"draftsman: {e}", file=sys.stderr)
        return 2
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    print(f"draftsman: rendered {len(scene.types)} types, {len(scene.relations)} relations, "
          f"{len(scene.inferred)} inferred", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
