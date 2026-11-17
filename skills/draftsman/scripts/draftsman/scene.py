"""IR + View -> Scene: the exact set of things to draw, independent of format."""

from __future__ import annotations

import fnmatch
from collections import deque
from dataclasses import dataclass, field, replace
from typing import Optional

from .model import IR, External, Member, Relation, Type
from .view import InferredEdge, TypeLookup, View, ViewError, split_hidden, type_matches


@dataclass
class Scene:
    types: list[Type]                       # visible project types, members already filtered
    externals: list[External]
    ghosts: list[str]                       # endpoints of inferred edges that are not in the IR
    relations: list[Relation]
    inferred: list[InferredEdge]            # endpoints are type ids, external ids or ghosts
    groups: list[tuple[str, list[str]]]
    highlights: list[tuple[str, str]]
    notes: list[tuple[str, str]]
    focus: Optional[str]
    hops: int
    direction: Optional[str]
    title: Optional[str]
    warnings: list[str] = field(default_factory=list)


def _neighbours(relations: list[Relation], nodes: set[str]) -> dict[str, set[str]]:
    adj: dict[str, set[str]] = {n: set() for n in nodes}
    for r in relations:
        if r.from_ in nodes and r.to in nodes:
            adj[r.from_].add(r.to)
            adj[r.to].add(r.from_)
    return adj


def _within_hops(start: str, adj: dict[str, set[str]], hops: int) -> set[str]:
    seen = {start}
    queue = deque([(start, 0)])
    while queue:
        node, d = queue.popleft()
        if d == hops:
            continue
        for nxt in sorted(adj.get(node, ())):
            if nxt not in seen:
                seen.add(nxt)
                queue.append((nxt, d + 1))
    return seen


def _collapse_dependencies(relations: list[Relation]) -> list[Relation]:
    """One dependency arrow per pair, and none where a stronger relation exists."""
    structural = {(r.from_, r.to) for r in relations if r.kind != "dependency"}
    seen: set[tuple[str, str]] = set()
    out = []
    for r in relations:
        if r.kind == "dependency":
            pair = (r.from_, r.to)
            if pair in structural or pair in seen:
                continue
            seen.add(pair)
        out.append(r)
    return out


def _filter_members(t: Type, member_globs: list[tuple[str, str]], detail: str,
                    used: set[int]) -> list[Member]:
    if detail == "none":
        return []
    out = []
    for m in t.members:
        if detail == "public" and m.visibility != "public" and m.kind != "enum_constant":
            continue
        hit = False
        for i, (tp, mp) in enumerate(member_globs):
            if type_matches(tp, t) and fnmatch.fnmatchcase(m.name, mp):
                used.add(i)
                hit = True
        if not hit:
            out.append(m)
    return out


