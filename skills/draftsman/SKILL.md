---
name: draftsman
description: Draws UML class diagrams from Java, C#, Kotlin, TypeScript, Python or C++ source where every class and relation comes from a tree-sitter parser, never from guessing. Outputs Mermaid, a static SVG, or a single-file interactive HTML viewer. Use when the user asks for a class diagram, a structure/architecture diagram of classes, inheritance or dependency relationships between classes, or says things like "클래스 다이어그램", "구조 그려줘", "상속 관계 보여줘".
argument-hint: "[ClassName | path] [mermaid|svg|html] [members|public|no-members]"
---

# Draftsman

The parser measures, you draft. The scripts turn source into **ir.json** (facts); you
choose what to show; the renderer draws only facts. Paths below are relative to this
skill's directory.

## Hard rules

1. **No invented relations.** Every line in the diagram must come from ir.json. A relation
   you believe in that ir.json lacks may only go in a view's `inferred_edges`, with a
   `rationale`; it is drawn dotted and labelled «inferred».
2. **No hand-written diagrams.** If the output is wrong, change the flags or the view and
   draw again. If the facts are wrong, that is an extractor bug: tell the user.
3. **Report what you left out:** hidden types and members, and the unresolved references by
   reason: *ambiguous* and *unexplained* ones one by one, *outside* ones as a group.

Languages: Java, C#, Kotlin, TypeScript (incl. TSX), Python, C++. For anything else, say
it is not supported rather than drawing from reading the code.

## Draw

One command extracts, scopes, renders, checks the Mermaid syntax and reports:

```bash
python3 scripts/draw.py <path> [--focus Type] [--hops 1|2] [--format mermaid|svg|html]
```

stdout is the Mermaid text (svg/html: the report names the file); stderr is the report:
the repository's size, the scope drawn, what one more hop would add, what was hidden, the
unresolved references, the Mermaid check, and the `ir.json` to pass instead of `<path>`
when you draw again.

- Test directories are excluded; `--tests` keeps them. `--exclude GLOB` for generated code
  (`'**/Migrations/**'`, `'**/*.spec.ts'`, `'third_party/**'`), `--lang` in mixed
  repositories (a Kotlin app with Java tests).
- `--members all|public|none`, `--hide GLOB` (types `'*Dto'`, members `'*#get*'`,
  `'*#toString'`), `--relations extends,implements,association`, `-o FILE` for a file the
  user asked for.
- Java, TypeScript, Python: focus diagrams draw classes the focus's bodies name, or whose
  bodies name it; `--body none` drops them.
- Exit 2: a missing dependency; the message gives the install command
  (`references/setup.md` covers uv, sandboxes and Node). Never fall back to drawing by hand.
- Exit 3: more than `--max-types` (30) types; the report lists the options, with counts.

**Arguments** (`/draftsman:draftsman OrderService html`): a word that looks like a class
is `--focus`; a path is `<path>` (default: the current repository); `mermaid`, `svg`,
`html` set `--format`; `members`, `public`, `no-members` set `--members all|public|none`.

## Choose the scope

This is your judgement and it decides what the diagram covers; the report is there to
check it.

- Up to ~30 types: draw everything (no `--focus`).
- More: the class the user named as `--focus`. Without `--hops`, `draw.py` draws the
  widest neighbourhood within `--max-types`, two hops or one, and the report says what two
  would have drawn. If they named none, exit 3 lists the most connected types: ask which
  one to centre on, or offer `--format html` to explore.
- "Directly related" / "its neighbours" means `--hops 1`. When the user asked for that
  scope and exit 3 says it is larger than 30, raise `--max-types` to the count it gives
  (within any limit the user set, e.g. "at most 80 classes") rather than narrowing:
  `--relations` without `dependency` or `--body none` drops classes related only by use,
  which the user asked for. Narrow only if the user did not ask for a specific scope.
- The report's *one more hop adds* line shows what lies just outside; if the user's
  question needs some of it, draw again with other flags.
- A focus diagram draws nested types inside their outer type (`Connection.Request` is part
  of `Connection`'s box), so the users of a nested type are its neighbours.

Output: `mermaid` for docs, PRs and chat answers (default); `html` for "show me", "let me
explore", onboarding or more than ~50 classes; `svg` for an image to embed or put on a
slide. svg needs Node (`references/setup.md`).

## Editorial work: a view

Groups, notes, highlights, inferred edges or per-class member detail go in a view.json,
passed with `--view` (flags override its keys):

```json
{
  "title": "Order placement", "focus": "OrderService", "hops": 1,
  "members": {"*": "none", "OrderService": "all"},
  "hidden": ["*#get*", "com.shop.dto.*"],
  "groups": [{"name": "Payment", "members": ["PaymentGateway", "StripeGateway"]}],
  "notes": [{"target": "PaymentGateway", "text": "Single implementation"}],
  "highlights": [{"target": "Order", "reason": "bidirectional association"}],
  "inferred_edges": [{"from": "StripeGateway", "to": "StripeClient", "kind": "association",
                      "rationale": "field type from `import com.stripe.*`"}]
}
```

- `groups`: meaningful clusters (domain areas, layers), not just packages.
- `notes` / `highlights`: design smells you can point to *in the facts*: cycles, deep
  inheritance, god classes, interfaces with one implementor. In HTML they go in the side panel.
- `inferred_edges`: only to names in the report's unresolved references, with a rationale
  citing the import or naming evidence.
- `"externals": true` draws framework supertypes (Spring repositories);
  `"annotations": false` drops arrows to marker annotations (`@UnstableApi`).

Other keys (`nested`, `direction`, member globs) are in `references/view-schema.md`; read
it only when you need one.

## Answer

The Mermaid block (or the SVG/HTML path), then briefly: the scope (focus, hops, what was
hidden), your notes, and the unresolved references from the report.

## More

- `scripts/summary.py <ir.json> --focus Type` (overview, then the type's members and
  relations) or `--type Type`: detail the diagram does not show.
- `references/ir-schema.md` (ir.json fields and how each relation is derived),
  `references/lang-notes.md` (per-language behaviour; read only the section for the
  language), `references/query-protocol.md` (only when adding or fixing a language).
