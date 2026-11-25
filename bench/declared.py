"""Declared relations against an answer key (issue #7).

The answer keys of bench/*_oracle record, besides the names in bodies, the names written
where the extractor draws declared relations: supertypes, field and property types,
parameter and return types, annotations, decorators and attributes, with their type
arguments. Those records have "pos" "declared" (answer_key.py's format otherwise). This
module lists what the extractor made of each name there and compares the two.

`watch(builder)` is called on a _Builder before its build(); afterwards
`builder.declared_names` lists, for every name a declared relation is resolved from:

    {"file", "line", "from", "written", "where", "status", "targets", "external"}

"line" is the declaration's (a member's first line, a supertype's or an annotation's
line), not the name's; "written" the name as the extractor resolved it (`Outer.Inner`,
`p::Foo`); "where" one of "super", "annotation", "field", "signature"; "status" the
resolver's, and "targets" the project types a relation is drawn to from it (an alias's
expansion included, the type itself left out). A supertype outside the sources is drawn
too, as an external node: "external" holds its id then. Building with the watch on gives
the same ir.json as without (tests/test_declared_key.py).

`compare(names, recs)` matches each name the key resolved in a declared position with the
extractor's names of the same file, type and simple name, and counts:

    mismatch   the extractor draws a project type the key does not give there (the key
               gives another one, a type outside the sources, a type parameter ...), or
               draws a supertype as external where the key gives a project type
    miss       the key gives a project type the extractor does not draw: it resolves the
               name to nothing of the project, leaves it unresolved, or reads no name there
    agreed     the rest of the key's names the extractor read; "unread" the key's names of
               types outside the sources at places the extractor reads none (a
               supertype's type arguments)
"""

from __future__ import annotations

import bisect
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Callable, Optional

DECLARED = "declared"


def declared_records(recs: list[dict]) -> list[dict]:
    return [r for r in recs if "use" in r and r.get("pos") == DECLARED]


def body_records(recs: list[dict]) -> list[dict]:
    """The records a body comparison reads: all but the declared names."""
    return [r for r in recs if r.get("pos") != DECLARED]


# ------------------------------------------------------------------ the extractor's side

