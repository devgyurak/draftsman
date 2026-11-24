"""The Kotlin compiler as the answer key for Kotlin body relations (issue #5).

TypeUses/ is a compiler plugin (K2): once a file is resolved it records what every name
in it was resolved to, once per compilation (a Gradle compile task, or a directory given to
the compiler). This script runs it in a container, turns its records into the format
bench/answer_key.py gives and joins the compilations each file is in.

    uv run bench/kotlin_oracle/oracle.py selftest
    uv run bench/kotlin_oracle/oracle.py key DIR [-o OUT.jsonl] [--compare] [-v]
    uv run bench/kotlin_oracle/oracle.py review [SET ...]
    uv run bench/kotlin_oracle/oracle.py run REPO --checkout DIR -o OUT.jsonl [--raw DIR [--rejoin]]
    uv run bench/kotlin_oracle/oracle.py scope REPO OUT.jsonl ir.json
    uv run bench/kotlin_oracle/oracle.py compare REPO OUT.jsonl --checkout DIR [-v]
    uv run bench/kotlin_oracle/oracle.py measure OUT.jsonl [--ir ir.json]

`selftest` checks the key against the hand-written answers in tests/fixtures/kotlin/body
(tests/fixtures/java/body/README.md gives the marker format). `key` answers for any
directory: its `.kt` files are compiled together for the JVM, with the standard library
alone on the classpath, and `--compare` checks the extractor's body relations of the same
files against it; `review` does that for every set of sources reviews wrote by hand
(review/, one directory each) and fails on a mismatch review/README.md does not list as a
known limit. `run` builds a repository's main code with its own Gradle build, the plugin
put into every Kotlin compile task, and records the sources its end-to-end page extracts
(docs/e2e/kotlin/); it takes the network. `scope` fails unless the key saw the same types,
declared in the same files, as ir.json of those sources. `compare` extracts the same
sources and checks every name a body relation is drawn from against what the compiler
resolved at its place. `measure` prints what the rules for hiding names are decided by.

What a record says. A name in a body (a function's body, an initializer, a default
argument, an `init` block, a constructor's delegation) is recorded with "pos" "type" when
only a type can stand there (`val x: Foo`, `is Foo`, `<Foo>`) and "receiver" when a value
can too (`Foo(...)`, `Foo.x`, `Foo::class`, a name alone); member names after a `.` are
not recorded, but a nested class's constructor (`Outer.Inner()`) is. "kind" is "type"
when the name is a class, interface, object, typealias, or a constructor of one (also
through a typealias, and a SAM constructor), with "target" its id as ir.json writes it (a
typealias is the class it stands for, as ir.json resolves through it, and "alias" names
it; an `actual typealias` is the `expect class` of its id);
otherwise what the compiler resolved it to: "function", "property", "var" (a parameter
or local variable), "enumEntry", "tparam", "local" (a local class), "package", "label",
"error". "resolved" keeps the compiler's own kind (constructor, companion, object, ...),
"role" where a qualifier stands (receiver of `.x`, class literal, value, the receiver of
an `invoke` operator: `Foo("s")` calling Foo's companion's `invoke`). "maximal" is false
for a part of a longer type name (`Outer` in `Outer.Inner` and `Outer.Inner()`). "from"
is the named type the code is in, as ir.json has it: an anonymous object, an enum entry's
body and a local class are in the type around them; a companion object without
supertypes is folded into its class in ir.json, and so is a name of it; code outside
every type (top-level functions and properties) is from nothing ("from" null), and no
body relation can be drawn from it.

A file several compilations compile (a common source set in each target's compilation,
the metadata compilations of intermediate source sets) has the answers of all of them:
where they agree, that is the record; where they differ, or one of them compiles the file
and records nothing at the place, its kind is "split": no relation may be drawn there.
Two answers agree when a class and a typealias are one id (`expect class` and its
`actual typealias`), and so their constructors. A file no compilation compiles is "not
compiled" (Apple source sets, which no Linux host compiles; modules the build leaves out).
Only a type declared in the sources is the project's.

Everything runs in the image the Dockerfile here describes (built as `draftsman-kotlin`,
linux/amd64, with JDK 21, the Android SDK, the Kotlin compilers 2.3.0, 2.3.21 and 2.4.0
and the plugin built for each); Gradle's caches are kept in the Docker volume
`draftsman-gradle`, Kotlin/Native's in `draftsman-konan`. Nothing is installed on the host
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

FIXTURE = ROOT / "tests" / "fixtures" / "kotlin" / "body"
# sets of sources written by hand in reviews, each a directory (`review`)
REVIEW = HERE / "review"
SUFFIXES = (".kt",)
IMAGE = "draftsman-kotlin"
VOLUMES = {"draftsman-gradle": "/root/.gradle", "draftsman-konan": "/root/.konan"}
# the compiler `key` runs: Ktor's
KEY_COMPILER = "2.3.21"

# as docs/e2e/kotlin/ extracts them ("exclude" are extract.py's --exclude); "tasks" are
# what Gradle runs, "args" its other arguments. `typeUses` (typeuses.init.gradle) runs a
# project's Kotlin compile tasks of main code.
REPOS = {
    # Debug variants only (src/debug and src/release have no Kotlin); the unit tests of
    # the demo flavor for src/testDemo (in the e2e scope: `**/test/**` does not match it);
    # benchmarks has only a release variant. build-logic is compiled by the build itself.
    "nowinandroid": {
        "commit": "2982e63cb6",
        "exclude": ["**/test/**", "**/androidTest/**", "**/testing/**", "**/build/**"],
        "tasks": ["compileDemoDebugKotlin", "compileProdDebugKotlin",
                  "compileDemoDebugUnitTestKotlin", "compileKotlin", "compileDebugKotlin",
                  "compileDemoBenchmarkReleaseKotlin"],
        "args": []},
    # Every target a Linux host builds (JVM, JS, Wasm, Linux, Windows, Android Native,
    # Android, and the metadata compilations of the source sets between them). Apple
    # targets are skipped on Linux, also with kotlin.native.enableKlibsCrossCompilation
    # (Ktor turns it off): the cinterops of ktor-io and ktor-utils for Apple targets are
    # skipped, and so is every Apple compilation. ktor-client-tracing and
    # ktor-client-stetho are not in settings.gradle.kts; ktor-client-webrtc-rs needs cargo,
    # which the image lacks.
    "ktor": {
        "commit": "cc3d345bc2",
        "exclude": ["**/test/**", "**/test-*/**", "**/testData/**", "**/*-test/**",
                    "**/*-test-*/**", "**/*-tests/**", "**/build/**", "build-logic/**",
                    "build-settings-logic/**"],
        "tasks": ["typeUses"],
        # a build scan would be uploaded to develocity.jetbrains.com; two workers, as more
        # (each a Kotlin/Native compiler of up to 2 GB beside Gradle's 6 GB) ran Docker's
        # 16 GB out of memory
        "args": ["--no-configuration-cache", "--max-workers=2",
                 "-Pktor.develocity.skipBuildScans=true"]},
}

# what the compiler resolves a name to, as the key says it ("type" for these)
TYPES = {"class", "interface", "object", "enum", "annotation", "companion", "typealias",
         "enumEntry-class", "unknown-class", "class?", "constructor", "alias-constructor",
         "sam-constructor"}
KINDS = {"function": "function", "member-function": "function", "local-function": "function",
         "property": "property", "member-property": "property",
         "extension-property": "property", "field": "property", "local": "var",
         "param": "var", "local-class": "local"}


def image() -> None:
    """Build the image (Docker's cache makes it quick once built)."""
    subprocess.run(["docker", "build", "--platform", "linux/amd64", "-q", "-t", IMAGE, HERE],
                   check=True, stdout=subprocess.DEVNULL)


def container(cmd: list[str], mounts: dict[str, str], cwd: str = "/src", env: dict = {},
              check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    args = ["docker", "run", "--rm", "--platform", "linux/amd64", "-w", cwd]
    for source, target in mounts.items():
        args += ["-v", f"{source}:{target}"]
    for k, v in env.items():
        args += ["-e", f"{k}={v}"]
    return subprocess.run(args + [IMAGE, *cmd], check=check, text=True,
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.STDOUT if capture else None)


# -- the plugin's records ------------------------------------------------------------------

def read_raw(out: Path) -> tuple[list[dict], dict[str, dict[str, list[dict]]]]:
    """The compilations TypeUses wrote below ``out`` and, per file (its path as the
    compiler had it) and compilation, the records of the file."""
    comps, files = [], defaultdict(dict)
    for path in sorted(out.glob("*.jsonl")):
        current: Optional[list] = None
        for line in path.read_text().splitlines():
            r = json.loads(line)
            if "compilation" in r:
                comps.append(r)
            elif "file" in r:
                current = files[r["file"]].setdefault(r["comp"], [])
            elif current is not None:
                current.append(r)
    return comps, files


def ident(class_id: str) -> str:
    """ir.json's id of a compiler's class id (`a/b/Outer.Inner`)."""
    return class_id.replace("/", ".").lstrip(".")


class Types:
    """The types the sources declare: what ir.json has of them."""

    def __init__(self, declared: list[dict]):
        # a companion object without supertypes is a static scope of its class
        self.folded = {d["declared"] for d in declared
                       if d["kind"] == "companion" and not d.get("supertypes")}
        self.ids = {self.id(d["declared"]) for d in declared if d["kind"] != "typealias"}
        # a typealias is no type in ir.json, which resolves through it; but an `actual
        # typealias` has the id of its `expect class`
        self.aliases = {d["declared"] for d in declared
                        if d["kind"] == "typealias" and ident(d["declared"]) not in self.ids}

    def id(self, class_id: str) -> str:
        """A folded companion is its class, and a type nested in it is nested in its
        class (`A.Companion.Serializer` is `A.Serializer`)."""
        package, _, name = class_id.rpartition("/")
        parts = name.split(".")
        i = 1
        while i <= len(parts):
            if f"{package}/{'.'.join(parts[:i])}" in self.folded:
                del parts[i - 1]
            else:
                i += 1
        return ident(f"{package}/{'.'.join(parts)}")

    def owner(self, owners: list[str]) -> Optional[str]:
        """The named type code is in, ``owners`` the classes around it, innermost last."""
        for o in reversed(owners):
            if o not in ("<anonymous>", "<local>"):
                return self.id(o)
        return None


def convert(r: dict, file: str, types: Types) -> Optional[dict]:
    """The key's record of a name TypeUses recorded, None for one it does not keep: a name
    outside bodies, or a member name after a `.` (but a nested class's constructor)."""
    if not r["body"]:
        return None
    raw = r["kind"]
    if r.get("dotted") and raw not in TYPES and raw != "local-class":
        return None
    if r["pos"] == "type":
        pos, maximal = "type", r.get("part", 0) == 0
    else:
        pos = "receiver"
        maximal = r.get("part", 0) == 0 and r.get("role") != "outer"
    out = {"use": r["use"], "file": file, "line": r["line"], "col": r["col"], "pos": pos}
    if raw in TYPES:
        if r["target"] in types.aliases and not r.get("expanded"):
            # the class an alias stands for is the answer: an alias whose class the
            # plugin did not say is the plugin's mistake, not an answer
            raise ValueError(f"{file}:{r['line']}:{r['col'] + 1}: typealias {r['target']} "
                             "without the class it stands for")
        target = types.id(r["expanded"] if r["target"] in types.aliases else r["target"])
        out.update(kind="type", target=target, project=target in types.ids)
    else:
        kind = KINDS.get(raw, raw)
        if raw == "enumEntry" and pos == "receiver":
            kind = "enumEntry"
        out.update(kind=kind, target=r["target"] if kind in ("function", "property", "enumEntry", "tparam") else None,
                   project=False)
    out.update(maximal=maximal, **{"from": types.owner(r["owners"])}, resolved=raw)
    if r["target"] in types.aliases:
        out["alias"] = ident(r["target"])
    for k in ("role", "implicit", "call", "companion"):
        if r.get(k) not in (None, False):
            out[k] = r[k]
    return out


def _answer(r: dict) -> tuple:
    """What compilations must agree on: a type's id, but only the kind of anything else
    (`append` is a member on the JVM and an extension elsewhere: no type either way)."""
    return (r["kind"], r["target"] if r["kind"] == "type" else None, r["pos"], r["maximal"],
            r["from"])


def join(comps: list[dict], raw: dict[str, dict[str, list[dict]]], files: dict[str, str],
         diagnostics: list[dict] = []) -> list[dict]:
    """The records of every compilation, joined into one per place (module docstring).
    ``files`` maps the path of each file of the sources as the compiler had it to its
    path below the root the extractor is given."""
    declared = []
    for path, by in raw.items():
        if path in files:
            for c, rs in by.items():
                declared += [{**d, "file": files[path]} for d in rs if "declared" in d]
    types = Types(declared)
    out: list[dict] = [{"compilation": c["compilation"], "language": c["language"],
                        "sources": len(c["sources"])} for c in comps]
    out += diagnostics
    seen = set()
    twice = 0   # places with two records in one compilation
    for d in sorted(declared, key=lambda d: (d["declared"], d["file"])):
        key = (d["declared"], d["file"])
        if key not in seen:
            seen.add(key)
            # what ir.json does not have as a type: "folded" into its class, "alias"
            aside = ("folded" if d["declared"] in types.folded else
                     "alias" if d["declared"] in types.aliases else None)
            out.append({"declared": d["declared"] if aside == "folded" else types.id(d["declared"]),
                        "file": d["file"], "kind": d["kind"], "expect": d["expect"],
                        "actual": d["actual"], **({aside: True} if aside else {})})
    for path in sorted(raw, key=lambda p: files.get(p, "")):
        if path not in files:
            continue
        file = files[path]
        at: dict[tuple, dict[str, dict]] = defaultdict(dict)
        for comp, rs in raw[path].items():
            for r in rs:
                if "use" in r and (k := convert(r, file, types)) is not None:
                    place = (k["line"], k["col"])
                    # one name, two records (a type and a value): the type position wins
                    if comp in at.get(place, {}):
                        twice += 1
                    if comp not in at.get(place, {}) or k["pos"] == "type":
                        at[place][comp] = k
        compiling = set(raw[path])
        for (line, col), by in sorted(at.items()):
            answers = {c: _answer(r) for c, r in by.items()}
            first = next(iter(by.values()))
            if len(set(answers.values())) == 1 and set(by) == compiling:
                out.append({**first, "comps": len(compiling)})
            else:
                said = {c.split("#")[0] + "#" + c.split("#")[1][:4]:
                        f"{answer_key.answer(r)} {r['pos']} in {r['from']}"
                        + ("" if r["maximal"] else " (part)") for c, r in by.items()}
                said.update({c: "none" for c in compiling - set(by)})
                out.append({**first, "kind": "split", "target": None, "project": False,
                            "answers": dict(sorted(said.items())), "comps": len(compiling)})
    if twice:
        out.append({"twice": twice})
    compiled = {files[p] for p in raw if p in files}
    for file in sorted(set(files.values()) - compiled):
        out.append({"uncompiled": file, "lines": "all"})
    return out


def expected(root: Path) -> dict[tuple[str, int, int], tuple[str, str]]:
    return answer_key.expected(root, SUFFIXES)


# -- a directory ---------------------------------------------------------------------------

DIAGNOSTIC = re.compile(r"^(?:/src/)?(.+?\.kt):(\d+):(\d+): error: (.*)$")


def key_dir(directory: Path, out: Path) -> list[dict]:
    """The key for any directory: its .kt files compiled together for the JVM, the
    standard library alone on the classpath."""
    image()
    directory = directory.resolve()
    files = [rel for _, rel in discover(directory, {"kotlin"}, [])]
    if not files:
        sys.exit(f"oracle: no .kt file below {directory}")
    v = KEY_COMPILER
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        done = container(["kotlinc", v, "-no-stdlib", "-no-reflect", "-nowarn",
                          "-cp", f"/opt/kotlin/kotlin-stdlib-{v}.jar",
                          f"-Xplugin=/opt/type-uses/type-uses-{v}.jar",
                          "-P", "plugin:draftsman.typeuses:out=/work/out", "-d", "/work/classes",
                          *(f"/src/{f}" for f in files)],
                         {str(directory): "/src", str(work): "/work"}, check=False, capture=True)
        diagnostics = [{"diagnostic": m.group(4), "file": m.group(1), "line": int(m.group(2))}
                       for line in done.stdout.splitlines() if (m := DIAGNOSTIC.match(line))]
        comps, raw = read_raw(work / "out")
    recs = join(comps, raw, {f"/src/{f}": f for f in files}, diagnostics)
    recs.insert(0, {"config": {"directory": str(directory), "kotlin": v}})
    out.write_text("".join(json.dumps(r) + "\n" for r in recs))
    return recs


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
    return check(root, discover(root, {"kotlin"}, []), recs, args.verbose)


def review(args) -> int:
    """Every set of hand-written sources below review/ through `key --compare`: the names
    drawn and the mismatches of each. Fails on a mismatch review/README.md does not list
    as a known limit (`- `set/File.kt:line:col``) and on fewer names drawn than it lists
    for the set (`| `set` | n |`)."""
    import contextlib
    import io
    readme = (REVIEW / "README.md").read_text()
    known = set(re.findall(r"^- `([^`]+)`", readme, re.M))
    counts = {k: int(v) for k, v in re.findall(r"^\| `(\w+)` \| (\d+) \|", readme, re.M)}
    sets = sorted((d for d in REVIEW.iterdir() if d.is_dir() and not args.sets
                   or d.name in (args.sets or ())), key=lambda d: (len(d.name), d.name))
    new, seen = [], set()
    for d in sets:
        with tempfile.TemporaryDirectory() as tmp:
            text = io.StringIO()
            with contextlib.redirect_stdout(text), contextlib.redirect_stderr(io.StringIO()):
                recs = key_dir(d, Path(tmp, "key.jsonl"))
                check(d.resolve(), discover(d.resolve(), {"kotlin"}, []), recs, True)
        out = text.getvalue()
        drawn = re.search(r"compare: (\d+) names drawn", out)
        wrong = re.findall(r"^  mismatch: (\S+)", out, re.M)
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
            m = re.match(r"  mismatch: (\S+)", line)
            if m and f"{d.name}/{m.group(1).rstrip(':')}" in fresh:
                print(line)
    gone = sorted(k for k in known if k.split("/", 1)[0] in {d.name for d in sets} and k not in seen)
    for k in gone:
        print(f"known limit no longer a mismatch: {k}")
    return 1 if new else 0


# -- a repository --------------------------------------------------------------------------

def sources(repo: str, checkout: Path) -> list[tuple[Path, str]]:
    return discover(checkout, {"kotlin"}, REPOS[repo]["exclude"])


def summary(recs: list[dict], name: str) -> None:
    comps = [r for r in recs if "compilation" in r]
    errors = [r for r in recs if "diagnostic" in r]
    uses = Counter(r["kind"] for r in recs if "use" in r)
    print(f"{name}: {len(comps)} compilations, {len(errors)} compile errors (in "
          f"{len({r['file'] for r in errors})} source files); names: "
          + ", ".join(f"{k} {v}" for k, v in uses.most_common()))
    for r in errors[:20]:
        print(f"  {r['file']}:{r['line']}: {r['diagnostic']}")
    whole = [r["uncompiled"] for r in recs if "uncompiled" in r]
    print(f"not compiled: {len(whole)} files")
    for r in recs:
        if "twice" in r:
            print(f"places with two names in one compilation (the type position kept): {r['twice']}")


def run(args) -> int:
    conf = REPOS[args.repo]
    checkout = args.checkout.resolve()
    files = {f"/src/{rel}": rel for _, rel in sources(args.repo, checkout)}
    with tempfile.TemporaryDirectory() as tmp:
        raw_dir = args.raw.resolve() if args.raw else Path(tmp, "out")
        if args.rejoin:
            config = json.loads((raw_dir / "config.json").read_text())
        else:
            image()
            if raw_dir.exists():
                shutil.rmtree(raw_dir)
            raw_dir.mkdir(parents=True)
            work = Path(tmp)
            mounts = {str(checkout): "/src", str(raw_dir): "/out", str(work): "/work", **VOLUMES}
            # --rerun-tasks: a task up to date (or from the build cache) compiles nothing
            done = container(["sh", "-c", "./gradlew --no-daemon --no-watch-fs --continue --rerun-tasks "
                              "-I /opt/type-uses/typeuses.init.gradle "
                              + " ".join(conf["args"] + conf["tasks"]) + " > /work/gradle.log 2>&1"],
                             mounts, env={"TYPEUSES_OUT": "/out"}, check=False)
            text = (work / "gradle.log").read_text(errors="replace")
            if args.log:
                shutil.copy(work / "gradle.log", args.log)
            config = {"repo": args.repo, "commit": conf["commit"], "tasks": conf["tasks"],
                      "args": conf["args"], "exit": done.returncode,
                      "failed": re.findall(r"^> Task (\S+) FAILED", text, re.M)}
            (raw_dir / "config.json").write_text(json.dumps(config))
        comps, raw = read_raw(raw_dir)
    recs = join(comps, raw, files)
    recs.insert(0, {"config": {**config, "kotlin": sorted({c["language"] for c in comps})}})
    args.output.write_text("".join(json.dumps(r) + "\n" for r in recs))
    summary(recs, args.repo)
    print(f"gradle: exit {config['exit']}, failed tasks: {', '.join(config['failed']) or 'none'}")
    if config["exit"]:
        # a task that failed compiled nothing; a daemon that died (out of memory: run one
        # container at a time) compiled nothing after it
        print("gradle failed: the key lacks what it did not compile")
    return 1 if config["exit"] else 0


def declared_files(recs: list[dict]) -> dict[str, set[str]]:
    files: dict[str, set[str]] = defaultdict(set)
    for r in recs:
        if "declared" in r and not r.get("folded") and not r.get("alias"):
            files[r["declared"]].add(r["file"])
    return files


def in_scope(recs: list[dict], ir: dict[str, str]) -> int:
    """answer_key.in_scope, a type of several files (an `expect` and its `actual`s) taken
    as declared in any of them: ir.json gives one file for an id. Types declared in a file
    no compilation compiles are not seen, and listed as such; companion objects without
    supertypes are folded into their class in ir.json."""
    seen = declared_files(recs)
    flat = [{"declared": t, "file": ir[t] if t in ir and ir[t] in fs else sorted(fs)[0]}
            for t, fs in seen.items()]
    folded = sorted({r["declared"] for r in recs if r.get("folded")})
    if folded:
        print(f"known: {len(folded)} companion objects without supertypes, folded into their "
              f"classes in ir.json (e.g. {', '.join(folded[:3])})")
    aliases = sorted({r["declared"] for r in recs if "declared" in r and r.get("alias")})
    if aliases:
        print(f"known: {len(aliases)} typealiases, which ir.json resolves through "
              f"(e.g. {', '.join(aliases[:3])})")
    whole = {r["uncompiled"] for r in recs if "uncompiled" in r}
    unseen = {t: f"declared in {f}, which no compilation compiles"
              for t, f in ir.items() if f in whole and t not in seen}
    return answer_key.in_scope(flat, ir, unseen, language="Kotlin")


def scope(args) -> int:
    ir = {t["id"]: t["location"]["file"] for t in json.loads(args.ir.read_text())["types"]
          if t["language"] == "kotlin"}
    return in_scope(answer_key.read(args.oracle), ir)


def check(root: Path, files: list[tuple[Path, str]], recs: list[dict], verbose: bool) -> int:
    from draftsman.extractor import Extractor
    from draftsman.langs import spec_for_path
    from draftsman.resolve import _Builder
    from draftsman.wrappers import Wrappers

    raw = [Extractor(spec_for_path(rel)).extract(f, rel, root) for f, rel in files]
    builder = _Builder(str(root), raw, Wrappers.load())
    ir = builder.build()
    where = {t.id: t.location.file for t in ir.types if t.language == "kotlin"}
    if in_scope(recs, where):
        return 1
    # code outside every type draws nothing: not a miss. A file no compilation compiles
    # (a module the build leaves out) has no answers: what is drawn there is counted apart
    return answer_key.compare(builder.body_uses, recs, verbose, key="the compiler",
                              drawable=lambda r: answer_key.drawable(r) and r["from"] is not None,
                              uncompiled={r["uncompiled"] for r in recs if "uncompiled" in r})


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
    print(f"names recorded: {len(uses)}; in several compilations: "
          f"{sum(1 for r in uses if r['comps'] > 1)}, of which split: {len(split)}")
    for r in split[:None if args.verbose else 10]:
        print(f"  split: {r['file']}:{r['line']}:{r['col'] + 1} {r['use']}: {r['answers']}")

    def project(r: dict) -> bool:
        return answer_key.drawable(r) and r["from"] is not None

    def count(rs) -> str:
        rs = list(rs)
        p = {(r["from"], r["target"]) for r in rs if project(r)}
        text = f"{sum(map(project, rs))} uses, {len(p)} relations"
        return text + (f" ({len(p - declared)} not in ir.json)" if args.ir else "")

    print(f"project types named in bodies of types: {count(uses)}; outside every type: "
          f"{sum(1 for r in uses if answer_key.drawable(r) and r['from'] is None)}")
    for position in ("type", "receiver"):
        print(f"  {position} position: {count(r for r in uses if r['pos'] == position)}")
    forms = Counter(r.get("role") or ("call" if r.get("call") else r["resolved"])
                    for r in uses if project(r) and r["pos"] == "receiver")
    print("  receiver position, by form: " + ", ".join(f"{k} {v}" for k, v in forms.most_common()))
    names = {r["target"].rsplit(".", 1)[-1] for r in uses if r["kind"] == "type" and r["project"]}
    names |= {r["declared"].rsplit(".", 1)[-1] for r in recs if "declared" in r}
    shadows = Counter(r["kind"] + (" " + r["implicit"].split()[0] if r.get("implicit") else "")
                      for r in uses if r["kind"] not in ("type", "split") and r["use"] in names)
    print("names of a project type resolved to something else: "
          + ", ".join(f"{k} {v}" for k, v in shadows.most_common()))
    other = Counter(r["target"] for r in uses
                    if r["kind"] == "type" and not r["project"] and r["use"] in names)
    print(f"names of a project type resolved to a type outside the sources: {sum(other.values())} ("
          + ", ".join(f"{k} {v}" for k, v in other.most_common(8)) + ")")
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
    r.add_argument("--log", type=Path, help="keep Gradle's output here")
    r.add_argument("--raw", type=Path, help="keep TypeUses' records in this directory")
    r.add_argument("--rejoin", action="store_true",
                   help="join the records --raw keeps again, without building")
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
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
