"""Kotlin declared relations looked up as the compiler does (issue #7, cases 8 to 12): the
resolver's own lookup, which bodies share. Each test is a form of
bench/kotlin_oracle/review/kt15, whose answers the compiler gives."""

from conftest import extract_source


def _rels(ir, src: str) -> set[tuple[str, str]]:
    return {(r.to, r.via) for r in ir.relations if r.from_ == src and r.evidence is None}


def _body(ir, src: str) -> set[str]:
    return {r.to for r in ir.relations if r.from_ == src and r.evidence == "body"}


def test_an_interface_passes_on_no_nested_type(tmp_path):
    # #11: `N` in a class implementing Face is the package's; a superclass's is inherited
    ir = extract_source(tmp_path, {"shop/F.kt": (
        "package shop\ninterface Face { class N }\nclass N\n"
        "class Impl(val a: N) : Face { fun g(): Any = N() }\n"
        "open class Abs { class M }\nclass M\nclass Sub2(val a: M) : Abs()\n")})
    assert _rels(ir, "shop.Impl") == {("shop.Face", None), ("shop.N", "a")}
    assert _body(ir, "shop.Impl") == {"shop.N"}
    assert ("shop.Abs.M", "a") in _rels(ir, "shop.Sub2")


def test_a_superclass_companions_nested_type_is_not_inherited(tmp_path):
    # #12: Base and its nested types see InComp; a subclass sees the package's
    ir = extract_source(tmp_path, {"shop/C.kt": (
        "package shop\nopen class Base {\n  companion object { class InComp }\n"
        "  val own: InComp? = null\n}\nclass InComp\n"
        "class Sub(val a: InComp) : Base() { fun g(): Any = InComp() }\n")})
    assert ("shop.Base.InComp", "own") in _rels(ir, "shop.Base")
    assert ("shop.InComp", "a") in _rels(ir, "shop.Sub")
    assert _body(ir, "shop.Sub") == {"shop.InComp"}
