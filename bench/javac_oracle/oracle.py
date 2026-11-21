"""javac as the answer key for body relations (issue #2).

A body relation is drawn from a name written in a body, so citing its line proves
nothing: the line always names the target. Whether `Foo` is the Foo it was resolved to
is what javac answers. TypeUses.java records every name javac resolves in a body; this
script runs it and reads its output.

    uv run bench/javac_oracle/oracle.py selftest
    uv run bench/javac_oracle/oracle.py run REPO --checkout DIR -o OUT.jsonl
    uv run bench/javac_oracle/oracle.py scope REPO OUT.jsonl ir.json
    uv run bench/javac_oracle/oracle.py compare REPO OUT.jsonl --checkout DIR [-v]
    uv run bench/javac_oracle/oracle.py measure OUT.jsonl [--ir ir.json]
    uv run bench/javac_oracle/oracle.py jdk

`selftest` checks the oracle against the hand-written answers in
tests/fixtures/java/body (its README gives the marker format), so that a mismatch later
is the extractor's and not the oracle's. `run` compiles a benchmark repository's
production sources (bench/tasks.yaml's roots without its exclude) with its Maven compile
classpath. `scope` fails unless the oracle saw the same Java types, declared
in the same files, as ir.json of those sources: every comparison with ir.json rests on
it. `compare` extracts the same sources and checks every name a body relation is drawn
from against what javac resolved at its place; it fails on any mismatch outside the files
javac could not compile (after `scope`, on the IR it builds). `measure` prints the counts
the rules of the receiver position are decided by. `jdk` writes the table of the nested
types and fields JDK supertypes pass on (JdkMembers.java), which the extractor reads.

The JDK is $JAVA_HOME, else Homebrew's openjdk@21 (/usr/bin/javac on macOS is a stub).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from fnmatch import fnmatch
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent))
from select_focus import excluded  # noqa: E402

TASKS = HERE.parent / "tasks.yaml"
BUILD = HERE / "build"
FIXTURE = ROOT / "tests" / "fixtures" / "java" / "body"

# what javac needs to compile tasks.yaml's production sources; "root" is the root
# tasks.yaml extracts, so that paths compare with ir.json's. tasks.yaml's exclude applies
# on top. "context" is compiled but is no source: the extractor skips target/. "stubs" are
# sources the extractor reads that javac takes as class files (see TypeUses.java).
REPOS = {
    "spring-petclinic": {"root": "src/main", "sources": ["src/main/java"], "release": "17"},
    # java11/ holds three files that only build on 11; module-info.java needs a module path
    "jsoup": {"root": "src/main", "sources": ["src/main/java", "src/main/java11"],
              "release": "11", "skip": ["module-info.java"]},
    # needs a compiled checkout (the collections common/ generates from templates, and the
    # per-module classpaths), written by
    #   mvn -B -DskipTests -Dcheckstyle.skip -Danimal.sniffer.skip -Drevapi.skip \
    #       -Djapicmp.skip -Dforbiddenapis.skip -Dmaven.javadoc.skip -Denforcer.skip \
    #       compile dependency:build-classpath -Dmdep.includeScope=compile \
    #       -Dmdep.outputFile=target/oracle-cp.txt
    # The *-stub modules declare JDK types (java.lang.invoke.VarHandle) for --release 8:
    # on the classpath, as Netty builds, not among the sources.
    "netty": {"root": ".", "sources": ["*/src/main/java", ".github/scripts/*"],
              "context": ["common/target/generated-sources/collections"],
              "stubs": ["*-stub/src/main/java"], "exclude": ["*-stub"],
              # types of ir.json that javac does not show, and why
              "unseen": {"java.lang.invoke.MethodHandle.PolymorphicSignature":
                         "--release 8 reads MethodHandle from JDK 8, not from the stub, and "
                         "its nested annotation is not public there"},
              "release": "8", "skip": ["module-info.java"],
              "classpath": {"files": "*/target/oracle-cp.txt", "extra": ["*-stub/target/classes"]}},
}


def jdk() -> Path:
    for home in (os.environ.get("JAVA_HOME"), "/opt/homebrew/opt/openjdk@21"):
        if home and (Path(home) / "bin" / "javac").is_file():
            return Path(home)
    sys.exit("oracle: no JDK; set JAVA_HOME (on macOS /usr/bin/javac is only a stub)")


def build(home: Path) -> None:
    src = HERE / "TypeUses.java"
    cls = BUILD / "TypeUses.class"
    if cls.is_file() and cls.stat().st_mtime >= src.stat().st_mtime:
        return
    BUILD.mkdir(exist_ok=True)
    subprocess.run([home / "bin" / "javac", "-d", BUILD, src], check=True)


def oracle(root: Path, files: list[Path], options: list[str], out: Path,
           context: list[Path] = (), stubs: dict[str, str] = {}) -> list[dict]:
    """Run TypeUses over ``files`` (paths reported below ``root``) and read its records;
    ``context`` is compiled along but not recorded, ``stubs`` maps class-file types to the
    file they count as declared in."""
    home = jdk()
    build(home)
    with tempfile.TemporaryDirectory() as tmp:
        opts, srcs, ctx, stb = (Path(tmp, n) for n in ("options", "sources", "context", "stubs"))
        # -proc:none: annotation processors would need their own path; -implicit:none
        # and -d keep javac from writing class files next to the sources
        opts.write_text("\n".join([*options, "-proc:none", "-implicit:none", "-nowarn",
                                   "-d", str(Path(tmp, "classes"))]) + "\n")
        srcs.write_text("\n".join(str(f) for f in files) + "\n")
        ctx.write_text("\n".join(str(f) for f in context) + "\n")
        stb.write_text("".join(f"{n}\t{f}\n" for n, f in sorted(stubs.items())))
        subprocess.run([home / "bin" / "java", "-Xmx6g", "-cp", BUILD, "TypeUses",
                        out, root, opts, srcs, ctx, stb], check=True)
    return [json.loads(line) for line in out.read_text().splitlines()]


# ------------------------------------------------------------------ selftest

_MARKER = re.compile(r"//>(.*)$")


def expected(root: Path) -> dict[tuple[str, int, int], tuple[str, str]]:
    """(file, line, col) -> (answer, position) for every token a marker lists."""
    out = {}
    for path in sorted(root.rglob("*.java")):
        rel = str(path.relative_to(root))
        for no, text in enumerate(path.read_text().splitlines(), 1):
            m = _MARKER.search(text)
            if not m:
                continue
            code = text[:m.start()]
            seen: Counter = Counter()
            for item in m.group(1).split():
                name, _, rest = item.partition("=")
                answer, _, position = rest.partition("/")
                hits = [h.start() for h in re.finditer(rf"\b{re.escape(name)}\b", code)]
                if seen[name] >= len(hits):
                    raise SystemExit(f"{rel}:{no}: the marker lists more {name} than the line has")
                col = hits[seen[name]]
                seen[name] += 1
                out[(rel, no, col)] = (answer, {"t": "type", "r": "receiver"}.get(position, ""))
            for name, n in seen.items():
                if n != len(re.findall(rf"\b{re.escape(name)}\b", code)):
                    raise SystemExit(f"{rel}:{no}: the marker lists {n} of the {name} on the line")
    return out


def answer(rec: dict) -> str:
    return rec["target"] if rec["kind"] == "type" else rec["kind"]


def selftest(_args) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        recs = oracle(FIXTURE, sorted(FIXTURE.rglob("*.java")), ["--release", "21"],
                      Path(tmp, "fixture.jsonl"))
    want = expected(FIXTURE)
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
    # what the oracle reports that no marker expects: only names outside the sources
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


# ------------------------------------------------------------------ run

def classpath(checkout: Path, conf: dict) -> list[str]:
    """The compile classpath without the repository's own modules, which are compiled
    from source in the same run."""
    if "classpath" in conf:   # a multi-module build: what its modules wrote
        written = sorted(checkout.glob(conf["classpath"]["files"]))
        if not written:
            sys.exit(f"oracle: no {conf['classpath']['files']} in {checkout}; "
                     "build it first (see REPOS)")
        entries = [e for f in written for e in f.read_text().strip().split(os.pathsep) if e]
        entries += [str(d) for g in conf["classpath"]["extra"] for d in sorted(checkout.glob(g))]
    else:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp, "cp.txt")
            subprocess.run(["mvn", "-q", "-B", "dependency:build-classpath",
                            "-Dmdep.includeScope=compile", f"-Dmdep.outputFile={out}"],
                           cwd=checkout, check=True, env={**os.environ, "JAVA_HOME": str(jdk())})
            entries = [e for e in out.read_text().strip().split(os.pathsep) if e]
    own = str(checkout) + os.sep
    extra = {str(d) for g in conf.get("classpath", {}).get("extra", ()) for d in checkout.glob(g)}
    return list(dict.fromkeys(e for e in entries if not e.startswith(own) or e in extra))


def sources(checkout: Path, conf: dict, globs: list[str], exclude: list[str] = ()) -> list[Path]:
    """The .java files below ``globs``, without the modules of ``conf``'s exclude and the
    files tasks.yaml's ``exclude`` (patterns relative to the checkout) leaves out."""
    dirs = [d for g in globs for d in sorted(checkout.glob(g)) if d.is_dir()
            and not any(fnmatch(d.relative_to(checkout).parts[0], x)
                        for x in conf.get("exclude", ()))]
    return sorted(f for d in dirs for f in d.rglob("*.java")
                  if f.name not in conf.get("skip", ())
                  and not excluded(f.relative_to(checkout).as_posix(), exclude))


