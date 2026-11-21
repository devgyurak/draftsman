"""IR data model (the "facts" side). See references/ir-schema.md."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

IR_VERSION = 1

TYPE_KINDS = (
    "class", "interface", "abstract_class", "enum", "record", "struct", "union",
    "object", "trait", "mixin", "annotation",
)
MEMBER_KINDS = ("field", "method", "property", "constructor", "enum_constant")
RELATION_KINDS = ("extends", "implements", "association", "dependency")
MULTIPLICITIES = ("1", "0..1", "*")
VISIBILITIES = ("public", "protected", "package", "internal", "private")

# UML notation shared by every renderer
VISIBILITY_SYMBOLS = {"public": "+", "private": "-", "protected": "#", "package": "~", "internal": "~"}
STEREOTYPES = {
    "interface": "interface", "abstract_class": "abstract", "enum": "enumeration",
    "record": "record", "annotation": "annotation", "struct": "struct", "union": "union",
    "object": "object", "trait": "trait", "mixin": "mixin",
}


@dataclass
class Location:
    file: str
    line: int

    def to_dict(self) -> dict:
        return {"file": self.file, "line": self.line}

    @classmethod
    def from_dict(cls, d: dict) -> "Location":
        return cls(d["file"], d["line"])


@dataclass
class Param:
    name: str
    type_ref: Optional[str] = None

    def to_dict(self) -> dict:
        return {"name": self.name, "type_ref": self.type_ref}

    @classmethod
    def from_dict(cls, d: dict) -> "Param":
        return cls(d["name"], d.get("type_ref"))


@dataclass
class Member:
    name: str
    kind: str
    visibility: str
    type_ref: Optional[str] = None
    static: bool = False
    abstract: bool = False
    params: list[Param] = field(default_factory=list)
    modifiers: list[str] = field(default_factory=list)
    annotations: list[str] = field(default_factory=list)
    line: int = 0
    file: Optional[str] = None  # only when it differs from the type's file (partial types)
    receiver: Optional[str] = None  # Kotlin member extension: `fun Grammar.unaryPlus()`

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "name": self.name,
            "kind": self.kind,
            "visibility": self.visibility,
            "type_ref": self.type_ref,
            "static": self.static,
            "abstract": self.abstract,
        }
        if self.kind in ("method", "constructor"):
            d["params"] = [p.to_dict() for p in self.params]
        if self.modifiers:
            d["modifiers"] = self.modifiers
        if self.annotations:
            d["annotations"] = self.annotations
        if self.file:
            d["file"] = self.file
        if self.receiver:
            d["receiver"] = self.receiver
        d["line"] = self.line
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Member":
        return cls(
            name=d["name"],
            kind=d["kind"],
            visibility=d["visibility"],
            type_ref=d.get("type_ref"),
            static=d.get("static", False),
            abstract=d.get("abstract", False),
            params=[Param.from_dict(p) for p in d.get("params", [])],
            modifiers=d.get("modifiers", []),
            receiver=d.get("receiver"),
            annotations=d.get("annotations", []),
            line=d.get("line", 0),
            file=d.get("file"),
        )


@dataclass
class Type:
    id: str
    name: str
    qualified_name: str
    kind: str
    language: str
    location: Location
    namespace: Optional[str] = None
    outer: Optional[str] = None
    modifiers: list[str] = field(default_factory=list)
    annotations: list[str] = field(default_factory=list)
    generics: list[str] = field(default_factory=list)
    members: list[Member] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        """Name including enclosing types, e.g. ``Outer.Inner``."""
        if self.namespace and self.qualified_name.startswith(self.namespace):
            rest = self.qualified_name[len(self.namespace):]
            if rest[:1] in (".", ":"):
                return rest.lstrip(".:")
        return self.qualified_name

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "qualified_name": self.qualified_name,
            "kind": self.kind,
            "language": self.language,
            "namespace": self.namespace,
            "outer": self.outer,
            "modifiers": self.modifiers,
            "annotations": self.annotations,
            "generics": self.generics,
            "location": self.location.to_dict(),
            "members": [m.to_dict() for m in self.members],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Type":
        return cls(
            id=d["id"],
            name=d["name"],
            qualified_name=d["qualified_name"],
            kind=d["kind"],
            language=d["language"],
            location=Location.from_dict(d["location"]),
            namespace=d.get("namespace"),
            outer=d.get("outer"),
            modifiers=d.get("modifiers", []),
            annotations=d.get("annotations", []),
            generics=d.get("generics", []),
            members=[Member.from_dict(m) for m in d.get("members", [])],
        )


@dataclass
class Relation:
    from_: str
    to: str
    kind: str
    source_location: Location
    multiplicity: Optional[str] = None
    ownership: Optional[str] = None
    via: Optional[str] = None  # member that produced the relation (field name, method name)
    # "body": a name written in a body (`new Foo()`, `Foo.bar()`); None: a declaration
    evidence: Optional[str] = None

    def key(self) -> tuple:
        return (self.from_, self.to, self.kind, self.via or "", self.evidence or "")

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"from": self.from_, "to": self.to, "kind": self.kind}
        if self.multiplicity is not None:
            d["multiplicity"] = self.multiplicity
        if self.ownership is not None:
            d["ownership"] = self.ownership
        if self.via is not None:
            d["via"] = self.via
        if self.evidence is not None:
            d["evidence"] = self.evidence
        d["source_location"] = self.source_location.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Relation":
        return cls(
            from_=d["from"],
            to=d["to"],
            kind=d["kind"],
            source_location=Location.from_dict(d["source_location"]),
            multiplicity=d.get("multiplicity"),
            ownership=d.get("ownership"),
            via=d.get("via"),
            evidence=d.get("evidence"),
        )


@dataclass
class External:
    """A type outside the analysed sources that a project type inherits from."""

    id: str
    name: str

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name}

    @classmethod
    def from_dict(cls, d: dict) -> "External":
        return cls(d["id"], d["name"])


@dataclass
class Unresolved:
    from_: str
    raw_type: str
    location: Location
    via: Optional[str] = None
    candidates: list[str] = field(default_factory=list)
    hint: Optional[str] = None
    # why it stays unresolved: "ambiguous" (project types share the name: candidates),
    # "outside" (only something outside the sources explains it: a wildcard or default
    # import, a nested type of an external supertype), "unexplained" (anything else)
    reason: Optional[str] = None

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"from": self.from_, "raw_type": self.raw_type}
        if self.reason is not None:
            d["reason"] = self.reason
        if self.via is not None:
            d["via"] = self.via
        if self.candidates:
            d["candidates"] = self.candidates
        if self.hint is not None:
            d["hint"] = self.hint
        d["location"] = self.location.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Unresolved":
        return cls(
            from_=d["from"],
            raw_type=d["raw_type"],
            location=Location.from_dict(d["location"]),
            via=d.get("via"),
            candidates=d.get("candidates", []),
            hint=d.get("hint"),
            reason=d.get("reason"),
        )


@dataclass
class Diagnostic:
    file: str
    line: int
    message: str
    end_line: Optional[int] = None   # last line of the span, when it is longer than one

    def to_dict(self) -> dict:
        d = {"file": self.file, "line": self.line, "message": self.message}
        if self.end_line is not None and self.end_line != self.line:
            d["end_line"] = self.end_line
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Diagnostic":
        return cls(d["file"], d["line"], d["message"], d.get("end_line"))


@dataclass
class IR:
    root: str
    languages: list[str] = field(default_factory=list)
    files: int = 0
    types: list[Type] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    externals: list[External] = field(default_factory=list)
    unresolved: list[Unresolved] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)

    def type_index(self) -> dict[str, Type]:
        return {t.id: t for t in self.types}

    def to_dict(self) -> dict:
        return {
            "version": IR_VERSION,
            "root": self.root,
            "languages": self.languages,
            "files": self.files,
            "types": [t.to_dict() for t in self.types],
            "relations": [r.to_dict() for r in self.relations],
            "externals": [e.to_dict() for e in self.externals],
            "unresolved": [u.to_dict() for u in self.unresolved],
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "IR":
        if d.get("version") != IR_VERSION:
            raise ValueError(f"unsupported ir.json version: {d.get('version')!r}")
        return cls(
            root=d["root"],
            languages=d.get("languages", []),
            files=d.get("files", 0),
            types=[Type.from_dict(t) for t in d["types"]],
            relations=[Relation.from_dict(r) for r in d["relations"]],
            externals=[External.from_dict(e) for e in d.get("externals", [])],
            unresolved=[Unresolved.from_dict(u) for u in d.get("unresolved", [])],
            diagnostics=[Diagnostic.from_dict(x) for x in d.get("diagnostics", [])],
        )

    def dump(self, path: Optional[Path]) -> str:
        text = json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n"
        if path is not None:
            path.write_text(text, encoding="utf-8")
        return text

    @classmethod
    def load(cls, path: Path) -> "IR":
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
