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
| `nested` | `"fold"` \| `"boxes"` | `"fold"` with `focus`, else `"boxes"` | nested types drawn inside their outer type, or as boxes of their own (see below) |
| `relations` | list | all four | relation kinds to draw *and* to traverse for focus: `extends`, `implements`, `association`, `dependency` |
| `hidden` | list of patterns | `[]` | types or members to leave out (see below) |
| `members` | `"all"` \| `"public"` \| `"none"`, or `{type glob: level}` | `"all"` | member detail (see below); enum constants always shown unless `"none"` |
| `externals` | bool | `false` | draw external supertypes (e.g. `CrudRepository`) as `<<external>>` boxes |
| `annotations` | bool | `true` | draw the dependencies annotations create (`via` `@Name`, see below) |
| `body` | `"focus"` \| `"all"` \| `"none"` | `"focus"` with `focus` or `"output": "html"`, else `"none"` | draw the dependencies names in bodies create (`evidence` `"body"`, see below) |
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

## nested

A nested type (`Connection.Request`, `Order.Status`) is related to the rest of the code on
its own: `CookieUtil` uses `Connection.Request`, not `Connection`. Nesting is no relation,
so a focus on `Connection` would not reach `CookieUtil` if nested types were boxes of their
own.

- `"fold"` (the default with `focus`): every nested type is drawn as its outermost type, in
  the neighbourhood and in the drawing. `CookieUtil → Connection.Request` is one arrow
  `CookieUtil → Connection`; a relation between two types that fold onto the same box
  (`Order.status: Order.Status`) draws nothing. Inheritance is the exception: that
  `Element.TextAccumulator` implements `NodeVisitor` does not make `Element` one, so a
  folded `extends`/`implements` is drawn as a dependency labelled with whose it is
  (`Element ..> NodeVisitor : TextAccumulator implements`), unless the outer types
  themselves inherit. The fact behind a folded arrow is kept:
  its source location still points into the nested type, an association's label names it
  (`Response.cookies`), and the HTML viewer lists the nested types of each box and says
  which nested type a relation really goes to. A focus on a nested type keeps its own
  box, and its own nested types fold into it.
- `"boxes"`: today's drawing, one box per nested type. With `focus`, the neighbourhood
  starts from the focus *and* its nested types, so the same types are reached; the
  diagram is larger (jsoup's `Connection` at one hop: 20 boxes, against 11 folded).

Without `focus` nested types stay boxes unless `"nested": "fold"` is set: a whole-repository
view is where a reader looks for that structure. Notes, highlights and groups on a folded
type go to its box, with a warning for notes and highlights.

## annotations

An annotation whose type is a project type, and every project type named in an
annotation's arguments (`@Import(Hints.class)`, `[JsonConverter(typeof(Conv))]`,
`@Module({imports: [UsersModule]})`), is a dependency of the annotated type, `via` the
annotation (`@Import`). Marker annotations (`@UnstableApi`, `@KtorDsl`) can tie many types
to one, so in the focus neighbourhood an annotation leads only from the annotated type to
what it names, never back: a class marked `@UnstableApi` brings in `UnstableApi`, not the
other classes marked with it (133 types in Netty, nested ones counted on their own). A
focus on the annotation type itself does show the types that carry it, one hop away:
`UnstableApi` at one hop draws 124 boxes with nested types folded, 134 as `"boxes"`. A pair connected by a signature too is followed both
ways, as usual. `"annotations": false` leaves out the dependencies that only annotations
create altogether.

## body

A name written in a body (`new Foo()`, `Foo.bar()`, a cast, a local variable's type) is a
dependency marked `evidence: "body"` (Java, TypeScript and Python, see `ir-schema.md`). Bodies name
far more types than declarations do, so they draw less by default:

- `"focus"` (the default with `focus`): only the body relations that touch the focus (or
  a nested type folded into it), both ways. The class at the other end is drawn, but the
  neighbourhood does not go on from it: a helper the focus calls brings in itself, not
  everything the helper is related to.
- `"all"`: also the body relations between any two types the diagram draws. They still
  bring in no type beyond the focus's.
- `"none"` (the default without `focus`, but in html): none.

Between two types, a signature's dependency is drawn rather than an annotation's, and
either rather than a body's. A body relation is dotted more finely than a signature's and,
in Mermaid, labelled `body`. The HTML viewer gets them all unless `"none"`, with or without
`focus`, and shows them as its reader moves the focus (none before one is picked); its
Bodies button hides them. Reference cycles are found on declared relations only, as the
most connected types are counted.

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
  class the view allows; `focus`/`hops` only set where it starts. With `focus`, nested
  types are folded as in the focus diagram; search still finds them, in their box. Readers can search,
  change focus and hops, toggle dependencies/body relations/inferred edges/cycle highlighting, expand
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
