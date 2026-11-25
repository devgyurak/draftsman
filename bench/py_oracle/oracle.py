"""mypy, pyright and ty as the answer key for Python body relations (issue #5).

Python has no compiler to take as the answer, so the key is where three checkers agree on
which declaration a name in a body is. type_uses.py records every name mypy binds in a
body, in the format bench/answer_key.py gives; lsp.py asks pyright's and ty's language
servers for the definition at each of those places; this script runs the three and joins
their answers.

    uv run bench/py_oracle/oracle.py selftest
    uv run bench/py_oracle/oracle.py run REPO --checkout DIR --python PY -o OUT.jsonl
    uv run bench/py_oracle/oracle.py scope REPO OUT.jsonl ir.json
    uv run bench/py_oracle/oracle.py compare REPO OUT.jsonl --checkout DIR [-v]
    uv run bench/py_oracle/oracle.py compare REPO OUT.jsonl --checkout DIR --declared [--save F]
    uv run bench/py_oracle/oracle.py measure OUT.jsonl [--ir ir.json]
    uv run bench/py_oracle/oracle.py checkers OUT.jsonl
    uv run bench/py_oracle/oracle.py key DIR [-o OUT.jsonl] [--compare [--declared]] [-v]
    uv run bench/py_oracle/oracle.py review [SET ...]

Each answer is read as a project class (by its id), a class declared in a function
("local"), or anything else. Where the three give the same, the record keeps mypy's kind
and target; where they differ, its kind is "disputed": no relation may be drawn there,
and their count is how much of a repository static analysis cannot decide. A record also
carries each checker's answer as compared ("answers") and what each said ("mypy",
"pyright", "ty"). A checker abstains where it gives no definition and marks the place
unreachable itself ("abstained": mypy in a block its semantic analysis skipped, pyright in
the range of its hint of unreachable code, ty there too or where its hover says `Never`);
the others then decide, if two or more are left and give the same, and one left is a
dispute. A definition given in code marked unreachable is an answer, and no definition
without the mark is one too. Agreement is still not the
run-time answer: what all three cannot see (monkeypatching, a module-level name rebound
by code that runs later) is not in it.

`selftest` checks the key against the hand-written answers in tests/fixtures/python/body
(tests/fixtures/java/body/README.md gives the marker format, with `#>`). `run` checks a
repository's sources as its end-to-end page extracts them (docs/e2e/python/); PY is a
Python whose site-packages hold the repository's dependencies, as imports only resolve
through them, and not the repository itself (its sources are read from the checkout).
They were installed with `uv venv --python 3.14` and `uv pip install`: httpx's
`certifi 'httpcore==1.*' anyio idna` and its extras' `brotli 'click==8.*' 'pygments==2.*'
'rich>=10,<15' 'h2>=3,<5' 'socksio==1.*' 'zstandard>=0.18.0'`; Django's
`'asgiref>=3.13' 'sqlparse>=0.5.0'` and its extras' `argon2-cffi bcrypt` (the database
drivers, GDAL and the rest it imports when present are left out: a name from them is no
project class either way). `scope` fails
unless the key saw the same classes, declared in the same files, as ir.json of those
sources. `compare` extracts the same sources and checks every name a body relation is
drawn from against the key at its place; with `--declared`, the names declared relations
are drawn from instead (bench/declared.py, issue #7). `measure` prints what the rules for hiding names
are decided by, `checkers` how often each pair of checkers agrees.

`key` runs the three checkers over a directory of sources (no dependencies) and, with
`--compare`, compares them with the extractor as `compare` does; `review` does so for
every set of hand-written sources below review/ (bench/review_sets.py, review/README.md).

The checkers run in environments of their own, pinned below, never in the plugin's:
mypy's pure-Python wheel through `uv run --with` (type_uses.py subclasses its visitors,
which the compiled wheel does not allow), pyright and ty through `uvx`.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "skills" / "draftsman" / "scripts"))
import answer_key  # noqa: E402
import declared  # noqa: E402
from extract import discover  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "python" / "body"
SUFFIXES = (".py", ".pyi")
MARKER = "#>"

MYPY = ["uv", "run", "--quiet", "--isolated", "--no-project", "--with",
        "mypy @ https://files.pythonhosted.org/packages/21/5c/"
        "6e8010f8f2c4ad817364592d4b3883633417269b913fc9d5174fdeb7e565/"
        "mypy-2.4.1-py3-none-any.whl"
        "#sha256=1784648d6ec8c2b5465e3f26241b845a0b3cb4e56c993c64abe16989e7698999",
        "python", "-I"]
SERVERS = {
    "pyright": ["uvx", "--quiet", "--from", "pyright==1.1.414", "pyright-langserver",
                "--stdio"],
    "ty": ["uvx", "--quiet", "ty@0.0.108", "server"],
}
# Every platform's code is read, not only this machine's: pyright takes that from a
# configuration file only (in a workspace of its own, which finds the sources through
# extraPaths), ty does it by default. mypy reads `if sys.platform == ...` for the platform
# it runs on; a name only another platform's branch binds is disputed
PYRIGHT_CONFIG = {"pythonPlatform": "All"}
CHECKERS = ("mypy", "pyright", "ty")

# as docs/e2e/python/ extracts them: "root" is the path given to extract.py
REPOS = {
    "httpx": {"commit": "7cff5f79bc", "root": "httpx", "exclude": []},
    "django": {"commit": "d3954c9813", "root": "django",
               "exclude": ["contrib/*/migrations/**"]},
}


def modules(root: Path, files: list[tuple[Path, str]]) -> tuple[Path, list[tuple[Path, str, str]]]:
    """(the directory the top package sits in, [(file, module, path below root)]), with
    the module names the extractor gives."""
    from draftsman.langs import spec_for_path
    spec = spec_for_path("x.py")
    prefix = spec.package_root(root)
    base = root.resolve()
    for _ in prefix.split("/") if prefix else ():
        base = base.parent
    return base, [(f.resolve(), spec.file_namespace(f"{prefix}/{rel}" if prefix else rel), rel)
                  for f, rel in files]


def class_tokens(files: list[tuple[Path, str, str]]) -> dict[tuple[str, int, int], str]:
    """(file, line, column) of each class name in the sources -> its id, or "local" for
    one inside a function: where a definition a language server answers with points."""
    tokens = {}
    for path, mod, _ in files:
        # without a UTF-8 BOM, which ast.parse rejects ("invalid non-printable character")
        text = path.read_text(encoding="utf-8-sig")
        lines = text.split("\n")
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue

        def visit(node, prefix, local):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.ClassDef):
                    line = lines[child.lineno - 1]
                    start = len(line.encode()[:child.col_offset].decode())
                    at = line.index(child.name, start + len("class"))
                    col = len(line[:at].encode("utf-16-le")) // 2
                    cid = f"{prefix}.{child.name}"
                    tokens[(str(path), child.lineno, col)] = "local" if local else cid
                    visit(child, cid, local)
                elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                    visit(child, prefix, True)
                else:
                    visit(child, prefix, local)
        visit(tree, mod, False)
    return tokens


def mypy_answer(r: dict) -> str:
    if r["kind"] == "type" and r["project"]:
        return f"T:{r['target']}"
    return "local" if r["kind"] == "local" else "other"


def server_answer(rec: dict, sources: set[str], tokens: dict) -> tuple[str, str]:
    """(the answer as compared, what the server said) for one position."""
    if "error" in rec:
        return "error", f"error: {rec['error']}"
    said = []
    for path, line, col in rec["defs"]:
        if path not in sources:
            said.append("ext")
        else:
            token = tokens.get((path, line, col))
            said.append(f"T:{token}" if token and token != "local" else token or "var")
    if not said:
        return "other", "none"
    cmp = {s if s.startswith("T:") or s == "local" else "other" for s in said}
    return (cmp.pop() if len(cmp) == 1 else "several"), " ".join(sorted(set(said)))


def oracle(root: Path, files: list[tuple[Path, str]], python: str, out: Path,
           checkers=CHECKERS) -> list[dict]:
    base, mods = modules(root, files)
    with tempfile.TemporaryDirectory() as tmp:
        srcs = Path(tmp, "sources")
        srcs.write_text("".join(f"{p}\t{m}\t{rel}\n" for p, m, rel in mods))
        raw = Path(tmp, "mypy.jsonl")
        subprocess.run([*MYPY, HERE / "type_uses.py", raw, srcs, python], check=True,
                       cwd=base)
        recs = answer_key.read(raw, declared=True)
        uses = [r for r in recs if "use" in r]
        to_path = {rel: str(p) for p, _, rel in mods}
        places = Path(tmp, "places")
        places.write_text("".join(f"{to_path[r['file']]}\t{r['line']}\t{r['col']}\n"
                                  for r in uses))
        workspace = Path(tmp, "pyright")
        workspace.mkdir()
        (workspace / "pyrightconfig.json").write_text(json.dumps(
            {**PYRIGHT_CONFIG, "extraPaths": [str(base)]}))
        said = {}
        for name in checkers[1:]:
            got = Path(tmp, f"{name}.jsonl")
            subprocess.run([sys.executable, "-I", HERE / "lsp.py", got,
                            workspace if name == "pyright" else base, places, python,
                            "--", *SERVERS[name]], check=True)
            said[name] = {(r["file"], r["line"], r["col"]): r
                          for r in answer_key.read(got, declared=True)}
    sources = {str(p) for p, _, _ in mods}
    tokens = class_tokens(mods)
    for r in uses:
        mine = mypy_answer(r)
        answers = {"mypy": mine}
        abstained = ["mypy"] if abstains_mypy(r) else []
        for name in checkers[1:]:
            rec = said[name].get((to_path[r["file"]], r["line"], r["col"]),
                                 {"error": "not asked"})
            answers[name], r[name] = server_answer(rec, sources, tokens)
            if abstains_server(name, rec):
                abstained.append(name)
        r["answers"], r["abstained"] = answers, abstained
        given = {answers[n] for n in answers if n not in abstained}
        if len(given) != 1 or len(answers) - len(abstained) < 2:
            r["kind"], r["target"], r["project"] = "disputed", None, False
        elif "mypy" in abstained:   # the others' answer, mypy having none
            agreed = given.pop()
            r["kind"], r["target"], r["project"] = (
                ("type", agreed[2:], True) if agreed.startswith("T:")
                else (agreed if agreed == "local" else "var", None, False))
    out.write_text("".join(json.dumps(r) + "\n" for r in recs))
    return recs


def abstains_mypy(r: dict) -> bool:
    """Whether mypy abstains at a place: it binds the name to nothing there, in a block its
    semantic analysis skipped as unreachable (`if TYPE_CHECKING:`'s else, `if PY2:`)."""
    return r["mypy"] == "-" and r.get("unreachable", False)


def abstains_server(name: str, rec: dict) -> bool:
    """Whether a language server abstains at a place: it gives no definition there, and
    marks the place unreachable itself (a hint of unreachable code; ty also by a `Never`
    hover). A definition given in code marked unreachable is an answer, and no
    definition without the mark is one too (a submodule the file does not import)."""
    return rec.get("defs") == [] and (
        rec.get("unreachable", False) or name == "ty" and rec.get("hover") == "Never")


def expected(root: Path) -> dict[tuple[str, int, int], tuple[str, str]]:
    return answer_key.expected(root, SUFFIXES, MARKER)


def selftest(_args) -> int:
    files = [(p, p.relative_to(FIXTURE).as_posix())
             for p in sorted(FIXTURE.rglob("*")) if p.suffix in SUFFIXES]
    with tempfile.TemporaryDirectory() as tmp:
        recs = answer_key.body(oracle(FIXTURE, files, sys.executable,
                                      Path(tmp, "fixture.jsonl")))
    for r in recs:
        if r.get("kind") == "disputed":
            print(f"disputed: {r['file']}:{r['line']}:{r['col'] + 1} {r['use']}: mypy "
                  f"{r['mypy']}, pyright {r['pyright']}, ty {r['ty']}")
    # one record per place: two would leave the answer to the order they come in
    twice = [k for k, n in Counter((r["file"], r["line"], r["col"]) for r in recs
                                   if "use" in r).items() if n > 1]
    for file, line, col in twice:
        print(f"{file}:{line}:{col + 1}: recorded twice")
    # mypy's errors are no compile errors of the fixture: its type errors are no concern
    return answer_key.selftest([r for r in recs if "mypy_error" not in r],
                               expected(FIXTURE)) or (1 if twice else 0)


def sources(repo: str, checkout: Path) -> list[tuple[Path, str]]:
    conf = REPOS[repo]
    return discover(checkout / conf["root"], {"python"}, conf["exclude"])


def run(args) -> int:
    conf = REPOS[args.repo]
    checkout = args.checkout.resolve()
    files = sources(args.repo, checkout)
    recs = oracle(checkout / conf["root"], files, args.python, args.output)
    errors = [r for r in recs if "mypy_error" in r]
    uses = Counter(r["kind"] for r in answer_key.body(recs) if "use" in r)
    print(f"{args.repo}: {len(files)} files, {len(errors)} mypy errors in "
          f"{len({r['file'] for r in errors})} files, uses: "
          + ", ".join(f"{k} {v}" for k, v in uses.most_common())
          + f"; declared names: {len(declared.declared_records(recs))}")
    print("abstained: " + abstentions([r for r in answer_key.body(recs) if "use" in r]))
    return 0


def abstentions(uses: list[dict]) -> str:
    """How many places each checker abstained at (oracle: abstains_*)."""
    count = Counter(n for r in uses for n in r.get("abstained", ()))
    return ", ".join(f"{n} {count[n]}" for n in CHECKERS)


def scope(args) -> int:
    ir = {t["id"]: t["location"]["file"] for t in json.loads(args.ir.read_text())["types"]
          if t["language"] == "python"}
    return answer_key.in_scope(answer_key.read(args.oracle), ir, language="Python")


def compare(args) -> int:
    from draftsman.extractor import Extractor
    from draftsman.langs import spec_for_path
    from draftsman.resolve import _Builder
    from draftsman.wrappers import Wrappers

    checkout = args.checkout.resolve()
    root = checkout / REPOS[args.repo]["root"]
    raw = [Extractor(spec_for_path(rel)).extract(f, rel, root)
           for f, rel in sources(args.repo, checkout)]
    builder = _Builder(str(root), raw, Wrappers.load())
    if args.declared:
        declared.watch(builder)
    ir = builder.build()
    recs = answer_key.read(args.oracle, declared=args.declared)
    if answer_key.in_scope(recs, {t.id: t.location.file for t in ir.types
                                  if t.language == "python"}, language="Python"):
        return 1
    if args.declared:
        return declared.report(builder, recs, root, args, key="the three checkers")
    return answer_key.compare(builder.body_uses, recs, args.verbose,
                              key="the three checkers")


def measure(args) -> int:
    recs = answer_key.read(args.oracle)
    uses = [r for r in recs if "use" in r]
    project_names = {d["declared"].rsplit(".", 1)[-1] for d in recs if "declared" in d}
    declared: set = set()
    if args.ir:
        declared = {(r["from"], r["to"]) for r in json.loads(args.ir.read_text())["relations"]}
    disputed = [r for r in uses if r["kind"] == "disputed"]
    print(f"names recorded: {len(uses)}; the three checkers agree on {len(uses) - len(disputed)}, "
          f"differ on {len(disputed)}")

    def pairs(rs) -> set:
        return {(r["from"], r["target"]) for r in rs if answer_key.drawable(r)}

    def count(rs) -> str:
        rs = list(rs)
        n, p = sum(map(answer_key.drawable, rs)), pairs(rs)
        text = f"{n} uses, {len(p)} relations"
        return text + (f" ({len(p - declared)} not in ir.json)" if args.ir else "")

    print(f"project classes named in bodies, where the three agree: {count(uses)}")
    print(f"  in annotations: {count(r for r in uses if r['annotation'])}")
    kinds = Counter(r["kind"] for r in uses)
    print("by kind: " + ", ".join(f"{k} {v}" for k, v in kinds.most_common()))
    shadows = [r for r in uses if r["kind"] in ("var", "local") and r["use"] in project_names]
    print(f"variables and local classes named like a project class: {len(shadows)}")
    for r in shadows[:None if args.verbose else 10]:
        print(f"  {r['file']}:{r['line']}:{r['col'] + 1} {r['use']} ({r['kind']}: "
              f"{r['mypy']}) in {r['from']}")
    print("disputed, by what each said (mypy | pyright | ty):")
    by = Counter((r["mypy"].split(" ")[0], r.get("pyright", "-").split(":")[0],
                  r.get("ty", "-").split(":")[0]) for r in disputed)
    for (m, p, t), n in by.most_common(None if args.verbose else 15):
        print(f"  {n:6}  {m} | {p} | {t}")
    return 0


def checkers(args) -> int:
    """How often each pair of checkers gives the same answer, and how often a server
    gives none."""
    uses = [r for r in answer_key.read(args.oracle) if "use" in r]
    for name in CHECKERS[1:]:
        errors = Counter(r.get(name, "") for r in uses if r.get(name, "").startswith("error"))
        none = sum(1 for r in uses if r.get(name) == "none")
        print(f"{name}: {len(uses)} positions, {sum(errors.values())} without an answer "
              f"({', '.join(f'{k} {v}' for k, v in errors.most_common(3)) or '-'}), "
              f"{none} answered with no definition")
    print("abstained (no definition where it marks the code unreachable): "
          + abstentions(uses))
    for a, b in (("mypy", "pyright"), ("mypy", "ty"), ("pyright", "ty")):
        same = sum(1 for r in uses if r["answers"].get(a) == r["answers"].get(b))
        print(f"{a} = {b}: {same} of {len(uses)}")
    return 0


REVIEW = HERE / "review"


def key_dir(d: Path, out: Path) -> list[dict]:
    from extract import discover
    return oracle(d, discover(d, {"python"}, []), sys.executable, out)


def check_dir(root: Path, recs: list[dict], verbose: bool, args=None) -> int:
    from extract import discover
    from draftsman.extractor import Extractor
    from draftsman.langs import spec_for_path
    from draftsman.resolve import _Builder
    from draftsman.wrappers import Wrappers
    builder = _Builder(str(root), [Extractor(spec_for_path(rel)).extract(f, rel, root)
                                   for f, rel in discover(root, {"python"}, [])], Wrappers.load())
    if args is not None and args.declared:
        declared.watch(builder)
        builder.build()
        return declared.report(builder, recs, root, args, key="the three checkers")
    builder.build()
    return answer_key.compare(builder.body_uses, recs, verbose, key="the three checkers")


def key(args) -> int:
    d = args.dir.resolve()
    with tempfile.TemporaryDirectory() as tmp:
        out = args.output or Path(tmp, "key.jsonl")
        recs = key_dir(d, out)
        print(f"{args.dir}: {sum(1 for r in recs if 'use' in r)} names, "
              f"{sum(1 for r in recs if r.get('kind') == 'disputed')} disputed")
        if args.compare:
            return check_dir(d, answer_key.body(recs) if not args.declared else recs,
                             args.verbose, args)
    return 0


def review(args) -> int:
    import review_sets
    return review_sets.review(REVIEW, args.sets, key_dir, check_dir)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest").set_defaults(fn=selftest)
    r = sub.add_parser("run")
    r.add_argument("repo", choices=sorted(REPOS))
    r.add_argument("--checkout", type=Path, required=True)
    r.add_argument("--python", required=True,
                   help="a Python whose site-packages hold the repository's dependencies")
    r.add_argument("-o", "--output", type=Path, required=True)
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
    declared.arguments(k)
    k.set_defaults(fn=compare)
    m = sub.add_parser("measure")
    m.add_argument("oracle", type=Path)
    m.add_argument("--ir", type=Path, help="ir.json of the same sources: count only what it lacks")
    m.add_argument("-v", "--verbose", action="store_true", help="list every shadow and dispute")
    m.set_defaults(fn=measure)
    a = sub.add_parser("checkers")
    a.add_argument("oracle", type=Path)
    a.set_defaults(fn=checkers)
    kd = sub.add_parser("key")
    kd.add_argument("dir", type=Path)
    kd.add_argument("-o", "--output", type=Path)
    kd.add_argument("--compare", action="store_true")
    kd.add_argument("--declared", action="store_true")
    kd.add_argument("--save", type=Path)
    kd.add_argument("-v", "--verbose", action="store_true")
    kd.set_defaults(fn=key)
    rv = sub.add_parser("review")
    rv.add_argument("sets", nargs="*")
    rv.set_defaults(fn=review)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
