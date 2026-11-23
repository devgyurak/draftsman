# eShop — C#

The successor of eShopOnWeb: a .NET Aspire solution of microservices (catalog, basket, ordering, identity, webhooks), a Blazor web app and two .NET MAUI apps.

| | |
|---|---|
| Repository | [github.com/dotnet/eShop](https://github.com/dotnet/eShop) |
| Commit | `5e526931f7` (2026-11-16) |
| Extracted | `src/`: 19 projects and the shared `src/Shared` files (tests are under `tests/`) |

Measured on 2026-11-23 with Draftsman after 0.6.0 (at `1dab025`).

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
draftsman: 497 files, 506 types, relations: association 221, dependency 590, extends 75, implements 74, body dependency 442, 513 unresolved (1 ambiguous, 508 outside the sources, 4 unexplained), 0 diagnostics
```

| Files | Types | association | dependency | extends | implements | body dependency | Unresolved | Diagnostics |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 497 | 506 | 221 | 590 | 75 | 74 | 442 | 513 (1 ambiguous, 508 outside, 4 unexplained) | 0 |

Types by kind: 367 classes, 6 abstract classes, 42 interfaces, 81 records, 10 enums.

The Mermaid and SVG renders of the view draw 27 types and 39 relations (`OrderingContext` and its neighbours one hop away; 5 of them are EF migrations that name it in `[DbContext(typeof(OrderingContext))]`, 7 come only through body relations: the six `*EntityTypeConfiguration` classes `OnModelCreating` applies and `Extensions`, the four global `Extensions` classes of four projects that ir.json merges into one id), and the Mermaid file passes `validate.sh`. The HTML viewer carries all 506 types, as 491 boxes with 15 nested types folded into their outer types, and 933 relations (287 from bodies, shown around the class in focus) and opens on the same focus. No inferred edges.

## Unresolved

513 references to 207 names: 508 outside the sources, 1 ambiguous (a build-time gRPC type below), 4 unexplained (the `HybridApp` names below without a hint).

- 328 are library and framework types of the services, reached through `using` directives: EF Core (`ModelBuilder` 18, `EntityTypeBuilder`, `Migration`), MediatR (`IMediator` 17, `IRequest`, `INotification`), ASP.NET Core and Identity (`Controller`, `IActionResult`, `UserManager`), Duende IdentityServer (`IEventService`, `IIdentityServerInteractionService`), Aspire hosting and RabbitMQ. Each hint names the namespaces it may come from; a wildcard import cannot tell which of them declares the name.
- 183 are in the two MAUI apps (`ClientApp` 165, `HybridApp` 18): MAUI and CommunityToolkit types (`ContentPage`, `BindableProperty`, `MauiApp`). Two gaps show here:
  - 56 are alias-qualified names in the committed protobuf code of `ClientApp` (`pb::CodedInputStream`, `pbr::MessageDescriptor`, with `using pb = global::Google.Protobuf;`). Draftsman does not read a name through its `using` alias yet.
  - 4 in `HybridApp` (`Application`, `Window`, `IActivationState`, `ContentPage`) have no hint: the project uses `Microsoft.NET.Sdk.Razor` with `<UseMaui>`, whose implicit usings Draftsman does not know.
- 1 is an attribute argument: `[JsonConverter(typeof(JsonStringEnumConverter<OrderStatus>))]` on `OrderStatus`, from `System.Text.Json.Serialization`, which the file imports with `using`.
- gRPC types generated at build time from `Basket.API/Proto/basket.proto` (`Basket.BasketBase`, `GetBasketRequest`, `CustomerBasketResponse`, ...) are not in the sources. Draftsman reads the `<Protobuf Include>` items and the .proto, so in `Basket.API`'s `eShop.Basket.API.Grpc`, the namespace around `BasketService`, they are external types (`BasketService` extends `eShop.Basket.API.Grpc.Basket.BasketBase`). `WebApp` reaches them through `using eShop.Basket.API.Grpc;`, which they are not looked up in: its 1 `CustomerBasketResponse` is ambiguous, with `ClientApp`'s committed copy (`eShop.ClientApp.BasketGrpcClient`) as a candidate, not picked.

## What it covers

- A multi-project solution: 19 `.csproj` with different SDKs (`Microsoft.NET.Sdk.Web`, `Aspire.AppHost.Sdk`, MAUI), each with its own implicit usings and `global using`s; `src/Shared` files linked into several projects with `<Compile Include>`.
- 81 records: integration events, commands and DTOs (`OrderStartedIntegrationEvent`, `CreateOrderRequest`).
- The DDD aggregates of `Ordering.Domain` and their EF Core context (`OrderingContext`, the view's focus).
- Bodies: 442 dependencies from names in method bodies (`new CatalogItem(...)`, `OrderStatus.Submitted`, `UriHelper.CombineUri(...)`, `throw new OrderingDomainException(...)`), between 378 pairs of types; no declaration relates 295 of those pairs in that direction. All 560 places they are drawn from match what Roslyn resolves there (`bench/roslyn_oracle`: `eShop.Web.slnf`'s 25 projects built and compiled with the .NET 11 SDK as C# 15, Debug, and the MAUI apps for plain `net11.0`, `HybridApp` given it; one compile error, `HybridApp`'s missing entry point; 2268 names read in bodies; the 23 in the `src/Shared` files, which 4 or 5 projects compile each, are resolved alike by all of them). No relation is drawn from the 16 files of the MAUI apps' `Platforms/` folders and `ClientApp`'s `#if ANDROID` and `#if IOS || MACCATALYST` branches, which only a platform's build compiles (iOS and Mac Catalyst have no Linux workload, Android needs aapt2, built for x64), nor to `Program`, which `Catalog.API` and `Ordering.API` declare as two partial classes and other projects' top-level statements declare implicitly.
- Attributes: 35 dependencies, from `[JsonSerializable(typeof(X))]` source-generation contexts, `[DbContext(typeof(X))]` on EF migrations and the project's `[SecurityHeaders]`.
