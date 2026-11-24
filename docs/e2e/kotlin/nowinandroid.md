# nowinandroid — Kotlin

Google's Android sample: Compose, Hilt, Room, DataStore, many Gradle modules.

| | |
|---|---|
| Repository | [github.com/android/nowinandroid](https://github.com/android/nowinandroid) |
| Commit | `2982e63cb6` (2026-10-20) |
| Extracted | the whole repository without tests, test fixtures and generated `build/` output; `*.gradle.kts` build scripts are never extracted |

Measured on 2026-11-24 with Draftsman after 0.7.0 (at `a51520e`); the declared relations are the same as 0.3.0's.

## Run

From any directory, with `DRAFTSMAN` pointing at `skills/draftsman/scripts` of this repository (see [the index](../README.md#re-running)):

```bash
git clone https://github.com/android/nowinandroid nowinandroid && git -C nowinandroid checkout 2982e63cb6
cd nowinandroid
python3 "$DRAFTSMAN"/extract.py . --lang kotlin --exclude '**/test/**' --exclude '**/androidTest/**' --exclude '**/testing/**' --exclude '**/build/**' -o ir.json
python3 "$DRAFTSMAN"/render.py ir.json view.json -o focus.mmd
"$DRAFTSMAN"/validate.sh focus.mmd
python3 "$DRAFTSMAN"/render.py ir.json view.json --format svg -o focus.svg
python3 "$DRAFTSMAN"/render.py ir.json view.json --format html -o viewer.html
```

`view.json`:

```json
{
  "focus": "UserDataRepository",
  "hops": 1,
  "hidden": ["*#get*", "*#set*"]
}
```

## Result

`extract.py` prints:

```text
draftsman: 226 files, 237 types, relations: association 106, dependency 200, extends 27, implements 83, body dependency 107, 4 unresolved (3 outside the sources, 1 unexplained), 0 diagnostics
```

| Files | Types | association | dependency | extends | implements | body dependency | Unresolved | Diagnostics |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 226 | 237 | 106 | 200 | 27 | 83 | 107 | 4 (3 outside, 1 unexplained) | 0 |

Types by kind: 131 classes, 14 abstract classes, 38 interfaces, 41 objects, 9 enums, 4 annotation classes.

The Mermaid and SVG renders of the view draw 15 boxes and 19 relations (`UserDataRepository` and its neighbours one hop away), and the Mermaid file passes `validate.sh`. The HTML viewer carries all 237 types, as 198 boxes with 39 nested types folded into their outer types, and 288 relations (body relations among them) and opens on the same focus. No inferred edges.

## Unresolved

3 outside the sources, 1 unexplained (the one without a hint).

- `UserPreferences`, in four classes of `core.datastore`: a protobuf message generated into `build/`, which is excluded. Three hints point at the generic supertype it is written in (`DataMigration<UserPreferences>`, `Serializer<UserPreferences>`).

## What it covers

- Names in bodies (`evidence: "body"`): 143 names are drawn as 107 body dependencies, and each matches what the Kotlin compiler resolves there (`bench/kotlin_oracle`, 101 compilations of the Debug variants, 0 mismatches). Code outside every type draws nothing (300 of the 454 project type names the compiler finds in bodies are there: the Compose UI is top-level functions; #8). Under supertypes outside the sources (`ViewModel`, Gradle's `DefaultTask`) nothing is hidden but what the library table knows.
- 41 `object`s and 4 annotation classes (`@Dispatcher`, `@ApplicationScope`, `@ThemePreviews`, `@DevicePreviews`).
- Hilt `@Inject constructor(...)`: a primary constructor with a plain parameter is listed and its parameters are dependencies; one made only of `val` properties is not.
- AndroidX supertypes (`ViewModel`, `ComponentActivity`, `DataMigration`, ...) as qualified external ids through Kotlin's imports.
- Annotations: Room's `@Database(entities = [X::class], autoMigrations = [AutoMigration(spec = DatabaseMigrations.Schema2to3::class)])`, `@Entity` foreign keys, `@HiltViewModel(assistedFactory = ...)` and the project's Hilt qualifiers (`@Dispatcher(IO)`, `@ApplicationScope`) are dependencies.