def run(args) -> int:
    conf = REPOS[args.repo]
    checkout = args.checkout.resolve()
    exclude = yaml.safe_load(TASKS.read_text())["repos"][args.repo]["exclude"]
    files = sources(checkout, conf, conf["sources"], exclude)
    context = sources(checkout, conf, conf.get("context", []))
    stubs = {}   # top-level type -> its file, by package and file name
    for d in (d for g in conf.get("stubs", ()) for d in sorted(checkout.glob(g))):
        for f in sorted(d.rglob("*.java")):
            if f.name not in conf.get("skip", ()) and f.name != "package-info.java":
                name = ".".join((*f.relative_to(d).parent.parts, f.stem))
                stubs[name] = str(f.relative_to(checkout / conf["root"]))
    cp = classpath(checkout, conf)
    options = ["--release", conf["release"], "-encoding", "UTF-8"]
    if cp:
        options += ["-classpath", os.pathsep.join(cp)]
    recs = oracle(checkout / conf["root"], files, options, args.output, context, stubs)
    errors = [r for r in recs if "diagnostic" in r]
    uses = Counter(r["kind"] for r in recs if "use" in r)
    print(f"{args.repo}: {len(files)} files ({len(context)} more compiled as context, "
          f"{len(stubs)} stubs), "
          f"{len(errors)} compile errors, uses: "
          + ", ".join(f"{k} {v}" for k, v in uses.most_common()))
    for r in errors[:20]:
        print(f"  {r['file']}:{r['line']}: {r['diagnostic']}")
    return 0


