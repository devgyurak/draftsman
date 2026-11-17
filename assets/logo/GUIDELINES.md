# Draftsman — Logo Guidelines

![Draftsman](draftsman-horizontal.svg)

## 1. The logo

**Idea:** the UML inheritance arrowhead is a draftsman's set square. The mark names the
tool (a 45° drafting triangle with its rounded opening) and the product (the hollow arrow
that points to a parent class) in one shape. The amber head is the set square; the thin ink
line is the diagram's connecting line — heavy object line, light connecting line, as in a
technical drawing.

| File | Use |
|---|---|
| `draftsman-horizontal.svg` | primary — README headers, websites, slides |
| `draftsman-stacked.svg` | square-ish spaces: posters, stickers, social cards |
| `draftsman-symbol.svg` | the mark alone, 32 px and up |
| `draftsman-symbol-small.svg` | the mark at 24 px and below (heavier walls, larger opening) |
| `draftsman-wordmark.svg` | text-only contexts where the mark already appears nearby |
| `*-reversed.svg` | on Ink or other dark backgrounds (walls drawn slightly thinner) |
| `../icon.svg`, `../icon.png` | plugin / app icon: reversed mark on an Ink tile |
| `export/` | one-colour black, white and amber versions, PNGs, favicon and web icon set |

All files are outlines (no live text, no effects). `build_logo.py` regenerates every master
from the construction rules.

## 2. Construction

- 256-unit grid. Set square: apex angle 90°, legs at 45°, height 106, wall 24
  (horizontal wall 22 — horizontals are drawn ~8 % thinner so they look equal).
- Opening: the outer triangle offset inward by the wall, corners softened by a 10-unit cut.
- Line: 14 units wide, 84 long, centred under the base.
- Wordmark: `draftsman` in JetBrains Mono Medium, outlined, tracking −20/1000. In the
  horizontal lockup its x-height is 33 % of the mark's height and its baseline sits one
  wall below the set square's base, so the line hangs like a descender.

## 3. Clear space

Keep a clear zone of **1 × O** on all sides, where **O** is the height of the set square's
opening (≈ a quarter of the mark's height). The zone scales with the logo.

## 4. Minimum size

| Version | Screen | Print |
|---|---|---|
| Horizontal | 96 px wide | 25 mm wide |
| Stacked | 64 px wide | 18 mm wide |
| Symbol | 32 px (`draftsman-symbol.svg`) | 8 mm |
| Symbol, small cut | 16–24 px (`draftsman-symbol-small.svg`, favicons) | 5 mm |

## 5. Colour

| Name | Role | HEX | RGB | CMYK (approx.) | Pantone (nearest, verify) |
|---|---|---|---|---|---|
| Drafting Amber | the set square, accents | `#D96A00` | 217 106 0 | 0 51 100 15 | 1595 C |
| Drafting Ink | the line, wordmark, dark tiles | `#15181D` | 21 24 29 | 28 17 0 89 | Black 6 C |
| Drafting Paper | reversed line and wordmark, light backgrounds | `#FAF8F3` | 250 248 243 | 0 1 3 2 | — |

Contrast: Amber on white 3.5 : 1, Amber on Ink 5.1 : 1 (both pass 3 : 1 for graphics).
Amber is not a text colour on white; use Ink for text.

**Approved pairs:** full colour on white or Paper · reversed (Amber + Paper) on Ink ·
Amber one-colour on white · black on white · white on Ink or on Amber.
On photos, use the one-colour white or black version on a calm area, or put the symbol on
an Ink tile.

## 6. Typography

- Wordmark: JetBrains Mono Medium (SIL Open Font License 1.1), always used as the outlined
  artwork — never retyped.
- Product text next to the logo: JetBrains Mono for code and names, the platform's system
  sans-serif for prose.

## 7. Don'ts

Don't stretch, squash or rotate the mark (rotated 180° it becomes a funnel) · don't fill the
opening · don't thicken the line to the wall weight (it turns into a sign on a post) ·
don't recolour outside the palette or swap the two colours · don't add shadows, outlines,
gradients or glows · don't rearrange or resize the parts of a lockup · don't place the
full-colour version on Amber or on busy backgrounds without an Ink tile.

## 8. Notes

- Trademark clearance has not been checked; run a professional search before registering.
- Nearby marks in the category: Vercel (solid equilateral triangle) and Prisma (prism with an
  inner facet). Draftsman differs in angle (90° apex), the open rounded hole, the two-tone
  head and line, and the attached shaft — keep those features intact.
