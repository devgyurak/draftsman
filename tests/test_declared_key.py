"""bench/declared.py: what the extractor resolves declared relations from, compared with an
answer key's names in declared positions (issue #7)."""

import copy
import sys
from pathlib import Path

import pytest

from draftsman.extractor import Extractor
from draftsman.langs import spec_for_path
from draftsman.resolve import _Builder
from draftsman.wrappers import Wrappers

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench"))
import declared  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _raw(root: Path) -> list:
    return [Extractor(spec_for_path(p.name)).extract(p, p.relative_to(root).as_posix(), root)
            for p in sorted(root.rglob("*")) if p.is_file() and spec_for_path(p.name)]


@pytest.mark.parametrize("fixture", sorted(str(d.relative_to(FIXTURES))
                                           for d in FIXTURES.glob("*/*") if d.is_dir()))
def test_watching_a_build_changes_nothing(fixture):
    root = FIXTURES / fixture
    raw = _raw(root)
    plain = _Builder(str(root), copy.deepcopy(raw), Wrappers.load()).build().to_dict()
    watched = _Builder(str(root), copy.deepcopy(raw), Wrappers.load())
    declared.watch(watched)
    assert watched.build().to_dict() == plain
    assert watched.declared_names


def _names(tmp_path, files: dict[str, str]):
    for rel, text in files.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(text)
    builder = _Builder(str(tmp_path), _raw(tmp_path), Wrappers.load())
    declared.watch(builder)
    builder.build()
    return builder


def _use(name, line, col, target, project=True, kind="type", **more):
    return {"use": name, "file": "p/A.java", "line": line, "col": col, "pos": "declared",
            "kind": kind, "target": target, "project": project, "maximal": True,
            "from": "p.A", **more}


def test_names_are_matched_within_their_declaration(tmp_path):
    builder = _names(tmp_path, {
        "p/B.java": "package p;\npublic class B {}\n",
        "p/A.java": "package p;\n"
                    "public class A extends B {\n"          # 2
                    "    B b;\n"                            # 3
                    "    java.util.concurrent.Future f;\n"  # 4
                    "    void m(Object o,\n"                # 5
                    "           B x) {}\n"                  # 6
                    "    void n(java.util.List<? super B> l) {}\n"  # 7
                    "}\n"})
    names = builder.declared_names
    assert {(n["line"], n["written"], tuple(n["targets"])) for n in names
            if n["from"] == "p.A" and n["targets"]} == {(2, "B", ("p.B",)), (3, "B", ("p.B",)),
                                                        (5, "B", ("p.B",)), (7, "B", ("p.B",))}
    recs = [_use("B", 2, 23, "p.B"), _use("B", 3, 4, "p.B"),
            _use("B", 6, 11, "p.B"),
            # a key that disagrees: the field's B is another type
            _use("B", 3, 4, "q.B"),
            # a type outside the sources, which the extractor reads no name of
            _use("Future", 4, 25, "java.util.concurrent.Future", project=False),
            # `? super B` (read since #9, case 26)
            _use("B", 7, 34, "p.B"),
            # a name of the type the extractor reads no name of
            _use("C", 4, 4, "p.C")]
    out = declared.compare(builder, recs[:3] + recs[4:], tmp_path)
    assert (out["counts"]["agreed"], out["counts"]["unread"]) == (4, 1)
    assert [r["line"] for r in out["rows"]] == [4]
    assert out["rows"][0]["verdict"] == "miss" and out["rows"][0]["status"] == "not read"
    out = declared.compare(builder, [recs[3]], tmp_path)
    assert [(r["verdict"], r["drawn"]) for r in out["rows"]] == [("mismatch", ["p.B"])]


def test_names_the_key_never_met_are_counted(tmp_path):
    builder = _names(tmp_path, {
        "p/B.java": "package p;\npublic class B {}\n",
        "p/A.java": "package p;\n"
                    "public class A {\n"        # 2
                    "    B b;\n"                # 3
                    "    B c(B x) { return x; }\n"  # 4
                    "}\n"})
    out = declared.compare(builder, [_use("B", 3, 4, "p.B")], tmp_path)
    assert [(n["line"], n["where"]) for n in out["uncompared"]] == [(4, "signature")]
    out = declared.compare(builder, [_use("B", 3, 4, "p.B"), _use("B", 4, 4, "p.B")], tmp_path)
    assert out["uncompared"] == []   # `B c(B x)`: one name compared stands for the other


def test_a_type_defined_only_in_lines_not_compiled_is_counted_apart(tmp_path):
    # the header declares Impl; its one definition is in a branch no unit compiles, so the
    # key takes the id for no type of the sources: a mismatch, but counted apart
    builder = _names(tmp_path, {
        "n/h.h": "#pragma once\nnamespace n {\nstruct Impl;\nstruct Ctx { Impl* p; };\n}\n",
        "n/s.cc": "#include \"h.h\"\nnamespace n {\n#ifdef _WIN32\nstruct Impl { int a; };\n#endif\n}\n"})
    rec = {"use": "Impl", "file": "n/h.h", "line": 4, "col": 14, "pos": "declared",
           "kind": "type", "target": "n::Impl", "project": False, "maximal": True,
           "from": "n::Ctx"}
    out = declared.compare(builder, [rec], tmp_path, uncompiled={"n/s.cc": {3, 4, 5}})
    assert out["counts"]["mismatch (not compiled)"] == 1
    out = declared.compare(builder, [rec], tmp_path, uncompiled={})
    assert out["counts"]["mismatch"] == 1


def test_an_alias_naming_only_its_own_type_is_compared(tmp_path):
    # `type Cb = (s: A) => void` written in A names A alone: no project type to agree with,
    # so another type drawn there is a mismatch, not passed over
    builder = _names(tmp_path, {"a.ts": (
        "export class B {}\n"
        "export type Cb = (s: A) => void;\n"
        "export class A { cb?: Cb; b?: B; }\n")})
    rec = {"use": "Cb", "file": "a.ts", "line": 3, "col": 22, "pos": "declared",
           "kind": "alias", "target": None, "project": False, "maximal": True,
           "from": "a.A", "targets": ["a.A"]}
    out = declared.compare(builder, [rec], tmp_path)
    assert out["counts"]["agreed"] == 1 and not out["rows"]
    wrong = dict(rec, use="B", col=34, kind="alias", targets=["a.A"])
    out = declared.compare(builder, [wrong], tmp_path)
    assert [r["verdict"] for r in out["rows"]] == ["mismatch"]


def test_each_declared_relation_needs_a_key_record_of_its_target(tmp_path):
    builder = _names(tmp_path, {
        "p/B.java": "package p;\npublic class B {}\n",
        "p/C.java": "package p;\npublic class C {}\n",
        "p/A.java": "package p;\npublic class A {\n    B b;\n    C c;\n}\n"})
    out = declared.pairs(builder, [_use("B", 3, 4, "p.B")])
    assert out["counts"]["no record"] == 1 and out["rows"][0][5] == "p.C"
    out = declared.pairs(builder, [_use("B", 3, 4, "p.B"), _use("X", 4, 4, None, kind="error")])
    assert out["counts"]["the key has no answer there"] == 1
