#!/usr/bin/env python3
"""Draw a class diagram in one step: extract, choose the scope, render, validate, report.

    python scripts/draw.py <path | ir.json> [--focus TYPE] [--hops N]
        [--members all|public|none] [--hide GLOB]... [--relations KIND,...]
        [--exclude GLOB]... [--tests] [--lang L]... [--wrappers YAML]...
        [--format mermaid|svg|html] [--view view.json] [-o FILE] [--work DIR]
        [--max-types N]

stdout: the Mermaid text (svg and html: nothing, the report names the file).
stderr: a report for judging the scope: the repository's size, what was drawn, what one
more hop would add, what the view hid, the unresolved references of the drawn types, the
Mermaid check, and the ir.json to pass instead of <path> when drawing again.

Flags override the same keys of --view; --hide adds to its `hidden`. Test directories
(`**/test/**`, `**/tests/**`) are excluded unless --tests is given. When neither the flags
nor the view set `hops`, a focus diagram is drawn at the widest hops (the view default
2, down to 1) that fits --max-types, and the report says what the wider one would draw.

Exit codes: 0 drawn; 1 bad input, a view error or invalid Mermaid; 2 a missing
dependency; 3 not drawn, the scope has more than --max-types types (the report says how
to narrow it).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import replace
from pathlib import Path

from draftsman.model import IR, RELATION_KINDS
from draftsman.render_web import RenderError
from draftsman.scene import Scene, build_scene
from draftsman.view import MEMBER_DETAIL, OUTPUTS, View, ViewError, split_hidden, type_matches

HERE = Path(__file__).resolve().parent
TEST_EXCLUDES = ["**/test/**", "**/tests/**"]
EXTENSIONS = {"mermaid": "mmd", "svg": "svg", "html": "html"}
BY_EXTENSION = {".mmd": "mermaid", ".mermaid": "mermaid", ".svg": "svg", ".html": "html"}
INSTALL = """\
draftsman: missing Python package {name!r}. Install once:
  pip install "tree-sitter>=0.25" tree-sitter-language-pack pyyaml
Without pip, run every command through uv instead:
  uv run --with "tree-sitter>=0.25" --with tree-sitter-language-pack --with pyyaml \\
    python3 {script} ...
