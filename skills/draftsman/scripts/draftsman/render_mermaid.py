"""Scene -> Mermaid classDiagram text."""

from __future__ import annotations

import json
import re

from .model import STEREOTYPES, VISIBILITY_SYMBOLS, Member, Type
from .scene import Scene


def _sanitize(text: str) -> str:
    s = re.sub(r"\W", "_", text)
    return "_" + s if s[:1].isdigit() else s


def _mm_type(text: str | None) -> str:
    if not text:
        return ""
    text = text.replace("<", "~").replace(">", "~")
    return re.sub(r'[{}"`;]', "", text)


def _quote(text: str) -> str:
    return text.replace('"', "#quot;").replace("\n", "<br>")


def _comment(text: str) -> str:
    return re.sub(r"[{}\s]+", " ", text).strip()


def _member_line(m: Member) -> str:
    vis = VISIBILITY_SYMBOLS.get(m.visibility, "")
    if m.kind == "enum_constant":
        return m.name
    typ = _mm_type(m.type_ref)
    if m.kind in ("method", "constructor"):
        params = ", ".join(
            f"{_mm_type(p.type_ref)} {p.name}".strip() for p in m.params)
        flags = ("*" if m.abstract else "") + ("$" if m.static else "")
        ret = f" {typ}" if typ and m.kind == "method" else ""
        return f"{vis}{m.name}({params}){flags}{ret}"
    return f"{vis}{typ + ' ' if typ else ''}{m.name}{'$' if m.static else ''}"


class _Ids:
    """Stable, unique Mermaid identifiers for every drawable node."""

    def __init__(self, scene: Scene):
        self.ids: dict[str, str] = {}
        self.labels: dict[str, str] = {}
        entries = [(t.id, t.display_name) for t in scene.types]
        entries += [(e.id, e.name) for e in scene.externals]
        entries += [(g, g.rsplit(".", 1)[-1]) for g in scene.ghosts]
        taken: set[str] = set()
        short_count: dict[str, int] = {}
        for _, label in entries:
            short_count[_sanitize(label)] = short_count.get(_sanitize(label), 0) + 1
        for key, label in entries:
            base = _sanitize(label)
            ident = base if short_count[base] == 1 else _sanitize(key)
            n = 2
            while ident in taken:
                ident = f"{base}_{n}"
                n += 1
            taken.add(ident)
            self.ids[key] = ident
            self.labels[key] = label

    def __getitem__(self, key: str) -> str:
        return self.ids[key]

    def head(self, key: str, generics: list[str] = ()) -> str:
        ident, label = self.ids[key], self.labels[key]
        if label != ident:
            if generics:
                label += "<" + ", ".join(generics) + ">"
            return f'{ident}["{_quote(label)}"]'
        if generics:
            return f"{ident}~{', '.join(generics)}~"
        return ident


def _class_block(t: Type, ids: _Ids, indent: str) -> list[str]:
    body = []
    if t.kind in STEREOTYPES:
        body.append(f"<<{STEREOTYPES[t.kind]}>>")
    body += [_member_line(m) for m in t.members]
    head = f"{indent}class {ids.head(t.id, t.generics)}"
    if not body:
        return [head]
    return [head + " {", *(f"{indent}  {line}" for line in body), indent + "}"]


def render(scene: Scene) -> str:
    ids = _Ids(scene)
    out: list[str] = []
    if scene.title:
        # a JSON string is a valid YAML double-quoted scalar: `:`, `#`, quotes and
        # newlines in the title can no longer break or truncate the frontmatter
        out += ["---", f"title: {json.dumps(scene.title, ensure_ascii=False)}", "---"]
    out.append("classDiagram")
    meta = f"%% draftsman: {len(scene.types)} types"
    if scene.focus:
        meta += f", focus {scene.focus} ({scene.hops} hops)"
    out.append("  " + meta)
    if scene.direction:
        out.append(f"  direction {scene.direction}")

    by_id = {t.id: t for t in scene.types}
    grouped = set()
    for name, members in scene.groups:
        out.append(f"  %% group: {_comment(name)}")
        out.append(f"  namespace {_sanitize(name)} {{")
        for tid in members:
            out += _class_block(by_id[tid], ids, "    ")
            grouped.add(tid)
        out.append("  }")
    for t in scene.types:
        if t.id not in grouped:
            out += _class_block(t, ids, "  ")
    for e in scene.externals:
        out += [f"  class {ids.head(e.id)} {{", "    <<external>>", "  }"]
    for g in scene.ghosts:
        out += [f"  class {ids.head(g)} {{", "    <<inferred>>", "  }"]

    for r in scene.relations:
        a, b = ids[r.from_], ids[r.to]
        if r.kind == "extends":
            out.append(f"  {b} <|-- {a}")
        elif r.kind == "implements":
            out.append(f"  {b} <|.. {a}")
        elif r.kind == "association":
            arrow = "*--" if r.ownership == "owned" else "-->"
            mult = f' "{r.multiplicity}"' if r.multiplicity and r.multiplicity != "1" else ""
            label = f" : {r.via}" if r.via else ""
            out.append(f"  {a} {arrow}{mult} {b}{label}")
        else:
            out.append(f"  {a} ..> {b}")
    for e in scene.inferred:
        out.append(f"  {ids[e.from_]} ..> {ids[e.to]} : «inferred» {e.kind}")
        out.append(f"  %% inferred {e.from_} -> {e.to}: {_comment(e.rationale)}")

    for tid, text in scene.notes:
        out.append(f'  note for {ids[tid]} "{_quote(text)}"')
    if scene.focus:
        out.append(f"  style {ids[scene.focus]} stroke:#1971c2,stroke-width:3px")
    for tid, reason in scene.highlights:
        out.append(f"  %% highlight {tid}: {_comment(reason)}")
        out.append(f"  style {ids[tid]} stroke:#e03131,stroke-width:3px")
    return "\n".join(out) + "\n"
