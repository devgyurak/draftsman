"""Clang as the answer key for C++ body relations (issue #5).

TypeUses/ is a libTooling tool: it parses a translation unit as the compiler would and
records what every name written in a body was resolved to, once per translation unit. This
script runs it in a container, joins the translation units each file is in, and turns
its records into the format bench/answer_key.py gives.

    uv run bench/clang_oracle/oracle.py selftest
    uv run bench/clang_oracle/oracle.py key DIR [-o OUT.jsonl] [--compare] [-v]
    uv run bench/clang_oracle/oracle.py review [SET ...]
    uv run bench/clang_oracle/oracle.py run REPO --checkout DIR -o OUT.jsonl [--raw DIR [--rejoin]]
    uv run bench/clang_oracle/oracle.py scope REPO OUT.jsonl ir.json
    uv run bench/clang_oracle/oracle.py compare REPO OUT.jsonl --checkout DIR [-v]
    uv run bench/clang_oracle/oracle.py measure OUT.jsonl [--ir ir.json]
    uv run bench/clang_oracle/oracle.py table

`selftest` checks the key against the hand-written answers in tests/fixtures/cpp/body
(tests/fixtures/java/body/README.md gives the marker format). `key` answers for any
directory: each of its source files (`.cc`, `.cpp`, ...) is a translation unit, compiled
as C++17 with the directory as include path, and so is each header no translation unit
includes; `--compare` checks the extractor's body relations of the same files against it.
`review` does that for every set of sources reviews wrote by hand (review/, one directory
each) and fails on a mismatch review/README.md does not list as a known limit, and on
fewer names drawn than it lists. `run` configures a repository with CMake in the
container (REPOS below; compile_commands.json is all a configure gives, and all TypeUses
needs) and records the translation units of the sources its end-to-end page extracts
(docs/e2e/cpp/); then, as a translation unit of its own each, the headers of those sources
no translation unit includes. `scope` fails unless the key saw the same types, declared
in the same files, as ir.json of those sources. `compare` extracts the same sources and
checks every name a body relation is drawn from against what Clang resolved at its place.
`measure` prints what the rules for hiding names are decided by. `table` writes the
extractor's table of the classes of namespace `std` (libstdc++'s, the image's GCC 13).

What a record says. A name in a body (a function's body, a constructor's initializers, a
default argument, a default member initializer, a static member's initializer, an
enumerator's value) is recorded with "pos" "type" where only a type may stand (`Foo x`,
`new Foo`, a cast, `sizeof(Foo)`, a template argument, `Foo::` before a member: no variable
is looked up there) and "receiver" where a value may stand as well (`Foo(1)`, `: Base(1)`,
the parameter of a block-scope function declaration, `Lock l(Tag)`, and every name that is
no type). A member after `.` or `->` is not recorded. "kind" is "type" for a class,
struct, union, enum or class template, with "target" its id as ir.json writes it (anonymous
namespaces left out, a specialisation as its template) and "files" the file defining it;
a typedef or `using` alias is followed as the declared relations follow one: it stands
for every type its written type names, through other aliases ("targets", the first is
"target"; "alias" names it); otherwise what Clang resolved it to: "var" (a parameter or
local variable), "member" (a field or static member), "global", "function", "method",
"enumconst", "tparam", "namespace", "nsalias", "local" (a local or unnamed class),
"dependent" (a name in a template that depends on its parameters: no answer until it
is instantiated), "other". Only a template's pattern is visited, not its instances.
"maximal" is false for a part of a longer name (`A` in `A::B`). "from" is the type the
code is in, as ir.json has it: a member function's class, also where it is defined out of
the class (`void Foo::bar() {}`); a friend function defined in a class is that class's;
a lambda's or a local class's code is the function's around it; a free function and
namespace scope are no type (null). "spec" marks code in a template specialisation, which
the extractor does not read. "macro" "arg" marks a macro's argument; a name a macro's
body writes stands nowhere in the file and is not recorded.

A file several translation units enter (a header) has the answers of all of them: where
every translation unit that compiles the line agrees, that is the record; where they
differ, or one of them compiles the line and records nothing at the place, its kind is
"split": no relation may be drawn there. A line is "not compiled" when no translation
unit compiles it (a file none enters, an `#if` branch none takes); one is enough for its
answer. "header" marks a file only a translation unit made of that header enters. Only a
type defined in the sources is the project's; ids that several types defined in
different files share (two programs' `Benchmark`, types of anonymous namespaces) are
listed as such.

Everything runs in the image the Dockerfile here describes (built as `draftsman-clang`:
Ubuntu 24.04, LLVM 23.1.6, GCC 13's libstdc++, the libraries the e2e repositories'
optional parts need, TypeUses built against that Clang). Nothing is installed on the host
but Docker.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "skills" / "draftsman" / "scripts"))
import answer_key  # noqa: E402
from extract import discover  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "cpp" / "body"
# sets of sources written by hand in reviews, each a directory (`review`)
REVIEW = HERE / "review"
SUFFIXES = (".h", ".hh", ".hpp", ".hxx", ".h++", ".cpp", ".cc", ".cxx", ".c++", ".ipp", ".inl")
UNITS = (".cpp", ".cc", ".cxx", ".c++")
HEADERS = (".h", ".hh", ".hpp", ".hxx", ".h++")
IMAGE = "draftsman-clang"
JOBS = 8   # translation units at once

# as docs/e2e/cpp/ extracts them ("exclude" are extract.py's --exclude); "configure" are
# CMake's arguments, "submodules" whether the checkout's git submodules are needed;
# "extra" are translation units no CMake target compiles, given the flags of another
REPOS = {
    # the tests' targets give the benchmarks gmock's include path (benchmarks/ include
    # util/testutil.h); db_bench_log.cc is in no target, and compiles with db_bench.cc's flags
    "leveldb": {
        "commit": "29465588d3",
        "exclude": ["**/*_test.cc", "**/third_party/**"],
        "configure": ["-DLEVELDB_BUILD_TESTS=ON", "-DLEVELDB_BUILD_BENCHMARKS=ON"],
        "submodules": True,
        "extra": {"benchmarks/db_bench_log.cc": "benchmarks/db_bench.cc"}},
    # every optional component the image has the libraries of; DNSSD_DEFAULT would add
    # Avahi a second time (CMake fails). Windows' (NetSSL_Win, the *_WIN32 files) and other
    # platforms' files are not compiled on Linux
    "poco": {
        "commit": "2ef5cec8a9",
        "exclude": ["**/testsuite/**", "**/samples/**", "**/dependencies/**", "**/fuzzing/**",
                    "CppUnit/**", "Benchmark/**", "Data/SQLParser/**", "Data/DataTest/**"],
        "configure": ["-DENABLE_TESTS=OFF", "-DENABLE_SAMPLES=OFF", "-DENABLE_TRACE=ON",
                      "-DENABLE_SSH=ON", "-DENABLE_AI=ON", "-DENABLE_AI_MCP=ON",
                      "-DENABLE_AI_MCP_HTTP=ON", "-DENABLE_XSD_VALIDATOR=ON",
                      "-DENABLE_ENCODINGS_COMPILER=ON", "-DENABLE_DNSSD=ON",
                      "-DENABLE_DNSSD_AVAHI=ON", "-DENABLE_DNSSD_BONJOUR=ON",
                      "-DENABLE_SEVENZIP=ON", "-DENABLE_CPPPARSER=ON", "-DENABLE_POCODOC=ON",
                      "-DENABLE_PDF=ON"],
        "submodules": False,
        "extra": {}},
}
CMAKE = ["-G", "Ninja", "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON", "-DCMAKE_C_COMPILER=clang",
         "-DCMAKE_CXX_COMPILER=clang++", "-DCMAKE_BUILD_TYPE=Debug"]
# what `key DIR` compiles each translation unit with
KEY_FLAGS = ["-std=c++17", "-fsyntax-only"]

# the kinds TypeUses gives that are answers as they are
KINDS = {"tparam", "var", "member", "global", "function", "method", "enumconst", "namespace",
         "nsalias", "dependent", "local", "concept", "other"}


def image() -> None:
    """Build the image (Docker's cache makes it quick once built)."""
    subprocess.run(["docker", "build", "-q", "-t", IMAGE, HERE], check=True,
                   stdout=subprocess.DEVNULL)


def container(cmd: list[str], mounts: dict[str, str], cwd: str = "/work", check: bool = True,
              capture: bool = False) -> subprocess.CompletedProcess:
    args = ["docker", "run", "--rm", "-w", cwd]
    for source, target in mounts.items():
        args += ["-v", f"{source}:{target}"]
    return subprocess.run(args + [IMAGE, *cmd], check=check, text=True,
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.STDOUT if capture else None)


# -- running TypeUses ------------------------------------------------------------------------

DIAGNOSTIC = re.compile(r"^/src/(.+?):(\d+):\d+: (?:fatal )?error: (.*)$")


def diagnostics(text: str) -> list[dict]:
    seen, out = set(), []
    for line in text.splitlines():
        m = DIAGNOSTIC.match(line)
        if m and m.groups() not in seen:
            seen.add(m.groups())
            out.append({"diagnostic": m.group(3), "file": m.group(1), "line": int(m.group(2))})
    return out


# -- joining the translation units -----------------------------------------------------------

def _utf16_cols(root: Path):
    lines: dict[str, list[bytes]] = {}

    def col(file: str, line: int, byte: int) -> int:
        if file not in lines:
            lines[file] = (root / file).read_bytes().split(b"\n")
        text = lines[file][line - 1][:byte] if line <= len(lines[file]) else b""
        if text.isascii():
            return byte
        return len(text.decode("utf-8", "replace").encode("utf-16-le")) // 2
    return col


class Aliases:
    """What each alias of the sources names, as Clang resolved its written type: by the
    declaration (id, file, line), as several classes of one id may each declare one."""

    def __init__(self):
        self.names: dict[tuple, list] = {}

    def add(self, r: dict) -> None:
        self.names.setdefault((r["aliasdecl"], r["f"], str(r["l"])), r["names"])

    def targets(self, alias: tuple, defined: set, depth: int = 0, seen=None) -> list[str]:
        """The project types an alias names, through other aliases (as _expand_alias)."""
        seen = set() if seen is None else seen
        if alias in seen or depth > 4:
            return []
        seen.add(alias)
        out: list[str] = []
        for kind, ident, file, line in self.names.get(alias, ()):
            if kind == "type" and ident in defined:
                out.append(ident)
            elif kind == "alias":
                out += self.targets((ident, file, line), defined, depth + 1, seen)
        return list(dict.fromkeys(out))


def convert(r: dict, defined: set, aliases: Aliases) -> dict:
    """The key's record of a name TypeUses recorded (module docstring). ``defined``: the ids
    of the types the sources define (one only declared there, `struct bignum_st;`, is no
    type of them; one a unit sees only declared, `class PooledThread;`, is)."""
    out = {"use": r["n"], "file": r["f"], "line": r["l"], "col": r["c"], "pos": r["pos"],
           "maximal": bool(r["max"]), "from": r["from"] or None}
    k = r["k"]
    if k == "type":
        out.update(kind="type", target=r["t"], project=r["t"] in defined and r["tf"] != "<macro>",
                   files=[r["tf"]])
    elif k == "alias":
        file, _, line = r["tf"].rpartition(":")
        targets = aliases.targets((r["t"], file, line), defined)
        out.update(kind="type", target=targets[0] if targets else r["t"],
                   project=bool(targets), alias=r["t"], files=[])
        if len(targets) > 1:
            out["targets"] = targets
    else:
        out.update(kind=k if k in KINDS else "other", target=r["t"] or None, project=False)
    if r["spec"]:
        out["spec"] = True
    if r["m"]:
        out["macro"] = r["m"]
    return out


def _answer(r: dict) -> tuple:
    """What translation units must agree on."""
    return (r["k"], r["t"] if r["k"] in ("type", "alias") else None, r["pos"], r["max"],
            r["from"], r["spec"])


def join(raw: Path, files: list[str], root: Path, headers: set = frozenset()) -> list[dict]:
    """The records TypeUses wrote below ``raw`` (one file per translation unit), joined
    into one per place (module docstring). ``files`` are the sources, below ``root``;
    ``headers`` the translation units that are a header of its own."""
    scope = set(files)
    aliases = Aliases()
    entered: Counter = Counter()           # file -> translation units entering it
    by_header: Counter = Counter()         # the same, header units only
    skipped: Counter = Counter()           # (file, line) -> units that skip it
    at: dict[tuple, dict] = {}             # place -> answer -> [count, record]
    declared: dict[tuple, dict] = {}
    classes: dict[tuple, dict] = {}
    units, failed, twice = [], [], 0
    for path in sorted(raw.glob("*.jsonl")):
        recs = [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
        tu = next((r for r in recs if "tu" in r), None)
        if tu is None:
            continue
        is_header = tu["tu"] in headers
        if is_header and tu["rc"]:
            # a header that does not compile on its own (Windows', a sketch of a port)
            # is no more compiled than before
            failed.append(Path(tu["tu"]).name)
            continue
        units.append(tu)
        main = tu["tu"][len("/src/"):] if tu["tu"].startswith("/src/") else None
        enter = {r["inc"] for r in recs if "inc" in r}
        if main in scope:
            enter.add(main)
        for f in enter:
            entered[f] += 1
            if is_header:
                by_header[f] += 1
        skips: set = set()
        for r in recs:
            if "skip" in r and r["skip"] in scope:
                skips.update((r["skip"], line) for line in range(r["l1"], r["l2"] + 1))
        for k in skips:
            skipped[k] += 1
        here: dict[tuple, dict] = {}
        for r in recs:
            if "n" in r:
                if r["f"] not in scope:
                    continue
                place = (r["f"], r["l"], r["c"])
                if place in here:
                    twice += 1
                    if here[place]["k"] in ("type", "alias"):
                        continue   # one name, two records: the type wins
                here[place] = r
            elif "aliasdecl" in r:
                aliases.add(r)
            elif "decl" in r and r["f"] in scope:
                declared.setdefault((r["decl"], r["f"], r["l"]), r)
            elif "cls" in r and r["f"] in scope:
                classes.setdefault((r["cls"], r["f"]), r)
        for place, r in here.items():
            by = at.setdefault(place, {})
            a = _answer(r)
            if a in by:
                by[a][0] += 1
            else:
                by[a] = [1, r]
    col = _utf16_cols(root)
    defined = {ident for ident, _, _ in declared}
    out: list[dict] = [{"units": len(units), "errors": sum(1 for u in units if u["rc"]),
                        "failed": sorted(u["tu"] for u in units if u["rc"]),
                        "headers failed": len(failed)}]
    for (ident, f, line), d in sorted(declared.items()):
        out.append({"declared": ident, "file": f, "line": line, "kind": d["kind"],
                    **({"anonymous": True} if d["anon"] else {})})
    for (ident, f), c in sorted(classes.items()):
        out.append({"class": ident, "file": f, "bases": c["bases"]})
    for (alias, f, line), names in sorted(aliases.names.items()):
        out.append({"alias": alias, "file": f, "line": int(line), "names": names})
    for place, by in sorted(at.items()):
        f, line, _ = place
        compiling = entered[f] - skipped[(f, line)]
        first = next(iter(by.values()))[1]
        rec = convert(first, defined, aliases)
        rec["col"] = col(f, line, first["c"])
        rec["units"] = compiling
        if by_header[f] and by_header[f] == entered[f]:
            rec["header"] = True
        if len(by) > 1 or sum(n for n, _ in by.values()) != compiling:
            said = Counter()
            for n, r in by.values():
                c = convert(r, defined, aliases)
                said[f"{answer_key.answer(c)} {c['pos']} in {c['from']}"] += n
            missing = compiling - sum(n for n, _ in by.values())
            if missing > 0:
                said["none"] += missing
            rec.update(kind="split", target=None, project=False, answers=dict(said))
            rec.pop("targets", None)
        out.append(rec)
    if twice:
        out.append({"twice": twice})
    for f in sorted(scope):
        if not entered[f]:
            out.append({"uncompiled": f, "lines": "all"})
        else:
            lines = sorted(line for (g, line), n in skipped.items() if g == f and n >= entered[f])
            if lines:
                out.append({"uncompiled": f, "lines": lines})
    return out


def expected(root: Path) -> dict[tuple[str, int, int], tuple[str, str]]:
    return answer_key.expected(root, SUFFIXES)


# -- a directory ----------------------------------------------------------------------------

def _header_units(headers: list[str], work: Path, flags_of) -> tuple[list, list]:
    """A translation unit of its own for each of ``headers``: (compile entries, unit paths
    in the container), with the flags ``flags_of(header)`` gives (None: none)."""
    entries, units = [], []
    (work / "hdr").mkdir(exist_ok=True)
    for f in headers:
        got = flags_of(f)
        if got is None:
            continue
        directory, args = got
        name = re.sub(r"[^\w.]", "_", f) + ".cpp"
        (work / "hdr" / name).write_text(f'#include "/src/{f}"\n')
        unit = f"/work/hdr/{name}"
        entries.append({"directory": directory, "file": unit, "arguments": [*args, "-c", unit]})
        units.append(unit)
    return entries, units


INCLUDE = re.compile(r'^[ \t]*#[ \t]*include[ \t]*[<"]([^>"]+)[>"]', re.M)


def _included(root: Path, files: list[str]) -> dict[str, list[tuple[str, int]]]:
    """Where each header of ``files`` is included in them: (file, line)s, by the path
    written matched as a suffix (`"Poco/Mutex_VX.h"`)."""
    headers = [f for f in files if f.endswith(HEADERS)]
    by_tail: dict[str, list[str]] = defaultdict(list)
    for h in headers:
        parts = h.split("/")
        for k in range(len(parts)):
            by_tail["/".join(parts[k:])].append(h)
    out: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for f in files:
        text = (root / f).read_text(errors="replace")
        for m in INCLUDE.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            for h in by_tail.get(m.group(1), ()):
                out[h].append((f, line))
    return out


def _skipped(raw: Path) -> tuple[set[str], dict[str, set[int]]]:
    """The files the units below ``raw`` enter, and per file the lines every unit that
    enters it skips."""
    entered: Counter = Counter()
    skipped: Counter = Counter()
    for path in raw.glob("*.jsonl"):
        enter, skips = set(), set()
        for line in path.read_text().splitlines():
            r = json.loads(line)
            if "inc" in r:
                enter.add(r["inc"])
            elif "tu" in r and r["tu"].startswith("/src/"):
                enter.add(r["tu"][len("/src/"):])
            elif "skip" in r:
                skips.update((r["skip"], n) for n in range(r["l1"], r["l2"] + 1))
        entered.update(enter)
        skipped.update(skips)
    lines: dict[str, set[int]] = defaultdict(set)
    for (f, n), k in skipped.items():
        if k >= entered[f]:
            lines[f].add(n)
    return set(entered), lines


def _unincluded(root: Path, files: list[str], raw: Path) -> list[str]:
    """The headers no unit entered and no compiled line includes: a header of a platform
    is included in an `#if` branch no unit takes (`Mutex_VX.h`), and stays not compiled;
    one nobody includes (a template only tests use) is compiled on its own."""
    entered, skipped = _skipped(raw)
    sites = _included(root, files)
    out = []
    for f in files:
        if not f.endswith(HEADERS) or f in entered:
            continue
        if any(g not in entered or n in skipped.get(g, ()) for g, n in sites.get(f, ())):
            continue   # included where nothing is compiled
        out.append(f)
    return out


def key_dir(directory: Path, out: Path) -> list[dict]:
    """The key for any directory (module docstring)."""
    image()
    directory = directory.resolve()
    files = [rel for _, rel in discover(directory, {"cpp"}, [])]
    if not files:
        sys.exit(f"oracle: no C++ file below {directory}")
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        (work / "raw").mkdir()
        args = ["clang++", *KEY_FLAGS, "-I/src"]
        units = [f"/src/{f}" for f in files if f.endswith(UNITS)]
        db = [{"directory": "/src", "file": u, "arguments": [*args, "-c", u]} for u in units]
        mounts = {str(directory): "/src", str(work): "/work"}
        (work / "names.txt").write_text("\n".join(type_names(directory, discover(directory, {"cpp"}, []))))
        text = ""
        if units:
            text += run_units(units, db, mounts, "/work/names.txt", "units")
        entries, hdrs = _header_units(_unincluded(directory, files, work / "raw"), work,
                                      lambda f: ("/src", args))
        if hdrs:   # (one that fails is left out, and so are its errors)
            run_units(hdrs, db + entries, mounts, "/work/names.txt", "headers")
        recs = join(work / "raw", files, directory, set(hdrs))
    recs[:0] = [{"config": {"directory": str(directory), "flags": KEY_FLAGS}}]
    recs += diagnostics(text)
    out.write_text("".join(json.dumps(r) + "\n" for r in recs))
    return recs


def run_units(units: list[str], entries: list[dict], mounts: dict[str, str],
              names: Optional[str], tag: str) -> str:
    """TypeUses on ``units`` with the compile commands ``entries``, into /work/raw; Clang's
    messages. Each run's files have names of their own (``tag``): Docker Desktop's bind
    mount may show a file the host rewrote in part, which cut a compile database and a
    list of units short (`key` on review/cpp3 ran a unit `/work/hdr`)."""
    work = next(Path(h) for h, c in mounts.items() if c == "/work")
    (work / f"db-{tag}").mkdir(exist_ok=True)
    (work / f"db-{tag}" / "compile_commands.json").write_text(json.dumps(entries))
    (work / f"units-{tag}.txt").write_text("".join(u + "\n" for u in units))
    args = ["/opt/type-uses/type-uses", "-p", f"/work/db-{tag}", "-root", "/src", "-out",
            "/work/raw", '"--extra-arg=-resource-dir=$(clang -print-resource-dir)"']
    args += ["-names", names] if names else ["-all"]
    container(["bash", "-c", f"xargs -P {JOBS} -n 8 {' '.join(args)} < /work/units-{tag}.txt "
                             f"2> /work/stderr-{tag}.log; exit 0"], mounts)
    return (work / f"stderr-{tag}.log").read_text(errors="replace")


def selftest(_args) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        recs = key_dir(FIXTURE, Path(tmp, "fixture.jsonl"))
    for r in recs:
        if r.get("kind") == "split":
            print(f"split: {r['file']}:{r['line']}:{r['col'] + 1} {r['use']}: {r['answers']}")
    return answer_key.selftest(recs, expected(FIXTURE))


def key(args) -> int:
    out = args.output or Path(tempfile.mkstemp(suffix=".jsonl")[1])
    recs = key_dir(args.directory, out)
    summary(recs, str(args.directory))
    print(f"written to {out}")
    if not args.compare:
        return 0
    root = args.directory.resolve()
    return check(root, discover(root, {"cpp"}, []), recs, args.verbose)


def review(args) -> int:
    """Every set of hand-written sources below review/ through `key --compare`: the names
    drawn and the mismatches of each. Fails on a mismatch review/README.md does not list
    as a known limit (`- `set/file:line:col``) and on fewer names drawn than it lists for
    the set (`| `set` | n |`). A set compiles without errors: a mismatch in a file with
    compile errors counts too."""
    import contextlib
    import io
    readme = (REVIEW / "README.md").read_text()
    limits = readme.split("Known limits", 1)[-1].split("Names Clang finds", 1)[0]
    known = set(re.findall(r"^- `([^`]+)`", limits, re.M))
    counts = {k: int(v) for k, v in re.findall(r"^\| `(\w+)` \| (\d+) \|", readme, re.M)}
    sets = sorted((d for d in REVIEW.iterdir() if d.is_dir() and not args.sets
                   or d.name in (args.sets or ())), key=lambda d: (len(d.name), d.name))
    new, seen = [], set()
    for d in sets:
        with tempfile.TemporaryDirectory() as tmp:
            text = io.StringIO()
            with contextlib.redirect_stdout(text), contextlib.redirect_stderr(io.StringIO()):
                recs = key_dir(d, Path(tmp, "key.jsonl"))
                check(d.resolve(), discover(d.resolve(), {"cpp"}, []), recs, True)
        out = text.getvalue()
        drawn = re.search(r"compare: (\d+) names drawn", out)
        wrong = re.findall(r"^  (?:mismatch|in a file with compile errors): (\S+)", out, re.M)
        places = list(dict.fromkeys(f"{d.name}/{w.rstrip(':')}" for w in wrong))
        seen.update(places)
        fresh = [p for p in places if p not in known]
        new += fresh
        n = int(drawn.group(1)) if drawn else 0
        fewer = d.name in counts and n < counts[d.name]
        if fewer or not drawn:
            new.append(d.name)
        errors = sum(1 for r in recs if "diagnostic" in r)
        print(f"{d.name}: {n if drawn else '?'} names drawn, {len(places)} mismatches"
              + (f", {errors} compile errors" if errors else "")
              + (f", {len(fresh)} not among the known limits" if fresh else "")
              + (f", fewer than the {counts[d.name]} README.md lists" if fewer else "")
              + (" (scope check failed)" if not drawn else ""))
        for line in out.splitlines():
            m = re.match(r"  (?:mismatch|in a file with compile errors): (\S+)", line)
            if m and f"{d.name}/{m.group(1).rstrip(':')}" in fresh:
                print(line)
        for r in recs:
            if "diagnostic" in r:
                print(f"  compile error: {r['file']}:{r['line']}: {r['diagnostic']}")
    gone = sorted(k for k in known if k.split("/", 1)[0] in {d.name for d in sets} and k not in seen)
    for k in gone:
        print(f"known limit no longer a mismatch: {k}")
    return 1 if new else 0


# -- a repository ---------------------------------------------------------------------------

def sources(repo: str, checkout: Path) -> list[tuple[Path, str]]:
    return discover(checkout, {"cpp"}, REPOS[repo]["exclude"])


def type_names(checkout: Path, files: list[tuple[Path, str]]) -> list[str]:
    """The simple names of the sources' types and aliases: the names TypeUses records
    whatever they resolve to (a name of anything else is no relation the extractor draws)."""
    from draftsman.extractor import Extractor
    from draftsman.langs import spec_for_path
    names = set()
    for path, rel in files:
        rf = Extractor(spec_for_path(rel)).extract(path, rel, checkout)
        names |= {t.name for t in rf.types}
        names |= {a.rsplit("::", 1)[-1] for a in rf.scope.aliases}
    return sorted(names)


def summary(recs: list[dict], name: str) -> None:
    head = next((r for r in recs if "units" in r and "use" not in r), {"units": 0, "errors": 0})
    errors = [r for r in recs if "diagnostic" in r]
    uses = Counter(r["kind"] for r in recs if "use" in r)
    print(f"{name}: {head['units']} translation units ({head['errors']} with errors), "
          f"{len(errors)} compile errors in the sources ({len({r['file'] for r in errors})} files); "
          "names: " + ", ".join(f"{k} {v}" for k, v in uses.most_common()))
    for unit in head.get("failed", ()):
        print(f"  with errors: {unit}")
    for r in errors[:20]:
        print(f"  {r['file']}:{r['line']}: {r['diagnostic']}")
    unc = [r for r in recs if "uncompiled" in r]
    whole = [r["uncompiled"] for r in unc if r["lines"] == "all"]
    lines = sum(len(r["lines"]) for r in unc if r["lines"] != "all")
    print(f"not compiled: {len(whole)} files, and {lines} lines in {len(unc) - len(whole)} files")
    header = {r["file"] for r in recs if r.get("header")}
    if header or head.get("headers failed"):
        print(f"entered only by a translation unit of their own: {len(header)} headers; "
              f"such units that do not compile, left out: {head.get('headers failed', 0)}")
    for r in recs:
        if "twice" in r:
            print(f"places with two names in one translation unit (the type kept): {r['twice']}")


def run(args) -> int:
    conf = REPOS[args.repo]
    checkout = args.checkout.resolve()
    files = [rel for _, rel in sources(args.repo, checkout)]
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(args.raw.resolve() if args.raw else Path(tmp))
        raw = work / "raw"
        if not args.rejoin:
            image()
            if raw.exists():
                shutil.rmtree(raw)
            raw.mkdir(parents=True)
            mounts = {str(checkout): "/src", str(work): "/work"}
            if conf["submodules"]:
                subprocess.run(["git", "-C", str(checkout), "submodule", "update", "--init", "-q"],
                               check=True)
            container(["bash", "-c", "rm -rf /work/build && cmake -S /src -B /work/build "
                       + " ".join(CMAKE + conf["configure"]) + " > /work/cmake.log 2>&1"], mounts)
            db = json.loads((work / "build" / "compile_commands.json").read_text())
            scope = set(files)
            # one command per file: a file two targets compile (leveldb's util/ in the
            # library and in the tests) is one unit, with its first command
            entries = list({e["file"]: e for e in reversed(db) if e["file"].startswith("/src/")
                            and e["file"][len("/src/"):] in scope}.values())
            for extra, like in conf["extra"].items():
                e = next(e for e in db if e["file"] == f"/src/{like}")
                entries.append({**e, "file": f"/src/{extra}",
                                "command": e["command"].replace(like, extra),
                                "output": e["output"].replace(like.rsplit("/", 1)[-1],
                                                              extra.rsplit("/", 1)[-1])})
            units = sorted({e["file"] for e in entries})
            (work / "names.txt").write_text("\n".join(type_names(checkout, sources(args.repo, checkout))))
            text = run_units(units, entries, mounts, "/work/names.txt", "units")

            def flags_of(header: str):
                # the flags of a unit of the same component (the path before include/, src/)
                part = re.split(r"/(?:include|src)/", header)[0]
                like = [e for e in entries if e["file"][len("/src/"):].startswith(part + "/src/")] \
                    or [e for e in entries if e["file"][len("/src/"):].startswith(part + "/")] \
                    or entries
                e = like[0]
                args_ = e.get("arguments") or e["command"].split()
                cut, skip = [], False
                for a in args_:
                    if skip:
                        skip = False
                    elif a in ("-o", "-c"):
                        skip = a == "-o"
                    elif a != e["file"]:
                        cut.append(a)
                return e["directory"], cut
            hdr_entries, hdrs = _header_units(_unincluded(checkout, files, raw), work, flags_of)
            if hdrs:   # (one that fails is left out, and so are its errors)
                run_units(hdrs, entries + hdr_entries, mounts, "/work/names.txt", "headers")
            (work / "stderr.txt").write_text(text)
            (work / "headers.json").write_text(json.dumps(hdrs))
            config = {"repo": args.repo, "commit": conf["commit"], "configure": conf["configure"],
                      "units": len(units), "header units": len(hdrs)}
            (work / "config.json").write_text(json.dumps(config))
        config = json.loads((work / "config.json").read_text())
        recs = join(raw, files, checkout, set(json.loads((work / "headers.json").read_text())))
        recs += diagnostics((work / "stderr.txt").read_text())
    recs.insert(0, {"config": config})
    args.output.write_text("".join(json.dumps(r) + "\n" for r in recs))
    summary(recs, args.repo)
    return 0


def declared_files(recs: list[dict]) -> dict[str, set[str]]:
    files: dict[str, set[str]] = defaultdict(set)
    for r in recs:
        if "declared" in r:
            files[r["declared"]].add(r["file"])
    return files


def merged(recs: list[dict]) -> dict[str, set[str]]:
    """Ids several types defined in different files share: one type of ir.json."""
    return {t: fs for t, fs in declared_files(recs).items() if len(fs) > 1}


def in_scope(recs: list[dict], ir: dict[str, str], lines: dict[str, int] = {}) -> int:
    """answer_key.in_scope, a type of several files (types of one id) taken as declared in
    any of them: ir.json gives one file for an id. Types declared in a file or in lines no
    translation unit compiles are not seen, and listed as such."""
    seen = declared_files(recs)
    whole = {r["uncompiled"] for r in recs if "uncompiled" in r and r["lines"] == "all"}
    # ir.json's file for an id may be one no unit compiles (port_example.h's Mutex, beside
    # port_stdcxx.h's): the type of the compiled one is the same id's
    flat = [{"declared": t, "file": ir[t] if t in ir and (ir[t] in fs or ir[t] in whole)
             else sorted(fs)[0]} for t, fs in seen.items()]
    for t, fs in sorted(seen.items()):
        if t in ir and ir[t] in whole and ir[t] not in fs:
            print(f"known: {t}: ir.json's file {ir[t]} no unit compiles; Clang's is "
                  f"{', '.join(sorted(fs))}")
    for t, fs in sorted(merged(recs).items()):
        print(f"{len(fs)} types of one id: {t}: {', '.join(sorted(fs))}"
              + (f" (ir.json: one type, at {ir[t]})" if t in ir else ""))
    unseen = {t: f"declared in {f}, which no translation unit compiles"
              for t, f in ir.items() if f in whole and t not in seen}
    skipped = {r["uncompiled"]: set(r["lines"]) for r in recs
               if "uncompiled" in r and r["lines"] != "all"}
    unseen.update({t: f"declared in lines of {f} no translation unit compiles (line {lines[t]})"
                   for t, f in ir.items() if t not in seen and t in lines
                   and lines[t] in skipped.get(f, ())})
    return answer_key.in_scope(flat, ir, unseen, language="C++")


def scope(args) -> int:
    types = [t for t in json.loads(args.ir.read_text())["types"] if t["language"] == "cpp"]
    return in_scope(answer_key.read(args.oracle), {t["id"]: t["location"]["file"] for t in types},
                    {t["id"]: t["location"]["line"] for t in types})


def uncompiled(recs: list[dict]) -> dict:
    return {r["uncompiled"]: r["lines"] if r["lines"] == "all" else set(r["lines"])
            for r in recs if "uncompiled" in r}


def apart(ids: dict):
    """Why a key's answer that differs is no mismatch: the translation units differ, the
    name depends on a template's parameters, or the type is one of several of its id."""
    def why(r: dict) -> Optional[str]:
        if r["kind"] == "split":
            return "split between translation units"
        if r["kind"] == "dependent":
            return "a dependent name"
        if r["kind"] == "type" and r["target"] in ids:
            return "one id, several types"
        return None
    return why


def check(root: Path, files: list[tuple[Path, str]], recs: list[dict], verbose: bool) -> int:
    from draftsman.extractor import Extractor
    from draftsman.langs import spec_for_path
    from draftsman.resolve import _Builder
    from draftsman.wrappers import Wrappers

    raw = [Extractor(spec_for_path(rel)).extract(f, rel, root) for f, rel in files]
    builder = _Builder(str(root), raw, Wrappers.load())
    ir = builder.build()
    where = {t.id: t.location.file for t in ir.types if t.language == "cpp"}
    if in_scope(recs, where, {t.id: t.location.line for t in ir.types if t.language == "cpp"}):
        return 1
    ids = merged(recs)
    defined = declared_files(recs)

    def same(r: dict, dst: str) -> bool:
        # the file defining the key's type is one of those ir.json makes the id of; a type
        # only declared there (`class DeclHandler;`) is the id's too
        files = set(r.get("files", ()))
        if not r["project"]:
            return False   # a type outside the sources of the id (a system's `ip_mreq`)
        return r["target"] in ids or bool(r.get("targets")) or not files & defined.get(r["target"], set()) \
            or files <= builder.part_files.get(dst, set())

    # code outside every type and a template specialisation's draw nothing: no miss
    rc = answer_key.compare(builder.body_uses, recs, verbose, key="Clang", same=same,
                            drawable=lambda r: answer_key.drawable(r) and r["from"] is not None
                            and not r.get("spec"),
                            uncompiled=uncompiled(recs), apart=apart(ids))
    header = {r["file"] for r in recs if r.get("header")}
    uses = {(r["file"], r["line"], r["col"]): r for r in recs if "use" in r}
    drawn = Counter()
    for file, line, col, _, _ in builder.body_uses:
        r = uses.get((file, line, col))
        if file in header:
            drawn["in headers only a unit of their own compiles"] += 1
        if r is not None and r.get("alias"):
            drawn["through an alias"] += 1
        if r is not None and r.get("target") in ids:
            drawn["of an id several types share"] += 1
    if drawn:
        print("  of the names drawn: " + ", ".join(f"{k} {v}" for k, v in sorted(drawn.items())))
    return rc


def compare(args) -> int:
    checkout = args.checkout.resolve()
    return check(checkout, sources(args.repo, checkout), answer_key.read(args.oracle), args.verbose)


def measure(args) -> int:
    recs = answer_key.read(args.oracle)
    uses = [r for r in recs if "use" in r]
    declared: set = set()
    if args.ir:
        declared = {(r["from"], r["to"]) for r in json.loads(args.ir.read_text())["relations"]}
    split = [r for r in uses if r["kind"] == "split"]
    print(f"names recorded: {len(uses)}; in several translation units: "
          f"{sum(1 for r in uses if r['units'] > 1)}, of which split: {len(split)}")
    for r in split[:None if args.verbose else 10]:
        print(f"  split: {r['file']}:{r['line']}:{r['col'] + 1} {r['use']}: {r['answers']}")

    def project(r: dict) -> bool:
        return answer_key.drawable(r) and r["from"] is not None and not r.get("spec")

    def count(rs) -> str:
        rs = list(rs)
        p = {(r["from"], t) for r in rs if project(r) for t in r.get("targets") or [r["target"]]}
        text = f"{sum(map(project, rs))} uses, {len(p)} relations"
        return text + (f" ({len(p - declared)} not in ir.json)" if args.ir else "")

    whole = [r for r in uses if answer_key.drawable(r)]
    print(f"project types named in bodies of types: {count(uses)}; outside every type: "
          f"{sum(1 for r in whole if r['from'] is None)}; in template specialisations: "
          f"{sum(1 for r in whole if r.get('spec') and r['from'] is not None)}")
    for position in ("type", "receiver"):
        print(f"  {position} position: {count(r for r in uses if r['pos'] == position)}")
    print(f"  through an alias: {count(r for r in uses if r.get('alias'))}; "
          f"in a macro's argument: {count(r for r in uses if r.get('macro'))}; "
          f"in headers only a unit of their own compiles: {count(r for r in uses if r.get('header'))}")
    ids = merged(recs)
    print(f"  of an id several types share: {count(r for r in uses if r.get('target') in ids)} "
          f"({len(ids)} ids)")
    names = {d["declared"].rsplit("::", 1)[-1] for d in recs if "declared" in d}
    shadows = Counter(r["kind"] for r in uses if r["kind"] not in ("type", "split")
                      and r["use"] in names)
    print("names of a project type resolved to something else: "
          + ", ".join(f"{k} {v}" for k, v in shadows.most_common()))
    other = Counter(r["target"] for r in uses
                    if r["kind"] == "type" and not r["project"] and r["use"] in names)
    print(f"names of a project type resolved to a type outside the sources: {sum(other.values())} ("
          + ", ".join(f"{k} {v}" for k, v in other.most_common(8)) + ")")
    return 0


# the table of the `std` classes a class of the sources may derive from (`table`)
TABLE = ROOT / "skills" / "draftsman" / "scripts" / "draftsman" / "langs" / "cpp_std.json"
TABLE_STANDARD = "c++17"


def table(_args) -> int:
    """Write the extractor's table of `std` classes (TypeUses -table: module docstring)."""
    image()
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        (work / "std.cpp").write_text("#include <bits/stdc++.h>\n")
        container(["bash", "-c", "/opt/type-uses/type-uses -table /work/table.json /work/std.cpp "
                   f"-- -std={TABLE_STANDARD} -resource-dir $(clang -print-resource-dir)"],
                  {str(work): "/work"})
        got = json.loads((work / "table.json").read_text())
        gcc = container(["bash", "-c", "g++ -dumpfullversion"], {str(work): "/work"},
                        capture=True).stdout.strip()
    out = {"read from": {"library": f"libstdc++ of GCC {gcc} (Ubuntu 24.04)",
                         "standard": TABLE_STANDARD, "headers": "<bits/stdc++.h>"},
           "aliases": dict(sorted(got["aliases"].items())),
           "types": {t: {"bases": v["bases"], "members": v["members"], "types": v["types"]}
                     for t, v in sorted(got["types"].items())}}
    TABLE.write_text(json.dumps(out, indent=0) + "\n")
    print(f"{TABLE.relative_to(ROOT)}: {TABLE.stat().st_size // 1024} KB, {len(out['types'])} "
          f"classes, {len(out['aliases'])} aliases, "
          f"{sum(len(v['members']) for v in out['types'].values())} member names")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest").set_defaults(fn=selftest)
    d = sub.add_parser("key")
    d.add_argument("directory", type=Path)
    d.add_argument("-o", "--output", type=Path)
    d.add_argument("--compare", action="store_true",
                   help="check the extractor's body relations of the same files against it")
    d.add_argument("-v", "--verbose", action="store_true", help="list every miss and mismatch")
    d.set_defaults(fn=key)
    v = sub.add_parser("review")
    v.add_argument("sets", nargs="*", help="only these sets (directory names below review/)")
    v.set_defaults(fn=review)
    r = sub.add_parser("run")
    r.add_argument("repo", choices=sorted(REPOS))
    r.add_argument("--checkout", type=Path, required=True)
    r.add_argument("-o", "--output", type=Path, required=True)
    r.add_argument("--raw", type=Path, help="keep the build and TypeUses' records in this directory")
    r.add_argument("--rejoin", action="store_true",
                   help="join the records --raw keeps again, without running Clang")
    r.set_defaults(fn=run)
    c = sub.add_parser("scope")
    c.add_argument("repo", choices=sorted(REPOS))
    c.add_argument("oracle", type=Path)
    c.add_argument("ir", type=Path, help="ir.json of the repository's e2e scope")
    c.set_defaults(fn=scope)
    k = sub.add_parser("compare")
    k.add_argument("repo", choices=sorted(REPOS))
    k.add_argument("oracle", type=Path)
    k.add_argument("--checkout", type=Path, required=True)
    k.add_argument("-v", "--verbose", action="store_true", help="list every miss and mismatch")
    k.set_defaults(fn=compare)
    m = sub.add_parser("measure")
    m.add_argument("oracle", type=Path)
    m.add_argument("--ir", type=Path, help="ir.json of the same sources: count only what it lacks")
    m.add_argument("-v", "--verbose", action="store_true", help="list the splits")
    m.set_defaults(fn=measure)
    sub.add_parser("table", help="write the extractor's table of the std classes"
                   ).set_defaults(fn=table)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
