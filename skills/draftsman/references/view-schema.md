# view.json

Every key is optional; `{}` (or no view file) draws everything. Unknown keys are errors.
Wherever a type is referenced you may use its full id (`com.shop.order.Order`), its
simple name (`Order`) or its nested display name (`Order.Status`) — as long as it is
unambiguous. A name that matches nothing in ir.json is an error.

| key | type | default | meaning |
|---|---|---|---|
| `title` | string | – | diagram title |
| `focus` | type | `null` | draw only types within `hops` relations of this type |
| `hops` | int ≥ 0 | `2` | radius around `focus`; relations count in both directions |
| `relations` | list | all four | relation kinds to draw *and* to traverse for focus: `extends`, `implements`, `association`, `dependency` |
| `hidden` | list of patterns | `[]` | types or members to leave out (see below) |
| `members` | `"all"` \| `"public"` \| `"none"`, or `{type glob: level}` | `"all"` | member detail (see below); enum constants always shown unless `"none"` |
| `externals` | bool | `false` | draw external supertypes (e.g. `CrudRepository`) as `<<external>>` boxes |
| `groups` | `[{name, members: [type]}]` | `[]` | clusters (Mermaid `namespace`); a type may be in one group only |
| `highlights` | `[{target, reason}]` | `[]` | red outline; `reason` is kept as a comment |
| `notes` | `[{target, text}]` | `[]` | note attached to a type |
| `inferred_edges` | `[{from, to, kind, rationale}]` | `[]` | relations the parser could not establish; drawn dotted and labelled «inferred» |
| `direction` | `TB` \| `BT` \| `LR` \| `RL` | – | layout direction |
| `output` | `mermaid` \| `svg` \| `html` | `mermaid` | see "Outputs" below; `render.py --format` overrides it |

## hidden patterns

Shell-style globs (`*`, `?`, `[...]`), case-sensitive.

- `TypeGlob` hides types: matched against the id, the simple name and the display name.
  `com.shop.dto.*`, `*Test`, `Abstract*`. Relations touching hidden types disappear, and
  focus traversal does not pass through them.
- `TypeGlob#MemberGlob` hides members: `*#get*`, `*#toString`, `Order#lines`.
  An empty side means `*` (`#equals` hides `equals` everywhere). Relations produced by a
  hidden member go too: hiding `Order#lines` removes the `lines` association, and a
  dependency disappears once every member that produced it is hidden.

## members

A single level applies to every class. An object sets it per class: keys are type
globs matched like `hidden` (id, simple name or display name), `"*"` is every class,
and when several keys match, the **last** one wins — so put `"*"` first.

```json
"members": {"*": "none", "*Service": "public", "OrderService": "all"}
```

This only changes what is written inside the boxes; relations stay. A key that matches
no class in the diagram is a warning. `render.py --members all|public|none` overrides the
view's setting for one render, e.g. to export the same view with and without members.

## inferred_edges

- `from` and `to` must each be a type in ir.json, an external id, or a `raw_type` from
  ir.json's `unresolved` list. Anything else is rejected.
- `kind` is one of the four relation kinds; `rationale` is required and should cite
  evidence (an import, a naming convention, a framework annotation).
- An inferred edge identical to an existing fact is dropped with a warning.
- With `focus`, an inferred edge must touch a type inside the focus area; it pulls its
  other endpoint into the diagram.

## Outputs

- **mermaid** — `classDiagram` text. Composition (C++ owned values) is `*--`, inferred
  edges are `..>` labelled «inferred», notes become `note for`, highlights a red outline.
- **svg** — standalone drawing sheet laid out by ELK (layered, orthogonal edges), light/dark
  aware: a frame and a title block (title, classes, relations, scope), UML boxes with a kind
  badge, notes as note boxes, groups as dashed zones, highlights and cycles in red, inferred
  edges as blue dotted construction lines.
- **html** — one self-contained file (ELK inlined when installed). It contains *every*
  class the view allows; `focus`/`hops` only set where it starts. Readers can search,
  change focus and hops, toggle dependencies/inferred edges/cycle highlighting, expand
  members, and read your notes, highlights, cycles and unresolved references in a side
  panel.

## Example

```json
{
  "title": "Order placement",
  "focus": "OrderService",
  "hops": 2,
  "hidden": ["*#get*", "*#toString", "com.shop.common.Auditable"],
  "members": "all",
  "externals": true,
  "groups": [
    {"name": "Ordering", "members": ["Order", "OrderLine", "OrderRepository"]},
    {"name": "Payment", "members": ["PaymentGateway", "StripeGateway", "Receipt"]}
  ],
  "highlights": [{"target": "Order", "reason": "bidirectional association with Customer"}],
  "notes": [{"target": "PaymentGateway", "text": "Single implementation (StripeGateway)"}],
  "inferred_edges": [
    {"from": "StripeGateway", "to": "StripeClient", "kind": "association",
     "rationale": "field type comes from `import com.stripe.*`"}
  ]
}
```
