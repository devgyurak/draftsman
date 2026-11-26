"""Kotlin declared relations looked up as the compiler does (issue #7, cases 8 to 12): the
resolver's own lookup, which bodies share. Each test is a form of
bench/kotlin_oracle/review/kt15, whose answers the compiler gives."""

from conftest import extract_source


def _rels(ir, src: str) -> set[tuple[str, str]]:
    return {(r.to, r.via) for r in ir.relations if r.from_ == src and r.evidence is None}


def _body(ir, src: str) -> set[str]:
    return {r.to for r in ir.relations if r.from_ == src and r.evidence == "body"}


def test_a_star_import_comes_before_the_default_imports(tmp_path):
    # #8: kotlinx.serialization's Transient and kotlinx.serialization.json's Json, not the
    # default imports kotlin.jvm.Transient and kotlin.js.Json; a project package's Result
    # under `import p.*`, not kotlin.Result
    ir = extract_source(tmp_path, {
        "p/Result.kt": "package p\nclass Result\n",
        "q/A.kt": ("package q\nimport kotlinx.serialization.json.*\nimport p.*\n"
                   "class A(val j: Json, val r: Result)\n")})
    assert "Json" not in {u.raw_type for u in ir.unresolved}
    assert ("p.Result", "r") in _rels(ir, "q.A")


def test_an_import_alias_hides_the_name_from_the_package_and_star_imports(tmp_path):
    # #9: once p.Money is imported as Coin, `Money` is r.Money through `import r.*`
    ir = extract_source(tmp_path, {
        "p/T.kt": "package p\nclass Money\n",
        "r/T.kt": "package r\nclass Money\n",
        "p/Self.kt": ("package p\nimport p.Money as Coin\nimport r.*\n"
                      "class Same(val a: Money, val b: Coin) { fun g(): Any = Money() }\n"),
        "q/H.kt": ("package q\nimport p.*\nimport p.Money as Coin\nimport r.*\n"
                   "class H(val a: Money, val b: Coin, val c: p.Money)\n")})
    assert _rels(ir, "p.Same") == {("r.Money", "a"), ("p.Money", "b")}
    assert _body(ir, "p.Same") == {"r.Money"}
    assert _rels(ir, "q.H") == {("r.Money", "a"), ("p.Money", "b"), ("p.Money", "c")}


def test_a_library_superclass_nested_type_comes_before_the_package(tmp_path):
    # #10: Thread.State, which the table of library types knows
    ir = extract_source(tmp_path, {"shop/T.kt": (
        "package shop\nclass State\nclass T(val s: State) : Thread() { fun f(x: State) {} }\n"
        "class Plain(val s: State)\n")})
    assert not any(to == "shop.State" for to, _ in _rels(ir, "shop.T"))
    assert ("shop.State", "s") in _rels(ir, "shop.Plain")


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


def test_an_import_under_its_own_name_beside_an_alias_still_brings_the_name_in(tmp_path):
    # `import p.Money` beside `import p.Money as Coin`: `Money` is p.Money (kt16)
    ir = extract_source(tmp_path, {
        "p/T.kt": "package p\nclass Money\n",
        "q/B.kt": ("package q\nimport p.Money\nimport p.Money as Coin\n"
                   "class Both(val a: Money, val b: Coin) { fun f(): Any = Money() }\n")})
    assert _rels(ir, "q.Both") == {("p.Money", "a"), ("p.Money", "b")}
    assert _body(ir, "q.Both") == {"p.Money"}


def test_a_library_interfaces_nested_type_is_not_inherited(tmp_path):
    # `Map`'s `Entry` is no member of a class implementing it, nor of a Java class
    # implementing it (`java.util.AbstractMap`), whose own `SimpleEntry` is (kt16)
    ir = extract_source(tmp_path, {"shop/M.kt": (
        "package shop\nclass Entry<K, V>\nclass SimpleEntry<K, V>\n"
        "abstract class MyMap : Map<String, Int> { abstract val first: Entry<String, Int> }\n"
        "abstract class JMap : java.util.AbstractMap<String, Int>() {\n"
        "  abstract val e: SimpleEntry<String, Int>\n  abstract val x: Entry<String, Int>\n"
        "  fun g(): Any = Entry<String, Int>()\n}\n")})
    assert ("shop.Entry", "first") in _rels(ir, "shop.MyMap")
    assert ("shop.Entry", "x") in _rels(ir, "shop.JMap")
    assert ("shop.SimpleEntry", "e") not in _rels(ir, "shop.JMap")
    assert _body(ir, "shop.JMap") == {"shop.Entry"}   # the table no longer hides it


def _decl(ir, src: str) -> set[tuple[str, str, str]]:
    return {(r.kind, r.to.rsplit(".", 1)[-1], r.via) for r in ir.relations
            if r.from_ == src and r.evidence is None}


KT_TYPES = ("package shop\nclass Req\nclass Cfg\nclass Ctx\nclass Job\nclass Box<T>\n"
            "annotation class Api\n")


def _pipe(tmp_path, body: str, extra: str = ""):
    return extract_source(tmp_path, {"shop/T.kt": KT_TYPES, "shop/P.kt": (
        "package shop\n" + extra + "class Pipe {\n" + body + "\n}\n")})


def test_a_function_type_in_parentheses(tmp_path):
    # #9, case 40
    ir = _pipe(tmp_path, "    var cfg: (Cfg.() -> Unit) = {}\n"
                         "    fun filter(block: ((Req) -> Boolean)) {}")
    assert _decl(ir, "shop.Pipe") == {("dependency", "Cfg", "cfg"), ("dependency", "Req", "filter")}


def test_an_alias_of_a_suspend_function_type(tmp_path):
    # #9, case 36: a function type's parameter named like a class names none
    ir = _pipe(tmp_path, "    fun add(h: Handler) {}",
               extra="typealias Handler = suspend (Job: Req) -> Unit\n")
    assert _decl(ir, "shop.Pipe") == {("dependency", "Req", "add")}


def test_context_parameters(tmp_path):
    # #9, case 39: `context(c: Ctx)`, and the older `context(Ctx)`
    ir = _pipe(tmp_path, "    context(c: Ctx)\n    fun run() {}\n    context(Job)\n    fun old() {}")
    assert _decl(ir, "shop.Pipe") == {("dependency", "Ctx", "run"), ("dependency", "Job", "old")}


def test_an_extension_propertys_receiver(tmp_path):
    # #9, case 42
    ir = _pipe(tmp_path, "    private val Box<out Job?>.done: Boolean get() = true")
    assert _decl(ir, "shop.Pipe") == {("dependency", "Box", "done"), ("dependency", "Job", "done")}
