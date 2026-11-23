# The C# answer key's environment (bench/roslyn_oracle/oracle.py builds it as draftsman-roslyn):
# the .NET SDKs the end-to-end repositories' global.json files ask for, one image, each
# repository picking its own (eShopOnWeb 8.0, Serilog 10.0, eShop 11.0), and TypeUses
# built against Roslyn 5.12.0. Every base image is pinned by digest (linux/arm64).
FROM mcr.microsoft.com/dotnet/sdk:8.0@sha256:1b955f179b02df4f0eb5fadedaa898cbe44d620a64aab52eec72c8e91d1355b5 AS sdk8
FROM mcr.microsoft.com/dotnet/sdk:10.0@sha256:bef136a371963aaa46ec97882845ef6f54dec15728bb4b128b1c2a400ffbc9b4 AS sdk10
FROM mcr.microsoft.com/dotnet/sdk:11.0@sha256:65f3c7c6a25a239ab3e6719f2896147e7b68242ff2d8818dd70498bde6ef8bea
COPY --from=sdk8 /usr/share/dotnet/sdk/ /usr/share/dotnet/sdk/
COPY --from=sdk8 /usr/share/dotnet/shared/ /usr/share/dotnet/shared/
COPY --from=sdk8 /usr/share/dotnet/packs/ /usr/share/dotnet/packs/
COPY --from=sdk8 /usr/share/dotnet/sdk-manifests/ /usr/share/dotnet/sdk-manifests/
COPY --from=sdk10 /usr/share/dotnet/sdk/ /usr/share/dotnet/sdk/
COPY --from=sdk10 /usr/share/dotnet/shared/ /usr/share/dotnet/shared/
COPY --from=sdk10 /usr/share/dotnet/packs/ /usr/share/dotnet/packs/
COPY --from=sdk10 /usr/share/dotnet/sdk-manifests/ /usr/share/dotnet/sdk-manifests/
# eShop's two .NET MAUI apps need a MAUI workload to load at all; Linux has the Android one
# (its manifests as the SDK ships them). They are compiled for plain net11.0 (oracle.py)
RUN dotnet workload install maui-android --skip-manifest-update
COPY TypeUses/ /opt/type-uses-src/
RUN dotnet publish /opt/type-uses-src -c Release -o /opt/type-uses && rm -rf /opt/type-uses-src
