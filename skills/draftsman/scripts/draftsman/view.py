"""view.json: Claude's editorial decisions, validated against the IR.

The view may only *select and annotate* facts. Anything it adds that is not
in the IR (inferred_edges) is rendered as visibly inferred. References to
type ids that do not exist are errors, so a view cannot smuggle in classes.
"""

from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

from .model import IR, RELATION_KINDS, Type

OUTPUTS = ("mermaid", "svg", "html")
MEMBER_DETAIL = ("all", "public", "none")
DIRECTIONS = ("TB", "BT", "LR", "RL")
NESTED = ("fold", "boxes")

_KEYS = {
    "focus", "hops", "hidden", "groups", "highlights", "notes", "inferred_edges",
    "members", "relations", "externals", "direction", "output", "title", "nested",
    "annotations",
}


class ViewError(ValueError):
    pass


@dataclass
class Group:
    name: str
    members: list[str]


@dataclass
class Highlight:
    target: str
    reason: str


@dataclass
class Note:
    target: str
    text: str


@dataclass
class InferredEdge:
    from_: str
    to: str
    kind: str
    rationale: str


@dataclass
class View:
    focus: Optional[str] = None
    hops: int = 2
    hidden: list[str] = field(default_factory=list)
    groups: list[Group] = field(default_factory=list)
    highlights: list[Highlight] = field(default_factory=list)
    notes: list[Note] = field(default_factory=list)
    inferred_edges: list[InferredEdge] = field(default_factory=list)
    # one level for every type, or {type glob: level} where later keys win
    members: Union[str, dict[str, str]] = "all"
    relations: list[str] = field(default_factory=lambda: list(RELATION_KINDS))
    externals: bool = False
    direction: Optional[str] = None
    output: str = "mermaid"
    title: Optional[str] = None
    # nested types drawn inside their outer type ("fold") or as boxes of their own
    # ("boxes"); None: fold in a focus diagram, boxes otherwise
    nested: Optional[str] = None
    # draw the dependencies annotations create (`via` "@Name")
    annotations: bool = True

    @property
    def nested_mode(self) -> str:
        if self.nested is not None:
            return self.nested
        return "fold" if self.focus else "boxes"

    @classmethod
    def load(cls, path: Optional[Path]) -> "View":
        if path is None:
            return cls()
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ViewError(f"{path}: invalid JSON: {e}") from e
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, d: dict) -> "View":
        if not isinstance(d, dict):
            raise ViewError("view must be a JSON object")
        unknown = set(d) - _KEYS
        if unknown:
            raise ViewError(f"unknown view keys: {', '.join(sorted(unknown))}")

        def items(key: str, required: tuple[str, ...]) -> list[dict]:
            out = d.get(key, []) or []
            if not isinstance(out, list):
                raise ViewError(f"{key} must be a list")
            for i, it in enumerate(out):
                missing = [k for k in required if not (isinstance(it, dict) and it.get(k))]
                if missing:
                    raise ViewError(f"{key}[{i}] is missing {', '.join(missing)}")
            return out

        v = cls(
            focus=d.get("focus"),
            hops=d.get("hops", 2),
            hidden=list(d.get("hidden", []) or []),
            groups=[Group(g["name"], list(g["members"]))
                    for g in items("groups", ("name", "members"))],
            highlights=[Highlight(h["target"], h["reason"])
                        for h in items("highlights", ("target", "reason"))],
            notes=[Note(n["target"], n["text"]) for n in items("notes", ("target", "text"))],
            inferred_edges=[InferredEdge(e["from"], e["to"], e["kind"], e["rationale"])
                            for e in items("inferred_edges", ("from", "to", "kind", "rationale"))],
            members=d.get("members", "all"),
            relations=list(d.get("relations", RELATION_KINDS)),
            externals=bool(d.get("externals", False)),
            direction=d.get("direction"),
            output=d.get("output", "mermaid"),
            title=d.get("title"),
            nested=d.get("nested"),
            annotations=d.get("annotations", True),
        )
        if not isinstance(v.hops, int) or v.hops < 0:
            raise ViewError("hops must be a non-negative integer")
        if isinstance(v.members, dict):
            bad = {k: lv for k, lv in v.members.items()
                   if not isinstance(k, str) or not k or lv not in MEMBER_DETAIL}
            if bad:
                raise ViewError(f"members: each value must be one of {MEMBER_DETAIL}, "
                                f"got {bad}")
        elif v.members not in MEMBER_DETAIL:
            raise ViewError(f"members must be one of {MEMBER_DETAIL} "
                            "or an object of {type glob: level}")
        if v.output not in OUTPUTS:
            raise ViewError(f"output must be one of {OUTPUTS}")
        if not isinstance(v.annotations, bool):
            raise ViewError("annotations must be true or false")
        if v.nested is not None and v.nested not in NESTED:
            raise ViewError(f"nested must be one of {NESTED}")
        if v.direction is not None and v.direction not in DIRECTIONS:
            raise ViewError(f"direction must be one of {DIRECTIONS}")
        bad = [k for k in v.relations if k not in RELATION_KINDS]
        if bad:
            raise ViewError(f"unknown relation kinds: {bad}")
        for e in v.inferred_edges:
            if e.kind not in RELATION_KINDS:
                raise ViewError(f"inferred edge {e.from_}->{e.to}: unknown kind {e.kind!r}")
        return v


    def member_detail(self, t: Type) -> str:
        """The member level for one type: the last matching key of a members object."""
        if isinstance(self.members, str):
            return self.members
        level = "all"
        for pattern, lv in self.members.items():
            if pattern == "*" or type_matches(pattern, t):
                level = lv
        return level


class TypeLookup:
    """Resolve the names a view uses (ids or unique simple names) to type ids."""

    def __init__(self, ir: IR):
        self.types: dict[str, Type] = ir.type_index()
        self.externals = {e.id for e in ir.externals}
        self.by_name: dict[str, list[str]] = {}
        for t in ir.types:
            self.by_name.setdefault(t.name, []).append(t.id)
            if t.display_name != t.name:
                self.by_name.setdefault(t.display_name, []).append(t.id)

    def find(self, ref: str) -> Optional[str]:
        if ref in self.types:
            return ref
        ids = self.by_name.get(ref, [])
        if len(ids) > 1:
            raise ViewError(f"{ref!r} is ambiguous: {', '.join(sorted(ids))}; use the full id")
        return ids[0] if ids else None

    def require(self, ref: str, where: str) -> str:
        tid = self.find(ref)
        if tid is None:
            raise ViewError(f"{where}: no type {ref!r} in ir.json")
        return tid


def type_matches(pattern: str, t: Type) -> bool:
    return any(fnmatch.fnmatchcase(s, pattern) for s in (t.id, t.name, t.display_name))


def split_hidden(patterns: list[str]) -> tuple[list[str], list[tuple[str, str]]]:
    """Split hidden patterns into type globs and (type glob, member glob) pairs."""
    types, members = [], []
    for p in patterns:
        if "#" in p:
            tp, mp = p.split("#", 1)
            members.append((tp or "*", mp or "*"))
        else:
            types.append(p)
    return types, members
