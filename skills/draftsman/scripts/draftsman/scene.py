"""IR + View -> Scene: the exact set of things to draw, independent of format."""

from __future__ import annotations

import fnmatch
from collections import deque
from dataclasses import dataclass, field, replace
from typing import Optional

from .model import IR, External, Member, Relation, Type
from .view import InferredEdge, TypeLookup, View, ViewError, split_hidden, type_matches


@dataclass
class FoldedRelation(Relation):
    """A relation drawn between the outer types its ends are folded into; ``fact`` is
    the relation as ir.json states it, between the nested types."""

    fact: Optional[Relation] = None
    # written on the arrow when the drawn kind is not the fact's: an inheritance of a
    # nested type, drawn as a dependency of its outer type (`TextAccumulator implements`)
    label: Optional[str] = None


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
    nested: str = "boxes"                   # "fold": nested types drawn inside their outer type
    folded: dict[str, list[str]] = field(default_factory=dict)  # shown type -> nested ids in it
    body: str = "none"                      # View.body_mode


def _neighbours(relations: list[Relation],
                nodes: set[str]) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """(neighbours along every relation, both ways; the annotated types of an annotation
    or annotation argument). An annotation leads from the annotated type to what it names
    and no further back: `@UnstableApi` on one class must not bring in the 132 others
    that carry it. Only the focus itself looks back along annotations (its users)."""
    adj: dict[str, set[str]] = {n: set() for n in nodes}
    back: dict[str, set[str]] = {n: set() for n in nodes}
    for r in relations:
        if r.from_ in nodes and r.to in nodes:
            adj[r.from_].add(r.to)
            (back if is_annotation(r) else adj)[r.to].add(r.from_)
    return adj, back


def is_annotation(r: Relation) -> bool:
    """Whether an annotation created the relation (`via` is "@Name" in ir.json)."""
    fact = r.fact if isinstance(r, FoldedRelation) and r.fact is not None else r
    return fact.kind == "dependency" and (fact.via or "").startswith("@")


def is_body(r: Relation) -> bool:
    """Whether a name written in a body created the relation (`evidence` "body")."""
    return r.evidence == "body"


def _within_hops(starts: set[str], adj: tuple[dict[str, set[str]], dict[str, set[str]]],
                 hops: int) -> set[str]:
    both, back = adj
    seen = set(starts)
    queue = deque((s, 0) for s in sorted(starts))
    while queue:
        node, d = queue.popleft()
        if d == hops:
            continue
        near = both.get(node, set()) | (back.get(node, set()) if node in starts else set())
        for nxt in sorted(near):
            if nxt not in seen:
                seen.add(nxt)
                queue.append((nxt, d + 1))
    return seen


def _label(r: Relation) -> Optional[str]:
    return r.label if isinstance(r, FoldedRelation) else None


def _collapse_dependencies(relations: list[Relation]) -> list[Relation]:
    """One dependency arrow per pair, and none where a stronger relation exists. A
    labelled one (a nested type's inheritance) is kept per label instead of a plain one.
    Of the rest a signature's comes first, then an annotation's, then a body's."""
    structural = {(r.from_, r.to) for r in relations if r.kind != "dependency"}
    labelled = {(r.from_, r.to) for r in relations if r.kind == "dependency" and _label(r)}
    # a pair a signature connects keeps that arrow, which the neighbourhood follows both
    # ways, rather than an annotation's; a body's only stands where neither does
    plain = {(r.from_, r.to) for r in relations if r.kind == "dependency" and not _label(r)
             and not is_annotation(r) and not is_body(r)}
    declared = {(r.from_, r.to) for r in relations if r.kind == "dependency" and not is_body(r)}
    seen: set[tuple] = set()
    out = []
    for r in relations:
        if r.kind == "dependency":
            pair = (r.from_, r.to)
            key = (*pair, _label(r))
            if pair in structural or key in seen or (pair in labelled and not _label(r)) \
                    or (pair in plain and is_annotation(r)) or (pair in declared and is_body(r)):
                continue
            seen.add(key)
        out.append(r)
    return out


def _fold_roots(ir: IR, focus: Optional[str]) -> dict[str, str]:
    """The type each type is drawn as when nested types are folded: its outermost
    enclosing type, or the focus when the focus encloses it (a focus on a nested type
    keeps its own box, and its own nested types fold into it)."""
    by_id = ir.type_index()
    roots: dict[str, str] = {}
    for t in ir.types:
        cur = t
        while cur.id != focus and cur.outer in by_id:
            cur = by_id[cur.outer]
        roots[t.id] = cur.id
    return roots


def _fold(r: Relation, roots: dict[str, str], by_id: dict[str, Type]) -> Optional[Relation]:
    """``r`` between the types its ends are drawn as; None when both fold onto one."""
    f, t = roots.get(r.from_, r.from_), roots.get(r.to, r.to)
    if (f, t) == (r.from_, r.to):
        return r
    if f == t:
        return None
    def inside(tid: str, root: str) -> str:   # `TextAccumulator` for Element.TextAccumulator
        inner, outer = by_id[tid].display_name, by_id[root].display_name
        return inner[len(outer) + 1:] if inner.startswith(outer + ".") else by_id[tid].name

    if r.kind in ("extends", "implements"):
        # Element is no NodeVisitor because Element.TextAccumulator is one: drawn
        # between the outer types, the inheritance is a dependency that says whose it is
        label = " ".join(p for p in (
            inside(r.from_, f) if f != r.from_ else None, r.kind,
            inside(r.to, t) if r.to in by_id and t != r.to else None) if p)
        return FoldedRelation(f, t, "dependency", r.source_location, via=r.via,
                              evidence=r.evidence, fact=r, label=label)
    via = r.via
    if via is not None and f != r.from_ and not via.startswith("@"):
        # the member belongs to the nested type: `Response.cookies` on Connection's arrow
        via = f"{inside(r.from_, f)}.{via}"
    return FoldedRelation(f, t, r.kind, r.source_location, r.multiplicity, r.ownership, via,
                          r.evidence, fact=r)


