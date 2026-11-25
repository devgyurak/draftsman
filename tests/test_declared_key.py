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
                                                        (5, "B", ("p.B",))}
    recs = [_use("B", 2, 23, "p.B"), _use("B", 3, 4, "p.B"),
            _use("B", 6, 11, "p.B"),
            # a key that disagrees: the field's B is another type
            _use("B", 3, 4, "q.B"),
            # a type outside the sources, which the extractor reads no name of
            _use("Future", 4, 25, "java.util.concurrent.Future", project=False),
            # not read: `? super B`
            _use("B", 7, 34, "p.B")]
    out = declared.compare(builder, recs[:3] + recs[4:], tmp_path)
    assert (out["counts"]["agreed"], out["counts"]["unread"]) == (3, 1)
    assert [r["line"] for r in out["rows"]] == [7]
    assert out["rows"][0]["verdict"] == "miss" and out["rows"][0]["status"] == "not read"
    out = declared.compare(builder, [recs[3]], tmp_path)
    assert [(r["verdict"], r["drawn"]) for r in out["rows"]] == [("mismatch", ["p.B"])]