def watch(builder) -> None:
    """Record, in ``builder.declared_names``, every name its build resolves for a declared
    relation (module docstring)."""
    from draftsman.resolve import ALIAS, EXTERNAL, BUILTIN, PROJECT, UNRESOLVED
    from draftsman.typeref import Named, parse_type, value_names
    from draftsman.langs import LANGUAGES

    names: list[dict] = []
    builder.declared_names = names
    # (file, type) -> the first lines of the type and its members: a key's name belongs to
    # the nearest one at or above it, or to a supertype or annotation on its own line
    lines: dict[tuple, set] = defaultdict(set)
    builder.declaration_lines = lines
    for rt in builder.types.values():
        lines[(rt.location.file, rt.qualified_name)].add(rt.location.line)
        for rm in rt.members:
            lines[(rm.member.file or rt.location.file, rt.qualified_name)].add(rm.member.line)
    resolver = builder.resolver
    resolve = resolver.resolve
    state = {"depth": 0, "ctx": None}

    def targets(res, rtype, where: str) -> list[str]:
        own = rtype.qualified_name
        if res.status == PROJECT:
            out = [res.target]
        elif res.status == ALIAS and res.target:
            leaves, mentioned = builder._expand_alias(res.target)
            out = [t for t, _, _ in leaves] + list(mentioned) if where == "field" \
                else list(mentioned)
        else:
            out = []
        return [t for t in dict.fromkeys(out) if t != own]

    def note(rtype, file, line, written, where, res, values=()) -> None:
        if res.status == UNRESOLVED and written in values:
            status = "value"
        else:
            status = res.status
        names.append({"file": file, "line": line, "from": rtype.qualified_name,
                      "written": written, "where": where, "status": status,
                      "targets": targets(res, rtype, where), "external":
                      (res.target or written) if res.status in (EXTERNAL, BUILTIN) else None})

    def watched(name, rtype, member=None, *more, **kw):
        ctx = state["ctx"]
        if not more and state["depth"] == 0 and ctx is not None and "arity" in kw \
                and rtype is ctx[0]:
            state["depth"] += 1
            try:
                res = resolve(name, rtype, member, **kw)
            finally:
                state["depth"] -= 1
            rt, rm, where, values = ctx
            m = rm.member
            note(rt, m.file or rt.location.file, m.line, name, where, res, values)
            return res
        state["depth"] += 1
        try:
            return resolve(name, rtype, member, *more, **kw)
        finally:
            state["depth"] -= 1

    resolver.resolve = watched

    association, depend_on = builder._association, builder._depend_on

    def _association(rtype, rm):
        was = state["ctx"]
        state["ctx"] = (rtype, rm, "field", ())
        try:
            association(rtype, rm)
        finally:
            state["ctx"] = was

    def _depend_on(rtype, rm, ref, loc):
        was = state["ctx"]
        where = "field" if was and was[2] == "field" else "signature"
        state["ctx"] = (rtype, rm, where, value_names(ref))
        try:
            depend_on(rtype, rm, ref, loc)
        finally:
            state["ctx"] = was

    builder._association, builder._depend_on = _association, _depend_on

    supers = builder._supers

    def _supers(rtype):
        for sup, res in zip(rtype.supers, resolver.supertypes(rtype)):
            ref = parse_type(sup.text)
            if not isinstance(ref, Named):
                continue
            file = sup.scope.file if sup.scope else rtype.location.file
            if res.status == ALIAS and res.target:   # as _Builder._supers
                leaves, _ = builder._expand_alias(res.target)
                if len(leaves) == 1:
                    res = type(res)(PROJECT, leaves[0][0])
                else:
                    res = type(res)(UNRESOLVED)
            note(rtype, file, sup.line, ref.name, "super", res)
        supers(rtype)

    builder._supers = _supers

    annotations = builder._annotations

    def _annotations(rtype):
        """As _Builder._annotations resolves the names (kept in step with it)."""
        from draftsman.typeref import named_refs
        spec = LANGUAGES[rtype.language]
        sep = spec.separator
        for ann in rtype.annotation_refs:
            file = ann.scope.file
            last = None
            for name in spec.annotation_type_names(ann.name):
                last = resolve(name, rtype, None, scope=ann.scope)
                if last.status in (PROJECT, ALIAS):
                    break
            if last is not None:
                note(rtype, file, ann.line, ann.name, "annotation", last)
            for text, is_type, line in ann.args:
                if is_type:
                    ref = parse_type(spec.normalize_type(text))
                    for name, arity in named_refs(ref, lambda n: resolve(
                            n, rtype, None, scope=ann.scope).status == PROJECT):
                        if builder.wrappers.is_wrapper(name):
                            continue
                        note(rtype, file, line, name, "annotation",
                             resolve(name, rtype, None, scope=ann.scope, arity=arity))
                    continue
                name = text.replace(" ", "")
                while name:   # `Kind.A`: the type Kind, or a constant of one
                    res = resolve(name, rtype, None, scope=ann.scope)
                    if res.status in (PROJECT, ALIAS):
                        note(rtype, file, line, name, "annotation", res)
                        break
                    name = name.rsplit(sep, 1)[0] if sep in name else ""
        annotations(rtype)

    builder._annotations = _annotations


# ------------------------------------------------------------------ comparison

_HEAD = re.compile(r"[\w$.:]*$")


def _simple(written: str) -> str:
    return re.split(r"::|\.|/", written)[-1].split("<", 1)[0].strip()


class _Sources:
    """The line a key's record stands on, to read the qualifier written before it."""

    def __init__(self, root: Optional[Path]):
        self.root = root
        self.lines: dict[str, list[str]] = {}

    def written(self, r: dict) -> str:
        if self.root is None:
            return r["use"]
        lines = self.lines.get(r["file"])
        if lines is None:
            try:
                text = (self.root / r["file"]).read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                text = ""
            lines = self.lines[r["file"]] = text.splitlines()
        if not 0 < r["line"] <= len(lines):
            return r["use"]
        line = lines[r["line"] - 1]
        # the key's columns are UTF-16 units; the qualifier is ASCII in practice
        before = line.encode("utf-16-le")[:2 * r["col"]].decode("utf-16-le", "replace")
        head = _HEAD.search(before).group(0)
        return re.sub(r"^(global::|::)", "", head) + r["use"]