In a sandbox without network access, ask for permission to install, or ask the user to."""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("path", type=Path, help="source directory or file, or an ir.json")
    ap.add_argument("--focus", metavar="TYPE", help="draw this type and its neighbourhood")
    ap.add_argument("--hops", type=int, help="radius around --focus (view default: 2)")
    ap.add_argument("--members", choices=MEMBER_DETAIL, help="member detail for every class")
    ap.add_argument("--hide", action="append", default=[], metavar="GLOB",
                    help="hide types (`*Dto`) or members (`*#get*`); repeatable")
    ap.add_argument("--relations", metavar="KIND,...",
                    help=f"relation kinds to draw and follow: {','.join(RELATION_KINDS)}")
    ap.add_argument("--format", choices=OUTPUTS,
                    help="output (default: the view's, else from -o's extension, else mermaid)")
    ap.add_argument("--view", type=Path, help="view.json for groups, notes, highlights, ...")
    ap.add_argument("--exclude", action="append", default=[], metavar="GLOB",
                    help="skip source files matching (relative to <path>); repeatable")
    ap.add_argument("--tests", action="store_true",
                    help=f"keep test directories (default: exclude {' '.join(TEST_EXCLUDES)})")
    ap.add_argument("--lang", action="append", help="restrict to these languages (repeatable)")
    ap.add_argument("--wrappers", action="append", default=[], type=Path, metavar="YAML",
                    help="extra wrapper rules appended to config/wrappers.yaml")
    ap.add_argument("-o", "--output", type=Path, help="write the diagram here")
    ap.add_argument("--work", type=Path,
                    help="where ir.json and the diagram go (default: a new temporary "
                         "directory; next to <path> when it is an ir.json)")
    ap.add_argument("--max-types", type=int, default=30, metavar="N",
                    help="do not draw a mermaid or svg diagram of more types (default 30)")
    args = ap.parse_args(argv)

    if not args.path.exists():
        return fail(f"{args.path} does not exist")
    try:
        data = json.loads(args.view.read_text(encoding="utf-8")) if args.view else {}
    except (OSError, json.JSONDecodeError) as e:
        return fail(f"view error: {args.view}: {e}")
    if not isinstance(data, dict):
        return fail("view error: view must be a JSON object")
    overrides = {"focus": args.focus, "hops": args.hops, "members": args.members,
                 "output": args.format}
    if args.relations is not None:
        overrides["relations"] = [k.strip() for k in args.relations.split(",") if k.strip()]
    data.update({k: v for k, v in overrides.items() if v is not None})
    if args.hide:
        data["hidden"] = list(data.get("hidden") or []) + args.hide
    if "output" not in data and args.output is not None:
        data["output"] = BY_EXTENSION.get(args.output.suffix.lower(), "mermaid")

    # the facts: an ir.json given, or extracted now
    from_ir = args.path.is_file() and args.path.suffix == ".json"
    work = args.work or (args.path.resolve().parent if from_ir
                         else Path(tempfile.mkdtemp(prefix="draftsman-")))
    work.mkdir(parents=True, exist_ok=True)
    excludes = [] if from_ir else args.exclude + ([] if args.tests else TEST_EXCLUDES)
    if from_ir:
        try:
            ir = IR.load(args.path)
        except (ValueError, KeyError) as e:
            return fail(f"{args.path} is not an ir.json: {e}")
        ir_path = args.path
    else:
        try:
            import tree_sitter, tree_sitter_language_pack, yaml  # noqa: F401
        except ImportError as e:
            print(INSTALL.format(name=e.name, script=Path(__file__).relative_to(HERE.parent)),
                  file=sys.stderr)
            return 2
        from draftsman.langs import LANGUAGES
        from extract import extract
        unknown = sorted(set(args.lang or ()) - set(LANGUAGES))
        if unknown:
            return fail(f"unknown --lang {', '.join(unknown)}; one of {', '.join(LANGUAGES)}")
        langs = set(args.lang or LANGUAGES)
        ir = extract(args.path, langs, excludes, args.wrappers)
        if ir is None:
            return fail(f"no source files for {', '.join(sorted(langs))} under {args.path}")
        ir_path = work / "ir.json"
        ir.dump(ir_path)

    try:
        view = View.from_dict(data)
        fmt = view.output
        scene = build_scene(ir, view, whole=fmt == "html")
    except (ViewError, ValueError) as e:
        again = "" if from_ir else f" (the facts are in {ir_path}: draw from it)"
        return fail(f"view error: {e}{again}")

    # no hops asked for: the widest neighbourhood within the limit, down to one hop
    passed = None
    if scene.focus and fmt != "html" and "hops" not in data and size(scene) > args.max_types:
        for hops in range(view.hops - 1, 0, -1):
            narrower = build_scene(ir, replace(view, hops=hops))
            if size(narrower) <= args.max_types:
                passed = (view.hops, size(scene))
                view, scene = replace(view, hops=hops), narrower
                break

    report = Report(ir, view, scene, excludes, args.max_types, passed)
    if fmt != "html" and size(scene) > args.max_types:
        report.too_many()
        report.footer(ir_path)
        report.flush()
        return 3

    from render import RENDERERS
    try:
        text = RENDERERS[fmt](scene, ir)
    except RenderError as e:
        return fail(str(e), code=2)
    out = args.output or work / f"diagram.{EXTENSIONS[fmt]}"
    out.write_text(text, encoding="utf-8")
    report.drawn()

    code = 0
    if fmt == "mermaid":
        sys.stdout.write(text if text.endswith("\n") else text + "\n")
        sys.stdout.flush()
        code = report.validate(out)
    else:
        report.line(f"{fmt}: {out}")
    report.footer(ir_path)
    report.flush()
    return code


def size(scene: Scene) -> int:
    """The boxes a scene draws."""
    return len(scene.types) + len(scene.externals) + len(scene.ghosts)


def fail(message: str, code: int = 1) -> int:
    print(f"draftsman: {message}", file=sys.stderr)
    return code


class Report:
    """What the agent needs to judge the scope it chose, next to the diagram."""

    def __init__(self, ir: IR, view: View, scene: Scene, excludes: list[str],
                 limit: int, passed: tuple[int, int] | None = None):
        self.ir, self.view, self.scene = ir, view, scene
        self.limit = limit
        self.passed = passed   # (hops, types) of the default neighbourhood, over the limit
        self.types = ir.type_index()
        self.lines: list[str] = []
        from summary import counts
        self.line(f"repository: {counts(ir)}")
        if excludes:
            tests = all(p in excludes for p in TEST_EXCLUDES)
            self.line(f"excluded: {', '.join(excludes)}"
                      + (" (--tests keeps test directories)" if tests else ""))

    def line(self, text: str) -> None:
        self.lines.append(text)

    def flush(self) -> None:
        print("\n".join(f"draftsman: {l}" if not l.startswith(" ") else l
                        for l in self.lines), file=sys.stderr)

    def name(self, tid: str) -> str:
        t = self.types.get(tid)
        return t.display_name if t else tid

    def names(self, ids, limit: int = 12) -> str:
        ids = list(ids)
        shown = ", ".join(self.name(i) for i in ids[:limit])
        return shown + (f", … {len(ids) - limit} more" if len(ids) > limit else "")

    def by_degree(self, ids) -> list[str]:
        from summary import degree
        deg = degree(self.ir)
        return sorted(ids, key=lambda i: (-deg.get(i, 0), self.name(i)))

    def scope(self) -> None:
        s, v = self.scene, self.view
        if s.focus:
            hop = "hop" if s.hops == 1 else "hops"
            why = ""
            if self.passed:
                hops, n = self.passed
                why = (f" (chosen: {hops} hops would draw {n} types, over --max-types "
                       f"{self.limit}; --hops {hops} --max-types {n} draws them)")
            self.line(f"scope: focus {s.focus}, {s.hops} {hop}{why}")
        else:
            self.line("scope: every type the view allows (no focus)")
        if s.folded:
            nested = [n for ids in s.folded.values() for n in ids]
            self.line(f"nested types folded into their outer type: {len(nested)} "
                      f"({self.names(nested, 8)}); --view with \"nested\": \"boxes\" "
                      "draws them apart")
        if set(v.relations) != set(RELATION_KINDS):
            left = [k for k in RELATION_KINDS if k not in v.relations]
            self.line(f"relations: {', '.join(v.relations)} only (left out: {', '.join(left)})")
        if not v.annotations:
            self.line("annotations: dependencies only annotations create are left out")
        type_globs, member_globs = split_hidden(v.hidden)
        if type_globs:
            hits = {p: sum(type_matches(p, t) for t in self.ir.types) for p in type_globs}
            self.line("hidden types: " + ", ".join(f"{p} ({n})" for p, n in hits.items()))
        if member_globs:
            self.line("hidden members: " + ", ".join(f"{t}#{m}" for t, m in member_globs))
        members = v.members if isinstance(v.members, str) else json.dumps(v.members)
        self.line(f"members: {members}")

    def drawn(self) -> None:
        s = self.scene
        self.scope()
        ext = f", {len(s.externals)} external" if s.externals else ""
        self.line(f"drawn: {len(s.types)} types{ext}, {len(s.relations)} relations, "
                  f"{len(s.inferred)} inferred")
        if s.focus and not (self.view.output == "html"):
            more = {t.id for t in self.around(s.hops + 1).types} - self.shown()
            if more:
                self.line(f"one more hop adds {len(more)} types: "
                          f"{self.names(self.by_degree(more))}")
            else:
                self.line("one more hop adds nothing: the neighbourhood is complete")
        for w in s.warnings:
            self.line(f"warning: {w}")
        self.unresolved()

    def too_many(self) -> None:
        s, n = self.scene, size(self.scene)
        self.scope()
        self.line(f"NOT DRAWN: {n} types is over --max-types {self.limit}. Options, the ones "
                  "that keep every relation first:")
        self.line(f"  --max-types {n}: all {n} types; when the user asked for exactly this "
                  "scope and allows that many")
        if s.focus:
            for h in range(s.hops - 1, 0, -1):
                self.line(f"  --hops {h}: {size(self.around(h))} types")
        else:
            from summary import degree
            top = [f"{self.name(t)} ({k})" for t, k in degree(self.ir).most_common(12)]
            self.line("  --focus one type, the class the user named or one of the most "
                      "connected: " + ", ".join(top))
        structural = [k for k in self.view.relations if k != "dependency"]
        k = size(self.around(s.hops, relations=structural)) if structural else n
        if "dependency" in self.view.relations and k < n:
            self.line(f"  --relations {','.join(structural)}: {k} types, but classes related "
                      "only by use (parameters, locals, return types) drop out")
        self.line(f"  --format html: all {n} types in the explorable viewer")

    def shown(self) -> set[str]:
        return {t.id for t in self.scene.types}

    def around(self, hops: int, **changes) -> Scene:
        """The scene of the same view at ``hops`` (and other ``changes``)."""
        return build_scene(self.ir, replace(self.view, hops=hops, **changes))

    def unresolved(self) -> None:
        from summary import unresolved_lines
        drawn = self.shown() | {n for ids in self.scene.folded.values() for n in ids}
        entries = [u for u in self.ir.unresolved if u.from_ in drawn]
        if entries:
            self.lines.extend(unresolved_lines(self.ir, entries,
                                               "unresolved references of the drawn types"))
        elsewhere = len(self.ir.unresolved) - len(entries)
        if elsewhere:
            self.line(f"{elsewhere} more unresolved outside this diagram "
                      "(summary.py lists them)")
        if self.ir.diagnostics:
            files = Counter(d.file for d in self.ir.diagnostics)
            self.line(f"parse diagnostics: {len(self.ir.diagnostics)} in {len(files)} files "
                      "(summary.py lists them)")

    def validate(self, path: Path) -> int:
        try:
            res = subprocess.run(["bash", str(HERE / "validate.sh"), str(path)],
                                 capture_output=True, text=True, timeout=120)
        except (OSError, subprocess.TimeoutExpired) as e:
            self.line(f"mermaid: not syntax-checked ({e})")
            return 0
        if res.returncode == 0:
            self.line("mermaid: OK")
            return 0
        if res.returncode == 2:
            self.line(f"mermaid: not syntax-checked, no validator (npm ci --prefix {HERE})")
            return 0
        self.line("mermaid: INVALID; change the view or flags and draw again:")
        self.lines.extend("  " + l for l in (res.stderr or res.stdout).strip().splitlines()[:20])
        return 1

    def footer(self, ir_path: Path) -> None:
        self.line(f"ir.json: {ir_path} (pass it instead of the source path to draw again "
                  "without extracting)")


if __name__ == "__main__":
    sys.exit(main())