# ------------------------------------------------------------------ scope

def scope(args) -> int:
    recs = [json.loads(line) for line in args.oracle.read_text().splitlines()]
    # Java only: Netty's ir.json also holds C structs (io_uring_cqe)
    ir = {t["id"]: t["location"]["file"] for t in json.loads(args.ir.read_text())["types"]
          if t["language"] == "java"}
    return in_scope(args.repo, recs, ir)


def in_scope(repo: str, recs: list[dict], ir: dict[str, str]) -> int:
    """1 unless the oracle saw the Java types of ``ir`` (id -> file), in the same files."""
    unseen = REPOS[repo].get("unseen", {})
    seen = {r["declared"]: r["file"] for r in recs if "declared" in r}
    problems = [f"in ir.json only: {t} ({ir[t]})" for t in sorted(ir.keys() - seen.keys())
                if t not in unseen]
    problems += [f"in the oracle only: {t} ({seen[t]})" for t in sorted(seen.keys() - ir.keys())]
    problems += [f"{t}: ir.json declares it in {ir[t]}, the oracle in {seen[t]}"
                 for t in sorted(ir.keys() & seen.keys()) if ir[t] != seen[t]]
    problems += [f"listed as unseen but seen: {t}" for t in sorted(unseen) if t in seen]
    for p in problems:
        print(p)
    for t, why in sorted(unseen.items()):
        print(f"known: {t}: {why}")
    print(f"scope: {len(ir)} Java types in ir.json, {len(seen)} in the oracle, "
          f"{len(problems)} problems")
    return 1 if problems else 0


# ------------------------------------------------------------------ compare

