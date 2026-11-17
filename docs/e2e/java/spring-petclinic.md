# spring-petclinic — Java

Spring's sample application: JPA entities, Spring Data repositories, MVC controllers.

| | |
|---|---|
| Repository | [github.com/spring-projects/spring-petclinic](https://github.com/spring-projects/spring-petclinic) |
| Commit | `500158f732` (2026-09-29) |
| Extracted | `src/main` (tests are under `src/test`) |

Measured on 2026-11-17 with Draftsman `6c455fc`.

## Run

From any directory, with `DRAFTSMAN` pointing at `skills/draftsman/scripts` of this repository (see [the index](../README.md#re-running)):

```bash
git clone https://github.com/spring-projects/spring-petclinic spring-petclinic && git -C spring-petclinic checkout 500158f732
cd spring-petclinic
python3 "$DRAFTSMAN"/extract.py src/main --lang java -o ir.json
python3 "$DRAFTSMAN"/render.py ir.json view.json -o focus.mmd
"$DRAFTSMAN"/validate.sh focus.mmd
python3 "$DRAFTSMAN"/render.py ir.json view.json --format svg -o focus.svg
python3 "$DRAFTSMAN"/render.py ir.json view.json --format html -o viewer.html
```

`view.json`:

```json
{
  "focus": "Owner",
  "hops": 1,
  "hidden": ["*#get*", "*#set*"]
}
```

## Result

`extract.py` prints:

```text
draftsman: 30 files, 25 types, relations: association 11, dependency 46, extends 11, implements 5, 0 unresolved, 0 diagnostics
```

| Files | Types | association | dependency | extends | implements | Unresolved | Diagnostics |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 30 | 25 | 11 | 46 | 11 | 5 | 0 | 0 |

Types by kind: 22 classes, 3 interfaces.

The Mermaid and SVG renders of the view draw 8 types and 13 relations (`Owner` and its neighbours one hop away), and the Mermaid file passes `validate.sh`. The HTML viewer carries all 25 types and 32 relations and opens on the same focus. No inferred edges.

## Unresolved

None.

## What it covers

- An entity hierarchy over two levels: `Owner extends Person extends BaseEntity`, `Pet extends NamedEntity extends BaseEntity`; `BaseEntity implements java.io.Serializable`.
- Spring Data repositories whose supertype is outside the sources: `OwnerRepository` and `PetTypeRepository` extend `JpaRepository`, `VetRepository` extends `Repository`, all with qualified external ids.
- Collection fields: 4 of the 11 associations are many (`*`), e.g. an owner's pets.
