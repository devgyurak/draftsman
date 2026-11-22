"""The TypeScript compiler as the answer key for body relations (issue #5).

type_uses.mjs records every name the compiler's TypeChecker resolves in a body, in the
format bench/answer_key.py gives; this script runs it and reads its output.

    uv run bench/tsc_oracle/oracle.py selftest
    uv run bench/tsc_oracle/oracle.py run REPO --checkout DIR -o OUT.jsonl
    uv run bench/tsc_oracle/oracle.py scope REPO OUT.jsonl ir.json
    uv run bench/tsc_oracle/oracle.py compare REPO OUT.jsonl --checkout DIR [-v]
    uv run bench/tsc_oracle/oracle.py measure OUT.jsonl [--ir ir.json]

`selftest` checks the key against the hand-written answers in
tests/fixtures/typescript/body (tests/fixtures/java/body/README.md gives the marker
format). `run` compiles a repository's sources as its end-to-end page extracts them
(docs/e2e/typescript/), with the repository's tsconfig.json; its dependencies must be
installed (`npm ci --ignore-scripts`, `pnpm install --ignore-scripts`), as imports
only resolve through them. `scope` fails unless the key saw the same types, declared in
the same files, as ir.json of those sources. `compare` extracts the same sources and
checks every name a body relation is drawn from against what the compiler resolved at
its place. `measure` prints what the rules for hiding names are decided by.

The compiler is the `typescript` package pinned in package.json here: `npm ci` in
bench/tsc_oracle first. Node runs it.
"""

from __future__ import annotations

import argparse
import json
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
from extract import discover  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "typescript" / "body"
SUFFIXES = (".ts", ".tsx", ".mts", ".cts")

# as docs/e2e/typescript/ extracts them: "root" is the path given to extract.py,
# "tsconfig" the project's (relative to the checkout), "langs" its --lang
REPOS = {
    "nest": {"commit": "09b656cb8d", "root": "packages", "tsconfig": "tsconfig.json",
             "langs": ["typescript"], "exclude": ["**/test/**", "**/*.spec.ts"]},
    "typeorm": {"commit": "d5b143dd7e", "root": "packages/typeorm/src",
                "tsconfig": "packages/typeorm/tsconfig.json",
                "langs": ["typescript", "tsx"], "exclude": []},
}


def oracle(root: Path, files: list[Path], tsconfig: Path, out: Path) -> list[dict]:
    """Run type_uses.mjs over ``files`` (paths reported below ``root``)."""
    if not (HERE / "node_modules" / "typescript").is_dir():
        sys.exit(f"oracle: no typescript package; run `npm ci` in {HERE}")
    with tempfile.TemporaryDirectory() as tmp:
        srcs = Path(tmp, "sources")
        srcs.write_text("".join(f"{f}\n" for f in files))
        subprocess.run(["node", "--max-old-space-size=8192", HERE / "type_uses.mjs", out,
                        root, tsconfig, srcs], check=True)
    return answer_key.read(out)


def expected(root: Path) -> dict[tuple[str, int, int], tuple[str, str]]:
    return answer_key.expected(root, SUFFIXES)


def selftest(_args) -> int:
    files = sorted(p for p in FIXTURE.rglob("*") if p.suffix in SUFFIXES)
    with tempfile.TemporaryDirectory() as tmp:
        recs = oracle(FIXTURE, files, FIXTURE / "tsconfig.json", Path(tmp, "fixture.jsonl"))
    return answer_key.selftest(recs, expected(FIXTURE))


def sources(repo: str, checkout: Path) -> list[tuple[Path, str]]:
    conf = REPOS[repo]
    return discover(checkout / conf["root"], set(conf["langs"]), conf["exclude"])


def run(args) -> int:
    conf = REPOS[args.repo]
    checkout = args.checkout.resolve()
    files = [f for f, _ in sources(args.repo, checkout)]
    recs = oracle(checkout / conf["root"], files, checkout / conf["tsconfig"], args.output)
    errors = [r for r in recs if "diagnostic" in r]
    uses = Counter(r["kind"] for r in recs if "use" in r)
    print(f"{args.repo}: {len(files)} files, {len(errors)} compile errors in "
          f"{len({r['file'] for r in errors})} files, uses: "
          + ", ".join(f"{k} {v}" for k, v in uses.most_common()))
    for r in errors[:20]:
        print(f"  {r['file']}:{r['line']}: {r['diagnostic']}")
    return 0


def _languages() -> set[str]:
    return {"typescript", "tsx"}


def scope(args) -> int:
    ir = {t["id"]: t["location"]["file"] for t in json.loads(args.ir.read_text())["types"]
          if t["language"] in _languages()}
    return answer_key.in_scope(answer_key.read(args.oracle), ir, language="TypeScript")


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
    ir = builder.build()
    recs = answer_key.read(args.oracle)
    if answer_key.in_scope(recs, {t.id: t.location.file for t in ir.types
                                  if t.language in _languages()}, language="TypeScript"):
        return 1
    return answer_key.compare(builder.body_uses, recs, args.verbose, key="tsc")


def measure(args) -> int:
    recs = answer_key.read(args.oracle)
    uses = [r for r in recs if "use" in r]
    project_names = {d["declared"].rsplit(".", 1)[-1] for d in recs if "declared" in d}
    declared: set = set()
    if args.ir:
        declared = {(r["from"], r["to"]) for r in json.loads(args.ir.read_text())["relations"]}
    print(f"compile errors: {sum(1 for r in recs if 'diagnostic' in r)} in "
          f"{len({r['file'] for r in recs if 'diagnostic' in r})} files; names the compiler "
          f"could not resolve: {sum(1 for r in uses if r['kind'] == 'error')}")

    def pairs(rs) -> set:
        return {(r["from"], r["target"]) for r in rs if answer_key.drawable(r)}

    def count(rs) -> str:
        rs = list(rs)
        n, p = sum(map(answer_key.drawable, rs)), pairs(rs)
        text = f"{n} uses, {len(p)} relations"
        return text + (f" ({len(p - declared)} not in ir.json)" if args.ir else "")

    print(f"project types named in bodies: {count(uses)}")
    for position in ("type", "receiver"):
        print(f"  {position} position: {count(r for r in uses if r['pos'] == position)}")
    kinds = Counter(r["kind"] for r in uses if r["pos"] == "receiver")
    print("receiver position, by kind: " + ", ".join(f"{k} {v}" for k, v in kinds.most_common()))
    shadows = [r for r in uses if r["kind"] in ("var", "local") and r["use"] in project_names]
    print(f"variables and local classes named like a project type: {len(shadows)}")
    for r in shadows[:None if args.verbose else 10]:
        print(f"  {r['file']}:{r['line']}:{r['col'] + 1} {r['use']} ({r['kind']}, "
              f"{r['pos']} position) in {r['from']}")
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
    m.add_argument("-v", "--verbose", action="store_true", help="list the shadowing variables")
    m.set_defaults(fn=measure)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