def compare(args) -> int:
    sys.path.insert(0, str(ROOT / "skills" / "draftsman" / "scripts"))
    from extract import discover
    from draftsman.extractor import Extractor
    from draftsman.langs import spec_for_path
    from draftsman.resolve import _Builder
    from draftsman.wrappers import Wrappers

    conf = REPOS[args.repo]
    checkout = args.checkout.resolve()
    root = checkout / conf["root"]
    exclude = yaml.safe_load(TASKS.read_text())["repos"][args.repo]["exclude"]
    files = [(f, rel) for f, rel in discover(root, {"java"}, [])
             if not excluded(f.relative_to(checkout).as_posix(), exclude)]
    extractor = Extractor(spec_for_path("A.java"))
    builder = _Builder(str(root), [extractor.extract(f, rel, root) for f, rel in files],
                       Wrappers.load())
    ir = builder.build()
    recs = [json.loads(line) for line in args.oracle.read_text().splitlines()]
    if in_scope(args.repo, recs, {t.id: t.location.file for t in ir.types}):
        return 1

    # javac has the stubs as class files: nothing in them is recorded
    stubs = [d.relative_to(root).as_posix() + "/" for g in conf.get("stubs", ())
             for d in checkout.glob(g)]
    broken = {r["file"] for r in recs if "diagnostic" in r}
    uses = {(r["file"], r["line"], r["col"]): r for r in recs if "use" in r}
    drawn = [u for u in builder.body_uses if not any(u[0].startswith(d) for d in stubs)]
    problems: Counter = Counter()
    shown: list[str] = []
    for file, line, col, src, dst in drawn:
        r = uses.get((file, line, col))
        if r is None:
            why = "javac resolved no name there"
        elif r["kind"] != "type":
            why = f"javac: {r['kind']}"
        elif r["target"] != dst:
            why = f"javac: {r['target']}"
        elif r["from"] != src:
            why = f"javac draws it from {r['from']}"
        else:
            continue
        where = "in a file with compile errors" if file in broken else "mismatch"
        problems[where] += 1
        shown.append(f"  {where}: {file}:{line}:{col + 1} {src} -> {dst}; {why}")

    def drawable(r):   # what a body relation could be drawn from, as `measure` counts it
        return (r["kind"] == "type" and r["project"] and r["maximal"]
                and r["from"] != r["target"])

    at = {(f, line, col) for f, line, col, _, _ in drawn}
    missed = Counter(r["pos"] for k, r in uses.items() if drawable(r) and k not in at)
    pairs = {(s_, d) for *_, s_, d in drawn}
    want = {(r["from"], r["target"]) for r in uses.values() if drawable(r)}
    print(f"compare: {len(drawn)} names drawn as body relations ({len(pairs)} pairs); "
          + (", ".join(f"{k} {v}" for k, v in sorted(problems.items())) or "0 mismatches"))
    print(f"  javac's project types not drawn: "
          + ", ".join(f"{k} position {v}" for k, v in sorted(missed.items()))
          + f"; pairs javac has that are not drawn: {len(want - pairs)}")
    for line in shown[:None if args.verbose else 20]:
        print(line)
    if args.verbose:
        for k, r in sorted(uses.items()):
            if drawable(r) and k not in at and r["pos"] == "type":
                print(f"  not drawn: {k[0]}:{k[1]}:{k[2] + 1} {r['use']} = {r['target']} "
                      f"in {r['from']}")
    return 1 if problems["mismatch"] else 0


# ------------------------------------------------------------------ jdk

JDK_TABLE = ROOT / "skills" / "draftsman" / "scripts" / "draftsman" / "langs" / "java_jdk.json"


def jdk_table(_args) -> int:
    subprocess.run([jdk() / "bin" / "java", HERE / "JdkMembers.java", JDK_TABLE], check=True)
    print(f"{JDK_TABLE.relative_to(ROOT)}: {len(json.loads(JDK_TABLE.read_text())['types'])} types")
    return 0


# ------------------------------------------------------------------ measure