def compare(builder, recs: list[dict], root: Optional[Path] = None,
            verbose: bool = False, key: str = "the answer key",
            same: Callable[[dict, str], bool] = lambda r, dst: True,
            uncompiled=frozenset(), show: int = 30) -> dict:
    """Compare the extractor's declared names with the key's (module docstring); prints a
    summary and returns the counts and the listed places."""
    names = builder.declared_names
    starts = {k: sorted(v) for k, v in builder.declaration_lines.items()}
    broken = {r["file"] for r in recs if "diagnostic" in r}
    by_place: dict[tuple, list[dict]] = defaultdict(list)
    for n in names:
        by_place[(n["file"], n["from"], _simple(n["written"]))].append(n)
    src = _Sources(root)
    counts: Counter = Counter()
    rows: list[dict] = []
    matched: set[int] = set()
    for r in declared_records(recs):
        if not r.get("maximal", True):
            continue
        if r["kind"] == "type" and r["target"] == r["from"]:
            continue   # a type naming itself draws nothing
        here = by_place.get((r["file"], r["from"], r["use"]), [])
        written = src.written(r)
        pick = _pick(here, r, written, starts.get((r["file"], r["from"]), []))
        project = r["kind"] == "type" and r["project"]
        skipped = uncompiled.get(r["file"], ()) if isinstance(uncompiled, dict) else \
            ("all" if r["file"] in uncompiled else ())
        if pick is not None:
            matched.add(id(pick))
        drawn = pick["targets"] if pick is not None else []
        ext = pick["external"] if pick is not None and pick["where"] == "super" else None
        if project:
            wanted = r.get("targets") or [r["target"]]
            if any(t in drawn and same(r, t) for t in wanted):
                verdict = "agreed"
            elif drawn or ext:
                verdict = "mismatch"
            else:
                verdict = "miss"
        elif drawn:
            verdict = "mismatch"
        else:
            verdict = "agreed" if pick is not None else "unread"
        if verdict in ("mismatch", "miss"):
            if r["file"] in broken:
                verdict += " (file with compile errors)"
            elif skipped == "all" or r["line"] in skipped:
                verdict += " (not compiled)"
            elif r["kind"] == "error":
                verdict += " (key: error)"
        counts[verdict] += 1
        counts["names"] += 1
        counts["project names"] += project
        if verdict.split(" ")[0] in ("mismatch", "miss"):
            rows.append({"verdict": verdict, "file": r["file"], "line": r["line"],
                         "col": r["col"], "from": r["from"], "written": written,
                         "key": _answer(r), "key_project": project,
                         "drawn": drawn or ([f"external {ext}"] if ext else []),
                         "status": pick["status"] if pick is not None else "not read",
                         "where": pick["where"] if pick is not None else None,
                         "role": r.get("role"), "in_args": r.get("in_args")})
    # what the extractor draws where the key resolved no name
    keyed = {(r["file"], r["from"], r["use"]) for r in declared_records(recs)}
    unkeyed = [n for n in names if n["targets"]
               and (n["file"], n["from"], _simple(n["written"])) not in keyed]
    counts["drawn where the key has no name"] = len(unkeyed)
    print(f"declared: {counts['names']} names {key} resolved in declared positions "
          f"({counts['project names']} of project types); "
          + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())
                      if k not in ("names", "project names")))
    for row in rows[:None if verbose else show]:
        print(f"  {row['verdict']}: {row['file']}:{row['line']}:{row['col'] + 1} "
              f"{row['from']}: {row['written']} -> {', '.join(row['drawn']) or row['status']}"
              f"; {key}: {row['key']}")
    if verbose:
        for n in unkeyed:
            print(f"  no key name: {n['file']}:{n['line']} {n['from']}: {n['written']} -> "
                  f"{', '.join(n['targets'])}")
    return {"counts": dict(counts), "rows": rows,
            "unkeyed": [{k: n[k] for k in ("file", "line", "from", "written", "targets")}
                        for n in unkeyed]}


def _answer(r: dict) -> str:
    if r["kind"] != "type":
        return r["kind"]
    return r["target"] + ("" if r["project"] else " (outside)")


def _pick(here: list[dict], r: dict, written: str, starts: list[int]) -> Optional[dict]:
    """The extractor's name the key's record stands for: one of the declaration the
    record stands in (the nearest declaration line at or above it, or its own line),
    written the same way if one is."""
    at = bisect.bisect_right(starts, r["line"])
    start = starts[at - 1] if at else None
    pool = [n for n in here if n["line"] in (start, r["line"])]
    if not pool:
        return None
    exact = [n for n in pool if n["written"].replace(" ", "") == written]
    if exact:
        return exact[0]
    if "." in written or "::" in written:
        return None   # a qualified name the extractor did not read as such
    return pool[0]


def arguments(parser) -> None:
    """The options of a key's comparison for declared names."""
    parser.add_argument("--declared", action="store_true",
                        help="compare the names declared relations are drawn from (issue #7)")
    parser.add_argument("--save", type=Path, help="with --declared: write the result as JSON")


def report(builder, recs: list[dict], root: Path, args, **kw) -> int:
    """compare(), its result written to ``args.save``; 0 (a measurement, not a check)."""
    import json
    result = compare(builder, recs, root, getattr(args, "verbose", False), **kw)
    if getattr(args, "save", None):
        args.save.write_text(json.dumps(result, indent=1) + "\n")
    return 0
