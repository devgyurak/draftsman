# eShop — C#

The successor of eShopOnWeb: a .NET Aspire solution of microservices (catalog, basket, ordering, identity, webhooks), a Blazor web app and two .NET MAUI apps.

| | |
|---|---|
| Repository | [github.com/dotnet/eShop](https://github.com/dotnet/eShop) |
| Commit | `5e526931f7` (2026-11-16) |
| Extracted | `src/`: 19 projects and the shared `src/Shared` files (tests are under `tests/`) |

Measured on 2026-11-20 with Draftsman 0.3.0.

## Run

From any directory, with `DRAFTSMAN` pointing at `skills/draftsman/scripts` of this repository (see [the index](../README.md#re-running)):

```bash
git clone https://github.com/dotnet/eShop eShop && git -C eShop checkout 5e526931f7
cd eShop
python3 "$DRAFTSMAN"/extract.py src --lang csharp -o ir.json
python3 "$DRAFTSMAN"/render.py ir.json view.json -o focus.mmd
"$DRAFTSMAN"/validate.sh focus.mmd
python3 "$DRAFTSMAN"/render.py ir.json view.json --format svg -o focus.svg
python3 "$DRAFTSMAN"/render.py ir.json view.json --format html -o viewer.html
```

`view.json`:

```json
{
  "focus": "OrderingContext",
  "hops": 1
}
```

## Result

`extract.py` prints:

```text
draftsman: 497 files, 506 types, relations: association 221, dependency 590, extends 74, implements 74, 526 unresolved (7 ambiguous, 515 outside the sources, 4 unexplained), 0 diagnostics
```

| Files | Types | association | dependency | extends | implements | Unresolved | Diagnostics |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 497 | 506 | 221 | 590 | 74 | 74 | 526 (7 ambiguous, 515 outside, 4 unexplained) | 0 |

Types by kind: 367 classes, 6 abstract classes, 42 interfaces, 81 records, 10 enums.

The Mermaid and SVG renders of the view draw 20 types and 28 relations (`OrderingContext` and its neighbours one hop away; 5 of them are EF migrations that name it in `[DbContext(typeof(OrderingContext))]`), and the Mermaid file passes `validate.sh`. The HTML viewer carries all 506 types, as 491 boxes with 15 nested types folded into their outer types, and 646 relations and opens on the same focus. No inferred edges.

## Unresolved

526 references to 213 names: 515 outside the sources, 7 ambiguous (the build-time gRPC types below), 4 unexplained (the `HybridApp` names below without a hint).

- 335 are library and framework types of the services, reached through `using` directives: EF Core (`ModelBuilder` 18, `EntityTypeBuilder`, `Migration`), MediatR (`IMediator` 17, `IRequest`, `INotification`), ASP.NET Core and Identity (`Controller`, `IActionResult`, `UserManager`), Duende IdentityServer (`IEventService`, `IIdentityServerInteractionService`), Aspire hosting and RabbitMQ. Each hint names the namespaces it may come from; a wildcard import cannot tell which of them declares the name.
- 183 are in the two MAUI apps (`ClientApp` 165, `HybridApp` 18): MAUI and CommunityToolkit types (`ContentPage`, `BindableProperty`, `MauiApp`). Two gaps show here:
  - 56 are alias-qualified names in the committed protobuf code of `ClientApp` (`pb::CodedInputStream`, `pbr::MessageDescriptor`, with `using pb = global::Google.Protobuf;`). Draftsman does not read a name through its `using` alias yet.
  - 4 in `HybridApp` (`Application`, `Window`, `IActivationState`, `ContentPage`) have no hint: the project uses `Microsoft.NET.Sdk.Razor` with `<UseMaui>`, whose implicit usings Draftsman does not know.
- 1 is an attribute argument: `[JsonConverter(typeof(JsonStringEnumConverter<OrderStatus>))]` on `OrderStatus`, from `System.Text.Json.Serialization`, which the file imports with `using`.
- 7 are gRPC types generated at build time from `Basket.API/Proto/basket.proto` (`Basket.BasketBase`, `GetBasketRequest`, `CustomerBasketResponse`, ...), used by `Basket.API` and `WebApp`. They are not in the sources. `ClientApp` commits its own generated copy in another namespace (`eShop.ClientApp.BasketGrpcClient`); it is listed as a candidate and not picked.

## What it covers

- A multi-project solution: 19 `.csproj` with different SDKs (`Microsoft.NET.Sdk.Web`, `Aspire.AppHost.Sdk`, MAUI), each with its own implicit usings and `global using`s; `src/Shared` files linked into several projects with `<Compile Include>`.
- 81 records: integration events, commands and DTOs (`OrderStartedIntegrationEvent`, `CreateOrderRequest`).
- The DDD aggregates of `Ordering.Domain` and their EF Core context (`OrderingContext`, the view's focus).
- Attributes: 35 dependencies, from `[JsonSerializable(typeof(X))]` source-generation contexts, `[DbContext(typeof(X))]` on EF migrations and the project's `[SecurityHeaders]`.
