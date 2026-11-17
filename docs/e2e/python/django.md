# Django — Python

A web framework: ORM, forms, templates, admin, many contrib apps. Most of the code has no type annotations.

| | |
|---|---|
| Repository | [github.com/django/django](https://github.com/django/django) |
| Commit | `d3954c9813` (2026-11-16) |
| Extracted | the `django/` package without the contrib apps' generated `migrations/` (tests are under `tests/`) |

Measured on 2026-11-17 with Draftsman `6c455fc`.

## Run

From any directory, with `DRAFTSMAN` pointing at `skills/draftsman/scripts` of this repository (see [the index](../README.md#re-running)):

```bash
git clone https://github.com/django/django django && git -C django checkout d3954c9813
cd django
python3 "$DRAFTSMAN"/extract.py django --exclude 'contrib/*/migrations/**' -o ir.json
python3 "$DRAFTSMAN"/render.py ir.json view.json -o focus.mmd
"$DRAFTSMAN"/validate.sh focus.mmd
python3 "$DRAFTSMAN"/render.py ir.json view.json --format svg -o focus.svg
python3 "$DRAFTSMAN"/render.py ir.json view.json --format html -o viewer.html
```

`view.json` (the full id: forms and GIS also declare a `Field`):

```json
{
  "focus": "django.db.models.fields.Field",
  "hops": 1
}
```

## Result

`extract.py` prints:

```text
draftsman: 879 files, 1964 types, relations: association 4, dependency 1, extends 1848, 0 unresolved, 0 diagnostics
```

| Files | Types | association | dependency | extends | implements | Unresolved | Diagnostics |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 879 | 1964 | 4 | 1 | 1848 | 0 | 0 | 0 |

Types by kind: 1949 classes, 1 abstract class, 14 enums.

The Mermaid and SVG renders of the view draw 30 types and 29 relations (`Field`, its base and its subclasses), and the Mermaid file passes `validate.sh`. The HTML viewer carries all 1964 types and 1664 relations and opens on the same focus; the other 189 relations point at external types (`Exception`, `list`, ...). No inferred edges.

## Unresolved

None.

## What it covers

- An unannotated code base: Draftsman reads declared types only, so nearly every relation is `extends`. The 5 others come from the annotated `django.tasks` dataclasses and one annotated parameter in `listurls`.
- Multiple inheritance: 231 classes have several bases (mixins; `BaseDateDetailView` has 5).
- Package re-exports: `from django.db.models import Field` reaches `django.db.models.fields.Field` through `from django.db.models.fields import *` in the package's `__init__.py`. Ids carry the `django.` prefix, since `django/` is a package.
- External bases from the standard library and from drivers keep their module path (`argparse.ArgumentParser`, `ctypes.Structure`, `psycopg.adapt.Dumper`).
