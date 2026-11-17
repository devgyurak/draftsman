#!/usr/bin/env python3
"""Build the Draftsman logo masters from their construction rules.

    python3 assets/logo/build_logo.py [--font path/to/JetBrainsMono-Medium.ttf]

Symbol: a 45° set square that is also a UML generalization arrowhead, on a
256 grid. Apex angle 90°, legs at 45°; the hole is the outer triangle offset
inward by the wall thickness, with softened corners like a real set square.
The shaft is the UML line, drawn thinner than the set square as in drafting
(object lines heavy, connecting lines light) — it also stops the mark from
reading as a sign on a post. Horizontals are ~8 % thinner so they look equal.

The wordmark is "draftsman" in JetBrains Mono Medium (SIL OFL 1.1), converted
to outlines; fontTools is only needed when (re)building the wordmark.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

OUT = Path(__file__).resolve().parent

AMBER = "#D96A00"   # Drafting Amber: the tinted acrylic of a set square
INK = "#15181D"     # Drafting Ink
PAPER = "#FAF8F3"   # Drafting Paper (backgrounds, reversed tiles)
SQRT2 = math.sqrt(2)


def fmt(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".")


def symbol_paths(apex=39.0, base=145.0, wall=24.0, base_wall=22.0, shaft=14.0,
                 shaft_end=229.0, cut=10.0) -> tuple[str, str]:
    """(head path with hole, shaft path) on a 256 canvas."""
    cx = 128.0
    half = base - apex                           # 45° legs: half-width equals height
    outer = f"M{fmt(cx)} {fmt(apex)} L{fmt(cx + half)} {fmt(base)} L{fmt(cx - half)} {fmt(base)} Z"
    # hole: offset each leg by `wall` (perpendicular) and the base by `base_wall`
    i_apex = apex + wall * SQRT2
    i_base = base - base_wall
    i_half = i_base - i_apex
    a, l, r = (cx, i_apex), (cx - i_half, i_base), (cx + i_half, i_base)
    if cut <= 0:
        hole = f"M{fmt(a[0])} {fmt(a[1])} L{fmt(l[0])} {fmt(l[1])} L{fmt(r[0])} {fmt(r[1])} Z"
    else:
        d = cut / SQRT2  # along a 45° edge
        hole = (
            f"M{fmt(a[0] - d)} {fmt(a[1] + d)} "
            f"L{fmt(l[0] + d)} {fmt(l[1] - d)} Q{fmt(l[0])} {fmt(l[1])} {fmt(l[0] + cut)} {fmt(l[1])} "
            f"L{fmt(r[0] - cut)} {fmt(r[1])} Q{fmt(r[0])} {fmt(r[1])} {fmt(r[0] - d)} {fmt(r[1] - d)} "
            f"L{fmt(a[0] + d)} {fmt(a[1] + d)} Q{fmt(a[0])} {fmt(a[1])} {fmt(a[0] - d)} {fmt(a[1] + d)} Z"
        )
    head = outer + " " + hole
    shaft_path = (f"M{fmt(cx - shaft / 2)} {fmt(base)} H{fmt(cx + shaft / 2)} "
                  f"V{fmt(shaft_end)} H{fmt(cx - shaft / 2)} Z")
    return head, shaft_path


def svg(view: str, body: str, title: str = "Draftsman") -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view}" role="img">\n'
            f"  <title>{title}</title>\n{body}</svg>\n")


def symbol_body(head: str, shaft: str, head_fill: str, shaft_fill: str, dx=0.0, dy=0.0,
                scale=1.0) -> str:
    tf = f' transform="translate({fmt(dx)} {fmt(dy)}) scale({fmt(scale)})"' if (dx or dy or scale != 1) else ""
    return (f"  <g{tf}>\n"
            f'    <path fill="{head_fill}" fill-rule="evenodd" d="{head}"/>\n'
            f'    <path fill="{shaft_fill}" d="{shaft}"/>\n'
            f"  </g>\n")


def wordmark(font_path: Path, text="draftsman", tracking=-20) -> tuple[str, float, float, float]:
    """(path data in font units, y-flipped, baseline at 0; advance width; x-height; cap height)."""
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont

    font = TTFont(str(font_path))
    gs = font.getGlyphSet()
    cmap = font.getBestCmap()
    x = 0.0
    parts = []
    for i, ch in enumerate(text):
        g = cmap[ord(ch)]
        pen = SVGPathPen(gs, ntos=lambda v: fmt(v))
        gs[g].draw(TransformPen(pen, (1, 0, 0, -1, x, 0)))
        parts.append(pen.getCommands())
        x += gs[g].width + (tracking if i < len(text) - 1 else 0)
    os2 = font["OS/2"]
    return " ".join(parts), x, float(os2.sxHeight), float(os2.sCapHeight)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--font", type=Path,
                    default=Path.home() / "Library/Fonts/JetBrainsMonoNLNerdFontMono-Medium.ttf")
    args = ap.parse_args()

    head, shaft = symbol_paths()
    # small-size cut (≤ 24 px): heavier walls, sharp hole, shorter shaft so the hole stays open
    s_head, s_shaft = symbol_paths(apex=26, base=154, wall=29, base_wall=25, shaft=28,
                                   shaft_end=230, cut=0)
    # reversed (light on dark) looks heavier: thin every wall by ~1 unit
    r_head, r_shaft = symbol_paths(wall=22.5, base_wall=20.5, shaft=13)

    files = {
        "draftsman-symbol.svg": svg("0 0 256 256", symbol_body(head, shaft, AMBER, INK)),
        "draftsman-symbol-black.svg": svg("0 0 256 256", symbol_body(head, shaft, "#000000", "#000000")),
        "draftsman-symbol-small.svg": svg("0 0 256 256", symbol_body(s_head, s_shaft, "#000000", "#000000")),
        "draftsman-symbol-reversed.svg": svg("0 0 256 256", symbol_body(r_head, r_shaft, AMBER, PAPER)),
    }

    # --- wordmark and lockups -------------------------------------------------
    words, adv, xh, cap = wordmark(args.font)
    # lockup grid: symbol 190 units tall (apex 39 .. shaft end 229); the wordmark's
    # x-height is ~44 % of the symbol height, baseline on the base of the shaft area
    sym_top, sym_bottom = 39.0, 229.0
    sym_h = sym_bottom - sym_top
    scale = (sym_h * 0.33) / xh
    word_w = adv * scale
    unit = 24.0                                   # one wall = the spacing unit

    # horizontal: symbol | 1.25 walls | wordmark; the baseline sits 1 wall below the
    # set square's base, so the shaft hangs like a descender
    gap = unit * 1.25
    sym_left = 22.0                               # symbol bbox x: 22 .. 234
    text_x = 234 + gap
    baseline = 145 + unit
    width = text_x + word_w + 22
    h_body = (symbol_body(head, shaft, AMBER, INK)
              + f'  <path fill="{INK}" transform="translate({fmt(text_x)} {fmt(baseline)}) '
                f'scale({fmt(scale)})" d="{words}"/>\n')
    files["draftsman-horizontal.svg"] = svg(f"0 0 {fmt(width)} 256", h_body)
    files["draftsman-horizontal-black.svg"] = svg(
        f"0 0 {fmt(width)} 256", h_body.replace(AMBER, "#000000").replace(INK, "#000000"))
    files["draftsman-horizontal-reversed.svg"] = svg(
        f"0 0 {fmt(width)} 256",
        symbol_body(r_head, r_shaft, AMBER, PAPER)
        + f'  <path fill="{PAPER}" transform="translate({fmt(text_x)} {fmt(baseline)}) '
          f'scale({fmt(scale)})" d="{words}"/>\n')

    # stacked: symbol above, wordmark centred below; the word is 1.25x the set
    # square's width and sits 2 walls under the shaft so the two never touch
    s_word_w = 212 * 1.25
    s_scale = s_word_w / adv
    s_width = max(256.0, s_word_w + 44)
    s_baseline = sym_bottom + unit * 2 + cap * s_scale
    s_height = s_baseline + 30
    st_body = (symbol_body(head, shaft, AMBER, INK, dx=(s_width - 256) / 2)
               + f'  <path fill="{INK}" transform="translate({fmt((s_width - s_word_w) / 2)} '
                 f'{fmt(s_baseline)}) scale({fmt(s_scale)})" d="{words}"/>\n')
    files["draftsman-stacked.svg"] = svg(f"0 0 {fmt(s_width)} {fmt(s_height)}", st_body)
    files["draftsman-stacked-reversed.svg"] = svg(
        f"0 0 {fmt(s_width)} {fmt(s_height)}",
        symbol_body(r_head, r_shaft, AMBER, PAPER, dx=(s_width - 256) / 2)
        + f'  <path fill="{PAPER}" transform="translate({fmt((s_width - s_word_w) / 2)} '
          f'{fmt(s_baseline)}) scale({fmt(s_scale)})" d="{words}"/>\n')

    # wordmark alone
    w_scale = 160 / cap
    w_width = adv * w_scale + 32
    files["draftsman-wordmark.svg"] = svg(
        f"0 0 {fmt(w_width)} 256",
        f'  <path fill="{INK}" transform="translate(16 {fmt(128 + xh * w_scale / 2)}) '
        f'scale({fmt(w_scale)})" d="{words}"/>\n')

    # plugin / app icon: two-tone reversed mark on an Ink tile (assets/icon.svg)
    s = 1.6                                     # set square ≈ 66 % of the tile width
    icon = svg("0 0 512 512",
               f'  <rect width="512" height="512" rx="112" fill="{INK}"/>\n'
               + symbol_body(r_head, r_shaft, AMBER, PAPER, dx=256 - 128 * s,
                             dy=250 - (sym_top + sym_bottom) / 2 * s, scale=s))

    for name, text in files.items():
        (OUT / name).write_text(text, encoding="utf-8")
        print("wrote", name)
    (OUT.parent / "icon.svg").write_text(icon, encoding="utf-8")
    print("wrote ../icon.svg")


if __name__ == "__main__":
    main()
