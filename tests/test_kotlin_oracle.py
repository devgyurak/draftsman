"""The Kotlin answer key's joining of compilations (bench/kotlin_oracle/oracle.py): what
its selftest, one compilation of one directory, cannot show."""

import importlib.util
from pathlib import Path

ORACLE = Path(__file__).resolve().parents[1] / "bench" / "kotlin_oracle" / "oracle.py"
spec = importlib.util.spec_from_file_location("kotlin_oracle", ORACLE)
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)


def use(name, col, kind, target, owners=("p/Uses",), **extra):
    return {"use": name, "line": 3, "col": col, "pos": "value", "kind": kind, "target": target,
            "body": True, "owners": list(owners), "callables": [], **extra}


DECLARED = [{"declared": "p/Foo", "kind": "class", "expect": True, "actual": False},
            {"declared": "p/Uses", "kind": "class", "expect": False, "actual": False},
            {"declared": "p/Uses.Companion", "kind": "companion", "expect": False,
             "actual": False, "supertypes": 0}]


def joined(*per_comp):
    """The key of one file, Uses.kt, which every compilation compiles: its records in
    each compilation given."""
    comps = [{"compilation": f"c{i}#0000", "language": "2.3", "sources": [1]}
             for i in range(len(per_comp))]
    raw = {"/src/p/Uses.kt": {f"c{i}#0000": DECLARED + list(rs) for i, rs in enumerate(per_comp)}}
    return [r for r in oracle.join(comps, raw, {"/src/p/Uses.kt": "p/Uses.kt"}) if "use" in r]


def test_an_expect_class_and_its_actual_typealias_are_one_answer():
    # `Foo` is the expect class in one compilation, an actual typealias in another
    [r] = joined([use("Foo", 4, "class", "p/Foo")], [use("Foo", 4, "typealias", "p/Foo")])
    assert (r["kind"], r["target"], r["project"], r["comps"]) == ("type", "p.Foo", True, 2)


def test_a_constructor_and_a_typealias_constructor_of_one_id_are_one_answer():
    [r] = joined([use("Foo", 4, "constructor", "p/Foo")],
                 [use("Foo", 4, "alias-constructor", "p/Foo", **{"class": "q/Impl"})])
    assert (r["kind"], r["target"]) == ("type", "p.Foo")


def test_different_answers_or_a_missing_one_are_split():
    [r] = joined([use("Foo", 4, "constructor", "p/Foo")], [use("Foo", 4, "function", "p/Foo")])
    assert r["kind"] == "split" and r["target"] is None
    [r] = joined([use("Foo", 4, "constructor", "p/Foo")], [])
    assert r["kind"] == "split" and "none" in r["answers"].values()


def test_a_companion_without_supertypes_is_its_class():
    # code in the companion is from the class; the companion is not a type of its own
    [r] = joined([use("Foo", 4, "constructor", "p/Foo", owners=("p/Uses", "p/Uses.Companion"))])
    assert r["from"] == "p.Uses"
    [r] = joined([use("Companion", 4, "companion", "p/Uses.Companion")])
    assert (r["target"], r["project"]) == ("p.Uses", True)


def test_anonymous_objects_and_local_classes_are_in_the_type_around_them():
    [r] = joined([use("Foo", 4, "constructor", "p/Foo", owners=("p/Uses", "<anonymous>", "<local>"))])
    assert r["from"] == "p.Uses"
    [r] = joined([use("Foo", 4, "constructor", "p/Foo", owners=())])
    assert r["from"] is None


def test_member_names_after_a_dot_are_left_out_but_nested_constructors():
    rs = joined([use("x", 4, "member-property", "p/Foo.x", dotted=True),
                 use("Inner", 8, "constructor", "p/Foo.Inner", dotted=True)])
    assert [(r["use"], r["kind"]) for r in rs] == [("Inner", "type")]


def test_a_typealias_is_the_class_it_stands_for_unless_an_expect_class_has_its_id():
    global DECLARED
    keep = DECLARED
    DECLARED = keep + [{"declared": "p/Cash", "kind": "typealias", "expect": False, "actual": False},
                       {"declared": "p/Foo", "kind": "typealias", "expect": False, "actual": True}]
    try:
        [r] = joined([use("Cash", 4, "alias-constructor", "p/Cash", expanded="p/Uses")])
        assert (r["target"], r["alias"], r["project"]) == ("p.Uses", "p.Cash", True)
        [r] = joined([use("Foo", 4, "typealias", "p/Foo", expanded="java/util/Foo")])
        assert (r["target"], r["project"]) == ("p.Foo", True)
    finally:
        DECLARED = keep


def test_a_type_nested_in_a_folded_companion_is_nested_in_its_class():
    types = oracle.Types(DECLARED + [{"declared": "p/Uses.Companion.Serializer", "kind": "object",
                                      "expect": False, "actual": False}])
    assert types.id("p/Uses.Companion.Serializer") == "p.Uses.Serializer"
    assert types.id("p/Uses.Companion") == "p.Uses"
    assert "p.Uses.Serializer" in types.ids


def test_compilations_need_not_agree_on_which_function_a_name_is():
    [r] = joined([use("append", 4, "function", "kotlin/text/append")],
                 [use("append", 4, "member-function", "java/lang/StringBuilder.append")])
    assert r["kind"] == "function"
