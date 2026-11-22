"""Relations read from names written in bodies (`evidence` "body", issue #2)."""

import sys
from pathlib import Path

from conftest import extract_source
from draftsman.extractor import Extractor, RawFile
from draftsman.langs import spec_for_path
from draftsman.model import IR, Location, Relation
from draftsman.resolve import _Builder
from draftsman.scene import FoldedRelation, build_scene, is_body
from draftsman.view import View
from draftsman.wrappers import Wrappers

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench" / "javac_oracle"))
from oracle import FIXTURE, expected  # noqa: E402   the hand-written answers' markers


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
    ir = _Builder(tmp_path.name, raw, Wrappers.load()).build()
    assert sorted((r.via, r.evidence or "") for r in ir.relations) == [("X", ""), ("X", "body")]


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


def _raw(tmp_path, text: str, name: str = "p/A.java") -> RawFile:
    (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / name).write_text(text)
    return Extractor(spec_for_path(name)).extract(tmp_path / name, name, tmp_path)


def _refs(raw: RawFile) -> list[tuple]:
    return [(t.qualified_name, r.text, r.position, r.via, r.classes)
            for t in raw.types for r in t.body_refs]


def test_a_body_name_belongs_to_the_named_type_and_the_member_around_it(tmp_path):
    raw = _raw(tmp_path, """package p;
record R(int v) { R { Rec.a(); } }
class A {
    static Object X = new Object() { void f() { Foo.a(); } }, Y = Bar.b();
    { Baz.c(); }
    void m() {
        new Thread() { void run() { Qux.d(); class L extends Base implements I { void g() { Deep.e(); } } } };
        Runnable r = () -> Lam.f();
        new Arg(Hdr.g()) { };
    }
    @Ann(Util.make()) void n() { }
    enum K { A(Foo.k()) { void q() { Bar.k(); } }; static { Init.s(); } }
}
""")
    assert _refs(raw) == [
        ("p.R", "Rec", "receiver", "R", []),          # a compact constructor
        ("p.A", "Object", "type", "X", []),
        ("p.A", "Foo", "receiver", "X", [["Object"]]),
        ("p.A", "Bar", "receiver", "Y", []),        # the declarator it is written in
        ("p.A", "Baz", "receiver", "{}", []),
        ("p.A", "Thread", "type", "m", []),
        ("p.A", "Qux", "receiver", "m", [["Thread"]]),
        ("p.A", "Base", "type", "m", [["Thread"]]),   # a local class's header: not in its scope
        ("p.A", "I", "type", "m", [["Thread"]]),
        ("p.A", "Deep", "receiver", "m", [["Base", "I"], ["Thread"]]),
        ("p.A", "Runnable", "type", "m", []),
        ("p.A", "Lam", "receiver", "m", []),
        ("p.A", "Arg", "type", "m", []),
        ("p.A", "Hdr", "receiver", "m", []),        # an argument, outside the anonymous class
        # `@Ann(Util.make())` is an annotation: never a body
        ("p.A.K", "Foo", "receiver", "A", []),
        ("p.A.K", "Bar", "receiver", "A", []),
        ("p.A.K", "Init", "receiver", "static {}", []),
    ]


def test_a_receiver_is_a_dotted_name_not_an_expression(tmp_path):
    raw = _raw(tmp_path, """package p;
class A { void m(A[] a) { this.Foo.m(); a[0].Bar.m(); m().Baz.m(); Qux.Y.m(); f(p.Zed::m); } }
""")
    assert [(r.text, r.position) for r in raw.types[0].body_refs] == \
        [("Qux.Y", "receiver"), ("p.Zed", "receiver")]


def test_a_member_collects_every_name_that_may_hide_a_type_in_it(tmp_path):
    raw = _raw(tmp_path, """package p;
class A {
    <T> void m(int p, String... q) {
        for (Foo f : xs) { }
        try (Res r = open()) { } catch (E1 | E2 e) { }
        Runnable l = (a, b) -> { }; l = x -> x; l = (int z) -> z;
        if (o instanceof Foo g && o instanceof Bar(Baz h)) { }
        switch (o) { case Foo k -> { } default -> { } }
        class L<U> { int w; }
        record R(int v) { }
        new Thread() { <V> void run() { } };
        Util.go();
    }
    void other() { Util.go(); }
}
""")
    names = {r.via: r.names for r in raw.types[0].body_refs}
    assert names["m"].variables == {"p", "q", "f", "r", "e", "l", "a", "b", "x", "z", "g", "h",
                                    "k", "w", "v"}
    assert names["m"].types == {"T", "L", "U", "R", "V"}
    assert not names["other"].variables and not names["other"].types


def test_a_body_name_has_its_column_in_characters(tmp_path):
    # javac's columns count UTF-16 code units: the emoji is two, and four bytes
    line = 'class A { void m() { String s = "\U0001F600\u00e9"; Foo.a(); } }'
    raw = _raw(tmp_path, f"package p;\n{line}\n")
    [ref] = [r for r in raw.types[0].body_refs if r.text == "Foo"]
    assert ref.places == [(2, line.index("Foo") + 1)]


# marked names never recorded: `Inner` in `o.new Inner()` is a member of o's type, which
# the scope does not tell, and its anonymous class inherits what is not known
_UNREAD = [("p/Qualified.java", n, "p.Outer.Inner") for n in (19, 20, 26, 37)] + \
    [("p/Qualified.java", 21, "p.Outer.Only"), ("p/Qualified.java", 28, "p.Outer.Inner.Util"),
     ("p/Qualified.java", 29, "var")]