def measure(args) -> int:
    recs = [json.loads(line) for line in args.oracle.read_text().splitlines()]
    uses = [r for r in recs if "use" in r]
    project_names = {d["declared"].rsplit(".", 1)[-1] for d in recs if "declared" in d}
    declared: set = set()   # pairs ir.json already relates, either way round
    if args.ir:
        ir = json.loads(args.ir.read_text())
        declared = {(r["from"], r["to"]) for r in ir["relations"]}
    print(f"compile errors: {sum(1 for r in recs if 'diagnostic' in r)}; names javac could "
          f"not resolve: {sum(1 for r in uses if r['kind'] == 'error')}")

    def project_type(r):   # a name a body relation could be drawn from
        return r["kind"] == "type" and r["project"] and r["maximal"] and r["from"] != r["target"]

    def shadow(r):         # a variable that bears a project type's name
        return r["kind"] == "var" and r["use"] in project_names

    def pairs(rs) -> set:
        return {(r["from"], r["target"]) for r in rs if project_type(r)}

    def count(rs) -> str:
        n, p = sum(map(project_type, rs)), pairs(rs)
        text = f"{n} uses, {len(p)} relations"
        return text + (f" ({len(p - declared)} not in ir.json)" if args.ir else "")

    every = pairs(uses)
    print(f"project types named in bodies: {count(uses)}")
    for position in ("type", "receiver"):
        here = [r for r in uses if r["pos"] == position]
        print(f"  {position} position: {count(here)}")
    recv = [r for r in uses if r["pos"] == "receiver"]
    shadows = [r for r in recv if shadow(r)]
    # the variables the extractor cannot see: fields of types outside the sources
    # (inherited, or brought in by a static import)
    unseen = [r for r in shadows if r["declared_in"] and not r["project"]]
    print(f"\nreceiver-position variables named like a project type: {len(shadows)}; "
          f"fields declared outside the sources: {len(unseen)}"
          + "".join(f"\n  {r['file']}:{r['line']}: {r['use']} is {r['declared_in']}.{r['use']}"
                    for r in unseen))

    def dropped(label: str, drop) -> None:
        gone = [r for r in uses if drop(r)]
        kept = pairs(r for r in uses if not drop(r))
        lost = pairs(gone) - kept - declared
        print(f"  {label}: {count(gone)}; relations no longer drawn at all: {len(lost)} "
              f"of {len(every - declared) if args.ir else len(every)}"
              + (f"; unseen fields it guards: {sum(1 for r in unseen if drop(r))}"))

    print("\nrule: drop receiver-position names in a type with a supertype outside the sources")
    for flag, label in (("outside_super", "any (Enum, Exception, Runnable too)"),
                        ("outside_super_not_lang", "one outside java.lang (Serializable counts)")):
        dropped(label, lambda r, f=flag: r["pos"] == "receiver" and r[f])
    stars = [r for r in recs if "static_star" in r and r["outside"]]
    files = {r["file"] for r in stars}
    print(f"\nrule: drop receiver-position names in a file with a static star import of a "
          f"type outside the sources ({len(stars)} imports in {len(files)} files)"
          + "".join(f"\n  {r['file']}:{r['line']}: {r['static_star']}.*" for r in stars))
    dropped("these files", lambda r: r["pos"] == "receiver" and r["file"] in files)
    if args.verbose:
        for r in shadows:
            print(f"  shadow {r['file']}:{r['line']}:{r['col'] + 1} {r['use']} in {r['from']}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest").set_defaults(fn=selftest)
    r = sub.add_parser("run")
    r.add_argument("repo", choices=sorted(REPOS))
    r.add_argument("--checkout", type=Path, required=True)
    r.add_argument("-o", "--output", type=Path, required=True)
    r.set_defaults(fn=run)
    c = sub.add_parser("scope")
    c.add_argument("repo", choices=sorted(REPOS))
    c.add_argument("oracle", type=Path)
    c.add_argument("ir", type=Path, help="ir.json of the repository's tasks.yaml scope")
    c.set_defaults(fn=scope)
    k = sub.add_parser("compare")
    k.add_argument("repo", choices=sorted(REPOS))
    k.add_argument("oracle", type=Path)
    k.add_argument("--checkout", type=Path, required=True)
    k.add_argument("-v", "--verbose", action="store_true", help="list every miss and mismatch")
    k.set_defaults(fn=compare)
    sub.add_parser("jdk").set_defaults(fn=jdk_table)
    m = sub.add_parser("measure")
    m.add_argument("oracle", type=Path)
    m.add_argument("--ir", type=Path, help="ir.json of the same sources: count only what it lacks")
    m.add_argument("-v", "--verbose", action="store_true", help="list the shadowing variables")
    m.set_defaults(fn=measure)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