def build_scene(ir: IR, view: View) -> Scene:
    lookup = TypeLookup(ir)
    warnings: list[str] = []
    externals = {e.id: e for e in ir.externals}
    unresolved_names = {u.raw_type for u in ir.unresolved}

    type_globs, member_globs = split_hidden(view.hidden)
    hidden: set[str] = set()
    for pat in type_globs:
        hits = {t.id for t in ir.types if type_matches(pat, t)}
        hits |= {e for e in externals if fnmatch.fnmatchcase(e, pat)
                 or fnmatch.fnmatchcase(externals[e].name, pat)}
        if not hits:
            warnings.append(f"hidden pattern {pat!r} matches no type")
        hidden |= hits

    focus = lookup.require(view.focus, "focus") if view.focus else None
    if focus in hidden:
        raise ViewError(f"focus {focus!r} is hidden by the view")

    candidates = {t.id for t in ir.types} - hidden
    kinds = set(view.relations)
    by_id = ir.type_index()

    def via_hidden(r: Relation) -> bool:
        return r.via is not None and any(
            type_matches(tp, by_id[r.from_]) and fnmatch.fnmatchcase(r.via, mp)
            for tp, mp in member_globs)

    relations = _collapse_dependencies([
        r for r in ir.relations
        if r.kind in kinds and r.from_ in candidates and not via_hidden(r)
        and (r.to in candidates or (view.externals and r.to in externals
                                    and r.to not in hidden))])

    if focus:
        visible = _within_hops(focus, _neighbours(relations, candidates), view.hops)
    else:
        visible = set(candidates)

    # inferred edges may pull in their endpoints
    ghosts: set[str] = set()
    inferred: list[InferredEdge] = []
    fact_pairs = {(r.from_, r.to, r.kind) for r in ir.relations}
    pulled: set[str] = set()
    for e in view.inferred_edges:
        ends = []
        for ref in (e.from_, e.to):
            tid = lookup.find(ref)
            if tid is not None:
                ends.append(("type", tid))
            elif ref in externals:
                ends.append(("external", ref))
            elif ref in unresolved_names:
                ends.append(("ghost", ref))
            else:
                raise ViewError(
                    f"inferred edge {e.from_} -> {e.to}: {ref!r} is neither a type in ir.json "
                    f"nor an unresolved reference; inferred edges may only connect those")
        (fk, fid), (tk, tid) = ends
        if (fid, tid, e.kind) in fact_pairs:
            warnings.append(f"inferred edge {fid} -> {tid} ({e.kind}) is already a fact; skipped")
            continue
        if any(k == "type" and i in hidden for k, i in ends):
            warnings.append(f"inferred edge {fid} -> {tid} touches a hidden type; skipped")
            continue
        if not any(k == "type" and i in visible for k, i in ends) and focus:
            warnings.append(f"inferred edge {fid} -> {tid} is outside the focus; skipped")
            continue
        for k, i in ends:
            if k == "type":
                pulled.add(i)
            elif k == "ghost":
                ghosts.add(i)
        inferred.append(InferredEdge(fid, tid, e.kind, e.rationale))
    visible |= pulled

    relations = [r for r in relations if r.from_ in visible
                 and (r.to in visible or r.to in externals)]
    shown_externals = sorted({r.to for r in relations if r.to in externals}
                             | {i for e in inferred for i in (e.from_, e.to) if i in externals})

    used_member_globs: set[int] = set()
    shown = [t for t in ir.types if t.id in visible]
    detail = {t.id: view.member_detail(t) for t in shown}
    types = [replace(t, members=_filter_members(t, member_globs, detail[t.id], used_member_globs))
             for t in shown]
    for i, (tp, mp) in enumerate(member_globs):
        if i not in used_member_globs and any(lv != "none" for lv in detail.values()):
            warnings.append(f"hidden pattern '{tp}#{mp}' matches no visible member")
    if isinstance(view.members, dict):
        for pattern in view.members:
            if pattern != "*" and not any(type_matches(pattern, t) for t in shown):
                warnings.append(f"members pattern {pattern!r} matches no visible type")

    drawable = visible | set(shown_externals) | ghosts

    def targets(entries, label):
        out = []
        for target, payload in entries:
            tid = lookup.find(target) or (target if target in externals else None)
            if tid is None:
                raise ViewError(f"{label}: no type {target!r} in ir.json")
            if tid not in drawable:
                warnings.append(f"{label} on {tid} skipped: not in the diagram")
                continue
            out.append((tid, payload))
        return out

    highlights = targets([(h.target, h.reason) for h in view.highlights], "highlight")
    notes = targets([(n.target, n.text) for n in view.notes], "note")

    groups: list[tuple[str, list[str]]] = []
    grouped: dict[str, str] = {}
    for g in view.groups:
        ids = []
        for ref in g.members:
            tid = lookup.require(ref, f"group {g.name!r}")
            if tid in grouped:
                raise ViewError(f"{tid} is in both group {grouped[tid]!r} and {g.name!r}")
            grouped[tid] = g.name
            if tid in visible:
                ids.append(tid)
        if ids:
            groups.append((g.name, sorted(ids)))

    return Scene(
        types=types,
        externals=[externals[e] for e in shown_externals],
        ghosts=sorted(ghosts),
        relations=relations,
        inferred=inferred,
        groups=groups,
        highlights=highlights,
        notes=notes,
        focus=focus,
        hops=view.hops,
        direction=view.direction,
        title=view.title,
        warnings=warnings,
    )
