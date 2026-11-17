# Scoring rubric

Committed before any measured run. A rule changed after the pilot is recorded in the
change log of [README.md](README.md); no rule changes after the measured runs start.

## What is scored

Every run is expected to answer with one Mermaid `classDiagram` block.

- **Failed run**: no Mermaid block, a block that does not parse, the budget cap or the turn
  limit reached, or a question back instead of a diagram. Failed runs are counted and
  reported per arm. They have no edges, so they are left out of the edge ratios and count
  as recall 0 in the main analysis.
- **Skill not invoked** (arms B and C, read from the transcript): the main analysis
  includes every run regardless; the runs where the skill was invoked are reported
  separately as a secondary result.
- **Inferred edges**: Draftsman draws relations it did not find in the parser output as
  dotted `<<inferred>>` edges. They are stripped before labelling and labelled like any
  other edge. The headline counts them; a secondary figure leaves them out.

## Normalising a diagram

- Class names: generics (`Name~T~`), stereotypes and namespaces are stripped to the simple
  name; the label and member lines are ignored.
- Edges, by Mermaid arrow:

  | Arrow | Kind | Direction |
  |---|---|---|
  | `<\|--`, `--\|>` | inheritance (extends) | towards the triangle |
  | `<\|..`, `..\|>` | inheritance (implements) | towards the triangle |
  | `-->`, `<--`, `--`, `*--`, `--*`, `o--`, `--o` | association | towards the arrowhead; the whole for `*`/`o`; unordered for `--` |
  | `..>`, `<..`, `..` | dependency | towards the arrowhead; unordered for `..` |

- Two edges between the same pair with the same kind and direction are one edge.

## Names

- **A class that does not exist**: its simple name appears nowhere in the checkout (any
  file, tests included). JDK and framework types appear in imports, so they exist.
- **Same simple name, several declarations**: resolve by the declaration if there is one;
  otherwise by the imports and package of the focus class's file (T2) or of the other end
  of the edge (T1). An edge still ambiguous after that is **undecidable**: left out of
  both numerator and denominator, and counted.

## Top-level types

Diagrams differ in whether they draw nested types, so the **main scoring is on top-level
types**: both ends of every drawn edge and every denominator row are collapsed to the
outermost type that contains them (`HttpConnection.Request → Connection.Request` becomes
`HttpConnection → Connection`), and a pair that collapses onto itself is dropped. A
collapsed pair keeps the strongest evidence of the rows it merges; it is inheritance only
if the two top-level types themselves inherit. Results on nested types as drawn are a
secondary figure.

## Edge labels

Each distinct edge gets the **first** label that applies, checked in this order:

1. **Unsupported** — the source has no relation between the two types in either
   direction, neither directly nor through a supertype: no supertype, field, signature,
   generic argument, annotation or method-body use of one type in the other's
   declaration. A chain through some other type (A uses X, X uses B) is no relation
   between A and B.
2. **Indirect** — the relation exists only through a supertype: indirect inheritance
   drawn as direct (`A → B → C`, drawn `A → C`), or a use through an inherited member
   (A uses B only through a field of its superclass).
3. **Wrong kind or direction** — a direct relation exists, but the edge contradicts it:
   - drawn as inheritance where there is none, or not as inheritance where there is one;
   - drawn in the reverse direction of every relation that exists.

   Association versus dependency (a field drawn as `..>`, a parameter drawn as `-->`) is
   **not** an error: the distinction is not judged.
4. **Body only** — the only evidence is inside method bodies or initialisers: local
   variables, `new`, static calls, casts, `instanceof`, `catch`, lambdas.
5. **Declared** — the evidence is in a declaration: supertype clause, field type,
   parameter, return or `throws` type, generic argument, annotation.

Boundary cases, decided in advance:

| Case | Label |
|---|---|
| Indirect inheritance drawn as direct | indirect |
| A use through an inherited member | indirect |
| A name that appears only in comments, Javadoc (`{@link}`, `@see`) or an unused import | not a relation; if there is no other evidence, unsupported |
| A generic argument (`List<Pet> pets`) | declared |
| A nested type (`Owner.Builder`) | its own type, not its outer class |

