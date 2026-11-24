"""What every language's answer key for body relations shares (issues #2 and #5).

A body relation is drawn from a name written in a body, so citing its line proves
nothing: the line always names the target. Whether `Foo` is the Foo it was resolved to
takes a resolver that is not Draftsman's own: javac for Java (javac_oracle/), the
TypeScript compiler for TypeScript (tsc_oracle/). Each runs it and writes its answers as
JSON lines, one record per line, in one format:

    {"use": NAME, "file", "line", "col", "pos", "kind", "target", "project", "maximal",
     "from", ...}
        a name in a body the resolver resolved: "pos" is "type" (only a type can stand
        there) or "receiver" (a variable can too); "kind" is "type" (then "target" is its
        qualified name, as ir.json writes it, and "project" whether it is declared in the
        sources), "var", "tparam", "local" or "error"; "maximal" is false for a part of a
        longer type name (`p` in `p.Foo`); "from" is the named type around it. Lines are
        1-based, columns 0-based in UTF-16 code units. A key adds fields of its own.
    {"declared": QUALIFIED_NAME, "file"}
        a type declared in the sources (not local or anonymous)
    {"diagnostic": MESSAGE, "file", "line"}
        a compile error; the uses around it may be missing or "error"

Paths are relative to the root the extractor is given, so that they compare with
ir.json's. What is here: the fixtures' hand-written answers (`expected`), the selftest
that checks a key against them, the scope check every comparison with ir.json rests on,
and the comparison of the extractor's body relations with a key.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Callable, Iterable


def read(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def expected(root: Path, suffixes: Iterable[str], marker: str = "//>"
             ) -> dict[tuple[str, int, int], tuple[str, str]]:
    """(file, line, col) -> (answer, position) for every token a marker lists, in the
    files below ``root`` with one of ``suffixes``. A marker ends a line (`//>` or `#>`,
    then items); tests/fixtures/java/body/README.md gives the format."""
    pattern = re.compile(re.escape(marker) + r"(.*)$")
    out = {}
    for path in sorted(p for p in root.rglob("*") if p.suffix in tuple(suffixes)):
        rel = path.relative_to(root).as_posix()
        for no, text in enumerate(path.read_text().splitlines(), 1):
            m = pattern.search(text)
            if not m:
                continue
            code = text[:m.start()]
            seen: Counter = Counter()
            for item in m.group(1).split():
                name, _, rest = item.partition("=")
                # a TypeScript answer is a path (`p/foo.Foo/r`): the position follows the last /
                answer, position = rest.rsplit("/", 1) if "/" in rest else (rest, "")
                hits = [h.start() for h in re.finditer(rf"(?<![\w$]){re.escape(name)}(?![\w$])",
                                                       code)]
                if seen[name] >= len(hits):
                    raise SystemExit(f"{rel}:{no}: the marker lists more {name} than the line has")
                col = _utf16(code, hits[seen[name]])
                seen[name] += 1
                out[(rel, no, col)] = (answer, {"t": "type", "r": "receiver"}.get(position, ""))
            for name, n in seen.items():
                if n != len(re.findall(rf"(?<![\w$]){re.escape(name)}(?![\w$])", code)):
                    raise SystemExit(f"{rel}:{no}: the marker lists {n} of the {name} on the line")
    return out


def _utf16(text: str, index: int) -> int:
    return len(text[:index].encode("utf-16-le")) // 2


def answer(rec: dict) -> str:
    return rec["target"] if rec["kind"] == "type" else rec["kind"]


def selftest(recs: list[dict], want: dict) -> int:
    """Check a key's records on a fixture against its hand-written answers ``want``, so
    that a mismatch later is the extractor's and not the key's."""
    uses = {(r["file"], r["line"], r["col"]): r for r in recs if "use" in r}
    problems = [f"compile error: {r['file']}:{r['line']}: {r['diagnostic']}"
                for r in recs if "diagnostic" in r]
    for key, (ans, position) in sorted(want.items()):
        where = f"{key[0]}:{key[1]}:{key[2] + 1}"
        got = uses.get(key)
        if ans == "-":
            if got is not None:
                problems.append(f"{where}: expected nothing, got {answer(got)}/{got['pos']}")
        elif got is None:
            problems.append(f"{where}: expected {ans}/{position}, got nothing")
        elif (answer(got), got["pos"]) != (ans, position):
            problems.append(f"{where}: expected {ans}/{position}, got {answer(got)}/{got['pos']}")
    # what the key reports that no marker expects: only names outside the sources
    # (String, Runnable) may go unlisted
    for key, rec in sorted(uses.items()):
        if key not in want and (rec["kind"] != "type" or rec["project"]):
            problems.append(f"{key[0]}:{key[1]}:{key[2] + 1}: unexpected "
                            f"{rec['use']}={answer(rec)}/{rec['pos']}")
    for p in problems:
        print(p)
    listed = sum(1 for a, _ in want.values() if a != "-")
    print(f"selftest: {listed} names, {len(want) - listed} non-names, "
          f"{len(problems)} problems")
    return 1 if problems else 0


def in_scope(recs: list[dict], ir: dict[str, str], unseen: dict[str, str] = {},
             language: str = "Java") -> int:
    """1 unless the key saw the types of ``ir`` (id -> file), in the same files;
    ``unseen`` lists types of ir.json the key does not show, and why."""
    seen = {r["declared"]: r["file"] for r in recs if "declared" in r}
    problems = [f"in ir.json only: {t} ({ir[t]})" for t in sorted(ir.keys() - seen.keys())
                if t not in unseen]
    problems += [f"in the answer key only: {t} ({seen[t]})"
                 for t in sorted(seen.keys() - ir.keys())]
    problems += [f"{t}: ir.json declares it in {ir[t]}, the answer key in {seen[t]}"
                 for t in sorted(ir.keys() & seen.keys()) if ir[t] != seen[t]]
    problems += [f"listed as unseen but seen: {t}" for t in sorted(unseen) if t in seen]
    for p in problems:
        print(p)
    for t, why in sorted(unseen.items()):
        print(f"known: {t}: {why}")
    print(f"scope: {len(ir)} {language} types in ir.json, {len(seen)} in the answer key, "
          f"{len(problems)} problems")
    return 1 if problems else 0


def drawable(r: dict) -> bool:
    """A name a body relation could be drawn from: a project type, as a whole, from
    another type."""
    return (r["kind"] == "type" and r["project"] and r["maximal"]
            and r["from"] != r["target"])


def compare(drawn: list[tuple[str, int, int, str, str]], recs: list[dict],
            verbose: bool = False, key: str = "the answer key",
            same: Callable[[dict, str], bool] = lambda r, dst: True,
            drawable: Callable[[dict], bool] = drawable, uncompiled: set = frozenset()) -> int:
    """Check every name a body relation is drawn from, (file, line, col, from, to) as
    _Builder.body_uses lists them, against what the key resolved at its place; 1 on any
    mismatch outside the files that did not compile. ``same`` tells whether the key's
    type of the target's id is the one drawn (C#'s two `Program` classes share an id);
    ``drawable`` which of the key's names count as not drawn when they are not;
    ``uncompiled`` files no compilation compiles, whose names the key cannot answer."""
    broken = {r["file"] for r in recs if "diagnostic" in r}
    uses = {(r["file"], r["line"], r["col"]): r for r in recs if "use" in r}
    problems: Counter = Counter()
    shown: list[str] = []
    for file, line, col, src, dst in drawn:
        r = uses.get((file, line, col))
        if r is None:
            why = f"{key} resolved no name there"
        elif r["kind"] != "type":
            why = f"{key}: {r['kind']}"
        elif r["target"] != dst:
            why = f"{key}: {r['target']}"
        elif not same(r, dst):
            why = f"{key}: {r['target']} of {', '.join(r.get('files', ()))}"
        elif r["from"] != src:
            why = f"{key} draws it from {r['from']}"
        else:
            continue
        where = ("in a file with compile errors" if file in broken else
                 "in a file no compilation compiles" if file in uncompiled else "mismatch")
        problems[where] += 1
        shown.append(f"  {where}: {file}:{line}:{col + 1} {src} -> {dst}; {why}")

    at = {(f, line, col) for f, line, col, _, _ in drawn}
    missed = Counter(r["pos"] for k, r in uses.items() if drawable(r) and k not in at)
    pairs = {(s_, d) for *_, s_, d in drawn}
    want = {(r["from"], r["target"]) for r in uses.values() if drawable(r)}
    print(f"compare: {len(drawn)} names drawn as body relations ({len(pairs)} pairs); "
          + (", ".join(f"{k} {v}" for k, v in sorted(problems.items())) or "0 mismatches"))
    print(f"  {key}'s project types not drawn: "
          + ", ".join(f"{k} position {v}" for k, v in sorted(missed.items()))
          + f"; pairs {key} has that are not drawn: {len(want - pairs)}")
    for line in shown[:None if verbose else 20]:
        print(line)
    if verbose:
        for k, r in sorted(uses.items()):
            if drawable(r) and k not in at:
                print(f"  not drawn: {k[0]}:{k[1]}:{k[2] + 1} {r['use']} = {r['target']} "
                      f"in {r['from']} ({r['pos']} position)")
    return 1 if problems["mismatch"] else 0
