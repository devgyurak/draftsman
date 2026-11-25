"""Review sets: sources written by hand below an oracle's review/ directory, one directory
per set, each put through the oracle's key and compared with the extractor, body and
declared relations (issue #7). Shared by the oracles whose review is written here (javac,
Python); Clang's, Roslyn's and Kotlin's have the same format in their own oracle.py.

README.md in review/ lists for each set `| `set` | body names drawn | declared names
agreed | ...`, the known limits (`- `set/file:line:col`` under "Known limits", and under
"Known limits of declared relations"), and the names not drawn (no failure). The review
fails on a mismatch not listed as a known limit and on fewer names than the table gives.
"""

from __future__ import annotations

import contextlib
import io
import re
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Callable


def review(directory: Path, sets: list[str] | None,
           key_dir: Callable[[Path, Path], list[dict]],
           check: Callable[[Path, list[dict], bool, object], int]) -> int:
    """``key_dir(set, out)``: the key's records of a set; ``check(set, recs, verbose,
    args)``: prints the comparison (`compare: ...`, or `declared: ...` where
    ``args.declared``)."""
    import answer_key
    readme = (directory / "README.md").read_text()
    body_part, _, dpart = readme.partition("Known limits of declared relations")
    limits = body_part.split("Known limits", 1)[-1].split("Names", 1)[0] \
        if "Known limits" in body_part else ""
    known = set(re.findall(r"^- `([^`]+)`", limits, re.M))
    dknown = set(re.findall(r"^- `([^`]+)`", dpart, re.M))
    counts = {k: int(v) for k, v in re.findall(r"^\| `(\w+)` \| (\d+) \|", readme, re.M)}
    dcounts = {k: int(v) for k, v in re.findall(r"^\| `(\w+)` \| \d+ \| (\d+) \|", readme, re.M)}
    wrong_re = r"^  (?:mismatch|in a file with compile errors): (\S+)"
    dwrong_re = r"^  mismatch(?: \((?:file with compile errors|key: error)\))?: (\S+)"
    chosen = sorted((d for d in directory.iterdir() if d.is_dir() and (not sets or d.name in sets)),
                    key=lambda d: (len(d.name), d.name))
    new, seen, dseen = [], set(), set()
    for d in chosen:
        with tempfile.TemporaryDirectory() as tmp:
            text, dtext = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(text), contextlib.redirect_stderr(io.StringIO()):
                recs = key_dir(d.resolve(), Path(tmp, "key.jsonl"))
                check(d.resolve(), answer_key.body(recs), True, None)
            with contextlib.redirect_stdout(dtext), contextlib.redirect_stderr(io.StringIO()):
                check(d.resolve(), recs, True, SimpleNamespace(declared=True, verbose=True, save=None))
        out, dout = text.getvalue(), dtext.getvalue()
        drawn = re.search(r"compare: (\d+) names drawn", out)
        places = list(dict.fromkeys(f"{d.name}/{w.rstrip(':')}" for w in re.findall(wrong_re, out, re.M)))
        dplaces = list(dict.fromkeys(f"{d.name}/{w.rstrip(':')}" for w in re.findall(dwrong_re, dout, re.M)))
        seen.update(places)
        dseen.update(dplaces)
        fresh = [p for p in places if p not in known]
        dfresh = [p for p in dplaces if p not in dknown]
        new += fresh + dfresh
        n = int(drawn.group(1)) if drawn else 0
        dnames = re.search(r"^declared: (\d+) names", dout, re.M)
        dagreed = re.search(r"^declared: .*?agreed (\d+)", dout, re.M)
        nd = int(dagreed.group(1)) if dagreed else 0
        fewer = d.name in counts and n < counts[d.name]
        dfewer = d.name in dcounts and nd < dcounts[d.name]
        if fewer or not drawn:
            new.append(d.name)
        if dfewer or not dnames:
            new.append(d.name + " (declared)")
        errors = sum(1 for r in recs if "diagnostic" in r)
        print(f"{d.name}: {n if drawn else '?'} names drawn, {len(places)} mismatches"
              + (f", {errors} compile errors" if errors else "")
              + (f", {len(fresh)} not among the known limits" if fresh else "")
              + (f", fewer than the {counts[d.name]} README.md lists" if fewer else "")
              + (" (no comparison)" if not drawn else "")
              + f"; declared: {dnames.group(1) if dnames else '?'} names, {nd} agreed, "
              f"{len(dplaces)} mismatches"
              + (f", {len(dfresh)} not among the known limits" if dfresh else "")
              + (f", fewer agreed than the {dcounts[d.name]} README.md lists" if dfewer else ""))
        for line in out.splitlines():
            m = re.match(wrong_re, line)
            if m and f"{d.name}/{m.group(1).rstrip(':')}" in fresh:
                print(line)
        for line in dout.splitlines():
            m = re.match(dwrong_re, line)
            if m and f"{d.name}/{m.group(1).rstrip(':')}" in dfresh:
                print("  declared" + line[1:])
    names = {d.name for d in chosen}
    for k in sorted(k for k in known | dknown if k.split("/", 1)[0] in names and k not in seen | dseen):
        print(f"known limit no longer a mismatch: {k}")
    return 1 if new else 0
