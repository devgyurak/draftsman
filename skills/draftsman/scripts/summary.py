#!/usr/bin/env python3
"""Summarise ir.json so the diagram's scope can be chosen without reading it all.

    python scripts/summary.py ir.json [--top 10]

Prints type/relation counts, namespaces, the most connected types, common
annotations, unresolved references and parse diagnostics. With --type, prints
the members and relations of the given types instead.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from draftsman.model import IR
from draftsman.view import TypeLookup, ViewError


def describe(ir: IR, tid: str) -> None:
    t = ir.type_index()[tid]
    head = f"{t.display_name} [{t.kind}] {tid}  ({t.location.file}:{t.location.line})"
    print(head)
    if t.annotations:
        print("  annotations: " + ", ".join("@" + a for a in t.annotations))
    if t.generics:
        print("  generics: " + ", ".join(t.generics))
    for m in t.members:
        flags = " ".join(f for f, on in (("static", m.static), ("abstract", m.abstract)) if on)
        sig = m.name
        if m.kind in ("method", "constructor"):
            sig += "(" + ", ".join(f"{p.type_ref} {p.name}" for p in m.params) + ")"
        typ = f": {m.type_ref}" if m.type_ref else ""
        print(f"  {m.visibility:9s} {m.kind:13s} {sig}{typ}{'  ' + flags if flags else ''}")
    out_rel = [r for r in ir.relations if r.from_ == tid]
    in_rel = [r for r in ir.relations if r.to == tid]
    for label, rels, other in (("out", out_rel, "to"), ("in", in_rel, "from_")):
        for r in rels:
            extra = " ".join(x for x in (r.multiplicity, f"via {r.via}" if r.via else None) if x)
            print(f"  {label:3s} {r.kind:11s} {getattr(r, other)}  {extra}".rstrip())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("ir", type=Path)
    ap.add_argument("--top", type=int, default=10, help="how many connected types to list")
    ap.add_argument("--type", action="append", metavar="NAME",
                    help="describe this type (id or unique name); repeatable")
    args = ap.parse_args(argv)
    ir = IR.load(args.ir)
    types = ir.type_index()

    if args.type:
        lookup = TypeLookup(ir)
        try:
            ids = [lookup.require(name, "--type") for name in args.type]
        except ViewError as e:
            print(f"draftsman: {e}", file=sys.stderr)
            return 1
        for i, tid in enumerate(ids):
            if i:
                print()
            describe(ir, tid)
        return 0

    kinds = Counter(t.kind for t in ir.types)
    rels = Counter(r.kind for r in ir.relations)
    print(f"root: {ir.root}  languages: {', '.join(ir.languages) or '-'}  files: {ir.files}")
    print(f"types: {len(ir.types)} ({', '.join(f'{k} {v}' for k, v in kinds.most_common())})")
    print(f"relations: {len(ir.relations)} "
          f"({', '.join(f'{k} {v}' for k, v in rels.most_common()) or 'none'})")

    namespaces = Counter(t.namespace or "(none)" for t in ir.types)
    print("\nnamespaces:")
    for ns, n in sorted(namespaces.items()):
        print(f"  {ns}: {n}")

    pairs = {frozenset((r.from_, r.to)) for r in ir.relations
             if r.from_ in types and r.to in types and r.from_ != r.to}
    degree: Counter = Counter(t for pair in pairs for t in pair)
    print(f"\nmost connected (distinct related project types, top {args.top}):")
    for tid, n in degree.most_common(args.top):
        t = types[tid]
        print(f"  {n:3d}  {t.display_name:30s} {t.kind:14s} {tid}")

    annos = Counter(a for t in ir.types for a in t.annotations)
    if annos:
        print("\ntype annotations: "
              + ", ".join(f"@{a} {n}" for a, n in annos.most_common(15)))

    if ir.externals:
        print(f"\nexternal supertypes: {', '.join(e.id for e in ir.externals)}")

    if ir.unresolved:
        # names only explained by something outside the sources (a wildcard import, an
        # external supertype: `LayoutParams` inside a FrameLayout subclass) are almost
        # always framework types; list them compactly, the rest in full
        wild = [u for u in ir.unresolved if u.reason == "outside"]
        rest = [u for u in ir.unresolved if u not in wild]
        reasons = Counter(u.reason for u in ir.unresolved if u.reason)
        split = ", ".join(f"{n} {r}" for r, n in sorted(reasons.items()))
        print(f"\nunresolved references ({len(ir.unresolved)}{': ' + split if split else ''}):")
        for u in rest:
            where = f"{types[u.from_].display_name}" + (f".{u.via}" if u.via else "")
            extra = []
            if u.candidates:
                extra.append("candidates: " + ", ".join(u.candidates))
            if u.hint:
                extra.append(u.hint)
            tail = f"  [{'; '.join(extra)}]" if extra else ""
            print(f"  {u.raw_type:24s} in {where}  ({u.location.file}:{u.location.line}){tail}")
        if wild:
            names = Counter(u.raw_type for u in wild)
            print(f"  + {len(wild)} only explained by wildcard imports or external supertypes "
                  "(likely external): "
                  + ", ".join(f"{n} ×{c}" if c > 1 else n for n, c in names.most_common(40))
                  + (" …" if len(names) > 40 else ""))

    if ir.diagnostics:
        files = len({d.file for d in ir.diagnostics})
        print(f"\ndiagnostics ({len(ir.diagnostics)} in {files} files):")
        for d in ir.diagnostics[:40]:
            span = f"{d.line}-{d.end_line}" if d.end_line and d.end_line != d.line else d.line
            print(f"  {d.file}:{span}: {d.message}")
        if len(ir.diagnostics) > 40:
            print(f"  … {len(ir.diagnostics) - 40} more in ir.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