def test_body_names_stand_where_the_hand_written_answers_say():
    # tests/fixtures/java/body, which the oracle's selftest checks against javac: every part
    # of a name the extractor records is in the position its marker gives, one no marker
    # lists is a variable or a package (lower case), and every marked name is recorded but
    # _UNREAD's
    want = expected(FIXTURE)
    problems, recorded = [], set()
    for path in sorted(FIXTURE.rglob("*.java")):
        rel = str(path.relative_to(FIXTURE))
        raw = Extractor(spec_for_path(rel)).extract(path, rel, FIXTURE)
        parts = ((r, part, line, col) for t in raw.types for r in t.body_refs
                 for part, (line, col) in zip(r.text.split("."), r.places))
        for r, part, line, col in parts:
            recorded.add((rel, line, col))
            where = f"{rel}:{line}:{col + 1} {part} of {r.text}"
            answer, position = want.get((rel, line, col), (None, None))
            if answer is None:
                if part[:1].isupper():
                    problems.append(f"{where}: no marker")
            elif answer == "-":
                problems.append(f"{where}: a declaration, recorded as {r.position}")
            elif position != r.position:
                problems.append(f"{where}: {r.position}, the marker says {position}")
    assert problems == []
    missed = sorted((rel, line, answer) for (rel, line, col), (answer, _) in want.items()
                    if answer != "-" and (rel, line, col) not in recorded)
    assert missed == sorted(_UNREAD)


def _body(ir) -> list[tuple]:
    return sorted((r.from_, r.to, r.via, r.source_location.line)
                  for r in ir.relations if r.evidence == "body")


def test_a_name_in_type_position_depends_on_the_type_it_stands_for(tmp_path):
    ir = extract_source(tmp_path, {
        "p/Foo.java": "package p; public class Foo { public static class In { } }",
        "p/A.java": """package p;
class A {
    static Object X = new Foo();
    void m(Object o) {
        Foo f = (Foo) o;
        Object c = Foo.In.class;
        new A();
        new Missing();
    }
}
"""})
    assert _body(ir) == [("p.A", "p.Foo", "X", 3), ("p.A", "p.Foo", "m", 5),
                         ("p.A", "p.Foo.In", "m", 6)]
    assert ir.unresolved == []   # a name in a body that names nothing is never unresolved


def test_a_type_declared_in_the_member_hides_the_name_everywhere_in_it(tmp_path):
    ir = extract_source(tmp_path, {
        "p/Foo.java": "package p; public class Foo { }",
        "p/A.java": """package p;
class A {
    <Foo> void tparam(Object o) { Object x = (Foo) o; }
    void local() { new Foo(); if (true) { class Foo { } } }
    void other() { new Foo(); }
}
"""})
    assert _body(ir) == [("p.A", "p.Foo", "other", 5)]


def test_an_anonymous_class_sees_the_nested_types_its_project_super_inherits(tmp_path):
    ir = extract_source(tmp_path, {
        "p/Entry.java": "package p; public class Entry { }",
        "p/Base.java": "package p; public class Base { public static class Entry { } }",
        "p/Sub.java": "package p; public class Sub extends Base { }",
        "p/State.java": "package p; public class State { }",
        "p/A.java": """package p;
class A {
    void project() { new Sub() { void f() { new Entry(); } }; }
    void outside() { new Thread() { public void run() { new State(); new Entry(); } }; }
}
"""})
    # Thread passes on Thread.State (java_jdk.json), and no Entry
    assert _body(ir) == [("p.A", "p.Base.Entry", "project", 3), ("p.A", "p.Entry", "outside", 4),
                         ("p.A", "p.Sub", "project", 3)]


def test_a_name_two_wildcard_imports_provide_draws_nothing(tmp_path):
    # javac rejects it; the extractor, which may see more types than javac, must not pick
    ir = extract_source(tmp_path, {
        "a/Foo.java": "package a; public class Foo { }",
        "b/Foo.java": "package b; public class Foo { }",
        "b/Bar.java": "package b; public class Bar { }",
        "p/A.java": "package p; import a.*; import b.*; class A { void m() { new Foo(); new Bar(); } }"})
    assert _body(ir) == [("p.A", "b.Bar", "m", 1)]


def test_body_relations_go_where_the_hand_written_answers_say():
    want = expected(FIXTURE)
    raw = [Extractor(spec_for_path(p.name)).extract(p, str(p.relative_to(FIXTURE)), FIXTURE)
           for p in sorted(FIXTURE.rglob("*.java"))]
    builder = _Builder("body", raw, Wrappers.load())
    builder.build()
    wrong, drawn = [], set()
    for file, line, col, _, to in builder.body_uses:
        drawn.add((file, line, col))
        answer, _ = want[(file, line, col)]
        if answer != to:
            wrong.append((file, line, answer))
    assert wrong == []
    # every project type is drawn, but the part of a longer name (`Util` in
    # `new Util.Helper()`), a type's own name, the names never read, and one the member
    # declares a variable of further down (`Owner Owner = ...`: the member is the scope)
    missed = [(file, line, answer) for (file, line, col), (answer, position) in want.items()
              if answer in builder.types and (file, line, col) not in drawn]
    assert sorted(missed) == sorted(
        [("p/Forms.java", 29, "p.Util"), ("p/Forms.java", 28, "p.Util"),
         ("p/Owner.java", 5, "p.Owner"), ("p/Forms.java", 26, "p.Owner")]
        + [u for u in _UNREAD if u[2] in builder.types])
