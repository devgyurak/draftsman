# eShopOnWeb — C#

A reference ASP.NET Core application: MVC, Razor Pages, Blazor admin, a public API and EF Core.

| | |
|---|---|
| Repository | [github.com/dotnet-architecture/eShopOnWeb](https://github.com/dotnet-architecture/eShopOnWeb) |
| Commit | `4da8212117` (2025-01-13) |
| Extracted | `src/` (tests are under `tests/`) |

Measured on 2026-11-23 with Draftsman after 0.6.0 (at `97383bd`).

## Run

From any directory, with `DRAFTSMAN` pointing at `skills/draftsman/scripts` of this repository (see [the index](../README.md#re-running)):

```bash
git clone https://github.com/dotnet-architecture/eShopOnWeb eShopOnWeb && git -C eShopOnWeb checkout 4da8212117
cd eShopOnWeb
python3 "$DRAFTSMAN"/extract.py src --lang csharp -o ir.json
python3 "$DRAFTSMAN"/render.py ir.json view.json -o focus.mmd
"$DRAFTSMAN"/validate.sh focus.mmd
python3 "$DRAFTSMAN"/render.py ir.json view.json --format svg -o focus.svg
python3 "$DRAFTSMAN"/render.py ir.json view.json --format html -o viewer.html
```

`view.json`:

```json
{
  "focus": "BasketService",
  "hops": 1,
  "hidden": ["*#get*", "*#set*"]
}
```

## Result

`extract.py` prints:

```text
draftsman: 209 files, 208 types, relations: association 96, dependency 209, extends 34, implements 27, body dependency 206, 194 unresolved (1 ambiguous, 193 outside the sources), 0 diagnostics
```

| Files | Types | association | dependency | extends | implements | body dependency | Unresolved | Diagnostics |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 209 | 208 | 96 | 209 | 34 | 27 | 206 | 194 (1 ambiguous, 193 outside) | 0 |

Types by kind: 185 classes, 5 abstract classes, 16 interfaces, 1 record, 1 enum.

The Mermaid and SVG renders of the view draw 7 types and 7 relations (`BasketService` and its neighbours one hop away, `BasketWithItemsSpecification` and `ConfigureCoreServices` only through body relations), and the Mermaid file passes `validate.sh`. The HTML viewer carries all 208 types, as 204 boxes with 4 nested types folded into their outer types, and 371 relations (112 from bodies, shown around the class in focus) and opens on the same focus. No inferred edges.

## Unresolved

193 outside the sources, 1 ambiguous.

- 193 are library and framework types reached through `using` directives: ASP.NET Core (`PageModel`, `IActionResult`, `Controller`), EF Core (`DbContext`, `ModelBuilder`, `EntityTypeBuilder`), Identity (`UserManager`, `SignInManager`), MediatR, AutoMapper and Ardalis (`Specification`, `EndpointBaseAsync.WithRequest.WithActionResult`). Each hint names the namespaces it may come from (*may come from wildcard import Microsoft.EntityFrameworkCore.*, ...*); a wildcard import cannot tell which of them declares the name, so none is picked.
- `IEmailSender` in `RegisterModel` is ASP.NET Identity's (`using Microsoft.AspNetCore.Identity.UI.Services;`). The project declares an `IEmailSender` of its own, which is listed as a candidate and not picked: ambiguous.
- The Blazor components `List.razor.cs` names (`Create`, `Delete`, `Details`, `Edit`) are declared in `.razor` files, which are not extracted: Draftsman takes them for types the build generates, in the namespace their folder gives, and they are not unresolved.
- 78 distinct names in all; `PageModel` (12) and `IActionResult` (10) are the most frequent.

## What it covers

- SDK implicit usings and `global using`s are imports of every file of their `.csproj`.
- A record, `0..1` associations from nullable types, and generic repositories (`IRepository<T>`, the most connected type).
- The only external supertypes are `System.Attribute`, `System.Exception` and `System.IDisposable`; framework base classes are unresolved, see above.
- Bodies: 206 dependencies from names in method bodies (`new CatalogItem(...)`, `new BasketWithItemsSpecification(...)`, `IRepository<Basket>` in a local's type), between 180 pairs of types; no declaration relates 114 of those pairs in that direction. All 251 places they are drawn from match what Roslyn resolves there (`bench/roslyn_oracle`: the 10 projects of `eShopOnWeb.sln` compiled with the .NET 8 SDK as C# 12, Debug, 0 compile errors, 793 names read in bodies).
- Attributes: `[DbContext(typeof(X))]` on EF migrations, the project's `[Endpoint]` (`EndpointAttribute`) and `[Authorize(Roles = Constants.Roles.ADMINISTRATORS)]`; ASP.NET's `[Route]` is not the project's static class `Route`.
