#!/usr/bin/env python3
"""Extract class-diagram facts from source code into ir.json.

    python scripts/extract.py <path> [-o ir.json] [--lang java] [--exclude GLOB]...

Nothing in the output is guessed: types, members and relations come from
tree-sitter parse trees. References the extractor could not resolve are
listed under "unresolved".
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import sys
from pathlib import Path

from draftsman.extractor import Extractor
from draftsman.langs import LANGUAGES, spec_for_path
from draftsman.langs.base import SKIP_DIRS
from draftsman.resolve import build_ir
from draftsman.wrappers import Wrappers


def excluded(rel: str, patterns: list[str]) -> bool:
    # fnmatch's `*` already crosses `/`; a leading `**/` should also match at the top level
    return any(fnmatch.fnmatch(rel, p) or (p.startswith("**/") and fnmatch.fnmatch(rel, p[3:]))
               for p in patterns)


def discover(root: Path, langs: set[str], excludes: list[str]) -> list[tuple[Path, str]]:
    if root.is_file():
        return [(root, root.name)]
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for fn in sorted(filenames):
            path = Path(dirpath) / fn
            rel = path.relative_to(root).as_posix()
            spec = spec_for_path(fn)
            if spec is None or spec.name not in langs:
                continue
            if excluded(rel, excludes):
                continue
            found.append((path, rel))
    return found


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("path", type=Path, help="source directory or file")
    ap.add_argument("-o", "--output", type=Path, help="write ir.json here (default: stdout)")
    ap.add_argument("--lang", action="append", choices=sorted(LANGUAGES),
                    help="restrict to these languages (repeatable)")
    ap.add_argument("--exclude", action="append", default=[], metavar="GLOB",
                    help="skip files whose path relative to <path> matches (repeatable), "
                         "e.g. 'src/test/**'")
    ap.add_argument("--wrappers", action="append", default=[], type=Path, metavar="YAML",
                    help="extra wrapper rules appended to config/wrappers.yaml")
    args = ap.parse_args(argv)

    root = args.path.resolve()
    if not root.exists():
        ap.error(f"{args.path} does not exist")
    langs = set(args.lang or LANGUAGES)
    files = discover(root, langs, args.exclude)
    if not files:
        print(f"no source files for {', '.join(sorted(langs))} under {args.path}",
              file=sys.stderr)
        return 1

    src_root = root if root.is_dir() else root.parent
    extractors = {}
    raw_files = []
    for path, rel in files:
        spec = spec_for_path(path.name)
        ex = extractors.setdefault(spec.name, Extractor(spec))
        raw_files.append(ex.extract(path, rel, src_root))

    ir = build_ir(str(args.path), raw_files, Wrappers.load(*args.wrappers))
    text = ir.dump(args.output)
    if args.output is None:
        sys.stdout.write(text)

    counts = {}
    for r in ir.relations:
        counts[r.kind] = counts.get(r.kind, 0) + 1
    rel_summary = ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) or "none"
    print(
        f"draftsman: {ir.files} files, {len(ir.types)} types, relations: {rel_summary}, "
        f"{len(ir.unresolved)} unresolved, {len(ir.diagnostics)} diagnostics",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
