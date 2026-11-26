"""Check the numbers the e2e pages quote against the ir.json they were measured from.

    uv run bench/e2e_pages.py IRDIR [--key REPO=KEY.jsonl ...] [-v]

IRDIR holds each repository's ir.json as `<name>.json` (`jsoup.json`, `spring-petclinic.json`
or `petclinic.json`, `nowinandroid.json` or `nia.json`, ...), extracted with the command
of its page (docs/e2e/<language>/<name>.md). The numbers are counted again from ir.json
and the renders of the page's view.json, and every place a page, the index table
(docs/e2e/README.md) or the status tables of README.md and README-KO.md writes another
number is listed; the exit status is 1 if there is one. A sentence a check expects and
does not find is listed too (its wording changed: update the check).

Some numbers are the answer key's, not ir.json's: C++'s "N of the M project type names
Clang finds in bodies" and POCO's names in code outside every type and in template
specialisations' bodies count the key's maximal names of project types in bodies (not in
a declaration), those with no type around them (`from` empty) and those in a
specialisation (`spec`). They are checked where `--key REPO=...` gives the key
(bench/clang_oracle/oracle.py key's output), and skipped otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Callable, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "draftsman" / "scripts"))

from draftsman.model import IR  # noqa: E402
from draftsman.scene import build_scene, is_body  # noqa: E402
from draftsman.view import View  # noqa: E402
from summary import counts  # noqa: E402

DOCS = ROOT / "docs" / "e2e"
PAGES = {"spring-petclinic": "java/spring-petclinic", "jsoup": "java/jsoup", "netty": "java/netty",
         "eshoponweb": "csharp/eshoponweb", "eshop": "csharp/eshop", "serilog": "csharp/serilog",
         "nowinandroid": "kotlin/nowinandroid", "ktor": "kotlin/ktor", "nest": "typescript/nest",
         "typeorm": "typescript/typeorm", "httpx": "python/httpx", "django": "python/django",
         "leveldb": "cpp/leveldb", "poco": "cpp/poco"}
ALIASES = {"petclinic": "spring-petclinic", "nia": "nowinandroid"}


@dataclass
class Repo:
    name: str
    path: Path
    key: Optional[Path] = None
    md: str = ""
    view_text: str = ""

    @cached_property
    def ir(self) -> IR:
        return IR.load(self.path)

    @cached_property
    def raw(self) -> dict:
        return json.loads(self.path.read_text())

    def _scene(self, whole: bool):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp, "view.json")
            p.write_text(self.view_text)
            return build_scene(self.ir, View.load(p), whole=whole)

    @cached_property
    def view(self):
        return self._scene(False)

    @cached_property
    def viewer(self):
        return self._scene(True)

    @cached_property
    def ids(self) -> set[str]:
        return {t["id"] for t in self.raw["types"]}

    @cached_property
    def declared(self) -> list[dict]:
        return [r for r in self.raw["relations"] if r.get("evidence") != "body"]

    @cached_property
    def body(self) -> list[dict]:
        return [r for r in self.raw["relations"] if r.get("evidence") == "body"]

    @cached_property
    def key_names(self) -> Optional[list[dict]]:
        if self.key is None:
            return None
        recs = [json.loads(line) for line in self.key.read_text().splitlines() if line.strip()]
        return [r for r in recs if "use" in r and r.get("pos") != "declared"
                and r.get("project") and r.get("maximal")]


def _focus_only_body(scene, focus: str) -> tuple[int, int]:
    """(the types the view draws only through body relations of the focus, those body
    relations)."""
    isf = lambda x: x == focus or x.endswith("." + focus) or x.endswith("::" + focus)  # noqa: E731
    other = lambda r: r.to if isf(r.from_) else r.from_  # noqa: E731
    body = [r for r in scene.relations if is_body(r) and (isf(r.from_) or isf(r.to))]
    declared = {other(r) for r in scene.relations if not is_body(r) and (isf(r.from_) or isf(r.to))}
    return len({other(r) for r in body} - declared), len(body)


def _neighbours(repo: Repo, simple: str) -> int:
    """Project types one hop away from the type of that simple name through declared
    relations, either way."""
    tid = next(t for t in repo.ids if t.rsplit(".", 1)[-1] == simple)
    return len({r["to"] if r["from"] == tid else r["from"] for r in repo.declared
                if tid in (r["from"], r["to"])} & repo.ids - {tid})


def _annotation_types(repo: Repo, target_simple: str) -> int:
    return len({r["from"] for r in repo.declared if (r.get("via") or "").startswith("@")
                and r["to"].rsplit(".", 1)[-1] == target_simple})


# a check: (pattern with groups of numbers, what they should be); None skips (no key)
Check = tuple[str, Callable[[Repo], Optional[tuple]]]


def _common(repo: Repo) -> list[Check]:
    focus = json.loads(repo.view_text).get("focus", "")
    unit = r"(?:types|boxes)"
    checks: list[Check] = [
        (r"renders of the view draw (\d+) " + unit + r" and (\d+) relations",
         lambda r: (len(r.view.types), len(r.view.relations))),
        (r"(\d+) (?:of the )?" + unit + r" only through the (\d+) body relations (?:of|that touch)",
         lambda r: _focus_only_body(r.view, focus)),
        (r"carries all (\d+) types, as (\d+) boxes with (\d+) nested types folded",
         lambda r: (len(r.ir.types), len(r.viewer.types),
                    sum(len(v) for v in r.viewer.folded.values()))),
        (r"carries all \d+ types(?:, as [^,]*,)? and (\d+) relations",
         lambda r: (len(r.viewer.relations),)),
        (r"carries all \d+ types(?:, as [^,]*,)? and \d+ relations \((\d+) from bodies",
         lambda r: (sum(1 for x in r.viewer.relations if is_body(x)),)),
        (r"(\d+) dependencies from names in method bodies[^;]*?between (\d+) pairs of types; "
         r"no declaration relates (\d+) of those pairs",
         lambda r: (len(r.body), len({(x["from"], x["to"]) for x in r.body}),
                    len({(x["from"], x["to"]) for x in r.body}
                        - {(x["from"], x["to"]) for x in r.declared}))),
        (r"names are drawn as (\d+) body dependencies", lambda r: (len(r.body),)),
        (r"Types by kind: ([^.]+)\.", None),   # (checked below, as words)
    ]
    return checks


def _required(repo: Repo, common: list[Check]) -> set[str]:
    """The common sentences every page has (the view's render, the viewer's relations, its
    nested types where it folds some, its body relations unless it says they are among
    them, the bodies' count): one a page lacks is listed, not passed over."""
    p = [pattern for pattern, _ in common]
    req = {p[0], p[3]}
    if sum(len(v) for v in repo.viewer.folded.values()):
        req.add(p[2])
    if "(body relations among them)" not in repo.md:
        req.add(p[4])
    if "only through the" in repo.md:
        req.add(p[1])
    if not re.search(p[6], repo.md):   # C++ and Kotlin write "names are drawn as N ..."
        req.add(p[5])
    return req


def _types_by_kind(repo: Repo) -> str:
    names = {"class": "class", "abstract_class": "abstract class", "interface": "interface",
             "enum": "enum", "record": "record", "struct": "struct", "union": "union",
             "object": "object", "annotation": "annotation"}
    c = Counter(t["kind"] for t in repo.raw["types"])
    return ", ".join(f"{n} {names.get(k, k)}" for k, n in c.items())


def _ownership(repo: Repo) -> tuple:
    a = [r for r in repo.declared if r["kind"] == "association"]
    c = Counter(r.get("ownership") for r in a)
    return len(a), c.get("owned", 0), c.get("shared", 0)


def _unresolved_names(repo: Repo) -> tuple:
    u = repo.raw["unresolved"]
    return len(u), len({x["raw_type"] for x in u})


SPECIFIC: dict[str, list[Check]] = {
    "jsoup": [(r"`Evaluator` \((\d+) non-dependency relations\)",
               lambda r: (sum(1 for x in r.declared + r.body if "org.jsoup.select.Evaluator"
                              in (x["from"], x["to"]) and x["kind"] != "dependency"),))],
    "netty": [(r"Dependencies outnumber every other kind \((\d+)\)",
               lambda r: (sum(1 for x in r.declared if x["kind"] == "dependency"),)),
              (r"Annotations: (\d+) dependencies, on `@UnstableApi` \((\d+) types",
               lambda r: (sum(1 for x in r.declared if (x.get("via") or "").startswith("@")),
                          _annotation_types(r, "UnstableApi"))),
              (r"(\d+) external types with qualified ids", lambda r: (len(r.raw["externals"]),))],
    "ktor": [(r"Annotations: (\d+) dependencies", lambda r: (
                 sum(1 for x in r.declared if (x.get("via") or "").startswith("@")),)),
             (r"`InternalAPI` named by (\d+) types, `KtorDsl` by (\d+)",
              lambda r: (_annotation_types(r, "InternalAPI"), _annotation_types(r, "KtorDsl"))),
             (r"(\d+) references to (\d+) names", _unresolved_names)],
    "eshop": [(r"Attributes: (\d+) dependencies", lambda r: (
                  sum(1 for x in r.declared if (x.get("via") or "").startswith("@")),)),
              (r"(\d+) references to (\d+) names", _unresolved_names)],
    "typeorm": [(r"`QueryRunner` (\d+), `EntityMetadata` (\d+)",
                 lambda r: (_neighbours(r, "QueryRunner"), _neighbours(r, "EntityMetadata")))],
    "django": [(r"Of the (\d+) others, \d+ come from [^,]*, (\d+) from decorators and (\d+) from bases made by calls",
                lambda r: (sum(1 for x in r.declared if x["kind"] != "extends"),
                           sum(1 for x in r.declared if (x.get("via") or "").startswith("@")),
                           sum(1 for x in r.declared if x["kind"] != "extends"
                               and not (x.get("via") or "").startswith("@") and x.get("via") is None))),
               (r"the other (\d+) declared relations point at external types",
                lambda r: (sum(1 for x in r.declared if x["to"] not in r.ids),))],
    "leveldb": [(r"Ownership: of (\d+) associations, (\d+) are `owned`", lambda r: _ownership(r)[:2]),
                (r"\((\d+) of the (\d+) project type names Clang finds in bodies",
                 lambda r: None if r.key_names is None else (
                     sum(1 for x in r.key_names if not x.get("from")), len(r.key_names)))],
    "poco": [(r"of (\d+) associations, (\d+) are `owned` and (\d+) `shared`", _ownership),
             (r"(\d+) references to (\d+) names", _unresolved_names),
             (r"code outside every type \((\d+) names\) and template specialisations' bodies \((\d+)\)",
              lambda r: None if r.key_names is None else (
                  sum(1 for x in r.key_names if not x.get("from")),
                  sum(1 for x in r.key_names if x.get("spec"))))],
}


def _row(repo: Repo) -> dict[str, str]:
    """Files, Types, "D + B body", Unresolved as the index and status tables write them."""
    line = counts(repo.ir)
    m = re.search(r", (\d+) unresolved(?: \(([^)]*)\))?", line)
    un = m.group(1) + (f" ({m.group(2).replace(' the sources', '')})" if m.group(2) else "")
    return {"files": re.search(r"(\d+) files", line).group(1),
            "types": re.search(r"(\d+) types", line).group(1),
            "relations": f"{len(repo.declared)} + {len(repo.body)} body", "unresolved": un}


def check(repo: Repo, out: list[str], verbose: bool) -> None:
    page = f"docs/e2e/{PAGES[repo.name]}.md"
    md = repo.md
    line = "draftsman: " + counts(repo.ir)
    if line not in md:
        written = re.search(r"^draftsman: .*$", md, re.M)
        out.append(f"{page}: extract.py prints\n    {line}\n  the page has\n    "
                   f"{written.group(0) if written else '(none)'}")
    # the table under it: the same numbers
    hdr = re.search(r"^\| Files \|.*\|$", md, re.M)
    if hdr:
        cols = [c.strip() for c in hdr.group(0).strip("|").split("|")]
        row = md[hdr.end():].split("\n")[2]
        cells = [c.strip() for c in row.strip("|").split("|")]
        nums = dict(re.findall(r"(body dependency|association|dependency|extends|implements) (\d+)", line))
        want = {"Files": _row(repo)["files"], "Types": _row(repo)["types"],
                "Diagnostics": re.search(r"(\d+) diagnostics", line).group(1)}
        for c, cell in zip(cols, cells):
            expected = want.get(c, nums.get(c, "0" if c in ("association", "dependency", "extends",
                                                           "implements", "body dependency") else None))
            if c == "Unresolved":
                expected = _row(repo)["unresolved"] if "(" in cell else _row(repo)["unresolved"].split()[0]
            if expected is not None and cell != expected:
                out.append(f"{page}: table column {c}: {cell}, ir.json gives {expected}")
    kinds = re.search(r"Types by kind: ([^.]+)\.", md)
    if kinds:
        have = Counter()
        for n, word in re.findall(r"(\d+) ([a-z ]+?)(?:es|s)?(?:,|$)", kinds.group(1)):
            have[word.strip()] += int(n)
        if sum(have.values()) != len(repo.raw["types"]):
            out.append(f"{page}: types by kind sum to {sum(have.values())}, ir.json has "
                       f"{len(repo.raw['types'])} ({_types_by_kind(repo)})")
    common = _common(repo)
    required = _required(repo, common)
    for pattern, fn in common + SPECIFIC.get(repo.name, []):
        if fn is None:
            continue
        found = re.search(pattern, md, re.S)
        if not found:
            if pattern in required or (pattern, fn) in SPECIFIC.get(repo.name, []):
                out.append(f"{page}: no sentence matches /{pattern}/")
            continue
        expected = fn(repo)
        if expected is None:
            if verbose:
                print(f"  {page}: skipped (no key): /{pattern}/")
            continue
        written = tuple(int(g) for g in found.groups())
        if written != tuple(expected):
            out.append(f"{page}: /{pattern}/ writes {written}, ir.json gives {tuple(expected)}")
        elif verbose:
            print(f"  {page}: {written} as counted")


def check_tables(repos: dict[str, Repo], out: list[str]) -> None:
    for doc in ("docs/e2e/README.md", "README.md", "README-KO.md"):
        text = (ROOT / doc).read_text()
        for line in text.splitlines():
            m = re.search(r"\]\((?:docs/e2e/)?((?:java|csharp|kotlin|typescript|python|cpp)/[\w-]+)\.md\)", line)
            if not (m and line.startswith("|")):
                continue
            name = next((n for n, p in PAGES.items() if p == m.group(1)), None)
            if name not in repos:
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            i = next(k for k, c in enumerate(cells) if " body" in c and "+" in c)
            want = _row(repos[name])
            got_un = cells[i + 1].split(";")[0] + (")" if ";" in cells[i + 1] else "")
            for label, got, exp in (("files", cells[i - 2], want["files"]),
                                    ("types", cells[i - 1], want["types"]),
                                    ("relations", cells[i], want["relations"]),
                                    ("unresolved", got_un, want["unresolved"])):
                if got != exp:
                    out.append(f"{doc}: {name} {label}: {got}, ir.json gives {exp}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("irdir", type=Path)
    ap.add_argument("--key", action="append", default=[], metavar="REPO=KEY.jsonl")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    keys = {ALIASES.get(k, k): Path(v) for k, v in (a.split("=", 1) for a in args.key)}
    repos: dict[str, Repo] = {}
    for p in sorted(args.irdir.glob("*.json")):
        name = ALIASES.get(p.stem, p.stem)
        if name in PAGES:
            md = (DOCS / f"{PAGES[name]}.md").read_text()
            vj = re.search(r"`view.json`[^\n]*\n\s*```json\n(.*?)```", md, re.S)
            repos[name] = Repo(name, p, keys.get(name), md, vj.group(1) if vj else "{}")
    out: list[str] = []
    for name in PAGES:
        if name in repos:
            if args.verbose:
                print(name)
            check(repos[name], out, args.verbose)
    check_tables(repos, out)
    missing = [n for n in PAGES if n not in repos]
    print(f"e2e pages: {len(repos)} repositories checked"
          + (f" ({', '.join(missing)}: no ir.json)" if missing else "")
          + f"; {len(out)} numbers differ")
    for line in out:
        print("  " + line)
    return 1 if out else 0


if __name__ == "__main__":
    sys.exit(main())
