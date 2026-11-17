"""Seeing through container types: List<Order> -> Order, multiplicity '*'."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import yaml

from .typeref import (NULL_LIKE, Array, Named, Nullable, Pointer, TypeRef, TypeTuple, TypeUnion,
                      special_form)

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "wrappers.yaml"

_RANK = {"1": 0, "0..1": 1, "*": 2}


def combine(a: str, b: Optional[str]) -> str:
    if b is None:
        return a
    return a if _RANK[a] >= _RANK[b] else b


@dataclass(frozen=True)
class WrapperRule:
    arg: object               # int index or "last"
    multiplicity: Optional[str] = None
    ownership: Optional[str] = None


@dataclass(frozen=True)
class Leaf:
    name: str
    multiplicity: str
    ownership: Optional[str]
    args: tuple = ()   # type arguments of a generic that is not a wrapper (Repository<User>)
    value: bool = False  # written as `typeof x`


class Wrappers:
    def __init__(self, rules: dict[str, WrapperRule]):
        self.rules = rules

    @classmethod
    def load(cls, *paths: Path) -> "Wrappers":
        rules: dict[str, WrapperRule] = {}
        for path in (DEFAULT_CONFIG, *paths):
            data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
            for entry in data.get("wrappers", []):
                rule = WrapperRule(
                    arg=entry.get("arg", 0),
                    multiplicity=entry.get("multiplicity"),
                    ownership=entry.get("ownership"),
                )
                if rule.multiplicity not in (None, "*", "0..1"):
                    raise ValueError(f"{path}: bad multiplicity {rule.multiplicity!r}")
                for name in entry["names"]:
                    rules[str(name)] = rule
        return cls(rules)

    def rule_for(self, name: str) -> Optional[WrapperRule]:
        if name in self.rules:
            return self.rules[name]
        for sep in ("::", "."):
            if sep in name:
                return self.rules.get(name.rsplit(sep, 1)[-1])
        return None

    def is_wrapper(self, name: str) -> bool:
        return self.rule_for(name) is not None

    def leaves(self, ref: Optional[TypeRef], is_project: Callable[[str], bool],
               track_ownership: bool = False,
               dropped: Optional[list] = None) -> list[Leaf]:
        """The element types a field of type ``ref`` actually points at. The type
        arguments a container rule does not follow (the K of `Map<K, V>`) are appended
        to ``dropped`` when given."""
        out: list[Leaf] = []

        def walk(r, mult: str, own: Optional[str]):
            if r is None:
                return
            if isinstance(r, Array):
                walk(r.elem, combine(mult, "*"), own)
            elif isinstance(r, Nullable):
                walk(r.inner, combine(mult, "0..1"), own)
            elif isinstance(r, Pointer):
                walk(r.inner, mult, own or "shared")  # pointers and references don't own
            elif isinstance(r, TypeTuple):   # one of each: (Person, Point)
                for item in r.items:
                    walk(item, mult, own)
            elif isinstance(r, TypeUnion):
                items = [i for i in r.items
                         if not (isinstance(i, Named) and i.name in NULL_LIKE)]
                if len(items) < len(r.items):
                    mult = combine(mult, "0..1")
                for item in items:
                    walk(item, mult, own)
            elif isinstance(r, Named):
                if r.name in NULL_LIKE:
                    return
                project = is_project(r.name)   # a project class of the name always wins
                form = None if project else special_form(r)
                if form == "values":            # Literal["a", "b"]
                    return
                if form == "tuple":             # tuple[P, Q], std::pair<P, Q>: one of each
                    for item in r.args:
                        walk(item, mult, own)
                    return
                rule = None if project else self.rule_for(r.name)
                if rule is None:
                    owner = (own or "owned") if track_ownership else None
                    out.append(Leaf(r.name, mult, owner, tuple(r.args), r.value))
                    return
                if not r.args:
                    return
                idx = len(r.args) - 1 if rule.arg == "last" else int(rule.arg)
                if dropped is not None:
                    dropped.extend(a for j, a in enumerate(r.args) if j != idx and a is not None)
                if idx >= len(r.args):
                    return
                walk(r.args[idx], combine(mult, rule.multiplicity), own or rule.ownership)

        walk(ref, "1", None)
        return out
