"""Relations read from names written in bodies (`evidence` "body", issue #2)."""

from conftest import extract_source
from draftsman.extractor import Extractor
from draftsman.langs import spec_for_path
from draftsman.model import IR, Location, Relation
from draftsman.resolve import _Builder
from draftsman.scene import FoldedRelation, build_scene, is_body
from draftsman.view import View
from draftsman.wrappers import Wrappers


def test_evidence_round_trips_and_is_absent_for_declarations():
    loc = Location("p/A.java", 3)
    body = Relation("p.A", "p.B", "dependency", loc, via="run", evidence="body")
    declared = Relation("p.A", "p.B", "dependency", loc, via="run")
    assert body.to_dict()["evidence"] == "body"
    assert "evidence" not in declared.to_dict()
    assert Relation.from_dict(body.to_dict()) == body
    assert Relation.from_dict(declared.to_dict()) == declared


def test_body_relation_of_a_member_stays_beside_its_declared_one(tmp_path):
    # `static Foo X = Foo.create();`: the field's type gives a dependency via X, and so
    # will the name in its initializer; neither may replace the other
    files = {"p/Foo.java": "package p; class Foo { static Foo create() { return null; } }",
             "p/A.java": "package p; class A { static Foo X = Foo.create(); }"}
    for name, text in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text)
    raw = [Extractor(spec_for_path(n)).extract(tmp_path / n, n, tmp_path) for n in files]
    builder = _Builder(tmp_path.name, raw, Wrappers.load())
    ir = builder.build()
    assert [(r.via, r.evidence) for r in ir.relations] == [("X", None)]
    builder.relations.append(Relation("p.A", "p.Foo", "dependency", Location("p/A.java", 1),
                                      via="X", evidence="body"))
    assert sorted((r.via, r.evidence or "") for r in builder._finalize_relations()) == \
        [("X", ""), ("X", "body")]


def test_folding_keeps_a_body_relation_one(tmp_path):
    ir = extract_source(tmp_path, {
        "p/A.java": "package p; class A { }",
        "p/B.java": "package p; class B { static class Inner { } }"})
    ir.relations.append(Relation("p.A", "p.B.Inner", "dependency", Location("p/A.java", 1),
                                 via="run", evidence="body"))
    ir = IR.from_dict(ir.to_dict())
    scene = build_scene(ir, View.from_dict({"focus": "B", "hops": 1}))
    [drawn] = [r for r in scene.relations if r.from_ == "p.A"]
    assert isinstance(drawn, FoldedRelation) and drawn.to == "p.B"
    assert is_body(drawn) and drawn.fact.evidence == "body"
