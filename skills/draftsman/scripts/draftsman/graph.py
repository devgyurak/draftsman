"""Scene -> plain graph JSON shared by the SVG renderer and the HTML viewer.

Everything here is already decided (members filtered, labels formatted); the
JavaScript side only lays it out (ELK) and draws it (assets/draw.js).
"""

from __future__ import annotations

from typing import Optional

from .model import IR, STEREOTYPES, VISIBILITY_SYMBOLS, Member, Relation, Type
from .scene import FoldedRelation, Scene, is_annotation, is_body


def member_text(m: Member) -> str:
    vis = VISIBILITY_SYMBOLS.get(m.visibility, "")
    if m.kind == "enum_constant":
        return m.name
    if m.kind in ("method", "constructor"):
        params = ", ".join(f"{p.name}: {p.type_ref}" if p.type_ref else p.name
                           for p in m.params)
        ret = f": {m.type_ref}" if m.type_ref and m.kind == "method" else ""
        name = f"{m.receiver}.{m.name}" if m.receiver else m.name
        return f"{vis} {name}({params}){ret}"
    return f"{vis} {m.name}: {m.type_ref}" if m.type_ref else f"{vis} {m.name}"


def _member(m: Member) -> dict:
    return {
        "text": member_text(m),
        "kind": m.kind,
        "static": m.static,
        "abstract": m.abstract,
    }


def _location(t: Type) -> str:
    return f"{t.location.file}:{t.location.line}"


def find_cycles(nodes: list[str], relations: list[Relation]) -> list[list[str]]:
    """Strongly connected components (size > 1) over associations and dependencies."""
    adj: dict[str, list[str]] = {n: [] for n in nodes}
    for r in relations:
        if r.kind in ("association", "dependency") and r.from_ in adj and r.to in adj \
                and r.from_ != r.to:
            adj[r.from_].append(r.to)
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    out: list[list[str]] = []
    counter = [0]

    def strong(v: str) -> None:  # iterative Tarjan
        work = [(v, iter(adj[v]))]
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on_stack.add(v)
        while work:
            node, it = work[-1]
            nxt = next(it, None)
            if nxt is not None:
                if nxt not in index:
                    index[nxt] = low[nxt] = counter[0]
                    counter[0] += 1
                    stack.append(nxt)
                    on_stack.add(nxt)
                    work.append((nxt, iter(adj[nxt])))
                elif nxt in on_stack:
                    low[node] = min(low[node], index[nxt])
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[node])
            if low[node] == index[node]:
                comp = []
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    comp.append(w)
                    if w == node:
                        break
                if len(comp) > 1:
                    out.append(sorted(comp))

    for n in sorted(nodes):
        if n not in index:
            strong(n)
    return sorted(out)


def build_graph(scene: Scene, ir: Optional[IR] = None) -> dict:
    group_of = {tid: name for name, ids in scene.groups for tid in ids}
    by_id = ir.type_index() if ir is not None else {}
    nested_label = lambda tid: by_id[tid].display_name if tid in by_id else tid  # noqa: E731
    nodes = []
    for t in scene.types:
        nodes.append({
            "id": t.id,
            "label": t.display_name + (f"<{', '.join(t.generics)}>" if t.generics else ""),
            "namespace": t.namespace,
            "kind": t.kind,
            "stereotype": STEREOTYPES.get(t.kind),
            "abstract": t.kind in ("abstract_class", "interface"),
            "members": [_member(m) for m in t.members],
            "annotations": t.annotations,
            "location": _location(t),
            "language": t.language,
            "group": group_of.get(t.id),
        })
        if t.outer:
            nodes[-1]["outer"] = t.outer
        if scene.folded.get(t.id):
            nodes[-1]["folded"] = [{"id": n, "label": nested_label(n),
                                    "kind": by_id[n].kind if n in by_id else "class"}
                                   for n in scene.folded[t.id]]
    for e in scene.externals:
        nodes.append({"id": e.id, "label": e.name, "namespace": None, "kind": "external",
                      "stereotype": "external", "abstract": False, "members": [],
                      "annotations": [], "location": None, "group": None})
    for g in scene.ghosts:
        nodes.append({"id": g, "label": g, "namespace": None, "kind": "inferred",
                      "stereotype": "inferred", "abstract": False, "members": [],
                      "annotations": [], "location": None, "group": None})

    edges = []
    for i, r in enumerate(scene.relations):
        edges.append({
            "id": f"r{i}",
            "from": r.from_,
            "to": r.to,
            "kind": r.kind,
            "multiplicity": r.multiplicity if r.multiplicity not in (None, "1") else None,
            "ownership": r.ownership,
            "via": r.via if r.kind == "association" else None,
            "inferred": False,
            "annotation": is_annotation(r),
            "body": is_body(r),
            "location": f"{r.source_location.file}:{r.source_location.line}",
        })
        if isinstance(r, FoldedRelation) and r.label:
            edges[-1]["label"] = r.label
        if isinstance(r, FoldedRelation) and r.fact is not None:
            # the relation as ir.json states it, between the nested types
            edges[-1]["fact"] = {"from": r.fact.from_, "to": r.fact.to, "via": r.fact.via,
                                 "from_label": nested_label(r.fact.from_),
                                 "to_label": nested_label(r.fact.to)}
    for i, e in enumerate(scene.inferred):
        edges.append({"id": f"i{i}", "from": e.from_, "to": e.to, "kind": e.kind,
                      "multiplicity": None, "ownership": None, "via": None,
                      "inferred": True, "rationale": e.rationale, "location": None})

    project_ids = [t.id for t in scene.types]
    graph = {
        "title": scene.title,
        "focus": scene.focus,
        "hops": scene.hops,
        "nested": scene.nested,
        "body": scene.body,
        "direction": scene.direction or "TB",
        "nodes": nodes,
        "edges": edges,
        "groups": [{"name": name, "members": ids} for name, ids in scene.groups],
        "notes": [{"target": t, "text": text} for t, text in scene.notes],
        "highlights": [{"target": t, "reason": reason} for t, reason in scene.highlights],
        # on declarations, as the most connected types: a viewer has every body relation,
        # and shows only those around its focus
        "cycles": find_cycles(project_ids, [r for r in scene.relations if not is_body(r)]),
    }
    if ir is not None:
        shown = set(project_ids) | {n for ids in scene.folded.values() for n in ids}
        graph["unresolved"] = [
            {"from": u.from_, "raw_type": u.raw_type, "via": u.via, "hint": u.hint,
             "location": f"{u.location.file}:{u.location.line}"}
            for u in ir.unresolved if u.from_ in shown]
        graph["source"] = {"root": ir.root, "languages": ir.languages, "types": len(ir.types)}
    return graph