def _encloses(outer: str, tid: str, by_id: dict[str, Type]) -> bool:
    cur = by_id[tid].outer
    while cur is not None and cur in by_id:
        if cur == outer:
            return True
        cur = by_id[cur].outer
    return False


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


def build_scene(ir: IR, view: View, whole: bool = False) -> Scene:
    """What to draw. ``whole``: every type the view allows, the focus only marking where
    a reader starts (the HTML viewer); nested types still fold as around the focus."""
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

    by_id = ir.type_index()
    fold = view.nested_mode == "fold"
    roots = _fold_roots(ir, focus) if fold else {t.id: t.id for t in ir.types}
    # a type folded into a hidden type goes with it
    candidates = {t.id for t in ir.types if t.id not in hidden and roots[t.id] not in hidden}
    kinds = set(view.relations)
    body = view.body_mode

    def via_hidden(r: Relation) -> bool:
        return r.via is not None and any(
            type_matches(tp, by_id[r.from_]) and fnmatch.fnmatchcase(r.via, mp)
            for tp, mp in member_globs)

    drawn = [
        r for r in ir.relations
        if r.kind in kinds and r.from_ in candidates and not via_hidden(r)
        and (view.annotations or not is_annotation(r))
        and (body != "none" or not is_body(r))
        and (r.to in candidates or (view.externals and r.to in externals
                                    and r.to not in hidden))]
    if fold:
        drawn = [f for r in drawn if (f := _fold(r, roots, by_id)) is not None]
    relations = _collapse_dependencies(drawn)
    nodes = {roots[c] for c in candidates}

    # drawn as boxes, the focus's nested types are where its neighbourhood starts
    starts = ({focus} | {c for c in candidates if _encloses(focus, c, by_id)}) & nodes \
        if focus else set()
    if focus and not whole:
        declared = [r for r in relations if not is_body(r)]
        visible = _within_hops(starts, _neighbours(declared, nodes), view.hops)
        if view.hops:
            # a type a body of the focus names, or whose body names the focus, is drawn but
            # leads nowhere: bodies name far more types than declarations do
            for r in relations:
                if is_body(r) and r.from_ in starts:
                    visible.add(r.to)
                elif is_body(r) and r.to in starts:
                    visible.add(r.from_)
    else:
        visible = set(nodes)
    # "focus": only the body relations that touch the focus; the viewer (``whole``) is given
    # all of them, as its reader moves the focus
    if body == "focus" and not (whole and focus):
        relations = [r for r in relations
                     if not is_body(r) or r.from_ in starts or r.to in starts]

    # inferred edges may pull in their endpoints
    ghosts: set[str] = set()
    inferred: list[InferredEdge] = []
    fact_pairs = {(roots.get(r.from_, r.from_), roots.get(r.to, r.to), r.kind)
                  for r in ir.relations}
    pulled: set[str] = set()
    for e in view.inferred_edges:
        ends = []
        for ref in (e.from_, e.to):
            tid = lookup.find(ref)
            if tid is not None:
                ends.append(("type", roots[tid]))
            elif ref in externals:
                ends.append(("external", ref))
            elif ref in unresolved_names:
                ends.append(("ghost", ref))
            else:
                raise ViewError(
                    f"inferred edge {e.from_} -> {e.to}: {ref!r} is neither a type in ir.json "
                    f"nor an unresolved reference; inferred edges may only connect those")
        (fk, fid), (tk, tid) = ends
        if fid == tid and fk == tk == "type" and fold:
            warnings.append(f"inferred edge {e.from_} -> {e.to} joins types folded into {fid}; "
                            "skipped")
            continue
        if (fid, tid, e.kind) in fact_pairs:
            warnings.append(f"inferred edge {fid} -> {tid} ({e.kind}) is already a fact; skipped")
            continue
        if any(k == "type" and i in hidden for k, i in ends):
            warnings.append(f"inferred edge {fid} -> {tid} touches a hidden type; skipped")
            continue
        if not any(k == "type" and i in visible for k, i in ends) and focus and not whole:
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
    folded: dict[str, list[str]] = {}
    if fold:
        for c in sorted(candidates):
            if roots[c] != c and roots[c] in visible:
                folded.setdefault(roots[c], []).append(c)

    def targets(entries, label):
        out = []
        for target, payload in entries:
            tid = lookup.find(target) or (target if target in externals else None)
            if tid is None:
                raise ViewError(f"{label}: no type {target!r} in ir.json")
            if roots.get(tid, tid) != tid:
                warnings.append(f"{label} on {tid} drawn on {roots[tid]}: nested types are "
                                "folded into their outer type")
                tid = roots[tid]
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
            tid = roots[lookup.require(ref, f"group {g.name!r}")]
            if tid in grouped and grouped[tid] == g.name:
                continue   # several nested types of one outer type
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
        nested=view.nested_mode,
        folded=folded,
        body=body,
    )
