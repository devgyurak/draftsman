# leveldb — C++

Google's key-value store: plain C++ with a C API, ports and benchmarks.

| | |
|---|---|
| Repository | [github.com/google/leveldb](https://github.com/google/leveldb) |
| Commit | `29465588d3` (2026-11-12) |
| Extracted | the whole repository without `*_test.cc` and `third_party/` |

Measured on 2026-11-24 with Draftsman after 0.8.0 (at `81ecfac`); the declared relations are the same as 0.3.0's.

## Run

From any directory, with `DRAFTSMAN` pointing at `skills/draftsman/scripts` of this repository (see [the index](../README.md#re-running)):

```bash
git clone https://github.com/google/leveldb leveldb && git -C leveldb checkout 29465588d3
cd leveldb
python3 "$DRAFTSMAN"/extract.py . --lang cpp --exclude '**/*_test.cc' --exclude '**/third_party/**' -o ir.json
python3 "$DRAFTSMAN"/render.py ir.json view.json -o focus.mmd
"$DRAFTSMAN"/validate.sh focus.mmd
python3 "$DRAFTSMAN"/render.py ir.json view.json --format svg -o focus.svg
python3 "$DRAFTSMAN"/render.py ir.json view.json --format html -o viewer.html
```

`view.json`:

```json
{
  "focus": "DBImpl",
  "hops": 1,
  "hidden": ["*#get*", "*#set*"]
}
```

## Result

`extract.py` prints:

```text
draftsman: 102 files, 161 types, relations: association 227, dependency 616, extends 17, implements 25, body dependency 597, 2 unresolved (2 unexplained), 9 diagnostics
```

| Files | Types | association | dependency | extends | implements | body dependency | Unresolved | Diagnostics |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 102 | 161 | 227 | 616 | 17 | 25 | 597 | 2 (2 unexplained) | 9 |

Types by kind: 90 classes, 48 structs, 4 abstract classes, 8 interfaces, 11 enums.

The Mermaid and SVG renders of the view draw 42 boxes and 179 relations (`DBImpl` and its neighbours one hop away), and the Mermaid file passes `validate.sh`. The HTML viewer carries all 161 types, as 131 boxes with 30 nested types folded into their outer types, and 517 relations (body relations among them) and opens on the same focus. No inferred edges.

## Unresolved

Both unexplained, with no hint: C++ has no wildcard import that could explain them.

- `HANDLE` in `leveldb::ScopedHandle` (`util/env_windows.cc`): the Windows API type from `<windows.h>`, which is not in the sources.
- `BlockFunction` in `leveldb::TwoLevelIterator` (`table/two_level_iterator.cc`): a typedef of a function pointer, `typedef Iterator* (*BlockFunction)(...)`. Such typedefs are not read as aliases yet; the name stays unresolved rather than being dropped.

## Parse diagnostics

9 syntax-error spans. Declarations inside a span may be missing; the rest of the file is read.
(`port/thread_annotations.h`, counted until 2026-11-17, was broken by Draftsman's own
preprocessing: an `#endif` after a `#define ... (...)` line was taken for one inside
an expression and blanked.)

- `benchmarks/db_bench.cc:679` — a pointer-to-member field, `void (Benchmark::*method)(ThreadState*);`: the field `method` is missing from `ThreadArg`.
- `port/port_stdcxx.h:19` — `#if __has_include(...)`.
- `include/leveldb/c.h:266` — `} /* end extern "C" */` in an `#ifdef __cplusplus` block; the `extern "C" {` it closes is opened in another one, at line 50.
- `util/testutil.h:18` — gMock's `MATCHER(IsOK, "") { ... }`.
- Five in function bodies, which are not read, so no fact is affected: `benchmarks/db_bench.cc:698` (a pointer-to-member call), `benchmarks/db_bench_log.cc:81` (a string literal next to the `PRIu64` macro), `db/c.cc:269-270` (a comma expression), `db/version_set.cc:1228` and `util/cache.cc:128` (`new T*[n]`).

## What it covers

- Names in bodies (`evidence: "body"`): 877 names are drawn as 597 body dependencies, and each matches what Clang resolves there (`bench/clang_oracle`: 45 translation units configured by CMake, `db_bench_log.cc` with `db_bench.cc`'s flags; a header's answer only where every unit that compiles the line agrees; 0 mismatches). Not checked: 60 names in `util/env_windows.cc` and in lines no unit compiles, which the extractor reads as any other. Member functions defined out of their class (`void DBImpl::CompactRange(...)`) are their class's; code outside every type draws nothing (220 of the 1027 project type names Clang finds in bodies; #8). The ids several programs' classes share (`Benchmark`, `RandomGenerator` of the three `db_bench*.cc`) are one type, as in the declared relations (#7).
- Ownership: of 227 associations, 105 are `owned` (values, `unique_ptr`; drawn as composition) and 122 `shared` (pointers, references).
- Namespaces (`leveldb::`, `leveldb::port::`), 30 nested types, typedefs drawn through (`typedef SkipList<const char*, KeyComparator> Table;`), `std::pair` elements.
- Pure virtual classes: 8 are interfaces (only pure virtual methods, no data), 4 abstract classes.