Decided while writing the recall denominators, before any output was seen:

| Case | Rule |
|---|---|
| A qualified nested name (`Connection.Request` in `CookieUtil`) | recorded as a relation to the nested type; the main scoring collapses it (see *Top-level types* above) |
| A use that never names the type (a call on a field of that type, a nested class using its outer class's field) | not in the denominators; a drawn edge resting on it is labelled *body only* with the flag *unnamed*, not *unsupported*, and the flagged labels are counted |
| Anonymous classes and enum-constant bodies | belong to the enclosing named type |
| A class literal in an annotation argument | declared |
| A generic argument in a supertype clause (`implements ChunkedInput<ByteBuf>`) | declared, kind *other*: an edge drawn as inheritance to `ByteBuf` is wrong kind |
| A focus class naming its own nested type | a relation at the nested level; it collapses onto the focus and drops out of the main scoring |
| An override whose signature names the type | declared, not indirect |
| "Classes" in T1 | every type: classes, interfaces, enums, records |

Every label carries the `file:line` it rests on (none for unsupported).

### Two levels, and nesting edges

Settled before labelling, after the measured runs and before any edge was labelled or
looked at by arm:

- Each edge is labelled **twice**:
  - **top level** (`label_top`, the main scoring): both ends collapsed to their top-level
    types, and evidence collapsed the same way, so a use inside a nested type counts for
    its outer type (`HttpConnection → X` is supported if only `HttpConnection.Response`
    uses X). An edge whose ends collapse onto one type is labelled **self** and left out.
  - **as drawn** (`label_drawn`, secondary): the names as the diagram gives them, nested
    types as types of their own.
- A **nesting** edge (`Outer +-- Inner`, drawn from an outer type to its nested type) is
  *self* at the top level. As drawn, it is *declared* when Inner is declared inside Outer
  (cite that declaration); *wrong kind or direction* when reversed; otherwise it is judged
  like any edge that is not inheritance.

## Labelling procedure

1. Pool the edges of all runs, deduplicate, shuffle, and drop the arm and run: the
   labeller sees a pair of names, a kind and a direction only.
2. A **separate session** that did not run the benchmark gives the first labels, at both
   levels, each with its `file:line`.
3. `check_citations.py` checks every *declared* and *body only* label at both levels: the cited line must
   contain the other type's simple name, inside the cited type's file. A label that fails
   goes to human review; an *unnamed* label always does.
4. **Human review**: every *unsupported*, *indirect* and *wrong kind or direction* label at
   either level, every label
   that failed step 3, and a random 20% of the rest (fixed seed). `review.csv` lists, per
   edge, the production files in which both simple names appear (grep), so an empty list
   confirms *unsupported* at once.

## Measures

T2 compares **edges incident to the focus class**; all edges are a secondary figure. The
headline uses the top-level labels; the as-drawn labels give the secondary figure.

- **Unsupported (headline)**: count and share of incident edges labelled unsupported.
- **Indirect** and **wrong kind or direction**: count and share each, reported separately,
  never added to the headline.
- **Classes that do not exist**: count per diagram.
- **Recall**, split into **outgoing** (types the focus uses) and **incoming** (types that
  use the focus), each against two denominators:
  - declared relations;
  - declared plus body-only relations.

  A direction whose denominator is empty (a focus class that uses no project type, or
  that no project type uses) has no recall: it is reported as *n/a*, left out of the
  averages, and the number of such cases is given.

### Recall denominators

Written by hand from the source, with `file:line`, and committed **before the measured
runs** (`labels/denominators/`): for each T2 focus class its outgoing and incoming
relations, and for T1 every relation among the classes of spring-petclinic. Only types
declared in the production sources count, nested types as types of their own; JDK and
framework types, tests and examples are not part of it. Relations through a supertype
(*indirect*) are not part of it either.

A real relation found while labelling that the denominator missed is added, and the
number of such additions is reported per repository.
