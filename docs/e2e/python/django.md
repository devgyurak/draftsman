# Django — Python

A web framework: ORM, forms, templates, admin, many contrib apps. Most of the code has no type annotations.

| | |
|---|---|
| Repository | [github.com/django/django](https://github.com/django/django) |
| Commit | `d3954c9813` (2026-11-16) |
| Extracted | the `django/` package without the contrib apps' generated `migrations/` (tests are under `tests/`) |

Measured on 2026-11-26 with Draftsman 0.11.0 (at `b631f56`; 0.11.0 extracts the same `ir.json`). In 0.11.0 (#9) declarations name more: a decorator that is a class's attribute depends on the class (83 lookups registered with `@...register_lookup`), and a base made by a call depends on the classes it names (2): 85 declared relations added; the body relations are the same. 0.10.0's note: a name bound twice draws nothing in a declaration either: four bases `Transform` lose their `extends` (below).

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
draftsman: 879 files, 1964 types, relations: association 4, dependency 98, extends 1844, body dependency 3203, 4 unresolved (4 unexplained), 0 diagnostics
```

| Files | Types | association | dependency | extends | implements | body dependency | Unresolved | Diagnostics |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 879 | 1964 | 4 | 98 | 1844 | 0 | 3203 | 4 | 0 |

Types by kind: 1949 classes, 1 abstract class, 14 enums.

The Mermaid and SVG renders of the view draw 73 types and 80 relations (`Field`, its base and its subclasses, and 26 types only through the 26 body relations that touch `Field`), and the Mermaid file passes `validate.sh`. The HTML viewer carries all 1964 types, as 1936 boxes with 28 nested types folded into their outer types, and 4180 relations (2428 from bodies, shown around the class in focus) and opens on the same focus; the other 191 declared relations point at external types (`Exception`, `list`, `io.IOBase`, ...). No inferred edges.

## Unresolved

4, one name: the bases `Transform` of `GeometryType`, `IsEmpty`, `IsValid` and
`NumDimensions` in `contrib/gis/db/models/functions.py`. The module imports `Transform` from
`django.db.models` and declares a class `Transform` further down, so the name is bound twice
(*bound more than once where it is written: which binding it is depends on what ran*);
mypy, pyright and ty disagree there.

## What it covers

- An unannotated code base: the declarations give few types, so nearly every declared relation is `extends`. Of the 102 others, 5 come from the annotated `django.tasks` dataclasses and one annotated parameter in `listurls`, 95 from decorators and 2 from bases made by calls (below). Bodies give the rest (below).
- Multiple inheritance: 231 classes have several bases (mixins; `BaseDateDetailView` has 5).
- Package re-exports: `from django.db.models import Field` reaches `django.db.models.fields.Field` through `from django.db.models.fields import *` in the package's `__init__.py`. Ids carry the `django.` prefix, since `django/` is a package.
- External bases from the standard library and from drivers keep their module path (`argparse.ArgumentParser`, `ctypes.Structure`, `psycopg.adapt.Dumper`).
- Decorators: `@admin.register(User)` makes the admin class depend on the model, `@classproperty` and `@deprecate_posargs(RemovedInDjango2028Warning, ...)` name project classes, and a class's attribute is that class (`@Field.register_lookup` 17, `@BaseSpatialField.register_lookup` 33, `@RangeField.register_lookup` 12, ...). A base made by a call (`class Manager(BaseManager.from_queryset(QuerySet))`) is no supertype: the class depends on the classes the call names.
- Bodies: 3203 dependencies from names in method bodies and class-level values (`models.CharField(...)`, `objects = Manager()`, `from django.db.models import Q` in a method), between 2476 pairs of types; no declaration relates 2430 of those pairs in that direction. Where mypy, pyright and ty name the same declaration (`bench/py_oracle`) they match it, at all 4065 places they are drawn from. ty abstains at 8 places, giving no definition where it marks the code unreachable: among them `BaseModelAdmin`'s `formfield_for_foreignkey` and `formfield_for_manytomany`, under `elif db_field.name in self.raw_id_fields:` (and `filter_vertical`, `filter_horizontal`), which ty takes for never true since the class sets them to `()`; mypy and pyright agree there. The three checkers differ at 15 places (a submodule reached through a package that never imported it, `admin.helpers.AdminForm`; a module that rebinds a class's name, `EndToken = EndToken()`; a class beside an import of its name), and the extractor draws nothing at any of them. Names a body binds hide a class of their name (`ChangeList = self.get_changelist(request)` in `ModelAdmin`, 30 places).
- Declared relations changed in one place: `LimitedStream` and `FakePayload` extend `io.IOBase`, not `django.contrib.gis.geos.prototypes.io.IOBase` (an import's suffix match no longer drops a package).
