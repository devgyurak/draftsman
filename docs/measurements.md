# Measurements

The numbers in the README's status table, pinned to the commit each project was measured at
and the command that produced them, so a later re-run can tell a change in Draftsman from a
change in the project. Measured on 2026-11-17 with the code of this repository at that
date, re-run after each change that moved a number. `*.gradle.kts` build scripts are not
extracted, which is why nowinandroid counts fewer files than it has `.kt`/`.kts` files.

| Project | Repository | Commit (date) | Extract command (from the clone's root) |
|---|---|---|---|
| spring-petclinic | github.com/spring-projects/spring-petclinic | `500158f732` (2026-09-29) | `extract.py src/main --lang java` |
| jsoup | github.com/jhy/jsoup | `d90d57521d` (2026-11-04) | `extract.py src/main` |
| eShopOnWeb | github.com/dotnet-architecture/eShopOnWeb | `4da8212117` (2025-01-13) | `extract.py src --lang csharp` |
| nowinandroid | github.com/android/nowinandroid | `2982e63cb6` (2026-10-20) | `extract.py . --lang kotlin --exclude '**/test/**' --exclude '**/androidTest/**' --exclude '**/testing/**' --exclude '**/build/**'` |
| nest | github.com/nestjs/nest | `09b656cb8d` (2026-11-16) | `extract.py packages --lang typescript --exclude '**/test/**' --exclude '**/*.spec.ts'` |
| httpx | github.com/encode/httpx | `7cff5f79bc` (2026-11-16) | `extract.py httpx` |
| leveldb | github.com/google/leveldb | `29465588d3` (2026-11-12) | `extract.py . --lang cpp --exclude '**/*_test.cc' --exclude '**/third_party/**'` |

`extract.py` is `skills/draftsman/scripts/extract.py`. The summary line it prints is the
source of every number:

| Project | Files | Types | association | dependency | extends | implements | Unresolved | Diagnostics |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| spring-petclinic | 30 | 25 | 11 | 46 | 11 | 5 | 0 | 0 |
| jsoup | 105 | 230 | 147 | 1014 | 118 | 31 | 2 | 0 |
| eShopOnWeb | 209 | 208 | 96 | 199 | 34 | 27 | 199 | 0 |
| nowinandroid | 226 | 237 | 106 | 141 | 27 | 83 | 4 | 0 |
| nest | 730 | 738 | 415 | 1502 | 214 | 41 | 0 | 0 |
| httpx | 23 | 87 | 31 | 188 | 64 | 0 | 0 | 0 |
| leveldb | 102 | 161 | 222 | 613 | 17 | 25 | 2 | 10 |

To re-measure, clone at the commit (`git clone <repo> && git -C <dir> checkout <commit>`),
run the command, and update both tables and the README rows together. If the files or
types differ from this page, the project changed, not Draftsman.
